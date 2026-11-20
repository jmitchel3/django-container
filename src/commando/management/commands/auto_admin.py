from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import IntegrityError, transaction

from helpers import config


class Command(BaseCommand):
    help = "Create the configured superuser if the database has no superusers."

    def add_arguments(self, parser):
        parser.add_argument(
            "--force",
            action="store_true",
            help="Create the configured superuser or rotate its password even if a superuser exists.",
        )

    def handle(self, *args, **options):
        User = get_user_model()
        users = User.objects
        force = options["force"]
        if not force and users.filter(is_superuser=True).exists():
            self.stdout.write("A superuser already exists.")
            return

        username = User.normalize_username(
            config("DJANGO_ADMIN_USERNAME", default="admin")
        )
        password = config("DJANGO_ADMIN_PASSWORD", default="")
        if not username.strip():
            raise CommandError("DJANGO_ADMIN_USERNAME must contain a username.")
        if not password.strip():
            raise CommandError("DJANGO_ADMIN_PASSWORD must contain a password.")

        target = users.filter(username=username)
        if not target.exists():
            try:
                with transaction.atomic():
                    users.create_superuser(
                        username=username,
                        email=config("DJANGO_ADMIN_EMAIL", default="notset@notset.com"),
                        password=password,
                    )
            except IntegrityError:
                # A second replica may have created the same username first.
                if not target.exists():
                    raise
            else:
                self.stdout.write(
                    self.style.SUCCESS("Created the configured superuser.")
                )
                return

        eligible = target.filter(is_superuser=True, is_staff=True, is_active=True)
        conflict = "The configured username belongs to an account ineligible for admin password rotation."
        if not force:
            if not eligible.exists():
                raise CommandError(conflict)
            self.stdout.write("A superuser already exists.")
            return

        with transaction.atomic():
            # A conditional write locks the eligible account even on SQLite,
            # which doesn't support SELECT FOR UPDATE.
            if not eligible.update(is_active=True):
                raise CommandError(conflict)
            admin = eligible.get()
            admin.set_password(password)
            admin.save(update_fields=["password"])
        self.stdout.write(
            self.style.SUCCESS("Updated the configured superuser's password.")
        )
