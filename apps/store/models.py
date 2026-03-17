from django.db import models
from django.core.exceptions import ValidationError
from django.db.models import Q
from django.utils import timezone
from simple_history.models import HistoricalRecords
from datetime import timedelta
from django.contrib.auth.models import User, Group

# --- 1. Dynamic Configuration Models ---
class SplashConfig(models.Model):
    """ตั้งค่าหน้า Splash Screen (เช่น น้อมสำนึกในพระมหากรุณาธิคุณ) ก่อนเข้าเว็บ"""
    is_active = models.BooleanField(default=False, verbose_name="เปิดใช้งาน Splash Screen")
    title = models.CharField(max_length=200, default="น้อมสำนึกในพระมหากรุณาธิคุณอันหาที่สุดมิได้", verbose_name="หัวข้อข้อความ")
    message = models.TextField(default="ข้าพระพุทธเจ้า คณะกรรมการ ผู้บริหาร พนักงานและลูกจ้าง\nบริษัท อสมท จำกัด (มหาชน)", verbose_name="เนื้อหาข้อความ")
    image = models.ImageField(upload_to='splash/', blank=True, null=True, verbose_name="รูปภาพพระบรมฉายาลักษณ์ / รูปภาพพื้นหลัง")

    class Meta:
        verbose_name_plural = "ตั้งค่า - Splash Screen"

    def __str__(self):
        return "ตั้งค่าหน้าจอ Splash Screen"

    def clean(self):
        from django.core.exceptions import ValidationError
        if not self.pk and SplashConfig.objects.exists():
            raise ValidationError('มีแท็บตั้งค่า Splash Screen อยู่แล้ว ไม่สามารถสร้างเพิ่มได้ โปรดแก้ไขอันเดิม')

class ProductCategory(models.Model):
    """หมวดหมู่สินค้า (เช่น กล้อง, เลนส์, ไฟ, รถ OB)"""
    name = models.CharField(max_length=100, unique=True, verbose_name="ชื่อหมวดหมู่")
    slug = models.SlugField(max_length=100, unique=True, verbose_name="URL Slug")
    
    def __str__(self): return self.name
    class Meta: verbose_name_plural = "ตั้งค่า - หมวดหมู่สินค้า"

# Staff roles are now handled entirely by django.contrib.auth.models.User and Group

class PromotionCode(models.Model):
    """โค้ดโปรโมชั่น / ส่วนลด"""
    code = models.CharField(max_length=50, unique=True, verbose_name="โค้ดส่วนลด")
    discount_percent = models.IntegerField(default=0, verbose_name="ส่วนลด (เปอร์เซ็นต์ %)", help_text="ใส่ 0 หากต้องการใช้ส่วนลดเป็นจำนวนเงิน")
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, verbose_name="ส่วนลด (จำนวนบาท)", help_text="ใส่ 0 หากต้องการใช้ส่วนลดเป็น %")
    valid_from = models.DateTimeField(verbose_name="เริ่มใช้ได้ตั้งแต่")
    valid_to = models.DateTimeField(verbose_name="หมดอายุ")
    is_active = models.BooleanField(default=True, verbose_name="สถานะใช้งาน")

    def is_valid(self):
        now = timezone.now()
        return self.is_active and self.valid_from <= now <= self.valid_to

    def __str__(self): return self.code
    class Meta: verbose_name_plural = "ตั้งค่า - โค้ดส่วนลด (Promotions)"

# --- 2. Resource Models ---
class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    phone = models.CharField(max_length=20, verbose_name="เบอร์โทรศัพท์", blank=True, null=True)
    is_partner = models.BooleanField(default=False, verbose_name="สิทธิพาร์ทเนอร์ (Partner)")
    partner_discount_percent = models.IntegerField(default=10, verbose_name="เปอร์เซ็นต์ส่วนลดพาร์ทเนอร์")
    
    def __str__(self): return f"Profile of {self.user.username}"
    class Meta: verbose_name_plural = "โปรไฟล์ผู้ใช้ (Profiles)"

# Profile auto-creation via signals is removed to prevent IntegrityError with Admin inlines.
# Profile creation is now explicitly handled in UserAdmin (via ProfileInline) and UserRegisterForm.

from django.db.models.signals import m2m_changed
from django.dispatch import receiver

