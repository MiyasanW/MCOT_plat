from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from apps.store.models import Profile


class Command(BaseCommand):
    help = "Create missing Profile rows for users who do not have one yet."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show how many profiles are missing without creating them.",
        )

    def handle(self, *args, **options):
        user_model = get_user_model()
        missing_users = user_model.objects.filter(profile__isnull=True).order_by("id")
        missing_count = missing_users.count()

        if options["dry_run"]:
            self.stdout.write(
                self.style.WARNING(
                    f"[DRY RUN] Missing profiles: {missing_count} user(s)."
                )
            )
            return

        created = 0
        for user in missing_users.iterator():
            Profile.objects.get_or_create(user=user)
            created += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Backfill complete: created {created} profile(s)."
            )
        )
