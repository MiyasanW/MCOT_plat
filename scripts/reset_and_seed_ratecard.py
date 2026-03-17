from __future__ import annotations

import csv
import os
import re
import shutil
import sys
from dataclasses import dataclass
from datetime import timedelta
from decimal import Decimal
from pathlib import Path

import django
from PIL import Image, ImageDraw, ImageFont


BASE_DIR = Path(__file__).resolve().parent.parent
CSV_PATH = BASE_DIR / 'RateCard Equipment.csv'
MEDIA_DIR = BASE_DIR / 'media'

SUPERADMIN_USERNAME = 'superadmin'
SUPERADMIN_EMAIL = 'superadmin@mcot.local'
SUPERADMIN_PASSWORD = 'Admin12345!'

PLACEHOLDER_COLORS = {
    'camera': ('#112a46', '#3aa1ff'),
    'lens': ('#2d1b45', '#b07cff'),
    'monitor': ('#123c36', '#53d6c0'),
    'audio': ('#402312', '#ff9c54'),
    'lighting': ('#4a4112', '#ffd166'),
    'support': ('#352728', '#ff8fa3'),
    'live': ('#17293a', '#6ec1ff'),
    'editing': ('#1f3330', '#79c99e'),
    'display': ('#3c2c14', '#ffcf70'),
    'vehicle': ('#2e2436', '#c29cff'),
    'studio': ('#24303d', '#a0d8ff'),
    'package': ('#21332a', '#7fe0ad'),
    'service': ('#352019', '#ffb38a'),
    'generic': ('#30343b', '#b4c1d1'),
    'splash': ('#1d2440', '#cdd8ff'),
}


def setup_django() -> None:
    sys.path.insert(0, str(BASE_DIR))
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
    django.setup()


def normalize_text(value: str) -> str:
    return re.sub(r'\s+', ' ', (value or '').replace('\xa0', ' ')).strip().strip('"')


def slug_fragment(value: str) -> str:
    cleaned = re.sub(r'[^A-Za-z0-9]+', '-', value).strip('-').lower()
    return cleaned or 'item'


def parse_primary_price(value: str) -> Decimal:
    cleaned = normalize_text(value).replace(',', '')
    matches = re.findall(r'\d+(?:\.\d+)?', cleaned)
    if not matches:
        return Decimal('1000.00')
    return Decimal(matches[0]).quantize(Decimal('0.01'))


def extract_hourly_overage(note: str) -> str | None:
    match = re.search(r'ชั่วโมงละ\s*([\d,]+)', note)
    if not match:
        return None
    return match.group(1).replace(',', '')


def build_html_description(name: str, rate_text: str, old_price: str, note: str, kind: str) -> str:
    summary = {
        'product': 'รายการนี้ถูก seed จากตารางอัตราค่าบริการ เพื่อใช้เป็นข้อมูลตั้งต้นในระบบเช่าอุปกรณ์',
        'studio': 'ห้องส่งนี้ถูก seed จากตารางอัตราค่าบริการ เพื่อใช้เป็นข้อมูลตั้งต้นในระบบจองห้องส่ง',
        'package': 'แพ็กเกจนี้จัดขึ้นจากข้อมูลใน rate card และส่วนประกอบ mock เพื่อให้พร้อมทดสอบการจองแบบ bundle',
        'vehicle': 'ยานพาหนะนี้เป็นข้อมูล mock ที่เพิ่มเข้ามาเพื่อให้เมนู Vehicles ใช้งานและทดสอบ flow ได้ครบ',
        'service': 'บริการนี้ถูก seed จากข้อมูลอัตราค่าบริการ/ทีมงาน เพื่อใช้เป็นข้อมูลตั้งต้นในระบบบริการ',
    }[kind]

    bullets = [
        f'ชื่อรายการ: {name}',
        f'ราคาอ้างอิงจาก rate card: {rate_text or old_price or "ยังไม่ระบุ"}',
    ]
    if old_price and old_price != rate_text:
        bullets.append(f'ราคาชุดเดิม/ข้อความเดิมในเอกสาร: {old_price}')
    if note:
        bullets.append(f'หมายเหตุ: {note}')
    overage = extract_hourly_overage(note)
    if overage:
        bullets.append(f'มีข้อมูลค่าล่วงเวลา/เกินเวลาในเอกสาร: {overage} บาทต่อชั่วโมง')
    if kind in {'package', 'vehicle'}:
        bullets.append('รายละเอียดบางส่วนเป็น mock up เพื่อให้ระบบพร้อมใช้งานทันทีหลัง reset')

    items = ''.join(f'<li>{bullet}</li>' for bullet in bullets)
    return f'<p>{summary}</p><ul>{items}</ul>'


