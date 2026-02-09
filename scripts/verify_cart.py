import os
import django
from django.conf import settings
from django.test import Client, RequestFactory
from django.urls import reverse

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

def verify_cart():
    print("Verifying Cart Page...")
    client = Client()
    
    # Check if URL exists
    try:
        url = reverse('store:cart')
        print(f"URL for 'store:cart' is: {url}")
    except Exception as e:
        print(f"Error reversing URL: {e}")
        return

    # Get the page
    response = client.get(url)
    
    if response.status_code == 200:
        print("✅ Cart Page returned 200 OK")
    else:
        print(f"❌ Cart Page returned {response.status_code}")
        print(response.content.decode('utf-8')[:500])
        return

    content = response.content.decode('utf-8')
    
    # Check for critical elements
    checks = [
        ('id="cart-container"', "Cart Container"),
        ('onclick="processCheckout()"', "Checkout Button"),
        ('id="empty-cart"', "Empty Cart Message"),
        ('id="start-date"', "Start Date Input"),
        ('id="end-date"', "End Date Input"),
        ('fetch', "JavaScript Fetch API usage"),
        ('localStorage.getItem', "LocalStorage usage")
    ]
    
    for needle, description in checks:
        if needle in content:
            print(f"✅ Found {description}")
        else:
            print(f"❌ Missing {description}")

if __name__ == "__main__":
    verify_cart()
