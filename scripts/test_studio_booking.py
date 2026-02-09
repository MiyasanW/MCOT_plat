import os
import sys
import json
import django
from django.test import Client
from datetime import date, timedelta

# Add project root to path
sys.path.append('/Users/thanandorn/Desktop/MCOT_Rental_Platform')
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from apps.store.models import Studio, Booking
from django.contrib.auth.models import User

def test_booking():
    print("--- Testing Studio Booking API ---")
    
    # 1. Setup Data
    studio = Studio.objects.first()
    if not studio:
        print("❌ No studio found. Run seed_studio.py first.")
        return

    # Create dummy user if needed (API requires login)
    user, created = User.objects.get_or_create(username='testuser')
    if created:
        user.set_password('password')
        user.save()

    client = Client()
    client.force_login(user)

    # 2. Prepare Payload
    start_date = (date.today() + timedelta(days=1)).strftime("%Y-%m-%d")
    end_date = (date.today() + timedelta(days=2)).strftime("%Y-%m-%d")
    
    payload = {
        "start": start_date,
        "end": end_date,
        "items": [
            {
                "id": f"studio_{studio.id}",
                "type": "studio",
                "quantity": 1
            }
        ]
    }

    # 3. Call API
    print(f"Sending payload: {payload}")
    response = client.post(
        '/api/booking/create/', 
        data=payload, 
        content_type='application/json'
    )

    # 4. Verify Result
    if response.status_code == 200:
        print("✅ API returned 200 OK")
        data = response.json()
        print(f"Response: {data}")
        
        booking_id = data.get('booking_id')
        if booking_id:
            booking = Booking.objects.get(id=booking_id)
            if booking.studios.filter(id=studio.id).exists():
                print("✅ Booking verified in DB: Studio is attached")
            else:
                print("❌ Booking created but Studio NOT attached")
    else:
        print(f"❌ API Error {response.status_code}: {response.content.decode('utf-8')}")

if __name__ == "__main__":
    test_booking()
