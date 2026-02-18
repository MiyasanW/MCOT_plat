import random
from datetime import timedelta
from django.utils import timezone
from apps.store.models import Product, Equipment, Booking, BookingItem, User

def create_mock_history():
    print("🚀 Starting Mock Data Generation...")

    # 1. Setup User (Staff/Admin)
    admin_user = User.objects.filter(is_superuser=True).first()
    if not admin_user:
        admin_user = User.objects.create_superuser('admin', 'admin@example.com', 'password')

    # 2. Key Product: Sony FX6 Info (The "Hero" Item)
    product_name = "Sony FX6 Cinema Line"
    product, created = Product.objects.get_or_create(
        name=product_name,
        defaults={
            'price': 4500.00,
            'description': 'Full-frame Cinema Camera',
            'is_active': True,
            'quantity': 5
        }
    )
    
    # 3. Specific Equipment with History
    serial_no = "S-FX6-998877"
    equipment, created = Equipment.objects.get_or_create(
        serial_number=serial_no,
        defaults={
            'product': product,
            'asset_tag': 'AST-2024-001',
            'inventory_number': 'CAM-01-05',
            'status': 'available'
        }
    )
    print(f"🎥 Equipment Prepared: {product.name} (SN: {serial_no})")

    # 4. Generate Timeline (Reverse Chronological)
    # List of realistic scenarios
    scenarios = [
        {
            'project': 'Music Video - "Night Drive"',
            'customer': 'GMM Grammy',
            'days_ago': 60,
            'duration': 3,
            'status': 'returned',
            'note': 'สภาพปกติ เรียบร้อยดี',
            'b_status': 'completed'
        },
        {
            'project': 'Documentary - Wild Thailand',
            'customer': 'Thai PBS',
            'days_ago': 45,
            'duration': 7,
            'status': 'returned',
            'note': 'เลนส์มีฝุ่นเล็กน้อย ทำความสะอาดแล้ว',
            'b_status': 'completed'
        },
        {
            'project': 'Commercial - Lazada 11.11',
            'customer': 'Ogilvy Thailand',
            'days_ago': 20,
            'duration': 2,
            'status': 'damaged',
            'note': 'รอยขีดข่วนที่บอดี้ด้านขวา (แจ้งลูกค้าแล้ว + หักมัดจำ)',
            'b_status': 'completed'
        },
        {
            'project': 'Short Film - Thesis',
            'customer': 'BU Student (Napat)',
            'days_ago': 10,
            'duration': 1,
            'status': 'returned',
            'note': None,
            'b_status': 'completed'
        },
        {
            'project': 'Event Coverage - Motor Expo',
            'customer': 'AutoLife Thailand',
            'days_ago': 2,
            'duration': 4,
            'status': 'picked', # Currently active
            'note': None,
            'b_status': 'active'
        }
    ]

    for sc in scenarios:
        start_date = timezone.now() - timedelta(days=sc['days_ago'])
        end_date = start_date + timedelta(days=sc['duration'])
        
        # Create Booking
        booking = Booking.objects.create(
            customer_name=sc['customer'],
            project_name=sc['project'],
            phone=f"08{random.randint(10000000, 99999999)}",
            start_time=start_date,
            end_time=end_date,
            status=sc['b_status'],
            created_by=admin_user,
            total_price=product.price * sc['duration']
        )

        # Assign Item
        BookingItem.objects.create(
            booking=booking,
            product=product,
            quantity=1,
            price_at_booking=product.price,
            equipment=equipment,
            status=sc['status'],
            returned_at=end_date if sc['status'] in ['returned', 'damaged'] else None,
            notes=sc['note'] or ''
        )
        print(f"✅ Added History: {sc['project']}")

    print("✨ Mock Data Generation Complete!")
    print(f"👉 Check ID: {equipment.id}")

create_mock_history()
