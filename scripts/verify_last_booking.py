import os
import sys
import django

sys.path.append('/Users/thanandorn/Desktop/MCOT_Rental_Platform')
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from apps.store.models import Booking

def verify():
    print("--- Latest Booking ---")
    booking = Booking.objects.order_by('-id').first()
    if booking:
        print(f"ID: {booking.id}")
        print(f"Customer: {booking.customer_name}")
        print(f"Items: {booking.items.count()}")
        print(f"Status: {booking.status}")
        print(f"Created: {booking.created_at}")
    else:
        print("No bookings found.")

if __name__ == "__main__":
    verify()
