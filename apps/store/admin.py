from django.contrib import admin
from django import forms
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User, Group
from django.contrib.admin import ModelAdmin
from simple_history.admin import SimpleHistoryAdmin
from import_export.admin import ImportExportModelAdmin
from django.utils.html import format_html
from django.utils.html import escape, strip_tags
from django.urls import reverse
import re
from html import unescape
from .models import (
    Product, ProductionVehicle, Equipment, Studio, Booking, Package,
    IssueReport, Notification, ProductCategory,
    PackageItem,
    BookingItem, BookingStudio, BookingStaff, BookingPackage,
    BookingServiceOffer, ServiceCategory, ServiceOffer,
    Profile, PromotionCode, SplashConfig
)
from apps.store.services.notification_service import NotificationService


# =============================================================================
# Helper: ตรวจ Role ของ User
# =============================================================================
def is_web_admin(user):
    """Check if user is strictly in web_admin group"""
    return user.groups.filter(name='web_admin').exists()

def is_staff_role(user):
    """Check if user is strictly in staff group"""
    return user.groups.filter(name='staff').exists()


# =============================================================================
# INLINES — แสดงรายการอุปกรณ์/สตูดิโอ/ทีมงาน/แพ็คเกจ ในหน้า Booking
# =============================================================================
class ProfileInline(admin.StackedInline):
    model = Profile
    can_delete = False
    verbose_name_plural = 'Customer Profile'
    fk_name = 'user'
    fields = ('phone', 'is_partner', 'partner_discount_percent')


class StudioHistoryInline(admin.TabularInline):
    """Read-only inline to show usage history in Studio Admin"""
    model = BookingStudio
    fk_name = 'studio'
    extra = 0
    can_delete = False
    fields = ['booking_link', 'price_at_booking']
    readonly_fields = ['booking_link', 'price_at_booking']
    verbose_name = "ประวัติการใช้งาน (Usage History)"
    verbose_name_plural = "🕒 ประวัติการใช้งาน (Usage History)"

    def has_add_permission(self, request, obj=None): return False

    @admin.display(description='Booking')
    def booking_link(self, obj):
        return format_html(
            '<a href="{}">#{} - {}</a><br><span style="color:#666; font-size:11px;">{} - {}</span>',
            reverse('admin:store_booking_change', args=[obj.booking.id]),
            obj.booking.id,
            obj.booking.customer_name,
            obj.booking.start_time.strftime('%d/%m/%Y'),
            obj.booking.end_time.strftime('%d/%m/%Y')
        )

# --- REFACTORED BOOKING ITEM INLINE ---
class BookingItemInline(admin.TabularInline):
    model = BookingItem
    extra = 1
    autocomplete_fields = ['product', 'equipment']
    fields = ['product', 'quantity', 'price_at_booking', 'equipment', 'status', 'returned_at', 'notes']
    readonly_fields = ['price_at_booking']
    
    verbose_name = "รายการสินค้า & เบิกจ่าย (Items & Assignment)"
    verbose_name_plural = "🛒 รายการสินค้าและจับคู่อุปกรณ์ (Items & Equipment)"

    def get_readonly_fields(self, request, obj=None):
        base = ['price_at_booking']
        return base


class BookingStudioInline(admin.TabularInline):
    model = BookingStudio
    extra = 0
    autocomplete_fields = ['studio']
    fields = ['studio', 'price_at_booking']
    readonly_fields = ['price_at_booking']


class BookingStaffInline(admin.TabularInline):
    model = BookingStaff
    extra = 0
    autocomplete_fields = ['staff']  # points to User now, make sure UserAdmin has search_fields.
    fields = ['staff']


class BookingPackageInline(admin.TabularInline):
    model = BookingPackage
    extra = 0
    autocomplete_fields = ['package']
    fields = ['package', 'quantity', 'price_at_booking']
    readonly_fields = ['price_at_booking']

class BookingServiceOfferInline(admin.TabularInline):
    model = BookingServiceOffer
    extra = 0
    autocomplete_fields = ['service']
    fields = ['service', 'quantity', 'price_at_booking']
    readonly_fields = ['price_at_booking']


