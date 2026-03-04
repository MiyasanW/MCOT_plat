import os
import sys

# Setup Django environment
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

import django
django.setup()

from django.contrib.auth.models import Group, Permission
from django.db.models import Q
from django.contrib.contenttypes.models import ContentType

def setup_staff_permissions():
    staff_group, created = Group.objects.get_or_create(name='staff')
    
    # We want staff to be able to "view" and "change" bookings, and "view" products, equipment, notifications
    # Get all permissions related to these models
    view_perms = [
        'view_product', 'view_equipment', 'view_notification',
        'view_studio', 'view_package', 'view_productionvehicle',
        'view_servicecategory', 'view_serviceoffer'
    ]
    
    permissions = Permission.objects.filter(
        Q(codename__in=['view_booking', 'change_booking', 'change_notification']) |
        Q(codename__in=view_perms)
    )
    
    # Add permissions to group
    staff_group.permissions.add(*permissions)
    
    print(f"Successfully added {permissions.count()} permissions to 'staff' group.")

if __name__ == '__main__':
    setup_staff_permissions()
