import os
import sys
import django
import json
from datetime import date, timedelta
import os
import sys
import django
import json
from datetime import date, timedelta

# Setup Django Environment
sys.path.append('/Users/thanandorn/Desktop/MCOT_Rental_Platform')
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from django.test import Client
from django.urls import reverse
from django.contrib.auth.models import User
from apps.store.models import Product, ProductCategory

def test_create_booking_api():
    print("--- Testing Booking Creation API ---")
    
    # 1. Setup Data
    password = 'testpassword123'
    username = 'test_booker'
    email = 'booker@example.com'
    
    user, created = User.objects.get_or_create(username=username, email=email)
    if created:
        user.set_password(password)
        user.save()
        print(f"Created test user: {username}")
    else:
        print(f"Using existing test user: {username}")
        
    # Ensure a product exists
    category, _ = ProductCategory.objects.get_or_create(name="Test Category", slug="test-cat")
    product, _ = Product.objects.get_or_create(
        name="Test Camera X1",
        defaults={
            'description': 'Test Description',
            'price': 1000,
            'quantity': 5,
            'category': category,
            'is_active': True
        }
    )
    print(f"Test Product: {product.name} (ID: {product.id})")
    
    # 2. Login
    client = Client()
    login_success = client.login(username=username, password=password)
    if not login_success:
        print("❌ Login Failed! Resetting password...")
        user.set_password(password)
        user.save()
        client.login(username=username, password=password)
        
    # 3. Prepare Payload
    start_date = (date.today() + timedelta(days=1)).strftime("%Y-%m-%d")
    end_date = (date.today() + timedelta(days=2)).strftime("%Y-%m-%d")
    
    payload = {
        "items": [
            {"id": product.id, "quantity": 1, "type": "product"}
        ],
        "start": start_date,
        "end": end_date
    }
    
    print(f"sending payload: {json.dumps(payload, indent=2)}")
    
    # 4. Send Request
    url = reverse('store:api_create_booking')
    try:
        response = client.post(
            url, 
            data=json.dumps(payload), 
            content_type='application/json'
        )
        
        print(f"Response Status: {response.status_code}")
        print(f"Response Body: {response.content.decode('utf-8')}")
        
        if response.status_code == 200:
            data = response.json()
            if data['success']:
                print(f"✅ Booking Created Successfully! ID: {data['booking_id']}")
            else:
                print(f"❌ Booking Failed Logic: {data}")
        else:
             print("❌ Request Failed")

    except Exception as e:
        print(f"❌ Exception: {e}")


def test_anonymous_booking():
    print("\n--- Testing Anonymous Booking ---")
    client = Client() # No login
    
    url = reverse('store:api_create_booking')
    
    # Payload (Simplified)
    payload = {
        "items": [], 
        "start": "2026-02-06",
        "end": "2026-02-07"
    }
    
    response = client.post(
        url, 
        data=json.dumps(payload), 
        content_type='application/json'
    )
    
    print(f"Response Status: {response.status_code}")
    if response.status_code == 302:
        print("✅ Correctly redirected to login (302)")
        print(f"Location: {response.url}")
    elif response.status_code == 403:
        print("✅ Correctly returned 403 Forbidden")
    else:
        print(f"❌ Unexpected status: {response.status_code}")


def test_stock_deduction():
    print("\n--- Testing Stock Deduction ---")
    from apps.store.models import Product, ProductCategory
    from apps.store.services.availability import AvailabilityService
    from django.utils import timezone
    
    # 1. Setup
    product = Product.objects.get(name="Test Camera X1")
    initial_qty = product.quantity # Should be 5
    
    start = timezone.now() + timedelta(days=5)
    end = timezone.now() + timedelta(days=6)
    
    # Check Initial Availability
    avail_before = AvailabilityService.get_available_quantity(product, start, end)
    print(f"Availability Before: {avail_before} / {initial_qty}")
    
    # 2. Create Booking via Client (Simulate User)
    client = Client()
    client.login(username='test_booker', password='testpassword123')
    
    payload = {
        "items": [{"id": product.id, "quantity": 2, "type": "product"}],
        "start": start.strftime("%Y-%m-%d"),
        "end": end.strftime("%Y-%m-%d")
    }
    
    url = reverse('store:api_create_booking')
    client.post(url, data=json.dumps(payload), content_type='application/json')
    
    # 3. Check Availability After
    avail_after = AvailabilityService.get_available_quantity(product, start, end)
    print(f"Availability After: {avail_after} / {initial_qty}")
    
    if avail_after == avail_before - 2:
        print("✅ Stock Deduction Verified (Decreased by 2)")
    else:
        print(f"❌ Stock Deduction Failed! Expected {avail_before - 2}, got {avail_after}")

if __name__ == "__main__":
    test_create_booking_api()
    test_anonymous_booking()
    test_stock_deduction()
