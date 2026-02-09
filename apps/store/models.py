from django.db import models
from django.core.exceptions import ValidationError
from django.db.models import Q
from django.utils import timezone
from simple_history.models import HistoricalRecords
from datetime import timedelta

# --- 1. Dynamic Configuration Models ---
class ProductCategory(models.Model):
    """หมวดหมู่สินค้า (เช่น กล้อง, เลนส์, ไฟ, รถ OB)"""
    name = models.CharField(max_length=100, unique=True, verbose_name="ชื่อหมวดหมู่")
    slug = models.SlugField(max_length=100, unique=True, verbose_name="URL Slug")
    
    def __str__(self): return self.name
    class Meta: verbose_name_plural = "ตั้งค่า - หมวดหมู่สินค้า"

class StaffPosition(models.Model):
    """ตำแหน่งพนักงาน (เช่น ช่างภาพ, ครีเอทีฟ, คนขับรถ)"""
    name = models.CharField(max_length=100, unique=True, verbose_name="ชื่อตำแหน่ง")
    base_daily_rate = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, verbose_name="ค่าแรงเริ่มต้น (Standard Rate)")
    
    def __str__(self): return self.name
    class Meta: verbose_name_plural = "ตั้งค่า - ตำแหน่งพนักงาน"

# --- 2. Resource Models ---
class Staff(models.Model):
    name = models.CharField(max_length=200, verbose_name="ชื่อพนักงาน")
    position = models.ForeignKey(StaffPosition, on_delete=models.SET_NULL, null=True, verbose_name="ตำแหน่ง")
    daily_rate = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, verbose_name="ค่าแรงต่อวัน (Specific Rate)")
    phone = models.CharField(max_length=20, verbose_name="เบอร์โทรศัพท์")
    is_active = models.BooleanField(default=True, verbose_name="สถานะใช้งาน")
    created_by = models.ForeignKey('auth.User', on_delete=models.SET_NULL, null=True, blank=True, verbose_name="เพิ่มโดย")
    history = HistoricalRecords()
    
    def save(self, *args, **kwargs):
        # ถ้าไม่ได้ระบุค่าแรงเฉพาะ ให้ใช้ค่าแรงมาตรฐานของตำแหน่ง
        if self.daily_rate == 0 and self.position:
            self.daily_rate = self.position.base_daily_rate
        super().save(*args, **kwargs)

    def __str__(self): return f"{self.name} ({self.position.name if self.position else 'N/A'})"
    class Meta: verbose_name_plural = "ทรัพยากร - พนักงาน"

class Product(models.Model):
    name = models.CharField(max_length=200, verbose_name="ชื่อสินค้า")
    description = models.TextField(verbose_name="รายละเอียด", blank=True, null=True)
    category = models.ForeignKey(ProductCategory, on_delete=models.SET_NULL, null=True, verbose_name="หมวดหมู่")
    image = models.ImageField(upload_to='products/', null=True, blank=True, verbose_name="รูปภาพ")
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="ราคาเช่าต่อวัน")
    quantity = models.IntegerField(default=1, verbose_name="จำนวนทั้งหมด")
    turnaround_time = models.DurationField(default=timedelta(hours=1), verbose_name="เวลาในการเตรียมของ (Buffer Time)", help_text="เวลาที่ต้องเว้นว่างหลังคืนของ เพื่อเช็ค/ทำความสะอาด")
    is_active = models.BooleanField(default=True, verbose_name="เปิดให้เช่า")

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

