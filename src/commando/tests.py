from io import StringIO
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase, override_settings


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"])
class AutoAdminTests(TestCase):
    def run_command(self, *args, **values):
        output = StringIO()

        # Use only test credentials, regardless of the developer's dotenv files.
        def config(key, default=None):
            return values.get(key, default)

        with patch("commando.management.commands.auto_admin.config", config):
            call_command("auto_admin", *args, stdout=output, stderr=output)
        return output.getvalue()

    def test_bootstrap_runs_once_and_preserves_the_original_password(self):
        credentials = {"DJANGO_ADMIN_PASSWORD": " nontrivial passphrase "}
        log = self.run_command(**credentials)
        log += self.run_command(DJANGO_ADMIN_PASSWORD="replacement")
        admin = get_user_model().objects.get(username="admin")
        self.assertTrue(admin.is_staff and admin.is_superuser and admin.is_active)
        self.assertTrue(admin.check_password(credentials["DJANGO_ADMIN_PASSWORD"]))
        self.assertNotIn(credentials["DJANGO_ADMIN_PASSWORD"].strip(), log)
        self.assertNotIn("replacement", log)

    def test_blank_password_cannot_create_an_account(self):
        for credentials in (
            {},
            {"DJANGO_ADMIN_PASSWORD": ""},
            {"DJANGO_ADMIN_PASSWORD": " \t "},
        ):
            with self.subTest(credentials=credentials), self.assertRaisesMessage(
                CommandError, "DJANGO_ADMIN_PASSWORD"
            ):
                self.run_command(**credentials)
        self.assertFalse(get_user_model().objects.exists())

    def test_force_rotates_the_target_superuser_password_only(self):
        users = get_user_model().objects
        users.create_superuser("other", password="keep")
        self.run_command(
            "--force",
            DJANGO_ADMIN_PASSWORD="before",
            DJANGO_ADMIN_EMAIL="admin@example.com",
        )
        with patch(
            "django.contrib.auth.password_validation.password_changed"
        ) as changed:
            log = self.run_command("--force", DJANGO_ADMIN_PASSWORD="after")
        changed.assert_called_once_with("after", users.get(username="admin"))
        admin = users.get(username="admin")
        self.assertTrue(admin.check_password("after"))
        self.assertEqual(admin.email, "admin@example.com")
        self.assertTrue(users.get(username="other").check_password("keep"))
        self.assertNotIn("after", log)

    def test_existing_regular_or_disabled_accounts_remain_untouched(self):
        users = get_user_model().objects
        for staff, superuser, active, flags in (
            (False, False, True, []),
            (False, False, True, ["--force"]),
            (True, True, False, ["--force"]),
            (False, True, True, ["--force"]),
        ):
            with self.subTest(
                staff=staff, superuser=superuser, active=active, flags=flags
            ):
                user = users.create_user(
                    "admin",
                    password="original",
                    is_staff=staff,
                    is_superuser=superuser,
                    is_active=active,
                )
                with self.assertRaises(CommandError):
                    self.run_command(*flags, DJANGO_ADMIN_PASSWORD="replacement")
                user.refresh_from_db()
                self.assertTrue(user.check_password("original"))
                self.assertEqual(
                    (user.is_staff, user.is_superuser, user.is_active),
                    (staff, superuser, active),
                )
                user.delete()
