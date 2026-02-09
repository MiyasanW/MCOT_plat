
import os
import sys
import django

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from apps.store.models import Product


def update_descriptions():
    updates = {
        "Sony A7S III": """
            <ul class="list-disc pl-5 space-y-1 text-gray-400">
                <li><strong>Sensor:</strong> 12MP Full-Frame Exmor R BSI CMOS</li>
                <li><strong>Video:</strong> UHD 4K 120p Video, 10-Bit 4:2:2</li>
                <li><strong>ISO:</strong> 80-102400 (Native)</li>
                <li><strong>Focus:</strong> Fast Hybrid AF</li>
            </ul>
            <p class="mt-4">The alpha 7S III features a 12.1MP Exmor R BSI CMOS sensor and updated BIONZ XR image processor.</p>
        """,
        "Canon R5": """
             <ul class="list-disc pl-5 space-y-1 text-gray-400">
                <li><strong>Sensor:</strong> 45MP Full-Frame CMOS</li>
                <li><strong>Video:</strong> 8K Raw Video / 4K 120fps</li>
                <li><strong>Stabilization:</strong> 5-Axis In-Body Image Stabilization</li>
                <li><strong>Focus:</strong> Dual Pixel CMOS AF II</li>
            </ul>
            <p class="mt-4">For the professional image-maker who needs resolution, speed, and video capabilities.</p>
        """,
        "Blackmagic Pocket 6K": """
             <ul class="list-disc pl-5 space-y-1 text-gray-400">
                <li><strong>Sensor:</strong> Super 35 HDR Sensor</li>
                <li><strong>Mount:</strong> EF Lens Mount</li>
                <li><strong>Video:</strong> 6K 6144 x 3456 up to 50 fps</li>
                <li><strong>ISO:</strong> Dual Native ISO to 25,600</li>
            </ul>
            <p class="mt-4">Next generation 6K digital film camera with high res Super 35 HDR sensor.</p>
        """,
        "Aputure LS 1200d Pro": """
             <ul class="list-disc pl-5 space-y-1 text-gray-400">
                <li><strong>Output:</strong> 1200W Output Daylight Point Source</li>
                <li><strong>Brightness:</strong> 83,100+ lux at 3m with Hyper Reflector</li>
                <li><strong>IP Rating:</strong> Weather Resistant Design</li>
                <li><strong>Control:</strong> Sidus Link, DMX, Art-Net, sACN</li>
            </ul>
            <p class="mt-4">The Light Storm 1200d Pro is Aputure's flagship Light Storm product.</p>
        """,
        "Test Camera X1": """
             <ul class="list-disc pl-5 space-y-1 text-gray-400">
                <li><strong>Sensor:</strong> 24MP APS-C CMOS</li>
                <li><strong>Video:</strong> 4K 30p</li>
                <li><strong>ISO:</strong> 100-25600</li>
            </ul>
            <p class="mt-4">Entry level cinema camera for testing purposes.</p>
        """
    }

    print("--- Updating Legacy Descriptions (Exact Match) ---")
    for name, desc in updates.items():
        try:
            # Use filter().update() to avoid get() errors and handle potential duplicates gracefully (or just update all distinct matches)
            # But here we want exact match on name
            products = Product.objects.filter(name=name)
            if products.exists():
                count = products.update(description=desc.strip())
                print(f"✅ Updated {count} items: {name}")
            else:
                print(f"⚠️ Not Found: {name}")
        except Exception as e:
            print(f"❌ Error {name}: {e}")

if __name__ == "__main__":
    update_descriptions()
