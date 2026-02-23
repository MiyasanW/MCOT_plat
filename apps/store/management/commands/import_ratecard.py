import os
import csv
import re
from datetime import timedelta
from django.core.management.base import BaseCommand
from django.conf import settings
from apps.store.models import ProductCategory, Product, StaffPosition, Staff

class Command(BaseCommand):
    help = 'Populate mockup data from RateCard Equipment.csv (Products, Equipment, Studio, Crew)'

    def parse_price(self, price_str):
        if not price_str:
            return 0
        # Extracts the first numeric value from strings like "1,500-2,000", "5000/วัน", "30,000*"
        price_str = price_str.replace(',', '').replace('*', '')
        match = re.search(r'\d+', price_str)
        if match:
            return int(match.group())
        return 0

    def handle(self, *args, **kwargs):
        self.stdout.write("Reading from RateCard Equipment.csv...")
        
        file_path = os.path.join(settings.BASE_DIR, 'RateCard Equipment.csv')
        
        if not os.path.exists(file_path):
            self.stdout.write(self.style.ERROR(f"File not found: {file_path}"))
            return

        # 1. Setup Categories based on the data we observe, using slug as the unique identifier
        cam_cat, _ = ProductCategory.objects.get_or_create(slug="cameras", defaults={"name": "กล้อง (Camera)"})
        lens_cat, _ = ProductCategory.objects.get_or_create(slug="lenses", defaults={"name": "เลนส์ (Lenses)"})
        monitor_cat, _ = ProductCategory.objects.get_or_create(slug="monitors", defaults={"name": "จอมอนิเตอร์ (Monitors)"})
        audio_cat, _ = ProductCategory.objects.get_or_create(slug="audio", defaults={"name": "ระบบเสียง (Audio)"})
        ob_cat, _ = ProductCategory.objects.get_or_create(slug="ob-switcher", defaults={"name": "ระบบถ่ายทอดสด (OB & Switcher)"})
        grip_cat, _ = ProductCategory.objects.get_or_create(slug="grip-lighting", defaults={"name": "อุปกรณ์ประกอบ (Grip & Lighting)"})
        edit_cat, _ = ProductCategory.objects.get_or_create(slug="edit-suites", defaults={"name": "ห้องตัดต่อ (Edit Suites)"})
        studio_cat, _ = ProductCategory.objects.get_or_create(slug="studios", defaults={"name": "สตูดิโอ (Studios)"}) # Treating studio as product for now for rental via cart

        with open(file_path, newline='', encoding='utf-8-sig') as csvfile:
            reader = csv.reader(csvfile)
            next(reader) # Row 1: Heading
            next(reader) # Row 2: Empty
            next(reader) # Row 3: Column Headers

            for row in reader:
                if len(row) < 5 or not row[1].strip():
                    continue

                item_name = row[1].strip()
                
                # Check if it's an extra note row or unrelated row
                if "ต่างจังหวัดระยะทาง" in row[4]:
                    continue  # Skip note continuation lines
                
                # Use raw price column (index 2) or formatted price column (index 3)
                price_str = row[3].strip() if row[3].strip() else row[2].strip()
                price = self.parse_price(price_str)
                notes = row[4].strip()

                if "ช่างภาพ" in item_name and "ช่างเทคนิค" in item_name:
                    continue # Skip footer info

                category = grip_cat # Default
                
                is_studio = False
                is_package = False
                
                if "ห้องส่ง" in item_name:
                    is_studio = True
                elif "ชุดถ่ายทอด" in item_name or "ชุด Live" in item_name or "ระบบ Sound" in item_name:
                    is_package = True
                elif "OB" in item_name.upper() or "SWITCHER" in item_name.upper() or "LIVE" in item_name.upper() or "CG" in item_name.upper() or "PLAY OUT" in item_name.upper():
                    category = ob_cat
                elif "กล้อง" in item_name and not ("เครนกล้อง" in item_name or "ขาตั้งกล้อง" in item_name):
                    category = cam_cat
                elif "เลนซ์" in item_name or "เลนส์" in item_name:
                    category = lens_cat
                elif "MONITOR" in item_name.upper() or "จอทีวี" in item_name:
                    category = monitor_cat
                elif "AUDIO" in item_name.upper() or "ไมค์" in item_name or "SOUND" in item_name.upper():
                    category = audio_cat
                elif "ตัดต่อ" in item_name:
                    category = edit_cat

                if price > 0:
                    description_text = notes if notes else "อุปกรณ์พร้อมสำหรับใช้งานการผลิตรายการ"
                    
                    if is_studio:
                        from apps.store.models import Studio
                        # Ensure price is handled specifically (e.g. rate per queue, we'll map to daily_rate)
                        Studio.objects.update_or_create(
                            name=item_name,
                            defaults={
                                "daily_rate": price,
                                "description": description_text,
                                "turnaround_time": timedelta(hours=2)
                            }
                        )
                    elif is_package:
                        from apps.store.models import Package
                        Package.objects.update_or_create(
                            name=item_name,
                            defaults={
                                "price": price,
                                "description": description_text,
                                "short_description": "แพ็คเกจพร้อมใช้งาน",
                                "is_active": True
                            }
                        )
                    else:
                        Product.objects.update_or_create(
                            name=item_name,
                            defaults={
                                "category": category,
                                "price": price,
                                "late_fee_per_day": price, # ค่าปรับรายวัน = ราคาเช่า 1 วัน
                                "description": description_text,
                                "quantity": 5, # Mock 5 items available for each
                                "is_active": True,
                                "turnaround_time": timedelta(hours=4)
                            }
                        )

        # Let's also add the Crew rates mentioned at the bottom
        sw_pos, _ = StaffPosition.objects.get_or_create(name="กำกับภาพ (SW)", defaults={"base_daily_rate": 3500})
        Staff.objects.get_or_create(name="ช่างภาพ / ช่างเทคนิค ทั่วไป", defaults={"position": StaffPosition.objects.filter(name__icontains="ช่างภาพ").first(), "phone": "-", "daily_rate": 1500, "is_active": True})
        Staff.objects.get_or_create(name="ผู้กำกับภาพระบบ (Switcher)", defaults={"position": sw_pos, "phone": "-", "daily_rate": 3500, "is_active": True})

        self.stdout.write(self.style.SUCCESS('Successfully imported real data from RateCard Equipment.csv!'))
