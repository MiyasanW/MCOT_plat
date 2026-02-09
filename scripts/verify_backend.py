import os
import django
import sys
from datetime import timedelta
from decimal import Decimal

# Setup Django Environment
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from django.utils import timezone
from django.contrib.auth.models import User
from apps.store.models import Product, Studio, Booking, BookingItem
from apps.store.services.availability import AvailabilityService
from apps.store.services.pricing_service import PricingService

def run_verification():
    print("\n" + "="*50)
    print("🚀 STARTING BACKEND ROBUSTNESS VERIFICATION")
    print("="*50 + "\n")

    # 1. SETUP DATA
    print("Step 1: Setting up Test Data...")
    user, _ = User.objects.get_or_create(username="tester")
    
    # Create Product (Camera) - Qty 2
    camera, _ = Product.objects.get_or_create(
        name="Test Camera Sony A7IV",
        defaults={'price': Decimal('1000.00'), 'quantity': 2, 'category': 'camera'}
    )
    # Ensure fresh state
    camera.quantity = 2
    camera.save()
    
    # Create Studio - Qty 1 (Implicit by resource)
    studio, _ = Studio.objects.get_or_create(
        name="Grand Studio",
        defaults={'daily_rate': Decimal('5000.00')}
    )
    
    # Clear old bookings for clean test
    Booking.objects.filter(customer_name__startswith="Test").delete()
    print("✅ Test Data Ready: Camera (Qty: 2), Studio (Qty: 1)\n")

    # 2. DEFINING TIMEFRAMES
    now = timezone.now()
    tomorrow_start = now + timedelta(days=1)
    tomorrow_end = now + timedelta(days=2) # 1 Day Rental
    overlap_start = now + timedelta(days=1, hours=2)
    overlap_end = now + timedelta(days=1, hours=6)

    # 3. TEST SCENARIO A: Standard Booking (Success)
    print("Step 2: Testing Standard Booking (Should Succeed)...")
    booking1 = Booking.objects.create(
        customer_name="Test User A",
        created_by=user,
        start_time=tomorrow_start,
        end_time=tomorrow_end,
        status='approved' # Active booking
    )
    BookingItem.objects.create(booking=booking1, product=camera, quantity=1, price_at_booking=camera.price)
    
    # Verify Stock
    remaining = AvailabilityService.get_available_quantity(camera, tomorrow_start, tomorrow_end)
    print(f"   -> Booking Created. Camera Remainder: {remaining} (Expected: 1)")
    if remaining == 1:
        print("✅ SUCCESS: Stock deducted correctly.")
    else:
        print(f"❌ FAIL: Stock mismatch. Got {remaining}")

    # 4. TEST SCENARIO B: Pricing Calculation
    print("\nStep 3: Testing Pricing Logic (PricingService)...")
    # 1 Day * 1000 = 1000
    total = PricingService.calculate_booking_total(booking1)
    print(f"   -> Calculated Total: {total:,.2f} (Expected: 1,000.00)")
    if total == 1000:
        print("✅ SUCCESS: Pricing Logic is correct.")
    else:
        print(f"❌ FAIL: Pricing mismatch. Got {total}")

    # 5. TEST SCENARIO C: Overbooking (Should Fail)
    print("\nStep 4: Testing Overbooking Protection...")
    # Try to book 2 Cameras (Only 1 left)
    is_avail, msg = AvailabilityService.check_availability(camera, tomorrow_start, tomorrow_end, 2)
    print(f"   -> Requesting 2 Cameras (1 Available). Result: {is_avail}")
    if not is_avail:
        print(f"✅ SUCCESS: Prevented Overbooking correctly. Message: {msg}")
    else:
        print("❌ FAIL: System allowed overbooking!")
        
    # 6. TEST SCENARIO D: Studio Conflict (Resource Overlap)
    print("\nStep 5: Testing Resource Conflict (Studio)...")
    # Book Studio for User A
    booking1.studios.add(studio) 
    
    # User B tries to book overlapping time
    is_valid, conflict = AvailabilityService.check_resource_overlap('studios', studio, overlap_start, overlap_end)
    print(f"   -> Checking Studio Availability for overlap time. Result Valid: {is_valid}")
    if not is_valid:
        print(f"✅ SUCCESS: Detected Studio Conflict with Booking #{conflict.id}")
    else:
        print("❌ FAIL: Failed to detect studio conflict!")

    print("\n" + "="*50)
    print("🏁 VERIFICATION COMPLETE")
    print("="*50)

if __name__ == "__main__":
    try:
        run_verification()
    except Exception as e:
        import traceback
        traceback.print_exc()
