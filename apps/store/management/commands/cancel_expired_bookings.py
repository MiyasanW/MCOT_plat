from django.core.management.base import BaseCommand
from django.utils import timezone
from apps.store.models import Booking

class Command(BaseCommand):
    help = 'Cancel bookings that have expired (unpaid after 24 hours)'

    def handle(self, *args, **kwargs):
        now = timezone.now()
        expired_bookings = Booking.objects.filter(
            status__in=['pending', 'draft'],
            payment_status='unpaid',
            expires_at__lt=now
        )

        count = 0
        for booking in expired_bookings:
            booking.status = 'cancelled'
            booking.save()
            count += 1
            self.stdout.write(self.style.WARNING(f'Cancelled Booking #{booking.id} (Expired)'))

        self.stdout.write(self.style.SUCCESS(f'Successfully cancelled {count} expired bookings'))