class Equipment(models.Model):
    """อุปกรณ์รายชิ้น (Physical Asset) - รองรับ Barcode/QR"""
    STATUS_CHOICES = [('available', 'พร้อมใช้งาน'), ('maintenance', 'ส่งซ่อม'), ('lost', 'สูญหาย')]
    
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='items', verbose_name="สินค้าหลัก", null=True)
    serial_number = models.CharField(max_length=100, unique=True, verbose_name="Serial Number")
    asset_tag = models.CharField(max_length=50, unique=True, blank=True, null=True, verbose_name="รหัสทรัพย์สิน (QR/Barcode)")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='available', verbose_name="สถานะ")
    
    history = HistoricalRecords()
    class Meta: verbose_name_plural = "ทรัพยากร - อุปกรณ์รายชิ้น (Asset)"
    def __str__(self): return f"{self.product.name} ({self.asset_tag or self.serial_number})"

class Studio(models.Model):
    name = models.CharField(max_length=200, verbose_name="ชื่อสตูดิโอ")
    description = models.TextField(verbose_name="รายละเอียด", blank=True, null=True)
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

# --- 3. Booking & Transaction Models ---
class Booking(models.Model):
    STATUS_CHOICES = [
        ('draft', 'รอตรวจสอบ (Draft)'),
        ('pending', 'รออนุมัติ (Pending)'),
        ('approved', 'อนุมัติแล้ว (Approved)'),
        ('active', 'กำลังใช้งาน (Active)'),
        ('completed', 'คืนของครบ (Completed)'),
        ('cancelled', 'ยกเลิก (Cancelled)'),
    ]
    
    # Customer Info
    customer_name = models.CharField(max_length=200)
    created_by = models.ForeignKey('auth.User', on_delete=models.SET_NULL, null=True)
    
    # Timeline
    start_time = models.DateTimeField(verbose_name="เริ่มใช้")
    end_time = models.DateTimeField(verbose_name="สิ้นสุด")
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    created_at = models.DateTimeField(auto_now_add=True)
    
    # Relationships (Using Through Models for Price Snapshot)
    products = models.ManyToManyField(Product, through='BookingItem', blank=True)
    studios = models.ManyToManyField(Studio, through='BookingStudio', blank=True)
    staff = models.ManyToManyField(Staff, through='BookingStaff', blank=True)
    packages = models.ManyToManyField(Package, through='BookingPackage', blank=True)

    history = HistoricalRecords()
    class Meta: verbose_name_plural = "รายการจอง (Booking)"
    def __str__(self): return f"#{self.id} {self.customer_name}"

    def calculate_total_price(self):
        from apps.store.services.pricing_service import PricingService
        return PricingService.calculate_booking_total(self)

# --- 4. Intermediary (Through) Models with Snapshots ---
class BookingItem(models.Model):
    booking = models.ForeignKey(Booking, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.PROTECT)  # Prevent product deletion
    quantity = models.PositiveIntegerField(default=1)
    price_at_booking = models.DecimalField(max_digits=10, decimal_places=2, help_text="ราคาต่อชิ้น ณ วันจอง")

    def save(self, *args, **kwargs):
        if not self.price_at_booking and self.product:
            self.price_at_booking = self.product.price
        super().save(*args, **kwargs)

class BookingStudio(models.Model):
    booking = models.ForeignKey(Booking, on_delete=models.CASCADE, related_name='booked_studios')
    studio = models.ForeignKey(Studio, on_delete=models.PROTECT)
    price_at_booking = models.DecimalField(max_digits=10, decimal_places=2, help_text="ราคาต่อวัน ณ วันจอง")

    def save(self, *args, **kwargs):
        if not self.price_at_booking and self.studio:
            self.price_at_booking = self.studio.daily_rate
        super().save(*args, **kwargs)

class BookingStaff(models.Model):
    booking = models.ForeignKey(Booking, on_delete=models.CASCADE, related_name='booked_staff')
    staff = models.ForeignKey(Staff, on_delete=models.PROTECT)
    daily_rate_at_booking = models.DecimalField(max_digits=10, decimal_places=2, help_text="ค่าแรงต่อวัน ณ วันจอง")

    def save(self, *args, **kwargs):
        if not self.daily_rate_at_booking and self.staff:
            self.daily_rate_at_booking = self.staff.daily_rate
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

