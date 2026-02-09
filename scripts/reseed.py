import os, django, sys
from django.contrib.auth import get_user_model

# Setup Django
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from apps.store.models import ProductCategory, StaffPosition, Studio, Staff, Product

def reseed_database():
    print("--- Reseeding Database ---")
    
    # 1. Create Superuser
    User = get_user_model()
    if not User.objects.filter(username="admin").exists():
        User.objects.create_superuser('admin', 'admin@example.com', 'password')
        print("✅ Superuser 'admin' created (password: password)")
    
    # 2. Create Categories
    cats = [
        ('Camera', 'camera'),
        ('Lens', 'lens'),
        ('Lighting', 'lighting'),
        ('Sound', 'sound'),
        ('Vehicle', 'vehicle'),
        ('Grip', 'grip'),
    ]
    for name, slug in cats:
        ProductCategory.objects.get_or_create(name=name, slug=slug)
    print(f"✅ Created {len(cats)} Product Categories")
    
    # 3. Create Staff Positions
    positions = [
        ('Cameraman', 1500.00),
        ('Driver', 1000.00),
        ('Editor', 2000.00),
        ('Technician', 1200.00),
    ]
    for name, rate in positions:
        StaffPosition.objects.get_or_create(name=name, base_daily_rate=rate)
    print(f"✅ Created {len(positions)} Staff Positions")
    
    print("--- Reseed Complete ---")

if __name__ == "__main__":
    reseed_database()