@receiver(m2m_changed, sender=User.groups.through)
def auto_assign_is_staff(sender, instance, action, pk_set, **kwargs):
    """
    Automatically set `is_staff=True` when a user is added to the 'staff' group
    so they can actually log into the Django Admin panel.
    """
    if action == "post_add":
        if Group.objects.filter(pk__in=pk_set, name='staff').exists():
            if not instance.is_staff:
                instance.is_staff = True
                instance.save(update_fields=['is_staff'])

# Staff model removed - we now use User and Groups directly.

class Product(models.Model):
    name = models.CharField(max_length=200, verbose_name="ชื่อสินค้า")
    description = models.TextField(verbose_name="รายละเอียด", blank=True, null=True)
    category = models.ForeignKey(ProductCategory, on_delete=models.SET_NULL, null=True, verbose_name="หมวดหมู่")
    image = models.ImageField(upload_to='products/', null=True, blank=True, verbose_name="รูปภาพ")
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="ราคาเช่าต่อวัน")
    quantity = models.IntegerField(default=1, verbose_name="จำนวนทั้งหมด")
    late_fee_per_day = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, verbose_name="ค่าปรับส่งคืนช้า (ต่อวัน)")
    turnaround_time = models.DurationField(default=timedelta(hours=1), verbose_name="เวลาในการเตรียมของ (Buffer Time)", help_text="เวลาที่ต้องเว้นว่างหลังคืนของ เพื่อเช็ค/ทำความสะอาด")
    is_active = models.BooleanField(default=True, verbose_name="เปิดให้เช่า")
    is_featured = models.BooleanField(default=False, verbose_name="แนะนำ (Featured)")
    created_at = models.DateTimeField(auto_now_add=True, null=True, verbose_name="วันที่เพิ่ม")

    class Meta: verbose_name_plural = "ทรัพยากร - สินค้า (Product)"
    def __str__(self): return self.name
    
    @property
    def remaining_quantity(self):
        # (Logic คำนวณคงเหลือเหมือนเดิม - จะย้ายไป AvailabilityService เพื่อความ Clean)
        return 0 # Placeholder for now

    @property
    def key_specs(self):
        """Extracts the first 3 bullet points from the HTML description."""
        if not self.description:
            return []
        import re
        # Find all <li> content
        items = re.findall(r'<li>(.*?)</li>', self.description, re.DOTALL)
        return [item.strip() for item in items[:3]]
class ProductionVehicle(Product):
    class Meta:
        proxy = True
        verbose_name = "ยานพาหนะ (Vehicle)"
        verbose_name_plural = "จัดการยานพาหนะ (Vehicles)"
        ordering = ['name']

    def save(self, *args, **kwargs):
        # Auto-assign category if exists, or just logic handle
        # Note: We need to handle category assignment via signals or logic if Category is dynamic now. 
        # For simple proxy, we just ensure it's treated as vehicle.
        # Ideally lookup "Vehicle" category object.
        super().save(*args, **kwargs)

class IssueReport(models.Model):
    PRIORITY_CHOICES = [('low', 'Low'), ('medium', 'Medium'), ('high', 'High'), ('critical', 'Critical')]
    STATUS_CHOICES = [('new', 'New'), ('investigating', 'Investigating'), ('fixed', 'Fixed'), ('closed', 'Closed')]
    
    title = models.CharField(max_length=200, verbose_name="หัวข้อปัญหา")
    description = models.TextField(verbose_name="รายละเอียด")
    # Equipment and Studio are standard ForeignKeys now
    equipment = models.ForeignKey('Equipment', on_delete=models.SET_NULL, null=True, blank=True)
    studio = models.ForeignKey('Studio', on_delete=models.SET_NULL, null=True, blank=True)
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default='medium')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='new')
    reporter = models.ForeignKey('auth.User', on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    history = HistoricalRecords()
    class Meta: verbose_name_plural = "รายงานปัญหา (Issue Reports)"

class Equipment(models.Model):
    """อุปกรณ์รายชิ้น (Physical Asset) - รองรับ Barcode/QR"""
    STATUS_CHOICES = [('available', 'พร้อมใช้งาน'), ('maintenance', 'ส่งซ่อม'), ('lost', 'สูญหาย')]
    
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='items', verbose_name="สินค้าหลัก", null=True)
    serial_number = models.CharField(max_length=100, unique=True, verbose_name="Serial Number")
    inventory_number = models.CharField(max_length=100, unique=True, blank=True, null=True, verbose_name="เลขครุภัณฑ์")
    asset_tag = models.CharField(max_length=50, unique=True, blank=True, null=True, verbose_name="รหัสทรัพย์สิน (QR/Barcode)")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='available', verbose_name="สถานะ")
    
    history = HistoricalRecords()
    class Meta: verbose_name_plural = "ทรัพยากร - อุปกรณ์รายชิ้น (Asset)"
    def __str__(self): return f"{self.product.name} ({self.inventory_number or self.serial_number})"

