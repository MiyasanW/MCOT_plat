import os
import sys
import django
from django.test import Client

# Add project root to path
sys.path.append('/Users/thanandorn/Desktop/MCOT_Rental_Platform')
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

def verify():
    client = Client()
    
    print("--- Verifying Studio Pages ---")
    
    # Check Studio List Page
    try:
        response = client.get('/studios/')
        if response.status_code == 200:
            print("✅ Studio List Page (/studios/) returned 200 OK")
        else:
            print(f"❌ Studio List Page returned {response.status_code}")
    except Exception as e:
        print(f"❌ Error checking Studio List Page: {e}")

    # Check Studio Detail Page (ID 2 exists)
    try:
        response = client.get('/studios/2/')
        if response.status_code == 200:
             print("✅ Studio Detail Page (/studios/2/) returned 200 OK")
        else:
             print(f"❌ Studio Detail Page returned {response.status_code}")
             
        # Check non-existent studio
        response = client.get('/studios/999/')
        if response.status_code == 404:
             print("✅ Search for non-existent studio returned 404 (Expected)")
        else:
             print(f"❌ Search for non-existent studio returned {response.status_code}")
             
    except Exception as e:
        print(f"❌ Error checking Studio Detail Page: {e}")

if __name__ == "__main__":
    verify()
