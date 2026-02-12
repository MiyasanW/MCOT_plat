from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User, Group
from django.contrib.admin import ModelAdmin
# from unfold.admin import ModelAdmin  <-- Removed
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
class UserAdmin(BaseUserAdmin):
    pass

@admin.register(Group)
class GroupAdmin(ModelAdmin):
    pass

@admin.register(Staff)
class StaffAdmin(SimpleHistoryAdmin):
    list_display = ['name', 'position', 'phone', 'is_active']
    search_fields = ['name', 'phone']
    list_filter = ['position', 'is_active']

from django_summernote.admin import SummernoteModelAdmin

@admin.register(Product)
class ProductAdmin(SummernoteModelAdmin, ImportExportModelAdmin):
    list_display = ['name', 'category', 'price', 'quantity', 'is_active']
    search_fields = ['name']
    list_filter = ['category', 'is_active']
    summernote_fields = ('description',)

@admin.register(ProductionVehicle)
class ProductionVehicleAdmin(ModelAdmin):
    list_display = ['name', 'price', 'quantity', 'is_active']
    search_fields = ['name']

@admin.register(Equipment)
class EquipmentAdmin(SimpleHistoryAdmin, ImportExportModelAdmin):
    list_display = ['product', 'serial_number', 'status']
    search_fields = ['serial_number', 'product__name']
    list_filter = ['status']
    autocomplete_fields = ['product']

@admin.register(Studio)
class StudioAdmin(ModelAdmin):
    list_display = ['name', 'daily_rate']
    search_fields = ['name']

@admin.register(Booking)
class BookingAdmin(SimpleHistoryAdmin, ImportExportModelAdmin):
    list_display = ['id', 'customer_name', 'status_badge', 'total_price_display', 'start_time', 'action_buttons']
    list_display_links = ['id', 'customer_name']
    search_fields = ['customer_name', 'customer_phone', 'id']
    list_filter = ['status', 'created_at']
    date_hierarchy = 'start_time'
    
    # Unfold Actions / Buttons
    actions_list = [] # Add custom buttons here if needed

    def action_buttons(self, obj):
        from django.utils.html import format_html
        from django.urls import reverse
        
        url = reverse('admin:store_booking_change', args=[obj.pk])
        return format_html(
            '<a class="button" href="{}" style="background-color: #409EFF; color: white; padding: 5px 10px; border-radius: 4px; text-decoration: none; font-weight: bold;">View / Edit</a>',
            url
        )
    action_buttons.short_description = "Actions"
    action_buttons.allow_tags = True

    def total_price_display(self, obj):
        return f"฿{obj.calculate_total_price():,.2f}"
    total_price_display.short_description = "Total Price"
    total_price_display.admin_order_field = 'total_price'

    def status_badge(self, obj):
        # Unfold specific: Use internal styling classes/logic if available, 
        # or simplified badge logic. 
        # Unfold automatically styles choices if configured, but we can customize:
        colors = {
            'pending': 'warning',
            'approved': 'success',
            'rejected': 'danger',
            'completed': 'info',
            'cancelled': 'danger',
        }
        color = colors.get(obj.status, 'secondary')
        # Return simple status context for Unfold to render, or raw HTML if needed.
        # For Unfold ModelAdmin, it often handles choices automatically.
        # Let's try leveraging the display decorator from Unfold if we had it, 
        # but standard Django html is safer for now.
        return obj.get_status_display()
    
    # Using Unfold's label capability if supported, otherwise standard.
    status_badge.short_description = "Status"
    # To actually make it a badge in Unfold, we usually define it in list_display_links or use specific Unfold methods.
    # But let's stick to standard ModelAdmin for now and see how Unfold themes it.

@admin.register(Package)
class PackageAdmin(ModelAdmin):
    list_display = ['name', 'price', 'is_highlight', 'is_active']
    list_filter = ['is_highlight', 'is_active']

@admin.register(IssueReport)
class IssueReportAdmin(SimpleHistoryAdmin):
    list_display = ['title', 'priority', 'status', 'reporter', 'created_at']
    list_filter = ['priority', 'status']
    
@admin.register(Notification)
class NotificationAdmin(ModelAdmin):
    list_display = ['recipient', 'message', 'is_read', 'created_at']
    list_filter = ['is_read', 'notification_type']
