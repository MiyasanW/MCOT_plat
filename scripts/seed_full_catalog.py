import os
import sys
import django
from decimal import Decimal

# Add project root to path
sys.path.append(os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from apps.store.models import ProductCategory, Product, Studio

def seed():
    print("--- Seeding Full Professional Catalog ---")
    
    # 1. Define Categories
    categories = {
        "cameras": "Cameras",
        "lenses": "Lenses",
        "lighting": "Lighting",
        "audio": "Audio",
        "grip": "Grip & Support"
    }
    
    cat_objs = {}
    for slug, name in categories.items():
        cat, created = ProductCategory.objects.update_or_create(
            slug=slug,
            defaults={"name": name}
        )
        cat_objs[slug] = cat
        print(f"Category: {name} ({'Created' if created else 'Updated'})")

    # 2. Define Products with Rich HTML Descriptions
    products = [
        # --- CAMERAS ---
        {
            "name": "Arri Alexa 35",
            "category": "cameras",
            "price": "35000.00",
            "quantity": 2,
            "description": """
            <ul class="list-disc pl-5 space-y-1 text-gray-400">
                <li><strong>Sensor:</strong> Super 35 ARRI ALEV 4 CMOS</li>
                <li><strong>Dynamic Range:</strong> 17 Stops</li>
                <li><strong>Resolution:</strong> 4.6K up to 120 fps</li>
                <li><strong>Mount:</strong> LPL (PL adapter included)</li>
                <li><strong>Native ISO:</strong> 800 / 3200 (Dual Gain)</li>
            </ul>
            <p class="mt-4">The new gold standard for digital cinematography. Features Reveal Color Science and the highest dynamic range of any digital camera.</p>
            """
        },
        {
            "name": "Sony Venice 2 8K",
            "category": "cameras",
            "price": "28000.00",
            "quantity": 2,
            "description": """
            <ul class="list-disc pl-5 space-y-1 text-gray-400">
                <li><strong>Sensor:</strong> Full Frame 8.6K CMOS</li>
                <li><strong>Resolution:</strong> 8640 x 5760</li>
                <li><strong>ISO:</strong> Dual Base 800 / 3200</li>
                <li><strong>Internal ND:</strong> 8-stop motorized</li>
                <li><strong>Recording:</strong> X-OCN XT / ST / LT</li>
            </ul>
            <p class="mt-4">Sony's flagship cinema camera with internal X-OCN recording and interchangeable sensor blocks.</p>
            """
        },
        {
            "name": "Red V-Raptor XL 8K VV",
            "category": "cameras",
            "price": "22000.00",
            "quantity": 3,
            "description": """
            <ul class="list-disc pl-5 space-y-1 text-gray-400">
                <li><strong>Sensor:</strong> Vista Vision 8K Global Shutter</li>
                <li><strong>Frame Rate:</strong> 120 fps at 8K 17:9</li>
                <li><strong>Dynamic Range:</strong> 17+ Stops</li>
                <li><strong>Codecs:</strong> REDCODE RAW HQ/MQ/LQ</li>
            </ul>
            <p class="mt-4">The ultimate multi-format system. High speed, high resolution, and global shutter in an XL production-ready body.</p>
            """
        },
        {
            "name": "Sony FX6",
            "category": "cameras",
            "price": "4500.00",
            "quantity": 8,
            "description": """
            <ul class="list-disc pl-5 space-y-1 text-gray-400">
                <li><strong>Sensor:</strong> Full-Frame 4K Back-illuminated Exmor R</li>
                <li><strong>Sensitivity:</strong> ISO 800 / 12800 (cinematic matches FX9/Venice)</li>
                <li><strong>AF:</strong> Fast Hybrid AF with Eye-AF</li>
                <li><strong>Weight:</strong> 0.89 kg (Body only)</li>
            </ul>
            <p class="mt-4">Compact, lightweight, and approved for Netflix 4K originals. Perfect for documentaries and run-and-gun.</p>
            """
        },
        {
            "name": "Blackmagic Pocket 6K Pro",
            "category": "cameras",
            "price": "2000.00",
            "quantity": 10,
            "description": """
            <ul class="list-disc pl-5 space-y-1 text-gray-400">
                <li><strong>Sensor:</strong> Super 35 HDR Sensor</li>
                <li><strong>Mount:</strong> Canon EF</li>
                <li><strong>ND Filters:</strong> Built-in 2, 4, 6 stop</li>
                <li><strong>Display:</strong> 1500 nit Tilt Screen</li>
            </ul>
            <p class="mt-4">A portable powerhouse featuring Gen 5 Color Science and built-in ND filters.</p>
            """
        },

        # --- LENSES ---
        {
            "name": "Cooke S7/i Full Frame Plus Set (6 Lenses)",
            "category": "lenses",
            "price": "45000.00",
            "quantity": 1,
            "description": """
            <ul class="list-disc pl-5 space-y-1 text-gray-400">
                <li><strong>Focal Lengths:</strong> 18, 25, 32, 50, 75, 100mm</li>
                <li><strong>Aperture:</strong> T2.0 across range</li>
                <li><strong>Coverage:</strong> Vista Vision / Full Frame</li>
                <li><strong>Look:</strong> The classic 'Cooke Look'</li>
            </ul>
            <p class="mt-4">Designed to cover the newest large format cinema sensors up to the full sensor area of the RED Weapon 8K.</p>
            """
        },
        {
            "name": "Arri Signature Prime Set (6 Lenses)",
            "category": "lenses",
            "price": "55000.00",
            "quantity": 1,
            "description": """
            <ul class="list-disc pl-5 space-y-1 text-gray-400">
                <li><strong>Mount:</strong> LPL Mount</li>
                <li><strong>Aperture:</strong> T1.8</li>
                <li><strong>Character:</strong> Warm, organic skin tones with crisp details</li>
                <li><strong>Features:</strong> LDS-2 Data System</li>
            </ul>
            <p class="mt-4">Modern lenses offering a timeless look. Warm skin tones, open shadows, and crisp blacks.</p>
            """
        },
        {
            "name": "DZOFilm Pictor Zoom 20-55mm T2.8",
            "category": "lenses",
            "price": "1500.00",
            "quantity": 4,
            "description": """
            <ul class="list-disc pl-5 space-y-1 text-gray-400">
                <li><strong>Focal Range:</strong> 20-55mm</li>
                <li><strong>Aperture:</strong> T2.8 Constant</li>
                <li><strong>Format:</strong> Super 35</li>
                <li><strong>Mount:</strong> PL / EF Interchangeable</li>
            </ul>
            <p class="mt-4">Versatile zoom lens with minimal breathing and parifocal design.</p>
            """
        },

        # --- LIGHTING ---
        {
            "name": "Arri SkyPanel S60-C",
            "category": "lighting",
            "price": "3500.00",
            "quantity": 6,
            "description": """
            <ul class="list-disc pl-5 space-y-1 text-gray-400">
                <li><strong>Output:</strong> ~2000W Tungsten Equivalent</li>
                <li><strong>Color:</strong> CCT 2800K - 10000K + RGBW</li>
                <li><strong>Control:</strong> DMX, Art-Net, Wireless DMX</li>
                <li><strong>Size:</strong> 645 x 300 mm aperture</li>
            </ul>
            <p class="mt-4">The industry standard soft light. Fully tuneable color and high output.</p>
            """
        },
        {
            "name": "Aputure LS 1200d Pro",
            "category": "lighting",
            "price": "5000.00",
            "quantity": 4,
            "description": """
            <ul class="list-disc pl-5 space-y-1 text-gray-400">
                <li><strong>Output:</strong> 1200W Daylight COB LED</li>
                <li><strong>Brightness:</strong> 83,100+ lux at 3m (with reflector)</li>
                <li><strong>Mount:</strong> Bowens Mount</li>
                <li><strong>Weatherproof:</strong> IP54 Rating</li>
            </ul>
            <p class="mt-4">The brightest Bowens mount LED on the market. Rivals 1.8K HMI fixtures.</p>
            """
        },
        {
            "name": "Astera Titan Tube Set (8 Tubes)",
            "category": "lighting",
            "price": "4000.00",
            "quantity": 3,
            "description": """
            <ul class="list-disc pl-5 space-y-1 text-gray-400">
                <li><strong>Length:</strong> 1 Meter (approx 4ft)</li>
                <li><strong>Battery:</strong> Up to 20h runtime</li>
                <li><strong>CRI/TLCI:</strong> 96+</li>
                <li><strong>Control:</strong> App, CRMX, Wired DMX</li>
            </ul>
            <p class="mt-4">The ultimate wireless LED tube for film and TV lighting.</p>
            """
        },

        # --- AUDIO ---
        {
            "name": "Sennheiser MKH-416",
            "category": "audio",
            "price": "1200.00",
            "quantity": 8,
            "description": """
            <ul class="list-disc pl-5 space-y-1 text-gray-400">
                <li><strong>Type:</strong> Shotgun Condenser Microphone</li>
                <li><strong>Pattern:</strong> Super-cardioid / Lobar</li>
                <li><strong>Frequency Response:</strong> 40Hz - 20kHz</li>
                <li><strong>Power:</strong> 48V Phantom</li>
            </ul>
            <p class="mt-4">The industry standard boom microphone for film and television dialogue.</p>
            """
        },
        {
            "name": "Zoom F8n Pro Field Recorder",
            "category": "audio",
            "price": "1500.00",
            "quantity": 4,
            "description": """
            <ul class="list-disc pl-5 space-y-1 text-gray-400">
                <li><strong>Inputs:</strong> 8 XLR/TRS Combo</li>
                <li><strong>Recording:</strong> 32-bit Float / 192kHz</li>
                <li><strong>Timecode:</strong> Accurate TXCO in/out</li>
                <li><strong>Dual SD:</strong> Redundant recording</li>
            </ul>
            <p class="mt-4">Professional field recorder with 32-bit float recording for unclipable audio.</p>
            """
        },

        # --- GRIP ---
        {
            "name": "Sachtler Flowtech 75 Tripod",
            "category": "grip",
            "price": "1800.00",
            "quantity": 6,
            "description": """
            <ul class="list-disc pl-5 space-y-1 text-gray-400">
                <li><strong>Head:</strong> FSB 8 or Aktiv8</li>
                <li><strong>Legs:</strong> Carbon Fiber Flowtech</li>
                <li><strong>Payload:</strong> Up to 12kg</li>
                <li><strong>Height:</strong> 26 - 153 cm</li>
            </ul>
            <p class="mt-4">The world's fastest deploying tripod legs. Lightweight, stable, and ergonomic.</p>
            """
        },
        {
            "name": "DJI Ronin 4D 6K",
            "category": "grip",
            "price": "8500.00",
            "quantity": 2,
            "description": """
            <ul class="list-disc pl-5 space-y-1 text-gray-400">
                <li><strong>Stabilization:</strong> 4-Axis Active Stabilization</li>
                <li><strong>Camera:</strong> Zenmuse X9-6K</li>
                <li><strong>Focus:</strong> LiDAR Range Finder</li>
                <li><strong>Transmission:</strong> O3 Pro Video Transmission</li>
            </ul>
            <p class="mt-4">The future of filmmaking. Integrated cinema camera with 4-axis gimbal and LiDAR autofocus.</p>
            """
        }
    ]

    for p_data in products:
        product, created = Product.objects.get_or_create(
            name=p_data["name"],
            defaults={
                "category": cat_objs[p_data["category"]],
                "price": Decimal(p_data["price"]),
                "quantity": p_data["quantity"],
                "description": p_data["description"].strip(),
                "is_active": True
            }
        )
        if created:
            print(f"Created: {product.name}")
        else:
            # Update description if exists
            product.description = p_data["description"].strip()
            product.category = cat_objs[p_data["category"]] # Ensure category
            product.price = Decimal(p_data["price"])
            product.save()
            print(f"Updated: {product.name}")

    print("--- Detailed Seeding Complete ---")

if __name__ == "__main__":
    seed()
