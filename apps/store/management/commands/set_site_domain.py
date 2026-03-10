"""
ตั้งค่า Domain ของ Site (SITE_ID=1) ให้ตรงกับที่รันเว็บ — ลิงก์ในเมล (รีเซ็ตรหัสผ่าน, ใบเสนอราคา) จะได้ชี้ไปถูกที่
ใช้: python manage.py set_site_domain 127.0.0.1:8000
หรือ: ใส่ SITE_DOMAIN=127.0.0.1:8000 ใน .env แล้วรัน python manage.py set_site_domain
"""
import os
from django.core.management.base import BaseCommand
from django.contrib.sites.models import Site


class Command(BaseCommand):
    help = 'ตั้งค่า domain ของ Site (สำหรับลิงก์ในอีเมล รีเซ็ตรหัสผ่าน ฯลฯ)'

    def add_arguments(self, parser):
        parser.add_argument(
            'domain',
            nargs='?',
            type=str,
            default=None,
            help='Domain เช่น 127.0.0.1:8000 หรือ yourdomain.com (ถ้าไม่ใส่จะอ่านจาก SITE_DOMAIN ใน .env)'
        )

    def handle(self, *args, **options):
        from django.conf import settings
        domain = options.get('domain') or getattr(settings, 'SITE_DOMAIN', None)
        if not domain:
            domain = os.environ.get('SITE_DOMAIN', '').strip()
        if not domain:
            self.stdout.write(
                self.style.WARNING('กรุณาระบุ domain เช่น: python manage.py set_site_domain 127.0.0.1:8000')
            )
            self.stdout.write('หรือใส่ SITE_DOMAIN=127.0.0.1:8000 ใน .env')
            return
        site_id = getattr(settings, 'SITE_ID', 1)
        site = Site.objects.get(id=site_id)
        site.domain = domain
        site.name = site.name or f'MCOT Rental ({domain})'
        site.save()
        self.stdout.write(self.style.SUCCESS(f'ตั้งค่า Site (id={site_id}) เป็น domain: {domain} แล้ว'))
        self.stdout.write('ลิงก์ในอีเมล (รีเซ็ตรหัสผ่าน ฯลฯ) จะชี้ไปที่นี้')