# =============================================================================
# LOOKUP MODELS — search_fields สำหรับ autocomplete
# =============================================================================
@admin.register(ProductCategory)
class ProductCategoryAdmin(ModelAdmin):
    list_display = ['name', 'slug']
    prepopulated_fields = {'slug': ('name',)}

@admin.register(SplashConfig)
class SplashConfigAdmin(ModelAdmin):
    list_display = ['__str__', 'is_active', 'title']
    fields = ['is_active', 'title', 'message', 'image']
    
    def has_add_permission(self, request):
        has_add = super().has_add_permission(request)
        if has_add and SplashConfig.objects.exists():
            return False
        return has_add
    search_fields = ['name']


@admin.register(ServiceCategory)
class ServiceCategoryAdmin(ModelAdmin):
    list_display = ['name', 'slug']
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ['name']

@admin.register(ServiceOffer)
class ServiceOfferAdmin(ImportExportModelAdmin):
    list_display = ['name', 'category', 'daily_rate', 'is_active']
    search_fields = ['name']
    list_filter = ['category', 'is_active']


# =============================================================================
# AUTH — User/Group
# =============================================================================
admin.site.unregister(User)
admin.site.unregister(Group)

@admin.register(User)
class UserAdmin(BaseUserAdmin):
    inlines = (ProfileInline,)
    list_display = ('username', 'email', 'first_name', 'last_name', 'get_phone', 'is_staff')
    search_fields = ('username', 'email', 'first_name', 'last_name')
    
    def get_phone(self, obj):
        return obj.profile.phone if hasattr(obj, 'profile') else '-'
    get_phone.short_description = 'Phone'

    # Protect User Management
    def has_view_permission(self, request, obj=None):
        return request.user.is_superuser or is_web_admin(request.user)
    
    def has_add_permission(self, request):
        return request.user.is_superuser or is_web_admin(request.user)

    def has_change_permission(self, request, obj=None):
        return request.user.is_superuser or is_web_admin(request.user)
    
    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser # Only Superuser can delete users

    def has_module_permission(self, request):
        return request.user.is_superuser or is_web_admin(request.user)

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        Profile.objects.get_or_create(user=obj)

@admin.register(PromotionCode)
class PromotionCodeAdmin(ModelAdmin):
    list_display = ['code', 'discount_percent', 'discount_amount', 'valid_from', 'valid_to', 'is_active']
    search_fields = ['code']
    list_filter = ['is_active', 'valid_from', 'valid_to']

@admin.register(Profile)
class ProfileAdmin(ModelAdmin):
    list_display = ['user', 'phone']
    search_fields = ['user__username', 'user__email', 'phone']

    def has_module_permission(self, request):
        return request.user.is_superuser or is_web_admin(request.user)

@admin.register(Group)
class GroupAdmin(ModelAdmin):
    def has_module_permission(self, request):
        return request.user.is_superuser or is_web_admin(request.user)


# =============================================================================
# RESOURCE MODELS — Product, Studio, Equipment, Vehicle
# =============================================================================

# Slug ที่ใช้แยก ยานพาหนะ ออกจากสินค้าทั่วไป
VEHICLE_CATEGORY_SLUG = 'vehicle'


def normalize_description_input(value):
    """Allow plain text input in admin and convert it into simple HTML blocks."""
    if not value:
        return value

    text = value.strip()
    if not text:
        return ""

    # If admin already pasted HTML, keep it as-is.
    if re.search(r'</?[a-zA-Z][^>]*>', text):
        return value

    lines = [line.rstrip() for line in text.splitlines()]
    parts = []
    in_list = False

    for raw in lines:
        line = raw.strip()
        if not line:
            if in_list:
                parts.append('</ul>')
                in_list = False
            continue

        if line.startswith('- ') or line.startswith('* '):
            if not in_list:
                parts.append('<ul>')
                in_list = True
            parts.append(f'<li>{escape(line[2:].strip())}</li>')
        else:
            if in_list:
                parts.append('</ul>')
                in_list = False
            parts.append(f'<p>{escape(line)}</p>')

    if in_list:
        parts.append('</ul>')

    return ''.join(parts)


