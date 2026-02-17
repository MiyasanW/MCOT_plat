import os
import django
from django.utils import timezone
from datetime import timedelta

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from django.contrib.auth.models import User
from apps.store.models import Booking, Product, BookingItem, Staff

def create_dummy():
    user = User.objects.filter(is_superuser=True).first()
    if not user:
        print("No superuser found.")
        return

    product = Product.objects.first()
    if not product:
        print("No product found.")
        return

    staff = Staff.objects.first() # Get any staff for coordinator

    # Create Booking
    booking = Booking.objects.create(
        customer_name="Admin Test",
        project_name="Test Project Dashboard",
        start_time=timezone.now() + timedelta(days=1),
        end_time=timezone.now() + timedelta(days=3),
        status='pending',
        created_by=user,
        coordinator=staff
    )

    # Add Item
    BookingItem.objects.create(
        booking=booking,
        product=product,
        quantity=1,
        price_at_booking=product.price
    )
    
    print(f"Created Booking #{booking.id} for user {user.username} with Coordinator {staff.name if staff else 'None'}")

if __name__ == "__main__":
    create_dummy()
