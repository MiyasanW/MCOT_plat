import os
import sys
import django
from decimal import Decimal

# Add project root to path
sys.path.append('/Users/thanandorn/Desktop/MCOT_Rental_Platform')
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from apps.store.models import ProductCategory, Product, Studio

def seed():
    print("--- Seeding Products ---")
    
    # 1. Create Category
    cat, created = ProductCategory.objects.get_or_create(
        name="Cameras",
        slug="cameras"
    )
    if created:
        print(f"Created Category: {cat.name}")
    else:
        print(f"Category already exists: {cat.name}")

    # 2. Create Products
    products = [
        {
            "name": "Sony A7S III",
            "price": Decimal("2500.00"),
            "quantity": 5
        },
        {
            "name": "Canon R5",
            "price": Decimal("3000.00"),
            "quantity": 3
        },
        {
            "name": "Blackmagic Pocket 6K",
            "price": Decimal("2000.00"),
            "quantity": 4
        }
    ]

    for p_data in products:
        product, created = Product.objects.get_or_create(
            name=p_data["name"],
            defaults={
                "category": cat,
                "price": p_data["price"],
                "quantity": p_data["quantity"],
                "is_active": True
            }
        )
        if created:
            print(f"Created Product: {product.name}")
        else:
            print(f"Product already exists: {product.name}")

    print("--- Seeding Complete ---")

if __name__ == "__main__":
    seed()
