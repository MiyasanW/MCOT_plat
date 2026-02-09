
import os
import django
from django.conf import settings
from django.template.loader import render_to_string
from django.utils import timezone

import sys
sys.path.append('/Users/thanandorn/Desktop/MCOT_Rental_Platform')

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.store.models import Product, ProductCategory

def test_render():
    try:
        # Create Dummy Context
        products = Product.objects.all()[:5]
        categories = ProductCategory.objects.all()
        
        context = {
            'products': products,
            'categories': categories,
            'selected_start_date': timezone.now().date(),
            'selected_end_date': timezone.now().date(),
        }
        
        # Render
        print("Rendering store/catalog.html...")
        rendered = render_to_string('store/catalog.html', context)
        
        # Check for literal tags
        if "{{ product.price" in rendered:
            print("FAILURE: Found literal {{ product.price }} in output!")
            # Print snippet
            idx = rendered.find("{{ product.price")
            print(rendered[idx-50:idx+100])
        else:
            print("SUCCESS: Template rendered variables correctly.")
            # Print sample price
            if "฿" in rendered:
                idx = rendered.find("฿")
                print("Sample Price Render search:", rendered[idx:idx+20])

    except Exception as e:
        print(f"ERROR: {e}")

if __name__ == "__main__":
    test_render()
