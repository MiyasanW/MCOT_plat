import random
from datetime import timedelta
from django.utils import timezone
from apps.store.models import Equipment, Booking, BookingItem, User, Product

def populate_real_db():
    print("🚀 Starting History Population for REAL DB...")

    # 1. Get Admin User
    admin_user = User.objects.filter(is_superuser=True).first()
    if not admin_user:
        print("⚠️ No Admin user found! Creating one...")
        admin_user = User.objects.create_superuser('admin', 'admin@example.com', 'password')

    # 2. Get All Real Equipment
    all_equipment = Equipment.objects.all()
    count = all_equipment.count()
    
    if count == 0:
        print("❌ No Equipment found in REAL DB!")
        print("   -> Please add some equipment first via Admin Panel.")
        return

    print(f"✅ Found {count} existing equipment items.")

    # 3. Define Mock Scenarios
    scenarios = [
        {'project': 'MV - Rockstar', 'customer': 'Yupp!', 'status': 'returned', 'note': 'คืนครบ'},
        {'project': 'Series - Hormones', 'customer': 'Nadao', 'status': 'returned', 'note': 'เลนส์เป็นรอย (ปรับ 500)'},
        {'project': 'Event - Big Mountain', 'customer': 'GMM', 'status': 'damaged', 'note': 'ขาตั้งหัก'},
        {'project': 'Wedding - K.Aum', 'customer': 'Freelance', 'status': 'returned', 'note': None},
        {'project': 'News - Politics', 'customer': 'Voice TV', 'status': 'picked', 'note': 'กำลังใช้งาน'},
    ]

    # 4. Inject History to Each Item
    for eq in all_equipment:
        # 50% chance to have history
        if random.random() > 0.1: 
            print(f"   -> Adding history to: {eq.product.name} ({eq.serial_number})")
            
            # Add 1-3 bookings per item
            for _ in range(random.randint(1, 4)):
                sc = random.choice(scenarios)
                days_ago = random.randint(5, 60)
                duration = random.randint(1, 5)
                
                start_time = timezone.now() - timedelta(days=days_ago)
                end_time = start_time + timedelta(days=duration)
                
                # Create Booking
                booking = Booking.objects.create(
                    customer_name=sc['customer'],
                    project_name=sc['project'],
                    phone='0812345678',
                    start_time=start_time,
                    end_time=end_time,
                    status='completed' if sc['status'] != 'picked' else 'active',
                    created_by=admin_user,
                    total_price=eq.product.price * duration
                )

                # Create BookingItem (History Record)
                BookingItem.objects.create(
                    booking=booking,
                    product=eq.product,
                    quantity=1,
                    price_at_booking=eq.product.price,
                    equipment=eq,
                    status=sc['status'],
                    returned_at=end_time if sc['status'] in ['returned', 'damaged'] else None,
                    notes=sc['note']
                )

    print("✨ Real DB Population Complete!")

populate_real_db()
