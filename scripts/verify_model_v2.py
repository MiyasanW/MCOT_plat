import os, django, sys
from decimal import Decimal
from datetime import datetime
from django.utils import timezone

# Setup Django
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from apps.store.models import Booking, Studio, Staff, BookingStudio, BookingStaff, ProductCategory, StaffPosition
from apps.store.services.pricing_service import PricingService

def verify_models_v2():
    print("--- Verifying Model 2.0 (Price Snapshots) ---")
    
    # 1. Setup Master Data
    category, _ = ProductCategory.objects.get_or_create(name="Studio", slug="studio")
    position, _ = StaffPosition.objects.get_or_create(name="Cameraman", base_daily_rate=Decimal("1500.00"))
    
    studio = Studio.objects.create(name="Test Studio A", daily_rate=Decimal("5000.00"))
    staff = Staff.objects.create(name="John Doe", position=position, daily_rate=Decimal("2000.00")) # Specific rate override
    
    print(f"Master Studio Rate: {studio.daily_rate}")
    print(f"Master Staff Rate: {staff.daily_rate}")

    # 2. Create Booking (Today only = 1 Day)
    start = timezone.now()
    end = start # Same day
    booking = Booking.objects.create(
        customer_name="Test Snapshot",
        start_time=start,
        end_time=end
    )
    
    # 3. Add Relations (Standard Way - logic should auto-snapshot)
    # Note: We need to use Manager or create object directly for Through Models to trigger defaults if safe logic isn't in add()
    # Django add() on m2m with through model requires creating through instance manually unless signals used.
    # Let's create manually to simulate rigorous process, or check if we added helper methods.
    # Standard Django M2M with through cannot use booking.studios.add(studio) directly usually.
    
    b_studio = BookingStudio.objects.create(booking=booking, studio=studio) # Should auto-snapshot price
    b_staff = BookingStaff.objects.create(booking=booking, staff=staff) # Should auto-snapshot price
    
    print(f"Snapshot Studio Price: {b_studio.price_at_booking}")
    print(f"Snapshot Staff Rate: {b_staff.daily_rate_at_booking}")
    
    # Validation 1: Check initial calculation (1 Day)
    # Total = 5000 + 2000 = 7000
    total_1 = PricingService.calculate_booking_total(booking)
    print(f"Booking Total (Initial): {total_1:,.2f}")
    assert total_1 == Decimal("7000.00"), "Initial calculation wrong"

    # 4. CHANGE MASTER DATA
    print(">> Changing Master Prices in Database... <<")
    studio.daily_rate = Decimal("99999.00")
    studio.save()
    
    staff.daily_rate = Decimal("500.00")
    staff.save()
    
    # 5. Re-Calculate Booking Total
    total_2 = PricingService.calculate_booking_total(booking)
    print(f"Booking Total (After Master Change): {total_2:,.2f}")
    
    if total_1 == total_2:
        print("✅ SUCCESS: Price integrity maintained! (Snapshot worked)")
    else:
        print("❌ FAILED: Price changed with master data! (Snapshot failed)")

    # Cleanup
    booking.delete()
    studio.delete()
    staff.delete()

if __name__ == "__main__":
    verify_models_v2()
