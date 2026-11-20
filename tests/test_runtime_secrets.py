import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import textwrap
import unittest


ENTRYPOINT = Path(__file__).resolve().parents[1] / "scripts" / "entrypoint.sh"


class RuntimeSecretsTests(unittest.TestCase):
    def setUp(self):
        self.work = Path(self.enterContext(tempfile.TemporaryDirectory()))
        (self.work / "python3").symlink_to(sys.executable)
        (self.work / "python").symlink_to(sys.executable)

    def start(self, *args, **env):
        return subprocess.run(
            [ENTRYPOINT, *args],
            cwd=self.work,
            env={"PATH": f"{self.work}:{os.defpath}", "HOME": str(self.work), **env},
            capture_output=True,
            text=True,
            timeout=10,
        )

    def write_script(self, name, source):
        path = self.work / name
        path.write_text("#!/usr/bin/env python3\n" + textwrap.dedent(source))
        path.chmod(0o755)

    def test_one_off_command_receives_files_and_preserves_arguments_and_exit(self):
        value = "  héllo\n$HOME `pwd` \"quotes\"  "
        secret = self.work / "mounted secret"
        secret.write_bytes(value.encode() + b"\r\n")
        arguments = ["two words", "", "*.py", "$(false)"]
        result = self.start(
            "python", "-c", textwrap.dedent("""
                import json, os, pathlib, sys
                expected = pathlib.Path("mounted secret").read_bytes()[:-2].decode()
                for name in ("DJANGO_SECRET_KEY", "DATABASE_URL", "DJANGO_ADMIN_PASSWORD", "CUSTOM"):
                    assert os.environ[name] == expected
                    assert name + "_FILE" not in os.environ
                assert os.environ["SSL_CERT_FILE"] == "unrelated"
                print(json.dumps(sys.argv[1:]))
                sys.exit(31)
            """), *arguments,
            DJANGO_SECRET_KEY_FILE=str(secret), DATABASE_URL_FILE=str(secret),
            DJANGO_ADMIN_PASSWORD_FILE=str(secret), CUSTOM_FILE=str(secret),
            SECRET_FILE_VARS="CUSTOM", SSL_CERT_FILE="unrelated",
        )
        self.assertEqual(result.returncode, 31, result.stderr)
        self.assertEqual(json.loads(result.stdout), arguments)
        self.assertNotIn(value, result.stderr)

    def test_invalid_sources_stop_before_executing_the_requested_command(self):
        secret = self.work / "secret"
        cases = [
            (None, {}, "DJANGO_SECRET_KEY_FILE"),
            (b"\n", {}, "DJANGO_SECRET_KEY_FILE"),
            (b"fixture\0", {}, "DJANGO_SECRET_KEY_FILE"),
            (b"\xff", {}, "DJANGO_SECRET_KEY_FILE"),
            (b"fixture", {"DJANGO_SECRET_KEY": "direct-fixture"}, "DJANGO_SECRET_KEY_FILE"),
            (b"fixture", {"SECRET_FILE_VARS": "BAD-NAME"}, "SECRET_FILE_VARS"),
            (b"fixture", {"RUNTIME_ENV_PROVIDER": "unknown"}, "RUNTIME_ENV_PROVIDER"),
        ]
        for contents, options, diagnostic in cases:
            with self.subTest(contents=contents, options=options):
                if contents is not None:
                    secret.write_bytes(contents)
                result = self.start("touch", "started", DJANGO_SECRET_KEY_FILE=str(secret), **options)
                self.assertNotEqual(result.returncode, 0)
                self.assertFalse((self.work / "started").exists())
                self.assertIn(diagnostic, result.stderr)
                self.assertNotIn("fixture", result.stderr + result.stdout)

    def install_web_commands(self):
        for executable in ("manage.py", "gunicorn"):
            self.write_script(executable, """
                import os, sys
                from pathlib import Path
                assert os.environ["DJANGO_SECRET_KEY"] == "app-fixture"
                assert "DOPPLER_TOKEN" not in os.environ
                print(Path(sys.argv[0]).name, *sys.argv[1:])
            """)

    def test_web_defaults_run_migrations_then_serve(self):
        self.install_web_commands()
        result = self.start(DJANGO_SECRET_KEY="app-fixture")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.splitlines(), [
            "manage.py migrate --no-input",
            "gunicorn cfehome.wsgi:application -c gunicorn.conf.py --bind [::]:8080",
        ])

    def test_doppler_resolves_token_before_release_steps(self):
        self.install_web_commands()
        token = self.work / "token"
        token.write_bytes(b"service-fixture\n")
        self.write_script("doppler", """
            import os, sys
            args = sys.argv[1:]
            separator = args.index("--")
            assert args[0] == "run" and "--no-fallback" in args[:separator]
            assert os.environ["DOPPLER_TOKEN"] == "service-fixture"
            assert "DOPPLER_TOKEN_FILE" not in os.environ
            os.environ.update(DJANGO_SECRET_KEY="app-fixture", RUN_AUTO_ADMIN="1",
                              RUN_COLLECTSTATIC="1")
            command = args[separator + 1:]
            os.execvp(command[0], command)
        """)
        result = self.start(RUNTIME_ENV_PROVIDER="doppler", DOPPLER_TOKEN_FILE=str(token), PORT="9000")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.splitlines(), [
            "manage.py migrate --no-input",
            "manage.py collectstatic --no-input",
            "manage.py auto_admin",
            "gunicorn cfehome.wsgi:application -c gunicorn.conf.py --bind [::]:9000",
        ])
        self.assertNotIn("fixture", result.stderr)

    def test_doppler_failure_prevents_web_startup(self):
        self.install_web_commands()
        self.write_script("doppler", "raise SystemExit(47)\n")
        result = self.start(RUNTIME_ENV_PROVIDER="doppler", DOPPLER_TOKEN="service-fixture")
        self.assertEqual(result.returncode, 47, result.stderr)
        self.assertEqual(result.stdout, "")
        self.assertNotIn("service-fixture", result.stderr)
