"""
MCOT Rental Platform — Role Setup Script
สร้าง 2 Groups พร้อม Permissions สำหรับพนักงาน

Usage:
    python3 manage.py shell < scripts/setup_roles.py
    
Roles:
    1. staff       — หน้างาน: สร้าง/ดู Booking + Notification
    2. web_admin   — ดูแลเว็บ: จัดการ Product/Studio/Package/Staff + อนุมัติ Booking
    3. (superuser)  — Django superuser ทำได้ทุกอย่างอยู่แล้ว
"""

from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType

# ===== 1. Staff Group (หน้างาน) =====
staff_group, created = Group.objects.get_or_create(name='staff')
staff_perms = [
    # Booking — สร้าง/ดู/แก้ได้ (ไม่ลบ)
    'add_booking', 'change_booking', 'view_booking',
    'add_bookingitem', 'change_bookingitem', 'view_bookingitem', 'delete_bookingitem',
    'add_bookingstudio', 'change_bookingstudio', 'view_bookingstudio', 'delete_bookingstudio',
    'add_bookingstaff', 'change_bookingstaff', 'view_bookingstaff', 'delete_bookingstaff',
    'add_bookingpackage', 'change_bookingpackage', 'view_bookingpackage', 'delete_bookingpackage',
    # ดูข้อมูลอ้างอิง (read-only)
    'view_product', 'view_studio', 'view_staff', 'view_package',
    'view_productcategory', 'view_staffposition',
    # Notification
    'view_notification', 'change_notification',
]
staff_group.permissions.set(
    Permission.objects.filter(codename__in=staff_perms)
)
print(f"✅ Group 'staff' {'created' if created else 'updated'} — {staff_group.permissions.count()} permissions")

# ===== 2. Web Admin Group (ดูแลเว็บ) =====
web_admin_group, created = Group.objects.get_or_create(name='web_admin')
# ให้ทุก permission ของ store app
store_perms = Permission.objects.filter(
    content_type__app_label='store'
)
web_admin_group.permissions.set(store_perms)
# เพิ่ม view users (ดู user list ได้แต่แก้ไม่ได้)
user_view = Permission.objects.filter(codename='view_user')
web_admin_group.permissions.add(*user_view)
print(f"✅ Group 'web_admin' {'created' if created else 'updated'} — {web_admin_group.permissions.count()} permissions")

print("\n🎉 Role setup complete!")
print("   Assign users via: Admin → Authentication → Users → Groups")
