import os
import sys
import django
from decimal import Decimal

# Setup Django environment
sys.path.append('/Users/thanandorn/Desktop/MCOT_Rental_Platform')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.store.models import Package, Product, ProductCategory, PackageItem

def run():
    print("Starting OB Package Import...")

    # 1. Create/Get Categories (Lookup by slug to avoid UniqueConstraint error)
    cat_vehicle, _ = ProductCategory.objects.get_or_create(slug="vehicle", defaults={'name': "Production Vehicle"})
    cat_camera, _ = ProductCategory.objects.get_or_create(slug="camera", defaults={'name': "Camera"})
    cat_broadcast, _ = ProductCategory.objects.get_or_create(slug="broadcast", defaults={'name': "Broadcast"})
    cat_sound, _ = ProductCategory.objects.get_or_create(slug="sound", defaults={'name': "Sound"})
    cat_crew, _ = ProductCategory.objects.get_or_create(slug="crew", defaults={'name': "Crew"})

    # 2. Create Products (Components)
    # Note: Prices here are arbitrary placeholders as they are part of a package
    p_ob_van, _ = Product.objects.get_or_create(
        name="OB Van Unit (Standard)",
        defaults={'category': cat_vehicle, 'price': 15000, 'description': "Standard OB Van"}
    )
    p_cam_chain, _ = Product.objects.get_or_create(
        name="Broadcast Camera Chain",
        defaults={'category': cat_camera, 'price': 5000, 'description': "Fiber Camera Chain"}
    )
    p_switcher, _ = Product.objects.get_or_create(
        name="Video Switcher (8-Input)",
        defaults={'category': cat_broadcast, 'price': 8000, 'description': "HD/4K Switcher"}
    )
    p_recorder, _ = Product.objects.get_or_create(
        name="Broadcast Recorder",
        defaults={'category': cat_broadcast, 'price': 3000, 'description': "ProRes/DNxHD Recorder"}
    )
    p_sound, _ = Product.objects.get_or_create(
        name="Audio Mixer Console",
        defaults={'category': cat_sound, 'price': 2000, 'description': "Digital Audio Console"}
    )
    
    # Crew (As Products for Package visibility)
    p_cameraman, _ = Product.objects.get_or_create(
        name="Cameraman",
        defaults={'category': cat_crew, 'price': 2500, 'description': "Professional Operator"}
    )
    p_switch_op, _ = Product.objects.get_or_create(
        name="Switcher Operator",
        defaults={'category': cat_crew, 'price': 3000, 'description': "Technical Director"}
    )
    p_sound_op, _ = Product.objects.get_or_create(
        name="Sound Engineer",
        defaults={'category': cat_crew, 'price': 2500, 'description': "Audio Engineer"}
    )
    p_ccu_op, _ = Product.objects.get_or_create(
        name="CCU Operator",
        defaults={'category': cat_crew, 'price': 2500, 'description': "Color Control Unit Operator"}
    )
    p_asst_cam, _ = Product.objects.get_or_create(
        name="Assistant Cameraman",
        defaults={'category': cat_crew, 'price': 1500, 'description': "Cable/Focus Puller"}
    )

    # 3. Create Packages
    
    # Package 1: OB 3 Cameras (Full Crew) - 45,000
    pkg_full, created = Package.objects.get_or_create(
        name="OB 3-Camera Live Production (Full Crew)",
        defaults={
            'price': Decimal('45000.00'),
            'short_description': "Complete Broadcast Solution for Events & Concerts",
            'description': """
            Full-service Outside Broadcasting (OB) unit with 3 camera chains.
            
            Conditions:
            - Rate for Bangkok & Perimeter
            - Upcountry (<400km): +10,000 THB/Day
            - Upcountry (>400km): +20,000 THB/Day
            - Overtime: Charged per hour after 8 hours.
            """,
            'is_active': True,
            'is_highlight': True
        }
    )
    if not created:
        pkg_full.price = Decimal('45000.00')
        pkg_full.save()

    # Clear existing items to reset
    PackageItem.objects.filter(package=pkg_full).delete()

    # Add Items to Pkg 1
    PackageItem.objects.create(package=pkg_full, product=p_ob_van, quantity=1)
    PackageItem.objects.create(package=pkg_full, product=p_cam_chain, quantity=3)
    PackageItem.objects.create(package=pkg_full, product=p_switcher, quantity=1)
    PackageItem.objects.create(package=pkg_full, product=p_recorder, quantity=1)
    PackageItem.objects.create(package=pkg_full, product=p_cameraman, quantity=3) # 3 Cameramen? Assumption: 1 per cam
    PackageItem.objects.create(package=pkg_full, product=p_switch_op, quantity=1)
    PackageItem.objects.create(package=pkg_full, product=p_sound_op, quantity=1)
    PackageItem.objects.create(package=pkg_full, product=p_ccu_op, quantity=1)


    # Package 2: OB 3 Cameras (Lite Crew) - 35,000
    pkg_lite, created = Package.objects.get_or_create(
        name="OB 3-Camera Live Production (Lite Crew)",
        defaults={
            'price': Decimal('35000.00'),
            'short_description': "Cost-effective Broadcast Setup",
            'description': """
            Standard Outside Broadcasting (OB) unit with 3 camera chains.
            Suitable for smaller events where full crew is not required or provided by client.
            
            Includes: Assistant Cam, Sound, CCU (No main Cameramen).
            
            Conditions:
            - Rate for Bangkok & Perimeter
            - Upcountry (<400km): +10,000 THB/Day
            - Upcountry (>400km): +20,000 THB/Day
            """,
            'is_active': True
        }
    )
    if not created:
        pkg_lite.price = Decimal('35000.00')
        pkg_lite.save()
        
    # Clear existing items
    PackageItem.objects.filter(package=pkg_lite).delete()

    # Add Items to Pkg 2
    PackageItem.objects.create(package=pkg_lite, product=p_ob_van, quantity=1)
    PackageItem.objects.create(package=pkg_lite, product=p_cam_chain, quantity=3)
    PackageItem.objects.create(package=pkg_lite, product=p_switcher, quantity=1)
    PackageItem.objects.create(package=pkg_lite, product=p_asst_cam, quantity=3) 
    PackageItem.objects.create(package=pkg_lite, product=p_sound_op, quantity=1)
    PackageItem.objects.create(package=pkg_lite, product=p_ccu_op, quantity=1)

    print("Successfully imported OB Packages.")

if __name__ == '__main__':
    run()