@dataclass
class RateCardEntry:
    index: str
    name: str
    old_price: str
    rate_text: str
    note: str


def parse_rate_card() -> tuple[list[RateCardEntry], list[RateCardEntry]]:
    products: list[RateCardEntry] = []
    studios: list[RateCardEntry] = []
    package_rows: list[RateCardEntry] = []
    current: RateCardEntry | None = None
    after_last_row = False

    with CSV_PATH.open('r', encoding='utf-8-sig', newline='') as handle:
        reader = csv.reader(handle)
        for raw_row in reader:
            row = [normalize_text(cell) for cell in raw_row]
            row += [''] * (7 - len(row))
            index, item, old_price, rate_text, note = row[:5]

            if 'ลำดับ' in index or item == 'รายการ':
                continue

            if current and not index and not item and note:
                current.note = normalize_text(' '.join(part for part in [current.note, note] if part))
                continue

            if after_last_row and not any([index, item, old_price, rate_text, note]):
                break

            if not item:
                continue

            if index == '32':
                after_last_row = True

            if not (index.isdigit() or rate_text):
                continue

            current = RateCardEntry(index=index, name=item, old_price=old_price, rate_text=rate_text, note=note)

            if 'ชุดถ่ายทอด OB' in item:
                package_rows.append(current)
                continue

            normalized_name = item.replace('ราคาห้องส่ง', 'ห้องส่ง').strip()
            if normalized_name.startswith('ห้องส่ง'):
                current.name = normalized_name
                studios.append(current)
            else:
                products.append(current)

    return products, studios


def category_definition(name: str) -> tuple[str, str]:
    rules = [
        (r'กล้อง|camera', ('camera', 'กล้อง')),
        (r'เลนซ์|เลนส์|lens', ('lens', 'เลนส์')),
        (r'monitor', ('monitor', 'มอนิเตอร์')),
        (r'audio mixer|ไวเรสไมค์|ไวเรสกล้อง|sound|pa', ('audio', 'ระบบเสียง')),
        (r'video switcher|switcher|cg|play out|live slow|live u|live stream', ('live-production', 'งานถ่ายทอดสด')),
        (r'ขาตั้ง|เครน', ('support-rig', 'อุปกรณ์ซัพพอร์ต')),
        (r'ไฟแสง|light', ('lighting', 'ไฟและแสง')),
        (r'เครื่องตัดต่อ|mac|pc', ('editing', 'ตัดต่อ')),
        (r'จอทีวี', ('display', 'จอแสดงผล')),
        (r'vehicle|ob van|รถ', ('vehicle', 'ยานพาหนะ')),
    ]
    lowered = name.lower()
    for pattern, result in rules:
        if re.search(pattern, lowered, re.IGNORECASE):
            return result
    return ('general', 'อุปกรณ์ทั่วไป')


def quantity_hint(name: str, slug: str) -> int:
    lowered = name.lower()
    if 'ไวเรสไมค์' in name:
        return 4
    if slug in {'camera', 'lens'}:
        return 3
    if slug in {'monitor', 'audio', 'display'}:
        return 2
    if slug == 'lighting':
        return 4
    if slug == 'studio-room' or slug == 'vehicle':
        return 1
    if 'ชุด live stream' in lowered:
        return 2
    return 1


def remove_old_seed_media() -> None:
    for folder in ('products', 'studios', 'packages', 'splash'):
        target_dir = MEDIA_DIR / folder
        target_dir.mkdir(parents=True, exist_ok=True)
        for path in target_dir.glob('seed_*'):
            path.unlink()


