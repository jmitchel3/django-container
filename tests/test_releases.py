import os
import unittest
from contextlib import chdir
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
spec = spec_from_file_location("release", ROOT / ".github/release.py")
release = module_from_spec(spec)
spec.loader.exec_module(release)


class ReleaseTests(unittest.TestCase):
    def test_auto_push_and_recoverable_publication(self):
        with TemporaryDirectory() as directory, chdir(directory), patch.dict(
            os.environ, {"GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1"}
        ):
            git = release.git
            git("init", "--quiet", "--bare", "origin.git")
            git("init", "--quiet", "--initial-branch=main", "project")
            with chdir("project"):
                git("remote", "add", "origin", "../origin.git")
                git("config", "user.name", "Release test")
                git("config", "user.email", "release@example.invalid")
                git("config", "core.hooksPath", str(ROOT / ".githooks"))
                git("commit", "--allow-empty", "-qm", "Historical commit")
                Path(".github").mkdir()
                Path(".github/release.py").touch()
                git("add", ".github")
                git("commit", "-qm", "feat: initial release", "-m", "- First release detail")
                first = git("rev-parse", "HEAD")

                # Simulate a failed GitHub release after the tag and changelog landed.
                with patch.object(release, "publish_notes", side_effect=RuntimeError):
                    with self.assertRaises(RuntimeError):
                        release.main()
                git("fetch", "--quiet", "--tags", "origin")
                self.assertEqual(git("rev-parse", "v0.1.0"), first)

                git("commit", "--allow-empty", "-qm", "Document the settings")
                git("switch", "--quiet", "-c", "feature")
                git("commit", "--allow-empty", "-qm", "feat(web): add a feature")
                git("switch", "--quiet", "main")
                git("merge", "--quiet", "--no-ff", "feature", "-m", "Merge feature")
                self.assertEqual(git("rev-parse", "origin/main"), git("rev-parse", "HEAD"))
                git("commit", "--allow-empty", "-qm", "Change runtime defaults",
                    "-m", "BREAKING CHANGE: A signing key is now required")
                head = git("rev-parse", "HEAD")
                self.assertEqual(git("ls-remote", "origin", "refs/heads/main").split()[0], head)

                with patch.object(release, "publish_notes") as publish:
                    release.main()
                    self.assertEqual([call.args[0] for call in publish.call_args_list],
                                     ["v0.1.0", "v0.1.1", "v0.2.0", "v1.0.0"])
                    git("fetch", "--quiet", "--tags", "origin")
                    metadata = git("rev-parse", "origin/releases")
                    release.main()
                    self.assertEqual(git("rev-parse", "origin/releases"), metadata)
                self.assertEqual(git("rev-parse", "v1.0.0"), head)
                self.assertEqual(git("show", "origin/releases:VERSION"), "1.0.0")
                changelog = git("show", "origin/releases:CHANGELOG.md")
                self.assertEqual(changelog.count("## v"), 4)
                self.assertIn("First release detail", changelog)
                self.assertIn("feat(web): add a feature", changelog)
                self.assertIn("A signing key is now required", changelog)
                self.assertNotIn("Historical commit", changelog)