def description_html_to_plain_text(value):
    """Convert stored HTML description into plain text for easier editing in admin."""
    if not value:
        return value

    text = value.strip()
    if not text:
        return ""

    if not re.search(r'</?[a-zA-Z][^>]*>', text):
        return value

    text = re.sub(r'<\s*br\s*/?\s*>', '\n', text, flags=re.IGNORECASE)
    text = re.sub(r'<\s*/\s*p\s*>', '\n\n', text, flags=re.IGNORECASE)
    text = re.sub(r'<\s*p[^>]*\s*>', '', text, flags=re.IGNORECASE)
    text = re.sub(r'<\s*li[^>]*\s*>', '- ', text, flags=re.IGNORECASE)
    text = re.sub(r'<\s*/\s*li\s*>', '\n', text, flags=re.IGNORECASE)
    text = re.sub(r'<\s*/?\s*(ul|ol)[^>]*\s*>', '\n', text, flags=re.IGNORECASE)
    text = strip_tags(text)
    text = unescape(text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()


class PlainDescriptionAdminForm(forms.ModelForm):
    """Admin form that always shows description as plain text with simple guidance."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if 'description' in self.fields:
            self.fields['description'].widget = forms.Textarea(attrs={
                'rows': 6,
                'placeholder': 'พิมพ์รายละเอียดปกติได้เลย (ไม่ต้องใส่ HTML)\nใช้ - ขึ้นต้นบรรทัดเพื่อทำรายการย่อยอัตโนมัติ'
            })
            current = self.initial.get('description')
            if current is None and getattr(self.instance, 'pk', None):
                current = self.instance.description
            self.initial['description'] = description_html_to_plain_text(current)


class ProductAdminForm(PlainDescriptionAdminForm):
    class Meta:
        model = Product
        fields = '__all__'


class ProductionVehicleAdminForm(PlainDescriptionAdminForm):
    class Meta:
        model = ProductionVehicle
        fields = '__all__'


@admin.register(Product)
class ProductAdmin(ImportExportModelAdmin):
    form = ProductAdminForm
    list_display = ['name', 'category', 'price', 'quantity', 'is_active']
    search_fields = ['name']
    list_filter = ['category', 'is_active']
    exclude = ('turnaround_time',)

    def get_queryset(self, request):
        """ซ่อนสินค้าที่อยู่ในหมวด 'ยานพาหนะ' — ให้จัดการผ่านหน้า Vehicles แทน"""
        return super().get_queryset(request).exclude(category__slug=VEHICLE_CATEGORY_SLUG)

    def has_view_permission(self, request, obj=None):
        return request.user.is_superuser or is_web_admin(request.user) or is_staff_role(request.user)

    def has_change_permission(self, request, obj=None):
        return request.user.is_superuser or is_web_admin(request.user)

    def has_add_permission(self, request):
        return request.user.is_superuser or is_web_admin(request.user)

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser or is_web_admin(request.user)

    def save_model(self, request, obj, form, change):
        obj.description = normalize_description_input(form.cleaned_data.get('description'))
        super().save_model(request, obj, form, change)


@admin.register(ProductionVehicle)
class ProductionVehicleAdmin(ModelAdmin):
    form = ProductionVehicleAdminForm
    list_display = ['name', 'price', 'quantity', 'is_active']
    search_fields = ['name']
    list_filter = ['is_active']
    exclude = ('turnaround_time',)

    def get_queryset(self, request):
        """แสดงเฉพาะสินค้าในหมวด 'ยานพาหนะ'"""
        return super().get_queryset(request).filter(category__slug=VEHICLE_CATEGORY_SLUG)

    def save_model(self, request, obj, form, change):
        """Auto-assign หมวด 'ยานพาหนะ' เมื่อเพิ่มยานพาหนะใหม่"""
        from apps.store.models import ProductCategory
        vehicle_cat, _ = ProductCategory.objects.get_or_create(
            slug=VEHICLE_CATEGORY_SLUG,
            defaults={'name': 'ยานพาหนะ'},
        )
        obj.category = vehicle_cat
        obj.description = normalize_description_input(form.cleaned_data.get('description'))
        super().save_model(request, obj, form, change)

    def has_view_permission(self, request, obj=None):
        return request.user.is_superuser or is_web_admin(request.user) or is_staff_role(request.user)

    def has_change_permission(self, request, obj=None):
        return request.user.is_superuser or is_web_admin(request.user)

    def has_add_permission(self, request):
        return request.user.is_superuser or is_web_admin(request.user)

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser or is_web_admin(request.user)


@admin.register(Equipment)
class EquipmentAdmin(SimpleHistoryAdmin, ImportExportModelAdmin):
    # Added 'usage_count' and 'last_used' to list display
    list_display = ['asset_tag', 'serial_number', 'product', 'status', 'usage_count', 'last_used']
    list_display_links = ['asset_tag', 'serial_number']
    # Added inventory_number to search fields
    search_fields = ['serial_number', 'inventory_number', 'asset_tag', 'product__name']
    list_filter = ['status', 'product__category', 'product']
    autocomplete_fields = ['product']

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs

    @admin.display(description='ใช้งาน (ครั้ง)')
    def usage_count(self, obj):
        # Count from BookingItem directly (where equipment is assigned)
        return obj.bookingitem_set.count()

    @admin.display(description='ใช้งานล่าสุด')
    def last_used(self, obj):
        # Last booking item using this equipment
        # Order by booking__start_time to get the latest usage
        last = obj.bookingitem_set.select_related('booking').order_by('-booking__start_time').first()
        if last:
            return f"{last.booking.start_time.strftime('%d/%m/%Y')} (#{last.booking.id})"
        return "-"

    def has_view_permission(self, request, obj=None):
        return request.user.is_superuser or is_web_admin(request.user) or is_staff_role(request.user)

    def has_change_permission(self, request, obj=None):
        return request.user.is_superuser or is_web_admin(request.user)
    
    def has_add_permission(self, request):
        return request.user.is_superuser or is_web_admin(request.user)
    
    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser or is_web_admin(request.user)


@admin.register(Studio)
class StudioAdmin(ModelAdmin):
    list_display = ['name', 'daily_rate', 'usage_count', 'last_used', 'image_thumb']
    search_fields = ['name']
    inlines = [StudioHistoryInline]
    readonly_fields = ['image_thumb']

    @admin.display(description='รูปภาพ')
    def image_thumb(self, obj):
        if obj.image:
            return format_html('<img src="{}" style="height:60px;border-radius:4px;">', obj.image.url)
        return "-"

    @admin.display(description='ใช้งาน (ครั้ง)')
    def usage_count(self, obj):
        return obj.bookingstudio_set.count()

    @admin.display(description='ใช้งานล่าสุด')
    def last_used(self, obj):
        # Sort by booking start_time via the related booking
        last = obj.bookingstudio_set.select_related('booking').order_by('-booking__start_time').first()
        if last:
            return f"{last.booking.start_time.strftime('%d/%m/%Y')} (#{last.booking.id})"
        return "-"

    def has_view_permission(self, request, obj=None):
        return request.user.is_superuser or is_web_admin(request.user) or is_staff_role(request.user)

    def has_change_permission(self, request, obj=None):
        return request.user.is_superuser or is_web_admin(request.user)
    
    def has_add_permission(self, request):
        return request.user.is_superuser or is_web_admin(request.user)
    
    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser or is_web_admin(request.user)


# =============================================================================
# BOOKING ADMIN — หัวใจหลัก (ปรับให้ใช้ง่าย)
# =============================================================================
@admin.register(Booking)
class BookingAdmin(SimpleHistoryAdmin, ImportExportModelAdmin):
    # --- List View ---
    list_display = ['id', 'booking_summary_link', 'customer_name', 'project_name', 'coordinator', 'status_badge', 'payment_status', 'payment_slip_preview',
                     'total_price_display', 'penalty_amount', 'start_time', 'end_time']
    list_display_links = ['id', 'customer_name']
    search_fields = ['customer_name', 'project_name', 'phone', 'id']
    search_help_text = 'ค้นหาด้วย ชื่อลูกค้า, ชื่อโปรเจค, เบอร์โทร, หรือ เลขที่จอง'
    list_filter = ['status', 'payment_status', 'created_at']
    date_hierarchy = 'start_time'
    autocomplete_fields = ['coordinator']
    list_per_page = 25
    save_on_top = True

    def get_list_display(self, request):
        """Staff เห็นคอลัมน์หลักที่อ่านง่ายก่อน ลดความแน่นของข้อมูล"""
        if request.user.is_superuser or is_web_admin(request.user):
            return self.list_display
        return [
            'id',
            'customer_name',
            'project_name',
            'status_badge',
            'payment_status',
            'start_time',
            'end_time',
            'booking_summary_link',
        ]

    def get_list_filter(self, request):
        if request.user.is_superuser or is_web_admin(request.user):
            return self.list_filter
        return ['status', 'payment_status']

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "coordinator":
            from django.contrib.auth.models import User
            # Limit the dropdown to only show users in the "staff" group
            kwargs["queryset"] = User.objects.filter(groups__name='staff')
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    # --- Inlines ---
    # BookingItemInline now has equipment fields
    inlines = [BookingItemInline, BookingStudioInline, BookingStaffInline, BookingPackageInline, BookingServiceOfferInline]

    # --- Batch Actions ---
    actions = ['action_request_payment', 'action_approve', 'action_confirm_payment', 'action_cancel', 'action_mark_active', 'action_mark_overdue', 'action_mark_completed', 'action_calculate_penalty']

    @admin.action(description='⚠️ คำนวณค่าปรับคืนช้า (Calculate Penalty)')
    def action_calculate_penalty(self, request, queryset):
        if not (request.user.is_superuser or is_web_admin(request.user)):
             self.message_user(request, '❌ คุณไม่มีสิทธิ์', level='error')
             return
        
        count = 0
        from django.utils import timezone
        
        for booking in queryset:
            penalty = 0
            # ตรวจสอบแต่ละอุปกรณ์ที่ถูกยืม ว่าคืนช้าไหม
            for item in booking.items.all():
                if item.returned_at and item.returned_at > booking.end_time:
                    days_late = (item.returned_at.date() - booking.end_time.date()).days
                    if days_late > 0 and item.product.late_fee_per_day:
                        penalty += (days_late * item.product.late_fee_per_day)
            
            if penalty > 0:
                booking.penalty_amount = penalty
                # อัปเดตยอดรวมใหม่ (บวกค่าปรับ)
                booking.total_price = booking.calculate_total_price()
                booking.save(update_fields=['penalty_amount', 'total_price'])
                count += 1

        self.message_user(request, f'⚠️ อัปเดตยอดค่าปรับแล้ว {count} รายการ')

    @admin.action(description='💰 ยืนยันการชำระเงิน (Confirm Payment)')
    def action_confirm_payment(self, request, queryset):
        if not (request.user.is_superuser or is_web_admin(request.user)):
             self.message_user(request, '❌ คุณไม่มีสิทธิ์', level='error')
             return
        updated = queryset.filter(payment_status='pending').update(payment_status='paid')
        self.message_user(request, f'💰 ยืนยันการชำระเงินแล้ว {updated} รายการ')

    @admin.action(description='📨 ขอเรียกเก็บมัดจำ (Request Payment)')
    def action_request_payment(self, request, queryset):
        if not (request.user.is_superuser or is_web_admin(request.user)):
             self.message_user(request, '❌ คุณไม่มีสิทธิ์', level='error')
             return
             
        from django.utils import timezone
        from datetime import timedelta
        from apps.store.services.notification_service import NotificationService
        from apps.store.services.pricing_service import PricingService
        
        count = 0
        for booking in queryset.filter(status='draft'):
            totals = PricingService.calculate_booking_total(booking)
            booking.total_price = totals['grand_total']
            booking.discount_amount = totals['discount']
            booking.deposit_amount = PricingService.calculate_deposit(totals['grand_total'])
            booking.status = 'pending'
            booking.expires_at = timezone.now() + timedelta(hours=24) # ให้เวลาชำระเงิน 24 ชม. หลังจากกดขอเรียกเก็บ
            booking.save(update_fields=['total_price', 'discount_amount', 'deposit_amount', 'status', 'expires_at'])
            NotificationService.send_notification(booking, 'pending_deposit')
            count += 1
            
        self.message_user(request, f'📨 ส่งเรื่องขอเรียกเก็บเงินแล้ว {count} รายการ')

    @admin.action(description='✅ อนุมัติ (Approve)')
    def action_approve(self, request, queryset):
        if not (request.user.is_superuser or is_web_admin(request.user)):
             self.message_user(request, '❌ คุณไม่มีสิทธิ์อนุมัติ', level='error')
             return
        # updated = queryset.filter(status__in=['draft', 'pending']).update(status='approved')
        # loop to trigger notifications
        count = 0
        for booking in queryset:
            if not booking.can_staff_cancel():
                continue
            booking.status = 'approved'
            booking.save()
            NotificationService.send_notification(booking, 'approved')
            count += 1
            
        self.message_user(request, f'✅ อนุมัติการจองแล้ว {count} รายการ (ส่งอีเมลแจ้งลูกค้าแล้ว)')

    def booking_summary_link(self, obj):
        from django.urls import reverse
        from django.utils.html import format_html
        url = reverse('store:staff_booking_summary', args=[obj.id])
        return format_html('<a class="button" href="{}" target="_blank" style="background-color: #ff6b00 !important; color: white !important; padding: 4px 10px !important; border-radius: 4px !important; font-weight: bold !important; text-decoration: none !important; white-space: nowrap !important; display: inline-block !important; font-size: 11px !important;">🔍 Summary</a>', url)
    booking_summary_link.short_description = "Staff View"

    @admin.action(description='❌ ยกเลิก (Cancel)')
    def action_cancel(self, request, queryset):
        if not (request.user.is_superuser or is_web_admin(request.user)):
             self.message_user(request, '❌ คุณไม่มีสิทธิ์ยกเลิก', level='error')
             return
        # updated = queryset.exclude(status__in=['completed', 'cancelled']).update(status='cancelled')
        # loop to trigger notifications
        count = 0
        for booking in queryset.exclude(status__in=['completed', 'cancelled']):
            booking.status = 'cancelled'
            booking.save()
            NotificationService.send_notification(booking, 'cancelled')
            count += 1

        self.message_user(request, f'❌ ยกเลิกแล้ว {count} รายการ')

    @admin.action(description='▶ เริ่มใช้งาน (Active)')
    def action_mark_active(self, request, queryset):
        updated = 0
        blocked = 0
        for booking in queryset:
            if booking.can_mark_active() and booking.has_complete_equipment_assignment():
                booking.status = 'active'
                booking.save(update_fields=['status'])
                updated += 1
            elif booking.can_mark_active():
                blocked += 1
        self.message_user(request, f'▶ เปิดใช้งานแล้ว {updated} รายการ')
        if blocked:
            self.message_user(request, f'⚠️ ข้าม {blocked} รายการ: ยังไม่ได้ assign Serial/Asset ครบ', level='warning')

    @admin.action(description='✔ คืนของครบ (Completed)')
    def action_mark_completed(self, request, queryset):
        # We can complete from active or overdue
        updated = 0
        for booking in queryset:
            if booking.can_mark_completed():
                booking.status = 'completed'
                booking.save(update_fields=['status'])
                updated += 1
        self.message_user(request, f'✔ คืนของครบแล้ว {updated} รายการ')

    @admin.action(description='⚠️ เกินกำหนด (Overdue)')
    def action_mark_overdue(self, request, queryset):
        updated = queryset.filter(status='active').update(status='overdue')
        from django.contrib import messages
        self.message_user(request, f'⚠️ ปรับเป็นเกินกำหนดแล้ว {updated} รายการ', level=messages.WARNING)

    # --- Permissions and Querysets ---
    def get_queryset(self, request):
        # Allow all roles (superuser, web_admin, staff) to see all bookings
        qs = super().get_queryset(request)
        return qs
        
    def has_view_permission(self, request, obj=None):
        return request.user.is_superuser or is_web_admin(request.user) or is_staff_role(request.user)

    def has_add_permission(self, request):
        return request.user.is_superuser or is_web_admin(request.user) or is_staff_role(request.user)

    def has_change_permission(self, request, obj=None):
        # Staff can edit (but fields are limited by get_readonly_fields)
        return request.user.is_superuser or is_web_admin(request.user) or is_staff_role(request.user)

    def has_delete_permission(self, request, obj=None):
        # Only Superuser/WebAdmin can delete
        return request.user.is_superuser or is_web_admin(request.user)

    def has_module_permission(self, request):
        return request.user.is_superuser or is_web_admin(request.user) or is_staff_role(request.user)

    # --- Custom columns ---
    @admin.display(description='Total Price', ordering='id')
    def total_price_display(self, obj):
        try:
            total = obj.calculate_total_price()
            return format_html(
                '<span style="font-weight:bold; color:#F26522;">฿{:,.2f}</span>',
                total
            )
        except Exception:
            return '—'

    @admin.display(description='Payment Slip')
    def payment_slip_preview(self, obj):
        if obj.payment_slip:
            return format_html(
                '<a href="{}" target="_blank"><img src="{}" style="height:40px !important; max-width:60px !important; object-fit:cover !important; border-radius:4px !important; border:1px solid #ccc !important;"></a>',
                obj.payment_slip.url,
                obj.payment_slip.url
            )
        return '-'

    @admin.display(description='รูปสลิปขนาดใหญ่ (Large Preview)')
    def payment_slip_large_preview(self, obj):
        if obj.payment_slip:
            return format_html(
                '<a href="{}" target="_blank">'
                '<img src="{}" style="max-height:400px; max-width:100%; border-radius:8px; border:1px solid #555; box-shadow:0 4px 15px rgba(0,0,0,0.3);">'
                '</a><br><span style="color:#aaa; font-size:12px;">(คลิกที่รูปเพื่อดูขนาดเต็ม)</span>',
                obj.payment_slip.url,
                obj.payment_slip.url
            )
        return '—'

    @admin.display(description='Status')
    def status_badge(self, obj):
        colors = {
            'draft': ('#FFC107', '#000'),
            'pending': ('#2196F3', '#fff'),
            'approved': ('#4CAF50', '#fff'),
            'active': ('#FF9800', '#fff'),
            'overdue': ('#D32F2F', '#fff'),
            'completed': ('#9E9E9E', '#fff'),
            'cancelled': ('#f44336', '#fff'),
        }
        bg, fg = colors.get(obj.status, ('#666', '#fff'))
        return format_html(
            '<span style="background:{}; color:{}; padding:4px 10px; border-radius:12px; '
            'font-size:11px; font-weight:bold; white-space:nowrap;">{}</span>',
            bg, fg, obj.get_status_display()
        )

    # --- ซ่อน batch actions จาก staff ที่ไม่มีสิทธิ์ ---
    def get_actions(self, request):
        actions = super().get_actions(request)
        if not (request.user.is_superuser or is_web_admin(request.user)):
            # Staff: เห็นแค่ mark_active และ mark_completed
            actions.pop('action_approve', None)
            actions.pop('action_cancel', None)
            actions.pop('action_confirm_payment', None)
            actions.pop('action_request_payment', None)
            actions.pop('action_mark_overdue', None)
            actions.pop('action_calculate_penalty', None)
        return actions

    # --- Fieldsets (จัดกลุ่ม) ---
    def get_fieldsets(self, request, obj=None):
        base_fieldsets = [
            ('📋 ข้อมูลลูกค้า', {
                'fields': ('customer_name', 'phone', 'project_name'),
            }),
            ('👤 ผู้ประสานงาน', {
                'fields': ('coordinator',),
            }),
            ('📅 ระยะเวลา', {
                'fields': ('start_time', 'end_time'),
            }),
            ('💰 การชำระเงิน', {
                'fields': ('total_price', 'deposit_amount', 'payment_status', 'payment_slip', 'payment_slip_large_preview', 'promotion', 'discount_amount', 'penalty_amount'),
            }),
            ('📄 เอกสาร (Documents)', {
                'fields': ('print_equipment_sheet', 'print_quotation'),
            }),
            ('📝 หมายเหตุ', {
                'fields': ('note',),
                # 'classes': ('collapse',),  <-- เอาออกเพื่อให้แสดงเลย
            }),
        ]

        # Staff ธรรมดา: ซ่อน status + created_by
        if request.user.is_superuser or is_web_admin(request.user):
            base_fieldsets.insert(0, ('⚡ สถานะ', {
                'fields': ('status', 'created_by', 'created_at'),
            }))
        else:
            # Staff เห็น status เป็น readonly แต่ไม่เห็น created_by
            base_fieldsets.append(('สถานะ', {
                'fields': ('status',),
            }))

        return base_fieldsets

    def get_readonly_fields(self, request, obj=None):
        readonly = ['created_at', 'total_price', 'deposit_amount', 'discount_amount', 'payment_slip_large_preview', 'print_equipment_sheet', 'print_quotation'] # Automation fields

        if not (request.user.is_superuser or is_web_admin(request.user)):
            # Staff: แก้ status, payment, coordinator ไม่ได้
            readonly += ['status', 'coordinator', 'payment_status', 'payment_slip']

        if obj:  # Editing existing
            readonly += ['created_by']

        return readonly

    @admin.display(description='🖨️ ใบจ่ายงาน (Equipment Sheet)')
    def print_equipment_sheet(self, obj):
        if not obj or not obj.id:
            return '-'
        url = reverse('store:download_booking_pdf', args=[obj.id])
        return format_html(
            '<a class="button" href="{}" target="_blank" style="background-color:#6c757d; color:white; padding:8px 15px; border-radius:4px; text-decoration:none;">🖨️ Print PDF</a>',
            url
        )

    @admin.display(description='📄 ใบเสนอราคา (Quotation)')
    def print_quotation(self, obj):
        if not obj or not obj.id:
            return '-'
        url = reverse('store:download_quotation_pdf', args=[obj.id])
        return format_html(
            '<a class="button" href="{}" target="_blank" style="background-color:#17a2b8; color:white; padding:8px 15px; border-radius:4px; text-decoration:none;">📄 Download Quote</a>',
            url
        )



# =============================================================================
# PACKAGE, ISSUE REPORT, NOTIFICATION
# =============================================================================
@admin.register(Package)
class PackageAdmin(ModelAdmin):
    class PackageItemInline(admin.TabularInline):
        model = PackageItem
        extra = 1
        autocomplete_fields = ['product']
        fields = ['product', 'quantity']

    list_display = ['name', 'price', 'item_count', 'is_highlight', 'is_active']
    list_filter = ['is_highlight', 'is_active']
    search_fields = ['name', 'short_description', 'description']
    inlines = [PackageItemInline]
    list_per_page = 25
    save_on_top = True

    @admin.display(description='จำนวนรายการย่อย')
    def item_count(self, obj):
        return obj.packageitem_set.count()

    def has_view_permission(self, request, obj=None):
        return request.user.is_superuser or is_web_admin(request.user) or is_staff_role(request.user)

    def has_change_permission(self, request, obj=None):
        return request.user.is_superuser or is_web_admin(request.user)
    
    def has_add_permission(self, request):
        return request.user.is_superuser or is_web_admin(request.user)
    
    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser or is_web_admin(request.user)


@admin.register(IssueReport)
class IssueReportAdmin(SimpleHistoryAdmin):
    list_display = ['title', 'priority', 'status', 'reporter', 'created_at']
    list_filter = ['priority', 'status']

    def has_module_permission(self, request):
        return request.user.is_superuser or is_web_admin(request.user)


@admin.register(Notification)
class NotificationAdmin(ModelAdmin):
    list_display = ['recipient', 'message', 'is_read', 'created_at']
    list_filter = ['is_read', 'notification_type']

    def has_module_permission(self, request):
        return request.user.is_superuser or is_web_admin(request.user) or is_staff_role(request.user)


# =============================================================================
# ADMIN SITE CONFIG
# =============================================================================
admin.site.site_header = 'MCOT Equipment Service — ระบบจัดการ'
admin.site.site_title = 'MCOT Equipment Service Admin'
admin.site.index_title = 'หน้าแรก'