def create_placeholder(relative_dir: str, filename: str, title: str, accent_key: str, subtitle: str) -> str:
    bg, accent = PLACEHOLDER_COLORS.get(accent_key, PLACEHOLDER_COLORS['generic'])
    folder = MEDIA_DIR / relative_dir
    folder.mkdir(parents=True, exist_ok=True)
    absolute_path = folder / filename

    image = Image.new('RGB', (1200, 800), bg)
    draw = ImageDraw.Draw(image)
    font_large = ImageFont.load_default()
    font_small = ImageFont.load_default()

    draw.rounded_rectangle((80, 80, 1120, 720), radius=36, outline=accent, width=8)
    draw.rectangle((120, 140, 1080, 200), fill=accent)
    draw.text((140, 156), title[:36].upper(), fill='white', font=font_large)
    draw.text((140, 260), subtitle[:90], fill='white', font=font_small)
    draw.text((140, 320), 'MCOT RENTAL SEED PLACEHOLDER', fill=accent, font=font_small)
    draw.text((140, 360), 'Generated automatically for local mock data', fill='white', font=font_small)
    draw.ellipse((860, 260, 1040, 440), outline=accent, width=10)
    draw.line((220, 620, 980, 620), fill=accent, width=6)
    image.save(absolute_path, format='PNG')
    return f'{relative_dir}/{filename}'


def ensure_groups() -> None:
    from django.contrib.auth.models import Group

    Group.objects.get_or_create(name='web_admin')
    Group.objects.get_or_create(name='staff')


