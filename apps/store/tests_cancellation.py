from django.test import TestCase, Client
from django.contrib.auth.models import User
from apps.store.models import Booking, Product, ProductCategory
from apps.store.services.booking_service import BookingService
from django.utils import timezone
from datetime import timedelta

class BookingCancellationTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='customer', password='password123')
        self.staff = User.objects.create_user(username='staff', password='password123', is_staff=True)
        
        self.cat = ProductCategory.objects.create(name="Test Cat", slug="test-cat")
        self.product = Product.objects.create(name="Test Prod", price=100, quantity=10, category=self.cat)
        
        # Create a booking
        self.booking = Booking.objects.create(
            created_by=self.user,
            customer_name="Test Customer",
            phone="0123456789",
            start_time=timezone.now(),
            end_time=timezone.now() + timedelta(days=1),
            status='draft'
        )

    def test_customer_can_cancel_draft(self):
        """Customer should be able to cancel a draft booking."""
        BookingService.cancel_booking(self.booking.id, self.user)
        self.booking.refresh_from_db()
        self.assertEqual(self.booking.status, 'cancelled')

    def test_customer_cannot_cancel_pending(self):
        """Customer should NOT be able to cancel a pending booking (quotation sent)."""
        self.booking.status = 'pending'
        self.booking.save()
        
        with self.assertRaises(ValueError):
            BookingService.cancel_booking(self.booking.id, self.user)
        
        self.booking.refresh_from_db()
        self.assertEqual(self.booking.status, 'pending')

    def test_staff_can_cancel_pending(self):
        """Staff should still be able to cancel a pending booking."""
        self.booking.status = 'pending'
        self.booking.save()
        
        BookingService.cancel_booking(self.booking.id, self.staff)
        self.booking.refresh_from_db()
        self.assertEqual(self.booking.status, 'cancelled')
