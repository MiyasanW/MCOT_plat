import os
import django
import sys
from decimal import Decimal

# Setup Django environment
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.store.models import Product, ProductCategory, Studio

def seed_ratecard():
    print("🚀 Starting Rate Card Seeding...")

    # --- 1. Categories ---
    categories = {
        'Camera': 'กล้อง',
        'Lens': 'เลนส์',
        'Monitor': 'มอนิเตอร์',
        'Audio': 'เสียง',
        'Lighting': 'ไฟ',
        'Support': 'อุปกรณ์เสริม/ขาตั้ง',
        'System': 'ระบบ (Live/Switching)',
        'Post Production': 'Post Production',
        'Vehicles': 'รถ OB', # Keep for completeness, though moved to Packages mostly
    }
    
    cat_objs = {}
    for key, name in categories.items():
        slug = key.lower().replace(' ', '-')
        # 1. Try to get by name first (to avoid unique constraint violation on name)
        try:
            cat = ProductCategory.objects.get(name=key)
            # Update slug if needed
            if cat.slug != slug:
                cat.slug = slug
                cat.save()
            print(f"   Found Category by Name: {key}")
        except ProductCategory.DoesNotExist:
            # 2. If not found by name, try retrieve by slug or create
            cat, created = ProductCategory.objects.update_or_create(
                slug=slug,
                defaults={'name': key}
            )
            print(f"   {'Created' if created else 'Found'} Category by Slug: {key}")
        
        cat_objs[key] = cat

    # --- 2. Products (Equipment & Services) ---
    # Format: (Name, Price, CategoryKey, Description/Note)
    products_data = [
        # Cameras
        ("Big Camera", 5000, "Camera", "กล้องใหญ่"),
        ("Big Camera + CCU + Remote", 7500, "Camera", "กล้องใหญ่พร้อม CCU และ Remote"),
        ("Small Camera", 1500, "Camera", "กล้องเล็ก (Range 1500-2000)"),
        ("DSLR Camera", 700, "Camera", "กล้อง DSLR (Range 700-1500)"),
        
        # Lenses
        ("Lens Size 40", 10000, "Lens", "เลนส์ขนาด 40"), # Rate card says 15000->10000? Using lower bound or exact? Image says 15000/10000. Let's use 10000 based on '10,000' col.
        ("Lens Size 60", 15000, "Lens", "เลนส์ขนาด 60"), 
        ("Lens Size 72", 20000, "Lens", "เลนส์ขนาด 72"),
        ("DSLR Lens", 200, "Lens", "เลนส์ DSLR (Range 200-800)"),

        # Monitors
        ("Monitor 14-17 inch", 1000, "Monitor", "จอมอนิเตอร์ขนาด 14-17 นิ้ว"),
        ("Monitor 20-27 inch", 2000, "Monitor", "จอมอนิเตอร์ขนาด 20-27 นิ้ว"),
        ("TV 40-55 inch + Stand", 2000, "Monitor", "จอทีวี 40-55 นิ้ว พร้อมขาตั้ง (Range 2000-2500)"),

        # Audio / Video Switching
        ("Audio Mixer 8-12 CH", 2000, "Audio", "มิกเซอร์เสียง 8-12 ช่อง"),
        ("Video Switcher 8 I/P", 5000, "System", "Video Switcher 8 Inputs"),
        ("Wireless Mic", 1000, "Audio", "ไมค์ไวเรส (ต่อตัว/วัน)"),
        ("Wireless Camera", 2000, "System", "ไวเรสกล้อง"),

        # Support / Lighting
        ("Big Tripod", 5000, "Support", "ขาตั้งกล้องใหญ่ (ต่อวัน)"),
        ("Lighting Set", 300, "Lighting", "อุปกรณ์ไฟแสง (ต่อชุด)"),
        ("Crane (Studio)", 10000, "Support", "เครนในห้องส่ง (10000/8 ชั่วโมง)"),
        ("Crane (Camera/Jib)", 30000, "Support", "เครนกล้อง (30,000/สัปดาห์ ไม่รวมคน)"),

        # Systems / Streaming
        ("Live Stream Set", 5000, "System", "ชุด Live Stream"),
        ("Live U", 15000, "System", "Live U (ต่อวัน)"),
        ("Live Slow", 10000, "System", "เครื่องทำภาพช้า (Live Slow)"),
        ("Play Out", 4000, "System", "เครื่อง Play Out"),
        ("CG", 5000, "System", "Computer Graphics (CG)"),
        
        # Sound Systems
        ("Sound System (Seminar)", 25000, "Audio", "ระบบ Sound สัมมนา (Range 25000-30000)"),
        ("Sound System (PA)", 35000, "Audio", "ระบบ Sound PA"),

        # Post Production Services
        ("Editing Mac", 5000, "Post Production", "เครื่องตัดต่อ MAC (5000/เดือน)"),
        ("Editing PC", 3000, "Post Production", "เครื่องตัดต่อ PC (3000/เดือน)"),
    ]

    print("\n--- Seeding Products ---")
    for name, price, cat_key, desc in products_data:
        prod, created = Product.objects.update_or_create(
            name=name,
            defaults={
                'price': Decimal(price),
                'category': cat_objs.get(cat_key),
                'description': desc,
                'is_active': True,
                # Default image placeholder if none
                # 'image': ... 
            }
        )
        print(f"   {'Created' if created else 'Updated'} Product: {name} - ฿{price}")

    # --- 3. Studios ---
    # Format: (Name, Price)
    studios_data = [
        ("Studio 5", 60000),
        ("Studio 7", 30000),
        ("Studio 3", 40000), # Extrapolated from Image 'ห้องส่ง 3' = 40000/คิว
    ]

    print("\n--- Seeding Studios ---")
    for name, price in studios_data:
        studio, created = Studio.objects.update_or_create(
            name=name,
            defaults={
                'daily_rate': Decimal(price),
                'description': f"{name} (Standard Rate)",
            }
        )
        print(f"   {'Created' if created else 'Updated'} Studio: {name} - ฿{price}")

    print("\n✅ Rate Card Seeding Complete!")

if __name__ == '__main__':
    seed_ratecard()
