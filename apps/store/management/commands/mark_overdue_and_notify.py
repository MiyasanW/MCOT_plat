"""
Management command: หาใบจองที่เกินวันคืนแล้ว ตั้ง status เป็น overdue และแจ้งเตือน Staff
รันผ่าน cron อย่างน้อยวันละครั้ง (เช่น 00:05)
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from apps.store.models import Booking
from apps.store.services.notification_service import NotificationService


class Command(BaseCommand):
    help = 'Mark active/approved bookings past end_time as overdue and notify staff'

    def handle(self, *args, **options):
        now = timezone.now()
        to_mark = Booking.objects.filter(
            status__in=['active', 'approved'],
            end_time__lt=now
        )
        count = 0
        for booking in to_mark:
            booking.status = 'overdue'
            booking.save(update_fields=['status'])
            try:
                NotificationService.send_notification(booking, 'overdue')
            except Exception as e:
                self.stdout.write(self.style.WARNING(f'Notification failed for #{booking.id}: {e}'))
            count += 1
            self.stdout.write(self.style.WARNING(f'Booking #{booking.id} marked overdue (end was {booking.end_time})'))
        self.stdout.write(self.style.SUCCESS(f'Marked {count} booking(s) as overdue and notified staff.'))
