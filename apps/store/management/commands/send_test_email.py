"""
ส่งอีเมลทดสอบ — ใช้ตรวจว่า SMTP ตั้งค่าส่งให้ลูกค้าถูกต้อง
ใช้: python manage.py send_test_email ลูกค้า@email.com
"""
from django.core.management.base import BaseCommand
from django.core.mail import send_mail
from django.conf import settings


class Command(BaseCommand):
    help = 'ส่งอีเมลทดสอบไปยังที่อยู่ที่กำหนด (ตรวจสอบการตั้งค่า SMTP สำหรับส่งให้ลูกค้า)'

    def add_arguments(self, parser):
        parser.add_argument('email', type=str, help='อีเมลปลายทาง (เช่น ลูกค้า@example.com)')

    def handle(self, *args, **options):
        to = options['email'].strip()
        if not to:
            self.stdout.write(self.style.ERROR('กรุณาระบุอีเมลปลายทาง'))
            return
        backend = getattr(settings, 'EMAIL_BACKEND', '')
        if 'console' in backend:
            self.stdout.write(self.style.WARNING(
                'กำลังใช้ Console Backend — เมลจะแสดงในเทอร์มินัล ไม่ได้ส่งจริง '
                'ใส่ EMAIL_HOST_USER และ EMAIL_HOST_PASSWORD ใน .env เพื่อส่งจริง'
            ))
        try:
            n = send_mail(
                subject='[MCOT Equipment Service] ทดสอบส่งอีเมล',
                message='นี่คืออีเมลทดสอบจากระบบ MCOT Equipment Service ถ้าคุณได้รับเมลนี้ แสดงว่าการตั้งค่าส่งอีเมลให้ลูกค้าพร้อมใช้งานแล้ว',
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[to],
                fail_silently=False,
            )
            self.stdout.write(self.style.SUCCESS(f'ส่งอีเมลทดสอบไปที่ {to} แล้ว (จำนวน {n} ฉบับ)'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'ส่งเมลไม่สำเร็จ: {e}'))
