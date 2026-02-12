import csv
import re
from decimal import Decimal
import django
import os
import sys

# Setup Django environment
sys.path.append('/Users/thanandorn/Desktop/MCOT_Rental_Platform')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.store.models import Product, ProductCategory, Studio

def get_or_create_category(name_map, item_name):
    # Default Category
    slug = "general"
    name = "General Equipment"

    # Map keywords to slugs
    for keyword, cat_data in name_map.items():
        if keyword.lower() in item_name.lower():
            slug = cat_data['slug']
            name = cat_data['name']
            break
    
    cat, _ = ProductCategory.objects.get_or_create(slug=slug, defaults={'name': name})
    return cat

def parse_price(price_str):
    if not price_str:
        return Decimal('0.00')
    
    # Remove commas and asterisks
    clean_str = price_str.replace(',', '').replace('*', '').strip()
    
    # Handle ranges "1500-2000" -> Take max "2000"
    if '-' in clean_str:
        parts = clean_str.split('-')
        try:
            # Take the last part as it's usually the max price
            clean_str = parts[-1]
        except:
            pass

    # Extract first number found
    match = re.search(r'\d+', clean_str)
    if match:
        return Decimal(match.group())
    return Decimal('0.00')

def run():
    csv_file_path = '/Users/thanandorn/Desktop/MCOT_Rental_Platform/RateCard Equipment.csv'
    
    # Category Keywords Mapping
    category_map = {
        'กล้อง': {'slug': 'camera', 'name': 'Camera'},
        'DSLR': {'slug': 'camera', 'name': 'Camera'},
        'เลนซ์': {'slug': 'lens', 'name': 'Lens'},
        'Monitor': {'slug': 'monitor', 'name': 'Monitor'},
        'Mixer': {'slug': 'sound', 'name': 'Sound'},
        'Switcher': {'slug': 'broadcast', 'name': 'Broadcast'},
        'ไวเรส': {'slug': 'sound', 'name': 'Sound'}, # Wireless Mic/Cam
        'ขาตั้ง': {'slug': 'support', 'name': 'Support (Tripod/Crane)'},
        'เครน': {'slug': 'support', 'name': 'Support (Tripod/Crane)'},
        'ไฟ': {'slug': 'lighting', 'name': 'Lighting'},
        'Stream': {'slug': 'broadcast', 'name': 'Broadcast'},
        'ตัดต่อ': {'slug': 'post-production', 'name': 'Post Production'},
        'Play Out': {'slug': 'broadcast', 'name': 'Broadcast'},
        'CG': {'slug': 'broadcast', 'name': 'Broadcast'},
        'Live': {'slug': 'broadcast', 'name': 'Broadcast'}, # Live U, Live Slow
        'ทีวี': {'slug': 'monitor', 'name': 'Monitor'},
        'จอ': {'slug': 'monitor', 'name': 'Monitor'},
        'Sound': {'slug': 'sound', 'name': 'Sound'},
    }

    print("Starting import...")
    
    with open(csv_file_path, newline='', encoding='utf-8') as csvfile:
        reader = csv.reader(csvfile)
        # Skip header rows (1-3)
        for _ in range(3):
            next(reader)
            
        for row in reader:
            if not row or len(row) < 4:
                continue
                
            seq = row[0]
            item_name = row[1].strip()
            # col 2 is original price, ignore
            price_str = row[3]
            note = row[4] if len(row) > 4 else ""
            
            if not item_name:
                continue

            # Skip OB items (Handled separately as Packages)
            if "ชุดถ่ายทอด OB" in item_name:
                print(f"Skipping OB Item (Package): {item_name}")
                continue

            # Parse Price
            price = parse_price(price_str)

            # --- STUDIO IMPORT ---
            if "ห้องส่ง" in item_name or "Studio" in item_name:
                print(f"Importing Studio: {item_name} - {price}")
                Studio.objects.update_or_create(
                    name=item_name,
                    defaults={
                        'daily_rate': price, # Use price as rate (per queue/day)
                        'description': f"{note} (Rate from CSV: {price_str})"
                    }
                )
                continue

            # --- PRODUCT IMPORT ---
            cat = get_or_create_category(category_map, item_name)
            
            # Special handling for "Machine/Month" or "Week"
            desc_extras = []
            if "/" in price_str:
                desc_extras.append(f"Rate: {price_str}")
            if note:
                desc_extras.append(f"Note: {note}")
            
            full_description = "\n".join(desc_extras) if desc_extras else ""

            print(f"Importing Product: {item_name} ({cat.name}) - {price}")
            
            Product.objects.update_or_create(
                name=item_name,
                defaults={
                    'category': cat,
                    'price': price,
                    'description': full_description,
                    'is_active': True
                }
            )

    print("Import completed.")

if __name__ == '__main__':
    run()
