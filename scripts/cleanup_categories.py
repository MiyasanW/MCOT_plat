import os
import sys
import django

sys.path.append('/Users/thanandorn/Desktop/MCOT_Rental_Platform')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.store.models import ProductCategory

def run():
    print("Starting Category Cleanup...")

    # 1. Merge Duplicates (Source -> Target)
    merges = {
        'Cameras': 'Camera',
        'Lenses': 'Lens',
        'Vehicles': 'Vehicle',
        'Audio': 'Sound',
        'Grip & Support': 'Support',
        'Test Category': 'General', 
    }

    for source_name, target_name in merges.items():
        try:
            source = ProductCategory.objects.filter(name=source_name).first()
            if not source:
                continue
                
            target, _ = ProductCategory.objects.get_or_create(
                slug=target_name.lower().replace(' ', '-'),
                defaults={'name': target_name}
            )
            
            print(f"Merging '{source.name}' ({source.product_set.count()} items) -> '{target.name}'")
            
            # Move products
            source.product_set.update(category=target)
            
            # Delete source
            source.delete()
        except Exception as e:
            print(f"Error merging {source_name}: {e}")

    # 2. Rename for Clarity/Consistency
    renames = {
        'Monitor': 'Monitors', # Plural for consistent UI? Or keep singular?
        # Actually, let's stick to Singular as "Camera", "Lens" are standard in rental
        # User output showed "Cameras" in sidebar, maybe they prefer Plural?
        # Let's standardise to Singular for now as per "Lens", "Camera" existing ones.
        # But wait, "Lenses" sounds better than "Lens". "Cameras" better than "Camera".
        # Let's switch EVERYTHING to Plural for better UX?
        # User input sidebar had "Cameras", "Lenses".
        # Let's go Plural.
    }
    
    # Actually, allow me to re-evaluate "Singular vs Plural".
    # "Camera" is a category. "Cameras" is the list.
    # Most e-commerce uses Plural (Cameras, Lenses).
    # I will standardise to Plural.

    final_map = {
        'Camera': 'Cameras',
        'Lens': 'Lenses',
        'Vehicle': 'Vehicles',
        'Sound': 'Audio & Sound',
        'Lighting': 'Lighting',
        'Monitor': 'Monitors',
        'Broadcast': 'Broadcast',
        'Support': 'Grip & Support',
        'Crew': 'Crew',
        'Post Production': 'Post Production',
        'General': 'General Equipment',
        'Studio': 'Studio', # Should be removed if empty?
    }

    for current_name, new_name in final_map.items():
        try:
            cat = ProductCategory.objects.filter(name=current_name).first()
            if cat:
                cat.name = new_name
                cat.save()
                print(f"Renamed '{current_name}' -> '{new_name}'")
        except:
            pass
            
    # 3. Remove Empty Categories
    for cat in ProductCategory.objects.all():
        if cat.product_set.count() == 0:
            print(f"Deleting empty category: {cat.name}")
            cat.delete()
            
    print("Cleanup Complete.")

if __name__ == '__main__':
    run()