def seed_data() -> None:
    from django.contrib.auth.models import User
    from django.contrib.sites.models import Site
    from django.db import transaction
    from django.utils import timezone

    from apps.store.models import (
        Equipment,
        Package,
        PackageItem,
        Product,
        ProductCategory,
        PromotionCode,
        ServiceCategory,
        ServiceOffer,
        SplashConfig,
        Studio,
    )

    products, studios = parse_rate_card()
    remove_old_seed_media()

    with transaction.atomic():
        ensure_groups()

        categories: dict[str, ProductCategory] = {}

        def get_category(name: str) -> ProductCategory:
            slug, label = category_definition(name)
            category = categories.get(slug)
            if category is None:
                category, _ = ProductCategory.objects.get_or_create(slug=slug, defaults={'name': label})
                categories[slug] = category
            return category

        product_lookup: dict[str, Product] = {}

        for index, entry in enumerate(products, start=1):
            category = get_category(entry.name)
            category_slug = category.slug
            quantity = quantity_hint(entry.name, category_slug)
            rel_image = create_placeholder(
                'products',
                f'seed_product_{index:02d}_{slug_fragment(category_slug)}.png',
                category_slug.replace('-', ' '),
                'vehicle' if category_slug == 'vehicle' else category_slug if category_slug in PLACEHOLDER_COLORS else 'generic',
                entry.name,
            )
            product = Product.objects.create(
                name=entry.name,
                description=build_html_description(entry.name, entry.rate_text, entry.old_price, entry.note, 'product'),
                category=category,
                price=parse_primary_price(entry.rate_text or entry.old_price),
                quantity=quantity,
                is_active=True,
                is_featured=index <= 6,
            )
            product.image.name = rel_image
            product.save(update_fields=['image'])
            product_lookup[entry.name] = product

            for unit in range(1, quantity + 1):
                serial_base = f'SEED-{index:02d}-{unit:02d}'
                Equipment.objects.create(
                    product=product,
                    serial_number=serial_base,
                    inventory_number=f'INV-{index:02d}-{unit:02d}',
                    asset_tag=f'ASSET-{index:02d}-{unit:02d}',
                    status='available',
                )

        vehicle_category = get_category('vehicle')
        vehicle_specs = [
            ('รถ OB Van Mock', 'รถสำหรับงานถ่ายทอดสดภาคสนาม พร้อมพื้นที่ติดตั้งระบบสวิตช์และมอนิเตอร์', Decimal('45000.00')),
            ('รถ Production Support Van Mock', 'รถซัพพอร์ตงานถ่ายทำ/ขนย้ายอุปกรณ์ สำหรับใช้ทดสอบหมวด Vehicles', Decimal('18000.00')),
        ]
        for index, (name, note, price) in enumerate(vehicle_specs, start=1):
            rel_image = create_placeholder('products', f'seed_vehicle_{index:02d}.png', 'vehicle', 'vehicle', name)
            product = Product.objects.create(
                name=name,
                description=build_html_description(name, f'{price:,.0f} บาท', '', note, 'vehicle'),
                category=vehicle_category,
                price=price,
                quantity=1,
                is_active=True,
                is_featured=True,
            )
            product.image.name = rel_image
            product.save(update_fields=['image'])
            product_lookup[name] = product
            Equipment.objects.create(
                product=product,
                serial_number=f'VEH-{index:02d}-01',
                inventory_number=f'VEH-INV-{index:02d}',
                asset_tag=f'VEH-ASSET-{index:02d}',
                status='available',
            )

        for index, entry in enumerate(studios, start=1):
            rel_image = create_placeholder('studios', f'seed_studio_{index:02d}.png', 'studio', 'studio', entry.name)
            studio = Studio.objects.create(
                name=entry.name,
                description=build_html_description(entry.name, entry.rate_text, entry.old_price, entry.note, 'studio'),
                daily_rate=parse_primary_price(entry.rate_text or entry.old_price),
            )
            studio.image.name = rel_image
            studio.save(update_fields=['image'])

        crew_category, _ = ServiceCategory.objects.get_or_create(slug='crew', defaults={'name': 'ทีมงานและบุคลากร'})
        post_category, _ = ServiceCategory.objects.get_or_create(slug='post-production', defaults={'name': 'โพสต์โปรดักชัน'})
        services = [
            ('ช่างภาพ', 'บุคลากรสำหรับควบคุมกล้องและเฟรมภาพหน้างาน', Decimal('1000.00'), crew_category),
            ('ช่างเทคนิค', 'บุคลากรสำหรับดูแลระบบหน้างานและอุปกรณ์สนับสนุน', Decimal('1500.00'), crew_category),
            ('กำกับภาพ (SW)', 'ผู้ควบคุมการสลับภาพและ flow ถ่ายทอดสด', Decimal('3000.00'), crew_category),
            ('ผู้ช่วยกล้อง', 'ผู้ช่วยเตรียมอุปกรณ์ เปลี่ยนเลนส์ และดูแล workflow หน้างาน', Decimal('1200.00'), crew_category),
            ('ช่างเสียง', 'ผู้ดูแลไมค์ มิกเซอร์ และสัญญาณเสียง', Decimal('1200.00'), crew_category),
            ('CCU Operator', 'ผู้ควบคุมและบาลานซ์สัญญาณกล้องในงานหลายกล้อง', Decimal('1500.00'), crew_category),
            ('ตัดต่อวิดีโอเบื้องต้น', 'บริการตัดต่อพื้นฐานเพื่อให้ระบบมี mock service ครบสำหรับทดสอบ', Decimal('5000.00'), post_category),
        ]
        for name, note, price, category in services:
            ServiceOffer.objects.create(
                name=name,
                description=build_html_description(name, f'{price:,.0f} บาท', '', note, 'service'),
                category=category,
                daily_rate=price,
                is_active=True,
            )

        packages = [
            {
                'name': 'ชุดถ่ายทอด OB 3 กล้อง (ทีมหลัก)',
                'short_description': 'แพ็กเกจถ่ายทอดสดพร้อมกล้อง 3 ชุดและงานสวิตช์ภาพ',
                'price': Decimal('45000.00'),
                'note': 'อ้างอิงจากแถวชุดถ่ายทอด OB 3 กล้อง + SW + บันทึก ใน rate card',
                'items': [('กล้องใหญ่', 2), ('Video Switcher 8 I/P', 1), ('Audio Mixer 8-12 CH', 1), ('Monitor 14-17 นิ้ว', 1), ('ไวเรสไมค์', 2)],
            },
            {
                'name': 'ชุดถ่ายทอด OB 3 กล้อง (ทีมผู้ช่วย)',
                'short_description': 'แพ็กเกจรุ่นย่อยสำหรับงาน OB ที่ใช้ทีมผู้ช่วยและอุปกรณ์หลักครบ',
                'price': Decimal('35000.00'),
                'note': 'อ้างอิงจากแถวผู้ช่วยกล้อง/เสียง/CCU ใน rate card',
                'items': [('กล้องใหญ่', 2), ('Monitor 14-17 นิ้ว', 1), ('Audio Mixer 8-12 CH', 1), ('ไวเรสไมค์', 2)],
            },
            {
                'name': 'ชุด Live Event Compact',
                'short_description': 'แพ็กเกจ mock สำหรับงาน event/live ขนาดเล็ก',
                'price': Decimal('12000.00'),
                'note': 'แพ็กเกจ mock เพิ่มเติมสำหรับทดสอบหน้า package list/detail',
                'items': [('ชุด Live Stream', 1), ('Audio Mixer 8-12 CH', 1), ('Monitor 20-27 นิ้ว', 1), ('ไวเรสไมค์', 2)],
            },
            {
                'name': 'ชุด Studio Interview Starter',
                'short_description': 'แพ็กเกจ mock สำหรับงานสัมภาษณ์ในสตูดิโอ',
                'price': Decimal('9000.00'),
                'note': 'แพ็กเกจ mock เพิ่มเติมเพื่อให้ระบบมีข้อมูลแพ็กเกจพร้อมใช้งาน',
                'items': [('กล้อง DSLR', 1), ('Monitor 14-17 นิ้ว', 1), ('อุปกรณ์ไฟแสง', 2), ('ไวเรสไมค์', 2)],
            },
        ]
        for index, package_data in enumerate(packages, start=1):
            rel_image = create_placeholder('packages', f'seed_package_{index:02d}.png', 'package', 'package', package_data['name'])
            package = Package.objects.create(
                name=package_data['name'],
                short_description=package_data['short_description'],
                description=build_html_description(package_data['name'], f"{package_data['price']:,.0f} บาท", '', package_data['note'], 'package'),
                price=package_data['price'],
                is_highlight=index <= 2,
                is_active=True,
            )
            package.image.name = rel_image
            package.save(update_fields=['image'])

            for item_name, quantity in package_data['items']:
                product = product_lookup.get(item_name)
                if product is None:
                    continue
                PackageItem.objects.create(package=package, product=product, quantity=quantity)

        promotion = PromotionCode.objects.create(
            code='WELCOME10',
            discount_percent=10,
            discount_amount=Decimal('0.00'),
            valid_from=timezone.now() - timezone.timedelta(days=1),
            valid_to=timezone.now() + timedelta(days=365),
            is_active=True,
        )

        rel_splash = create_placeholder('splash', 'seed_splash_main.png', 'mcot splash', 'splash', 'MCOT Equipment Service')
        splash = SplashConfig.objects.create(
            is_active=False,
            title='MCOT Equipment Service',
            message='ข้อมูลตั้งต้นถูกสร้างใหม่จาก RateCard Equipment.csv พร้อม mock data สำหรับใช้งานและทดสอบระบบ',
        )
        splash.image.name = rel_splash
        splash.save(update_fields=['image'])

        site, _ = Site.objects.get_or_create(id=1)
        site.domain = 'localhost:8000'
        site.name = 'MCOT Equipment Service'
        site.save()

        superuser = User.objects.create_superuser(
            username=SUPERADMIN_USERNAME,
            email=SUPERADMIN_EMAIL,
            password=SUPERADMIN_PASSWORD,
        )
        superuser.first_name = 'Super'
        superuser.last_name = 'Admin'
        superuser.save(update_fields=['first_name', 'last_name'])

        print('Seed complete')
        print(f'Products: {Product.objects.count()}')
        print(f'Equipment: {Equipment.objects.count()}')
        print(f'Studios: {Studio.objects.count()}')
        print(f'Packages: {Package.objects.count()}')
        print(f'Services: {ServiceOffer.objects.count()}')
        print(f'Categories: {ProductCategory.objects.count()}')
        print(f'Promotion codes: {PromotionCode.objects.count()}')
        print(f'Splash configs: {SplashConfig.objects.count()}')
        print(f'Superadmin: {SUPERADMIN_USERNAME} / {SUPERADMIN_PASSWORD}')
        print(f'Default promotion: {promotion.code}')


def main() -> None:
    setup_django()
    seed_data()


if __name__ == '__main__':
    main()