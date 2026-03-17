from __future__ import annotations

import os
import sys
from pathlib import Path

import django
from PIL import Image, ImageDraw, ImageFont


BASE_DIR = Path(__file__).resolve().parent.parent
MEDIA_DIR = BASE_DIR / 'media'


def setup_django() -> None:
    sys.path.insert(0, str(BASE_DIR))
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
    django.setup()


def gradient_background(width: int, height: int, top_rgb: tuple[int, int, int], bottom_rgb: tuple[int, int, int]) -> Image.Image:
    image = Image.new('RGB', (width, height), top_rgb)
    draw = ImageDraw.Draw(image)
    for y in range(height):
        ratio = y / max(1, height - 1)
        r = int(top_rgb[0] + (bottom_rgb[0] - top_rgb[0]) * ratio)
        g = int(top_rgb[1] + (bottom_rgb[1] - top_rgb[1]) * ratio)
        b = int(top_rgb[2] + (bottom_rgb[2] - top_rgb[2]) * ratio)
        draw.line((0, y, width, y), fill=(r, g, b))
    return image


def draw_card(relative_path: str, title: str, subtitle: str, palette: tuple[tuple[int, int, int], tuple[int, int, int], tuple[int, int, int]]) -> None:
    start, end, accent = palette
    output_path = MEDIA_DIR / relative_path
    output_path.parent.mkdir(parents=True, exist_ok=True)

    image = gradient_background(1280, 720, start, end)
    draw = ImageDraw.Draw(image)
    font = ImageFont.load_default()

    draw.rounded_rectangle((72, 72, 1208, 648), radius=28, outline=accent, width=6)
    draw.rounded_rectangle((108, 118, 1172, 210), radius=18, fill=accent)
    draw.text((140, 150), title[:48], fill='white', font=font)
    draw.text((140, 260), subtitle[:100], fill=(245, 245, 245), font=font)
    draw.text((140, 320), 'MCOT EQUIPMENT SERVICE', fill=accent, font=font)
    draw.text((140, 352), 'Seed Visual (Refined)', fill=(235, 235, 235), font=font)

    draw.ellipse((960, 250, 1120, 410), outline=accent, width=8)
    draw.line((230, 600, 1050, 600), fill=accent, width=4)
    image.save(output_path, format='PNG')


