import os
import sys
import django

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.store.models import Product

try:
    p = Product.objects.get(name__icontains="Canon R5")
    print(f"Product: {p.name}")
    print(f"Total Quantity (Stock): {p.quantity}")
except Product.DoesNotExist:
    print("Canon R5 not found")
except Exception as e:
    print(f"Error: {e}")
