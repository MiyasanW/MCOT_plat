import os
import sys
import django
# Add project root to path
sys.path.append('/Users/thanandorn/Desktop/MCOT_Rental_Platform')
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

import json
from datetime import date, timedelta
from django.test import Client
from django.contrib.auth.models import User
from apps.store.models import Product, Studio, Booking

def test_api():
    print("--- Testing Booking API ---")
    
    # 1. Setup User
    username = 'testuser_api'
    password = 'password123'
    if not User.objects.filter(username=username).exists():
        User.objects.create_user(username=username, password=password, email='test@example.com')
        print(f"Created user: {username}")
    
    client = Client()
    login_success = client.login(username=username, password=password)
    if login_success:
        print("✅ Login Successful")
    else:
        print("❌ Login Failed")
        return

    # 2. Get Resources
    product = Product.objects.first()
    studio = Studio.objects.filter(id=2).first()
    
    if not product:
        print("❌ No products found (Run seed_products.py first)")
        return
    
    print(f"Testing with Product: {product.name} (ID: {product.id})")

    # 3. Prepare Payload
    start_date = date.today() + timedelta(days=1)
    end_date = date.today() + timedelta(days=3)
    
    payload = {
        "start": start_date.strftime("%Y-%m-%d"),
        "end": end_date.strftime("%Y-%m-%d"),
        "items": [
            {
                "id": product.id,
                "quantity": 1,
                "type": "product"
            }
        ]
    }
    
    if studio:
        print(f"Adding Studio: {studio.name} (ID: {studio.id})")
        payload["items"].append({
            "id": f"studio_{studio.id}",
            "quantity": 1, 
            "type": "studio"
        })

    # 4. Make Request
    print(f"Sending Payload: {json.dumps(payload, indent=2)}")
    response = client.post(
        '/api/booking/create/',
        data=payload,
        content_type='application/json'
    )
    
    # 5. Verify Response
    if response.status_code == 200:
        data = response.json()
        if data.get('success'):
            booking_id = data.get('booking_id')
            print(f"✅ Booking Created Successfully! ID: {booking_id}")
            
            # Verify DB
            booking = Booking.objects.get(id=booking_id)
            print(f"   - DB Status: {booking.status}")
            print(f"   - Products: {booking.products.count()}")
            print(f"   - Studios: {booking.studios.count()}")
        else:
            print(f"❌ API returned success=False: {data}")
    else:
        print(f"❌ HTTP Error {response.status_code}: {response.content.decode()}")

if __name__ == "__main__":
    test_api()
