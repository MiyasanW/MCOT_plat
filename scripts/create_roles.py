import os
import sys
import django

# Setup Django Environment
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from apps.store.models import Booking

def create_roles():
    print("🚀 Starting Role Setup...")

    # 1. Create Web Admin Group
    web_admin, created = Group.objects.get_or_create(name='web_admin')
    if created:
        print("✅ Created group: 'web_admin'")
    else:
        print("ℹ️ Group 'web_admin' already exists")

    # 2. Create Staff Group
    staff, created = Group.objects.get_or_create(name='staff')
    if created:
        print("✅ Created group: 'staff'")
    else:
        print("ℹ️ Group 'staff' already exists")

    print("\n🎉 Roles created successfully!")
    print("Now you can assign users to these groups in Admin Panel.")

if __name__ == '__main__':
    create_roles()
