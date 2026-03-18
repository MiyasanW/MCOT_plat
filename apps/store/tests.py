from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from django.utils import timezone
from django.core.cache import cache
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
            "end": end_date,
            "phone": "0812345678"
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

    def test_create_booking_missing_product_returns_400(self):
        """Stale cart IDs should return a user-facing validation error, not system error."""
        self.client.login(username=self.username, password=self.password)

        start_date = (date.today() + timedelta(days=1)).strftime("%Y-%m-%d")
        end_date = (date.today() + timedelta(days=2)).strftime("%Y-%m-%d")

        payload = {
            "items": [{"id": 999999, "quantity": 1, "type": "product"}],
            "start": start_date,
            "end": end_date,
            "phone": "0812345678"
        }

        url = reverse('store:api_create_booking')
        response = self.client.post(url, data=json.dumps(payload), content_type='application/json')

        self.assertEqual(response.status_code, 400)
        self.assertFalse(response.json()['success'])
        self.assertIn('ไม่พบสินค้า', response.json()['message'])
        self.assertNotIn('System Error', response.json()['message'])

    def test_package_availability(self):
        """Test package availability checks component products correctly"""
        from apps.store.models import Package, PackageItem
        
        # Create a package
        package = Package.objects.create(
            name="Test Bundle",
            price=2000,
            is_active=True
        )
        
        # Add products to package (Need 2 of Product A)
        PackageItem.objects.create(
            package=package,
            product=self.product,
            quantity=2
        )
        
        start = timezone.now() + timedelta(days=5)
        end = timezone.now() + timedelta(days=6)
        
        # Initially, product has 5 in stock. Package needs 2. 
        # Requesting 1 package = needs 2 products. Avail: 5 >= 2 => True
        is_avail, msg = AvailabilityService.check_package_availability(package, start, end, requested_quantity=1)
        self.assertTrue(is_avail)
        
        # Requesting 3 packages = needs 6 products. Avail: 5 < 6 => False
        is_avail, msg = AvailabilityService.check_package_availability(package, start, end, requested_quantity=3)
        self.assertFalse(is_avail)
        
        # Create a booking that consumes 4 of Product A
        booking = Booking.objects.create(
            customer_name="Test User 2",
            created_by=self.user,
            start_time=start,
            end_time=end,
            status='approved'
        )
        from apps.store.models import BookingItem
        BookingItem.objects.create(booking=booking, product=self.product, quantity=4, price_at_booking=1000)
        
        # Now product has 1 left in stock. Package needs 2.
        # Requesting 1 package = needs 2. Avail: 1 < 2 => False
        is_avail, msg = AvailabilityService.check_package_availability(package, start, end, requested_quantity=1)
        self.assertFalse(is_avail)

    def test_create_booking_with_empty_package_succeeds(self):
        """Package without PackageItem should still be bookable as standalone item."""
        from apps.store.models import Package

        self.client.login(username=self.username, password=self.password)

        package = Package.objects.create(
            name="Standalone Package",
            price=5000,
            is_active=True,
        )

        start_date = (date.today() + timedelta(days=1)).strftime("%Y-%m-%d")
        end_date = (date.today() + timedelta(days=2)).strftime("%Y-%m-%d")

        payload = {
            "items": [{"id": f"pkg_{package.id}", "quantity": 1, "type": "package"}],
            "start": start_date,
            "end": end_date,
            "phone": "0812345678"
        }

        url = reverse('store:api_create_booking')
        response = self.client.post(url, data=json.dumps(payload), content_type='application/json')

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()['success'])

    def test_create_booking_idempotent_request_id(self):
        self.client.login(username=self.username, password=self.password)

        start_date = (date.today() + timedelta(days=1)).strftime("%Y-%m-%d")
        end_date = (date.today() + timedelta(days=2)).strftime("%Y-%m-%d")

        payload = {
            "items": [{"id": self.product.id, "quantity": 1, "type": "product"}],
            "start": start_date,
            "end": end_date,
            "phone": "0812345678",
            "request_id": "checkout-req-12345",
        }

        url = reverse('store:api_create_booking')
        response1 = self.client.post(url, data=json.dumps(payload), content_type='application/json')
        response2 = self.client.post(url, data=json.dumps(payload), content_type='application/json')

        self.assertEqual(response1.status_code, 200)
        self.assertEqual(response2.status_code, 200)
        self.assertTrue(response1.json()['success'])
        self.assertTrue(response2.json()['success'])
        self.assertEqual(response1.json()['booking_id'], response2.json()['booking_id'])
        self.assertEqual(Booking.objects.count(), 1)

    def test_booking_create_status_returns_created_booking(self):
        self.client.login(username=self.username, password=self.password)

        start_date = (date.today() + timedelta(days=1)).strftime("%Y-%m-%d")
        end_date = (date.today() + timedelta(days=2)).strftime("%Y-%m-%d")
        request_id = "checkout-status-created-1"

        payload = {
            "items": [{"id": self.product.id, "quantity": 1, "type": "product"}],
            "start": start_date,
            "end": end_date,
            "phone": "0812345678",
            "request_id": request_id,
        }

        create_url = reverse('store:api_create_booking')
        create_response = self.client.post(create_url, data=json.dumps(payload), content_type='application/json')
        self.assertEqual(create_response.status_code, 200)
        booking_id = create_response.json()['booking_id']

        status_url = reverse('store:api_booking_create_status')
        status_response = self.client.get(status_url, {'request_id': request_id})
        self.assertEqual(status_response.status_code, 200)
        self.assertTrue(status_response.json()['success'])
        self.assertTrue(status_response.json()['created'])
        self.assertEqual(status_response.json()['booking_id'], booking_id)

    def test_booking_create_status_returns_processing_when_lock_exists(self):
        self.client.login(username=self.username, password=self.password)

        request_id = "checkout-status-processing-1"
        lock_key = f"booking_create_lock:{self.user.id}:{request_id}"
        cache.set(lock_key, 1, timeout=30)
        try:
            status_url = reverse('store:api_booking_create_status')
            status_response = self.client.get(status_url, {'request_id': request_id})
            self.assertEqual(status_response.status_code, 200)
            self.assertTrue(status_response.json()['success'])
            self.assertFalse(status_response.json()['created'])
            self.assertTrue(status_response.json()['processing'])
        finally:
            cache.delete(lock_key)