def polish() -> None:
    from django.db import transaction

    from apps.store.models import Package, Product, ProductCategory, ServiceOffer, SplashConfig, Studio

    category_names = {
        'audio': 'ระบบเสียงและไมค์',
        'live-production': 'งานไลฟ์และถ่ายทอดสด',
        'support-rig': 'ขาตั้ง เครน และซัพพอร์ต',
        'editing': 'ตัดต่อและโพสต์โปรดักชัน',
        'vehicle': 'ยานพาหนะงานโปรดักชัน',
    }

    product_name_map = {
        'เลนซ์ ขนาด 40': 'เลนส์ขนาด 40x',
        'เลนซ์ ขนาด 60': 'เลนส์ขนาด 60x',
        'เลนซ์ ขนาด 72': 'เลนส์ขนาด 72x',
        'เลนซ์ DSLR ขนาด': 'เลนส์ DSLR (ขนาดตามรุ่น)',
        'Monitor 14-17 นิ้ว': 'มอนิเตอร์ 14-17 นิ้ว',
        'Monitor 20-27 นิ้ว': 'มอนิเตอร์ 20-27 นิ้ว',
        'Audio Mixer 8-12 CH': 'Audio Mixer 8-12 CH',
        'Video Switcher 8 I/P': 'Video Switcher 8 I/P',
        'Play Out': 'Playout',
        'Live U': 'LiveU',
        'รถ Production Support Van Mock': 'รถ Production Support Van (Mock)',
    }

    service_name_map = {
        'CCU Operator': 'CCU Operator (ผู้ควบคุมกล้อง)',
    }

    package_name_map = {
        'ชุด Live Event Compact': 'ชุด Live Event Compact (Mock)',
        'ชุด Studio Interview Starter': 'ชุด Studio Interview Starter (Mock)',
    }

    palettes = {
        'camera': ((9, 35, 74), (20, 104, 173), (132, 208, 255)),
        'lens': ((33, 26, 64), (86, 52, 140), (199, 162, 255)),
        'monitor': ((17, 56, 52), (18, 120, 108), (117, 243, 220)),
        'audio': ((60, 34, 20), (138, 76, 42), (255, 194, 129)),
        'live-production': ((20, 38, 66), (46, 86, 151), (149, 202, 255)),
        'support-rig': ((58, 36, 36), (110, 58, 58), (255, 178, 178)),
        'lighting': ((64, 58, 24), (155, 132, 46), (255, 219, 126)),
        'editing': ((25, 53, 44), (50, 120, 95), (136, 232, 194)),
        'display': ((62, 46, 24), (136, 95, 40), (255, 208, 126)),
        'vehicle': ((45, 34, 60), (95, 68, 130), (210, 182, 255)),
        'package': ((26, 61, 47), (45, 117, 88), (142, 237, 191)),
        'studio': ((32, 48, 68), (55, 95, 141), (170, 213, 255)),
        'splash': ((24, 33, 65), (56, 80, 154), (205, 219, 255)),
        'generic': ((40, 46, 58), (70, 82, 106), (186, 201, 231)),
    }

    with transaction.atomic():
        for slug, label in category_names.items():
            ProductCategory.objects.filter(slug=slug).update(name=label)

        products = list(Product.objects.select_related('category').all())
        for product in products:
            original_name = product.name
            product.name = product_name_map.get(product.name, product.name)

            category_slug = product.category.slug if product.category else 'generic'
            palette = palettes.get(category_slug, palettes['generic'])

            if product.image and 'seed_' in product.image.name:
                draw_card(product.image.name, product.name, product.category.name if product.category else 'หมวดหมู่ทั่วไป', palette)

            if product.description and 'Seed Visual' not in product.description:
                product.description = (
                    f"<p>ข้อมูลตั้งต้นจาก RateCard พร้อมข้อความอธิบายเพื่อทดสอบระบบค้นหา/แสดงผล</p>"
                    f"<p><strong>หมวดหมู่:</strong> {product.category.name if product.category else 'ทั่วไป'}</p>"
                    + product.description
                )

            changed_fields = []
            if product.name != original_name:
                changed_fields.append('name')
            changed_fields.append('description')
            product.save(update_fields=changed_fields)

        for studio in Studio.objects.all():
            if studio.image and 'seed_' in studio.image.name:
                draw_card(studio.image.name, studio.name, 'ห้องส่งและสิ่งอำนวยความสะดวก', palettes['studio'])
            if studio.description and 'Seed Visual' not in studio.description:
                studio.description = '<p>ห้องส่งตั้งต้นจากข้อมูลในอัตราค่าบริการ พร้อม mock description สำหรับทดสอบ</p>' + studio.description
                studio.save(update_fields=['description'])

        for package in Package.objects.all():
            original_name = package.name
            package.name = package_name_map.get(package.name, package.name)
            if package.image and 'seed_' in package.image.name:
                draw_card(package.image.name, package.name, package.short_description or 'แพ็กเกจเช่าอุปกรณ์', palettes['package'])
            if package.description and 'Seed Visual' not in package.description:
                package.description = '<p>แพ็กเกจนี้เป็นข้อมูลตั้งต้น/ตัวอย่างเพื่อทดสอบการจองแบบชุด</p>' + package.description
            update_fields = ['description']
            if package.name != original_name:
                update_fields.append('name')
            package.save(update_fields=update_fields)

        for service in ServiceOffer.objects.select_related('category').all():
            original_name = service.name
            service.name = service_name_map.get(service.name, service.name)
            if service.description and 'Seed Visual' not in service.description:
                service.description = '<p>บริการตั้งต้นจากเรทการ์ดและ mock workflow ทีมงาน</p>' + service.description
            fields = ['description']
            if service.name != original_name:
                fields.append('name')
            service.save(update_fields=fields)

        splash = SplashConfig.objects.first()
        if splash and splash.image and 'seed_' in splash.image.name:
            draw_card(splash.image.name, 'MCOT Equipment Service', 'Splash Screen Placeholder', palettes['splash'])

    print('Polish complete')
    print('Updated category labels, normalized names, refreshed descriptions, and regenerated seed images.')


def main() -> None:
    setup_django()
    polish()


if __name__ == '__main__':
    main()
