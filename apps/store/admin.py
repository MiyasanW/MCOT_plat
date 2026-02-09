from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User, Group
from unfold.admin import ModelAdmin
from unfold.forms import AdminPasswordChangeForm, UserChangeForm, UserCreationForm
from simple_history.admin import SimpleHistoryAdmin
from import_export.admin import ImportExportModelAdmin
from .models import (
    Staff, Product, ProductionVehicle, Equipment, Studio, Booking, Package, 
    IssueReport, Notification, ProductCategory, StaffPosition,
    BookingItem, BookingStudio, BookingStaff, BookingPackage
)

@admin.register(ProductCategory)
class ProductCategoryAdmin(ModelAdmin):
    list_display = ['name', 'slug']
    prepopulated_fields = {'slug': ('name',)}

@admin.register(StaffPosition)
class StaffPositionAdmin(ModelAdmin):
    list_display = ['name', 'base_daily_rate']

admin.site.unregister(User)
admin.site.unregister(Group)

@admin.register(User)
class UserAdmin(BaseUserAdmin, ModelAdmin):
    form = UserChangeForm
    add_form = UserCreationForm
    change_password_form = AdminPasswordChangeForm

@admin.register(Group)
class GroupAdmin(ModelAdmin):
    pass

@admin.register(Staff)
class StaffAdmin(ModelAdmin, SimpleHistoryAdmin):
    list_display = ['name', 'position', 'phone', 'is_active']
    search_fields = ['name', 'phone']
    list_filter = ['position', 'is_active']

@admin.register(Product)
class ProductAdmin(ModelAdmin, ImportExportModelAdmin):
    list_display = ['name', 'category', 'price', 'quantity', 'is_active']
    search_fields = ['name']
    list_filter = ['category', 'is_active']

@admin.register(ProductionVehicle)
class ProductionVehicleAdmin(ModelAdmin):
    list_display = ['name', 'price', 'quantity', 'is_active']
    search_fields = ['name']

@admin.register(Equipment)
class EquipmentAdmin(ModelAdmin, SimpleHistoryAdmin, ImportExportModelAdmin):
    list_display = ['product', 'serial_number', 'status']
    search_fields = ['serial_number', 'product__name']
    list_filter = ['status']
    autocomplete_fields = ['product']

@admin.register(Studio)
class StudioAdmin(ModelAdmin):
    list_display = ['name', 'daily_rate']
    search_fields = ['name']

@admin.register(Booking)
class BookingAdmin(ModelAdmin, SimpleHistoryAdmin, ImportExportModelAdmin):
    list_display = ['customer_name', 'start_time', 'end_time', 'status', 'total_price_display']
    search_fields = ['customer_name', 'customer_phone']
    list_filter = ['status', 'created_at']
    date_hierarchy = 'start_time'
    
    def total_price_display(self, obj):
        return f"{obj.calculate_total_price():,.0f}"
    total_price_display.short_description = "Total Price"

@admin.register(Package)
class PackageAdmin(ModelAdmin):
    list_display = ['name', 'price', 'is_highlight', 'is_active']
    list_filter = ['is_highlight', 'is_active']

@admin.register(IssueReport)
class IssueReportAdmin(ModelAdmin, SimpleHistoryAdmin):
    list_display = ['title', 'priority', 'status', 'reporter', 'created_at']
    list_filter = ['priority', 'status']
    
@admin.register(Notification)
class NotificationAdmin(ModelAdmin):
    list_display = ['recipient', 'message', 'is_read', 'created_at']
    list_filter = ['is_read', 'notification_type']
