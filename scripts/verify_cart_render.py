import os
import sys
import django
from django.test import Client
from django.urls import reverse

sys.path.append('/Users/thanandorn/Desktop/MCOT_Rental_Platform')
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

def verify_cart_render():
    print("--- Verifying Cart Page Rendering ---")
    client = Client()
    
    # Needs login? The view logic didn't enforce it, but let's check.
    # Actually, apps.store.views.cart doesn't seem to have @login_required based on my memory, 
    # but I should check. Even if it doesn't, it's public.
    
    try:
        url = reverse('store:cart')
        print(f"Testing URL: {url}")
        response = client.get(url)
        
        if response.status_code == 200:
            print("✅ Cart Page returned 200 OK")
            # Check for critical elements
            content = response.content.decode('utf-8')
            if 'Shopping Cart' in content and 'processCheckout()' in content:
                 print("✅ Vital elements (Header, JS) found")
            else:
                 print("⚠️ Vital elements missing")
        else:
            print(f"❌ Cart Page failed with {response.status_code}")
            print(response.content.decode('utf-8')[:500])
            
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    verify_cart_render()
