import os
import sys
import django
from decimal import Decimal

# Add project root to path
sys.path.append('/Users/thanandorn/Desktop/MCOT_Rental_Platform')
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from apps.store.models import Studio

from datetime import timedelta

def seed():
    print("--- Seeding Studio ---")
    if not Studio.objects.exists():
        Studio.objects.create(
            name="Grand Studio A",
            description="Large broadcasting studio with green screen and control room.",
            daily_rate=Decimal('15000.00'),
            turnaround_time=timedelta(hours=2)
        )
        print("✅ Created 'Grand Studio A'")
    else:
        print("ℹ️ Studios already exist")

if __name__ == "__main__":
    seed()
