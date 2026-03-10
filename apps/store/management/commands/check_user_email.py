"""
ตรวจว่าอีเมลนี้มีในระบบ (มี User ผูกอยู่หรือไม่) — ใช้ตอนลูกค้าบอกรีเซ็ตรหัสผ่านแล้วไม่มีเมล
ใช้: python manage.py check_user_email ลูกค้า@email.com
"""
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

User = get_user_model()


class Command(BaseCommand):
    help = 'ตรวจว่าอีเมลนี้มีในระบบหรือไม่ (มีบัญชี User หรือไม่)'

    def add_arguments(self, parser):
        parser.add_argument('email', type=str, help='อีเมลที่ต้องการตรวจ (เช่น user@example.com)')

    def handle(self, *args, **options):
        email = options['email'].strip().lower()
        if not email:
            self.stdout.write(self.style.ERROR('กรุณาระบุอีเมล'))
            return
        users = list(User.objects.filter(email__iexact=email, is_active=True))
        if not users:
            self.stdout.write(self.style.WARNING(
                f'ไม่พบบัญชีที่ใช้อีเมล "{email}" ในระบบ (หรือบัญชีถูกปิดใช้งาน)'
            ))
            self.stdout.write(
                '→ ลูกค้าต้องลงทะเบียนด้วยอีเมลนี้ก่อน จึงจะใช้ "รีเซ็ตรหัสผ่าน" ได้'
            )
            return
        for u in users:
            name = f'{u.first_name or ""} {u.last_name or ""}'.strip() or u.username or '-'
            self.stdout.write(self.style.SUCCESS(
                f'พบบัญชี: อีเมล={u.email}, ชื่อ={name}, username={u.username}'
            ))
        self.stdout.write(
            '→ ถ้ารีเซ็ตรหัสผ่านแล้วไม่มีเมล ตรวจ .env (EMAIL_HOST_USER, EMAIL_HOST_PASSWORD) และรัน send_test_email'
        )
