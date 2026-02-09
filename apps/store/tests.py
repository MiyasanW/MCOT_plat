from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from django.utils import timezone
from apps.store.models import Product, ProductCategory, Booking
from apps.store.services.availability import AvailabilityService
from datetime import timedelta, date
import json

class BookingFlowTests(TestCase):
    def setUp(self):
        # 1. Setup Data for all tests
        self.username = 'test_booker'
        self.password = 'testpassword123'
        self.user = User.objects.create_user(username=self.username, password=self.password)
        
        self.category = ProductCategory.objects.create(name="Test Category", slug="test-cat")
        self.product = Product.objects.create(
            name="Test Camera X1",
            price=1000,
            quantity=5,
            category=self.category,
            is_active=True
        )
        self.client = Client()

    def test_create_booking_success(self):
        """Test API successfully creates a booking for logged in user"""
        self.client.login(username=self.username, password=self.password)
        
        start_date = (date.today() + timedelta(days=1)).strftime("%Y-%m-%d")
        end_date = (date.today() + timedelta(days=2)).strftime("%Y-%m-%d")
        
        payload = {
            "items": [{"id": self.product.id, "quantity": 1, "type": "product"}],
            "start": start_date,
            "end": end_date
        }
        
        url = reverse('store:api_create_booking')
        response = self.client.post(url, data=json.dumps(payload), content_type='application/json')
        
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()['success'])
        self.assertEqual(Booking.objects.count(), 1)
        booking = Booking.objects.first()
        self.assertEqual(booking.customer_name, self.user.username)  # Or full name if set

    def test_anonymous_booking_redirect(self):
        """Test unauthenticated user is redirected"""
        # No login
        
        start_date = (date.today() + timedelta(days=1)).strftime("%Y-%m-%d")
        end_date = (date.today() + timedelta(days=2)).strftime("%Y-%m-%d")
        
        payload = {
            "items": [{"id": self.product.id, "quantity": 1}],
            "start": start_date,
            "end": end_date
        }
        
        url = reverse('store:api_create_booking')
        response = self.client.post(url, data=json.dumps(payload), content_type='application/json')
        
        # Should be 302 Found (Redirect to login)
        self.assertEqual(response.status_code, 302)
        self.assertIn('/accounts/login/', response.url)

    def test_stock_deduction(self):
        """Test availability logic correctly deducts stock"""
        start = timezone.now() + timedelta(days=5)
        end = timezone.now() + timedelta(days=6)
        
        # Initial check
        avail_initial = AvailabilityService.get_available_quantity(self.product, start, end)
        self.assertEqual(avail_initial, 5)
        
        # Create booking for 2 items
        booking = Booking.objects.create(
            customer_name="Test User",
            created_by=self.user,
            start_time=start,
            end_time=end,
            status='approved' # Or 'draft', service logic counts draft too
        )
        from apps.store.models import BookingItem
        BookingItem.objects.create(booking=booking, product=self.product, quantity=2, price_at_booking=1000)
        
        # Check after
        avail_after = AvailabilityService.get_available_quantity(self.product, start, end)
        self.assertEqual(avail_after, 3)

    def test_validate_past_dates(self):
        """Test booking validation prevents past dates (if applicable) or invalid ranges"""
        self.client.login(username=self.username, password=self.password)
        
        # End before Start
        payload = {
            "items": [{"id": self.product.id, "quantity": 1}],
            "start": "2024-02-10",
            "end": "2024-02-09" # Invalid
        }
        
        url = reverse('store:api_create_booking')
        response = self.client.post(url, data=json.dumps(payload), content_type='application/json')
        
        self.assertEqual(response.status_code, 400)
