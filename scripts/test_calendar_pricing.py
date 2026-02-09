from datetime import datetime, timedelta
from django.conf import settings
from django.utils import timezone
import os, django, sys

# Setup Django
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from apps.store.services.pricing_service import PricingService

def test_calendar_pricing():
    print("--- Testing Calendar Day Pricing Logic ---")
    
    # Base Date: Feb 1, 2024
    base_date = datetime(2024, 2, 1, 10, 0, 0) # 10:00 AM
    base_date = timezone.make_aware(base_date)

    scenarios = [
        # 1. Same Day (Morning -> Evening)
        {
            "start": base_date, 
            "end": base_date.replace(hour=18), 
            "expected": 1, 
            "desc": "Same Day (8 hours)"
        },
        # 2. Touch Next Day (Midnight Crossing)
        {
            "start": base_date.replace(hour=23), # Feb 1, 23:00
            "end": base_date.replace(day=2, hour=1), # Feb 2, 01:00
            "expected": 2,
            "desc": "Midnight Check (Feb 1 23:00 -> Feb 2 01:00)"
        },
        # 3. Full 24 Hours (No crossing midnight of NEXT day yet) -> Actually crossing once
        {
            "start": base_date, # Feb 1 10:00
            "end": base_date + timedelta(hours=24), # Feb 2 10:00
            "expected": 2,
            "desc": "Exactly 24 Hours (Feb 1 10:00 -> Feb 2 10:00)"
        },
        # 4. Three Days
        {
            "start": base_date, # Feb 1
            "end": base_date.replace(day=3), # Feb 3
            "expected": 3,
            "desc": "Three Days Span (Feb 1 -> Feb 3)"
        }
    ]

    for s in scenarios:
        days = PricingService.calculate_rental_days(s['start'], s['end'])
        status = "✅ PASS" if days == s['expected'] else f"❌ FAIL (Got {days})"
        print(f"Test: {s['desc']:<40} | Expected: {s['expected']} | Result: {status}")

if __name__ == "__main__":
    test_calendar_pricing()
