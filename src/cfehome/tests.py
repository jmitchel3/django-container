import os
import runpy
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch

from decouple import Config
from django.core.exceptions import ImproperlyConfigured

from helpers.dotenv import loader


class ConfigurationTests(TestCase):
    def test_runtime_and_local_overrides_preserve_other_dotenv_defaults(self):
        with TemporaryDirectory() as root:
            project_dir = Path(root)
            (project_dir / ".env").write_text("COLOR=red\nCOUNT=42\n")
            (project_dir / ".env.local").write_text("COLOR=blue\n")
            with patch.object(loader, "PROJECT_DIR", project_dir):
                config = loader.get_config()

        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(config("COLOR"), "blue")
            self.assertEqual(config("COUNT", cast=int), 42)
            os.environ["COLOR"] = "green"
            self.assertEqual(config("COLOR"), "green")

    def load_settings(self, **environment):
        # Exercise the settings module without reading the developer's .env.
        with patch.dict(os.environ, environment, clear=True), patch("helpers.config", Config({})):
            return runpy.run_path(
                str(Path(__file__).with_name("settings.py")), run_name="cfehome._test_settings"
            )

    def test_signing_key_required_in_production(self):
        for environment in ({}, {"DJANGO_SECRET_KEY": "  "}):
            with self.subTest(environment=environment):
                with self.assertRaisesRegex(ImproperlyConfigured, "DJANGO_SECRET_KEY"):
                    self.load_settings(**environment)
        self.assertEqual(self.load_settings(DJANGO_SECRET_KEY="test-key")["SECRET_KEY"], "test-key")
        self.assertTrue(self.load_settings(DJANGO_DEBUG="1")["SECRET_KEY"])

    def test_railway_uses_the_services_own_domains(self):
        settings = self.load_settings(
            DJANGO_SECRET_KEY="test-key",
            RAILWAY_PUBLIC_DOMAIN="example.up.railway.app",
            RAILWAY_PRIVATE_DOMAIN="example.railway.internal",
            DJANGO_ALLOWED_HOSTS="custom.example",
            DJANGO_CSRF_TRUSTED_ORIGINS="https://frontend.example",
        )
        self.assertCountEqual(settings["ALLOWED_HOSTS"], [
            "custom.example", "localhost", "127.0.0.1", "[::1]", "healthcheck.railway.app",
            "example.up.railway.app", "example.railway.internal",
        ])
        self.assertCountEqual(settings["CSRF_TRUSTED_ORIGINS"], [
            "https://frontend.example", "https://example.up.railway.app",
        ])
