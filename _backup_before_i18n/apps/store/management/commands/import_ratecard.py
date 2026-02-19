
import csv
import re
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.utils.text import slugify
from apps.store.models import Product, ProductCategory, Studio, ProductionVehicle

class Command(BaseCommand):
    help = 'Imports equipment data from RateCard Equipment.csv'

    def handle(self, *args, **options):
        file_path = 'RateCard Equipment.csv'
        
        self.stdout.write(self.style.SUCCESS(f'Starting import from {file_path}...'))

        # 1. Create Categories
        categories = {
            'Camera': ['กล้อง'],
            'Lens': ['เลนซ์'],
            'Monitor': ['Monitor', 'จอทีวี'],
            'Switcher': ['Mixer', 'Switcher'],
            'Lighting': ['ไฟ'],
            'Post Production': ['ตัดต่อ', 'Play Out', 'CG', 'Live Slow'],
            'Audio': ['Sound', 'ไมค์'],
            'Transmission': ['Live U', 'Live Stream'],
            'Support': ['ขาตั้ง', 'เครน'],
            'Vehicle': ['OB'], # Special category for Vehicles
            'General': []
        }
        
        cat_objects = {}
        for cat_name in categories.keys():
            slug = slugify(cat_name)
            cat, created = ProductCategory.objects.get_or_create(
                name=cat_name,
                defaults={'slug': slug}
            )
            cat_objects[cat_name] = cat
            if created:
                self.stdout.write(f'Created Category: {cat_name}')

        # 2. Read CSV
        with open(file_path, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            # Skip header items (Line 1-3)
            next(reader) # Line 1
            next(reader) # Line 2
            next(reader) # Line 3 (Headers)

            count_product = 0
            count_studio = 0
            
            for row in reader:
                if not row or len(row) < 4:
                    continue

                # Columns: Order, Item Name, Old Price, Service Rate, Note
                # Index: 0, 1, 2, 3, 4
                
                raw_name = row[1].strip()
                raw_price = row[3].strip()
                note = row[4].strip() if len(row) > 4 else ""

                if not raw_name:
                    continue

                # Parse Price
                price = self.parse_price(raw_price)
                if price is None:
                    # Some rows might be sub-headers or empty
                    continue

                # --- Mapping Logic ---
                
                # Case 1: Studio (ห้องส่ง)
                if "ห้องส่ง" in raw_name:
                    Studio.objects.update_or_create(
                        name=raw_name,
                        defaults={
                            'daily_rate': price,
                            'description': note
                        }
                    )
                    count_studio += 1
                    self.stdout.write(f'Imported Studio: {raw_name} ({price})')
                    continue

                # Case 2: Vehicle (OB) -> Product + Vehicle Category
                if "OB" in raw_name or "รถ" in raw_name:
                    product, created = Product.objects.update_or_create(
                        name=raw_name,
                        defaults={
                            'category': cat_objects['Vehicle'],
                            'price': price,
                            'description': note,
                            'is_active': True,
                            'quantity': 1 
                        }
                    )
                    self.stdout.write(f'Imported Vehicle: {raw_name} ({price})')
                    count_product += 1
                    continue

                # Case 3: Standard Product
                # Determine Category
                assigned_cat = cat_objects['General']
                for cat_key, keywords in categories.items():
                    for kw in keywords:
                        if kw in raw_name:
                            assigned_cat = cat_objects[cat_key]
                            break
                    if assigned_cat != cat_objects['General']:
                        break
                
                Product.objects.update_or_create(
                    name=raw_name,
                    defaults={
                        'category': assigned_cat,
                        'price': price,
                        'description': note,
                        'is_active': True,
                        'quantity': 5 # Default quantity
                    }
                )
                count_product += 1
                self.stdout.write(f'Imported Product: {raw_name} ({price}) - {assigned_cat.name}')

        self.stdout.write(self.style.SUCCESS(f'Successfully imported {count_product} products and {count_studio} studios.'))


    def parse_price(self, price_str):
        """
        Parses price string like "1,500-2,000" or "45,000*" to Decimal.
        Returns None if invalid.
        """
        if not price_str:
            return None

        # Cleaning
        clean_str = price_str.replace(',', '').replace('*', '').strip()
        
        # Handle "30,000/สัปดาห์" -> Take 30000
        clean_str = re.split(r'/', clean_str)[0].strip() # Take first part before slash

        # Handle Ranges "1500-2000" -> Take Max (2000)
        if '-' in clean_str:
            parts = clean_str.split('-')
            try:
                # Filter out empty strings
                valid_parts = [p.strip() for p in parts if p.strip()]
                if not valid_parts:
                    return None
                # Return the highest value
                return Decimal(max([float(p) for p in valid_parts]))
            except ValueError:
                return None
        
        try:
            return Decimal(clean_str)
        except:
            return None
