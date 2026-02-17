from django.test import TransactionTestCase, Client
from django.contrib.auth.models import User
from apps.store.models import Product, ProductCategory, Booking
from datetime import date, timedelta
import json
import concurrent.futures
import time

class BookingConcurrencyTests(TransactionTestCase):
    # Use TransactionTestCase to test database transactions/locking
    
    def setUp(self):
        # Create User
        self.user = User.objects.create_user(username='tester', password='password123')
        self.client.login(username='tester', password='password123')

        # Create Category & Product
        self.cat = ProductCategory.objects.create(name="Camera", slug="camera")
        self.product = Product.objects.create(
            name="Limited Camera",
            price=1000,
            quantity=1, # Only 1 in stock
            category=self.cat,
            is_active=True
        )
        
        self.booking_url = '/api/booking/create/'
        
        self.payload = {
            "items": [{"id": self.product.id, "quantity": 1, "type": "product"}],
            "start": "2024-03-01",
            "end": "2024-03-02",
            "project_name": "Test Project",
            "phone": "0812345678"
        }

    def test_overselling_sequential(self):
        """Test simple sequential overselling (Book 1 then Book another)"""
        print("\n--- Test 1: Sequential Overselling ---")
        
        # 1. First Booking -> Should Success
        response1 = self.client.post(self.booking_url, json.dumps(self.payload), content_type='application/json')
        print(f"Booking 1: {response1.status_code}")
        self.assertEqual(response1.status_code, 200)
        
        # 2. Second Booking (Same dates) -> Should Fail
        response2 = self.client.post(self.booking_url, json.dumps(self.payload), content_type='application/json')
        print(f"Booking 2: {response2.status_code}")
        self.assertEqual(response2.status_code, 409) # 409 Conflict (or 400 depending on implementation)
        self.assertIn("สินค้าบางรายการถูกจองตัดหน้า", response2.json()['message'])

    def test_race_condition(self):
        """Test race condition using threads"""
        print("\n--- Test 2: Race Condition (Concurrent) ---")
        
        # We need a fresh product for this test to avoid interference
        product_race = Product.objects.create(
            name="Race Camera",
            price=1000,
            quantity=1, 
            category=self.cat,
            is_active=True
        )
        
        payload_race = {
            "items": [{"id": product_race.id, "quantity": 1, "type": "product"}],
            "start": "2024-04-01",
            "end": "2024-04-02",
            "project_name": "Race Project",
            "phone": "0999999999"
        }

        # Function to be executed by threads
        # Note: We need separate DB connections for threads ideally, 
        # but Django Client in TransactionTestCase handles this somewhat. 
        # However, standard Django Test Client is synchronous.
        # To truly test concurrency, we need to artificially inject delay in the View?
        # Or rely on the fact that threads will hit the server. 
        # Since we use 'manage.py test', it uses a test DB. 
        # Running threads inside a test case is tricky because of transaction isolation.
        
        # ACTUALLY: The best way to test DB locking in Django TestCase is hard.
        # But we can try firing requests.
        
        results = []
        
        def make_request():
            # Create a new client per thread to simulate distinct sessions/connections?
            # Actually standard client shares cookies.
            c = Client()
            c.login(username='tester', password='password123')
            return c.post(self.booking_url, json.dumps(payload_race), content_type='application/json')

        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            # Submit 2 requests effectively "at once"
            futures = [executor.submit(make_request) for _ in range(2)]
            for future in concurrent.futures.as_completed(futures):
                results.append(future.result())

        # Check results
        status_codes = [r.status_code for r in results]
        print(f"Race Results: {status_codes}")
        
        # One must vary (200) and one must fail (409)
        self.assertTrue(200 in status_codes)
        self.assertTrue(409 in status_codes)
        self.assertEqual(Booking.objects.filter(items__product=product_race).count(), 1)
