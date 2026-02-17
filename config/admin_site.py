"""
Custom AdminSite — controls app/model ordering in the sidebar.
Patches Django's default admin.site so sidebar + dashboard both use this ordering.
"""
from django.contrib.admin import AdminSite as _OriginalAdminSite

# Desired app order (by app_label)
APP_ORDER = [
    'store',              # ระบบจัดการการเช่า — first
    'auth',               # Authentication — second
    'django_summernote',  # Summernote — last
]

# Desired model order within the 'store' app (by object_name)
STORE_MODEL_ORDER = [
    'Booking',            # 📋 รายการจอง — core business
    'Product',            # 📦 สินค้า
    'ProductionVehicle',  # 🚗 ยานพาหนะ
    'Studio',             # 🎬 สตูดิโอ
    'Staff',              # 👤 พนักงาน
    'Equipment',          # 🔧 อุปกรณ์รายชิ้น
    'Package',            # 📦 แพ็คเกจ
    'ProductCategory',    # ⚙ หมวดหมู่
    'StaffPosition',      # ⚙ ตำแหน่ง
    'IssueReport',        # 🔔 Issue reports
    'Notification',       # 🔔 Notifications
]


class MCOTAdminSite(_OriginalAdminSite):
    """Override get_app_list to control ordering."""

    def get_app_list(self, request, app_label=None):
        app_list = super().get_app_list(request, app_label=app_label)

        # Sort apps by APP_ORDER
        def app_sort_key(app):
            label = app['app_label']
            try:
                return APP_ORDER.index(label)
            except ValueError:
                return len(APP_ORDER)

        app_list.sort(key=app_sort_key)

        # Sort models within the store app
        for app in app_list:
            if app['app_label'] == 'store':
                def model_sort_key(model):
                    name = model.get('object_name', '')
                    try:
                        return STORE_MODEL_ORDER.index(name)
                    except ValueError:
                        return len(STORE_MODEL_ORDER)
                app['models'].sort(key=model_sort_key)

        return app_list