class Studio(models.Model):
    name = models.CharField(max_length=200, verbose_name="ชื่อสตูดิโอ")
    description = models.TextField(verbose_name="รายละเอียด", blank=True, null=True)
    image = models.ImageField(upload_to='studios/', null=True, blank=True, verbose_name="รูปภาพสตูดิโอ")
    daily_rate = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="ราคาเช่าต่อวัน")
    turnaround_time = models.DurationField(default=timedelta(hours=2), verbose_name="เวลาทำความสะอาด (Buffer Time)")
    
    history = HistoricalRecords()
    class Meta: verbose_name_plural = "ทรัพยากร - สตูดิโอ"
    def __str__(self): return self.name

class Package(models.Model):
    name = models.CharField(max_length=200, verbose_name="ชื่อแพ็คเกจ")
    short_description = models.CharField(max_length=200, verbose_name="คำอธิบายสั้น", blank=True)
    description = models.TextField(verbose_name="รายละเอียด", blank=True, null=True)
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="ราคาเหมาจ่าย")
    image = models.ImageField(upload_to='packages/', null=True, blank=True, verbose_name="รูปภาพแพ็คเกจ")
    is_highlight = models.BooleanField(default=False, verbose_name="แนะนำ (Highlight)")
    is_active = models.BooleanField(default=True, verbose_name="เปิดใช้งาน")
    items = models.ManyToManyField(Product, through='PackageItem', verbose_name="สินค้าในแพ็คเกจ")
    
    def __str__(self): return self.name
    class Meta: verbose_name_plural = "ทรัพยากร - แพ็คเกจ"

class PackageItem(models.Model):
    package = models.ForeignKey(Package, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)

class ServiceCategory(models.Model):
    """หมวดหมู่บริการ (เช่น รับตัดต่อ, ถ่ายทำ)"""
    name = models.CharField(max_length=100, unique=True, verbose_name="ชื่อหมวดหมู่บริการ")
    slug = models.SlugField(max_length=100, unique=True)
    
    def __str__(self): return self.name
    class Meta: verbose_name_plural = "ตั้งค่า - หมวดหมู่บริการ"

class ServiceOffer(models.Model):
    """บริการ (เช่น ตัดต่อวิดีโอรายวัน)"""
    name = models.CharField(max_length=200, verbose_name="ชื่อบริการ")
    description = models.TextField(verbose_name="รายละเอียด", blank=True, null=True)
    category = models.ForeignKey(ServiceCategory, on_delete=models.SET_NULL, null=True, verbose_name="หมวดหมู่")
    daily_rate = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="ราคาเริ่มต้น (ต่อวัน/โปรเจกต์)")
    is_active = models.BooleanField(default=True, verbose_name="เปิดให้บริการ")
    
    history = HistoricalRecords()
    class Meta:
        verbose_name = "บริการ (Service)"
        verbose_name_plural = "ทรัพยากร - บริการ"
    def __str__(self): return self.name

