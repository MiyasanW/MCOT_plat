from apps.store.models import Product, Equipment

def add_more_products():
    print("🚀 Adding more mock products...")

    products_data = [
        {"name": "Canon EOS R5", "price": 1500, "qty": 3},
        {"name": "Aputure LS 1200d Pro", "price": 2000, "qty": 2},
        {"name": "Sony FE 24-70mm GM II", "price": 800, "qty": 5},
        {"name": "Sennheiser EW 100 G4", "price": 500, "qty": 4},
        {"name": "DJI Ronin RS3 Pro", "price": 1200, "qty": 2},
        {"name": "Blackmagic ATEM Mini Pro", "price": 1000, "qty": 1},
    ]

    for p_data in products_data:
        product, created = Product.objects.get_or_create(
            name=p_data['name'],
            defaults={
                'price': p_data['price'],
                'description': 'Mock Description',
                'is_active': True,
                'quantity': p_data['qty']
            }
        )
        
        # Create at least one serial number for each
        Equipment.objects.get_or_create(
            serial_number=f"SN-{p_data['name'][:3].upper()}-001",
            defaults={
                'product': product,
                'asset_tag': f"AST-{p_data['name'][:3].upper()}-001",
                'inventory_number': f"INV-{p_data['name'][:3].upper()}-001",
                'status': 'available'
            }
        )
        print(f"✅ Added: {product.name}")

    print("✨ More products added successfully!")

add_more_products()