# --- 3. Booking & Transaction Models ---
class Booking(models.Model):
    STATUS_CHOICES = [
        ('draft', 'รอตรวจสอบ (Draft)'),
        ('pending', 'รออนุมัติ (Pending)'),
        ('approved', 'อนุมัติแล้ว (Approved)'),
        ('active', 'กำลังใช้งาน (Active)'),
        ('overdue', 'เกินกำหนด (Overdue)'),
        ('completed', 'คืนของครบ (Completed)'),
        ('cancelled', 'ยกเลิก (Cancelled)'),
    ]
    # Shared flow constants to keep views/services/admin rules aligned.
    STOCK_BLOCKING_STATUSES = ('pending', 'approved', 'active', 'overdue')
    STAFF_ACTIVATABLE_STATUSES = ('pending', 'approved')
    COMPLETABLE_STATUSES = ('active', 'overdue')
    STAFF_CANCELLABLE_STATUSES = ('draft', 'pending')
    PAYMENT_SETTLED_STATUSES = ('paid', 'waived')
    PAYMENT_CONFIRMABLE_STATUSES = ('unpaid', 'pending')
    
    # Customer Info
    customer_name = models.CharField(max_length=200, verbose_name="ชื่อลูกค้า") # E.g. Contact Person
    customer_email = models.EmailField(verbose_name="อีเมลลูกค้า (Contact Email)", blank=True, null=True)
    created_by = models.ForeignKey('auth.User', on_delete=models.SET_NULL, null=True)
    
    # Project Info (New)
    project_name = models.CharField(max_length=200, verbose_name="ชื่อโปรเจค/งาน", blank=True, null=True)
    phone = models.CharField(max_length=20, verbose_name="เบอร์โทรศัพท์ติดต่อ", blank=True, null=True)
    note = models.TextField(verbose_name="หมายเหตุ", blank=True, null=True)
    internal_notes = models.TextField(verbose_name="บันทึกภายใน (Staff Only)", blank=True, null=True)

    # Coordinator
    coordinator = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='coordinated_bookings',
        verbose_name="ผู้ประสานงาน (Staff)"
    )

    # Timeline
    start_time = models.DateTimeField(verbose_name="เริ่มใช้")
    end_time = models.DateTimeField(verbose_name="สิ้นสุด")
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    created_at = models.DateTimeField(auto_now_add=True)
    
    # Payment Info (New)
    total_price = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="ยอดรวมทั้งหมด")
    deposit_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="ยอดมัดจำ (30%)")
    payment_slip = models.ImageField(upload_to='payment_slips/', blank=True, null=True, verbose_name="สลิปโอนเงิน")
    PAYMENT_STATUS_CHOICES = [
        ('unpaid', 'ยังไม่จ่าย (Unpaid)'),
        ('pending', 'รอตรวจสอบ (Pending Verification)'),
        ('paid', 'จ่ายแล้ว (Paid)'),
        ('waived', 'ไม่เก็บมัดจำ (Waived)'),
        ('refunded', 'คืนเงิน (Refunded)'),
    ]
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default='unpaid', verbose_name="สถานะการชำระเงิน")
    
    # Promotions and Penalties (New)
    promotion = models.ForeignKey(PromotionCode, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="โค้ดส่วนลดที่ใช้")
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="ยอดส่วนลดรวม")
    penalty_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="ค่าปรับ (ส่งคืนช้า, ของชำรุด ฯลฯ)")

    # Expiration (New)
    expires_at = models.DateTimeField(null=True, blank=True, verbose_name="หมดอายุการจอง (ชำระเงินภายใน)")

    @property
    def is_expired(self):
        if self.status in Booking.STAFF_CANCELLABLE_STATUSES and self.payment_status == 'unpaid' and self.expires_at:
            return timezone.now() > self.expires_at
        return False
    
    # Relationships (Using Through Models for Price Snapshot)
    products = models.ManyToManyField(Product, through='BookingItem', blank=True)
    studios = models.ManyToManyField(Studio, through='BookingStudio', blank=True)
    staff = models.ManyToManyField(User, through='BookingStaff', blank=True, related_name='assigned_as_staff')
    packages = models.ManyToManyField(Package, through='BookingPackage', blank=True)

    history = HistoricalRecords()
    class Meta: verbose_name_plural = "รายการจอง (Booking)"
    def __str__(self): return f"#{self.id} {self.customer_name}"

    def calculate_total_price(self):
        from apps.store.services.pricing_service import PricingService
        # Now returns a dictionary with breakdown, so we return the grand_total for legacy calls
        totals = PricingService.calculate_booking_total(self)
        if isinstance(totals, dict):
            return totals.get('grand_total', 0)
        return totals

    @property
    def item_total(self):
        return sum((item.price_at_booking * item.quantity) for item in self.items.all())

    @property
    def studio_total(self):
        return sum(bs.price_at_booking for bs in self.booked_studios.all())
        
    @property
    def package_total(self):
        return sum((bp.price_at_booking * bp.quantity) for bp in self.booked_packages.all())
        
    @property
    def service_total(self):
        return sum((bs.price_at_booking * bs.quantity) for bs in self.booked_services.all())
        
    @property
    def rental_days(self):
        if not self.start_time or not self.end_time:
            return 1
        return max(1, (self.end_time.date() - self.start_time.date()).days + 1)
        
    @property
    def calculated_total_price(self):
        return (self.item_total + self.studio_total + self.package_total + self.service_total) * self.rental_days

# --- 4. Intermediary (Through) Models with Snapshots ---
class BookingItem(models.Model):
    STATUS_CHOICES = [
        ('picked', 'รับของแล้ว (Picked Up)'),
        ('returned', 'คืนของแล้ว (Returned)'),
        ('missing', 'สูญหาย (Missing)'),
        ('damaged', 'ชำรุด (Damaged)'),
    ]

    booking = models.ForeignKey(Booking, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.PROTECT)  # Prevent product deletion
    quantity = models.PositiveIntegerField(default=1)
    price_at_booking = models.DecimalField(max_digits=10, decimal_places=2, help_text="ราคาต่อชิ้น ณ วันจอง")

    # Inventory Assignment Fields
    equipment = models.ForeignKey(Equipment, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="อุปกรณ์ที่ระบุ (Optional)")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='picked', blank=True, verbose_name="สถานะคืน")
    returned_at = models.DateTimeField(null=True, blank=True, verbose_name="เวลาที่คืน")
    notes = models.TextField(blank=True, null=True, verbose_name="หมายเหตุ (สภาพตอนคืน)")

    def save(self, *args, **kwargs):
        if self.price_at_booking is None and self.product:
            self.price_at_booking = self.product.price
        super().save(*args, **kwargs)

class BookingStudio(models.Model):
    booking = models.ForeignKey(Booking, on_delete=models.CASCADE, related_name='booked_studios')
    studio = models.ForeignKey(Studio, on_delete=models.PROTECT)
    price_at_booking = models.DecimalField(max_digits=10, decimal_places=2, help_text="ราคาต่อวัน ณ วันจอง")

    def save(self, *args, **kwargs):
        if self.price_at_booking is None and self.studio:
            self.price_at_booking = self.studio.daily_rate
        super().save(*args, **kwargs)

class BookingStaff(models.Model):
    """คนทำงานที่ถูก Assign เข้าไปในโปรเจกต์ (HR Use)"""
    booking = models.ForeignKey(Booking, on_delete=models.CASCADE, related_name='assigned_staff')
    staff = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="พนักงาน")
    assigned_date = models.DateField(auto_now_add=True)

class BookingServiceOffer(models.Model):
    """บริการที่ลูกค้าสั่งซื้อเข้าตะกร้า"""
    booking = models.ForeignKey(Booking, on_delete=models.CASCADE, related_name='booked_services')
    service = models.ForeignKey(ServiceOffer, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    price_at_booking = models.DecimalField(max_digits=10, decimal_places=2)

    def save(self, *args, **kwargs):
        if not self.price_at_booking and self.service:
            self.price_at_booking = self.service.daily_rate
        super().save(*args, **kwargs)

class BookingPackage(models.Model):
    booking = models.ForeignKey(Booking, on_delete=models.CASCADE, related_name='booked_packages')
    package = models.ForeignKey(Package, on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField(default=1)
    price_at_booking = models.DecimalField(max_digits=10, decimal_places=2)

    def save(self, *args, **kwargs):
        if not self.price_at_booking and self.package:
            self.price_at_booking = self.package.price
        super().save(*args, **kwargs)

# --- 5. Support Models ---
class Notification(models.Model):
    TYPE_CHOICES = [('info', 'Info'), ('success', 'Success'), ('warning', 'Warning'), ('error', 'Error')]
    recipient = models.ForeignKey('auth.User', on_delete=models.CASCADE, related_name='notifications')
    message = models.CharField(max_length=255)
    link = models.CharField(max_length=255, blank=True, null=True)
    is_read = models.BooleanField(default=False)
    notification_type = models.CharField(max_length=20, choices=TYPE_CHOICES, default='info')
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta: verbose_name_plural = "การแจ้งเตือน (Notifications)"
