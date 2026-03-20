from decimal import Decimal
from django.utils import timezone
from math import ceil

class PricingService:
    """
    Service สำหรับคำนวณราคา (Centralized Pricing Logic)
    ช่วยให้การปรับเปลี่ยนสูตรคำนวณทำได้ง่ายในจุดเดียว (เช่น การคิดราคาตามจำนวนวัน, ส่วนลด, VAT)
    """

    @staticmethod
    def calculate_rental_days(start_date, end_date):
        """
        คำนวณจำนวนวันที่เช่า (Rental Days) - แบบ Calendar Day
        Logic: นับตาม "วันปฏิทิน" ที่ครอบคลุม ไม่สนใจจำนวนชั่วโมง
        - เช่า 1 ก.พ. 10:00 -> คืน 1 ก.พ. 18:00 = 1 วัน
        - เช่า 1 ก.พ. 22:00 -> คืน 2 ก.พ. 02:00 = 2 วัน (ข้ามวันนับเป็นวันใหม่)
        
        Args:
            start_date (datetime): วันเวลาที่เริ่มเช่า
            end_date (datetime): วันเวลาที่คืนของ
            
        Returns:
            int: จำนวนวันที่ต้องจ่ายเงิน (ขั้นต่ำ 1 วัน)
        """
        if not start_date or not end_date:
            return 0
        
        # ปรับ Timezone ให้ถูกต้องก่อนเปรียบเทียบ (เผื่อ Database เป็น UTC)
        if start_date.tzinfo is None: start_date = timezone.make_aware(start_date)
        if end_date.tzinfo is None: end_date = timezone.make_aware(end_date)
            
        start_local = timezone.localtime(start_date).date()
        end_local = timezone.localtime(end_date).date()
        
        # คำนวณส่วนต่างวัน (Day Difference)
        # ตัวอย่าง: 1 ก.พ. - 1 ก.พ. = 0 วัน -> +1 = 1 วัน
        # ตัวอย่าง: 2 ก.พ. - 1 ก.พ. = 1 วัน -> +1 = 2 วัน
        days_diff = (end_local - start_local).days
        
        return max(1, days_diff + 1)

    @staticmethod
    def calculate_item_price(price_per_unit, quantity, days):
        """
        คำนวณราคารวมของผู้รายการหนึ่ง (Subtotal)
        สูตร: (ราคาต่อชิ้น * จำนวนชิ้น) * จำนวนวัน
        """
        if price_per_unit is None:
            return Decimal('0.00')
            
        return (price_per_unit * quantity) * days

    @staticmethod
    def calculate_booking_total(booking_instance, update_db=False):
        """
        คำนวณราคารวมทั้งหมดของการจอง (Grand Total)
        รวม: สินค้า (Items) + สตูดิโอ (Studios) + แพ็คเกจ (Packages)
        รองรับ: หักส่วนลด (Promotions/Partner) และ บวกเพิ่มค่าปรับ (Penalties)
        
        Args:
            booking_instance (Booking): อ็อบเจกต์การจองที่ต้องการคำนวณ
            update_db (bool): ถ้าเป็น True จะบันทึกค่าลงฐานข้อมูล
        
        Returns:
            dict: { 'subtotal': Decimal, 'discount': Decimal, 'penalty': Decimal, 'grand_total': Decimal }
        """
        # 1. คำนวณจำนวนวัน
        rental_days = PricingService.calculate_rental_days(booking_instance.start_time, booking_instance.end_time)
        subtotal = Decimal('0.00')

        # 2. รวมราคาสินค้ารายชิ้น (Product Items)
        for item in booking_instance.items.all():
            subtotal += PricingService.calculate_item_price(item.price_at_booking, item.quantity, rental_days)

        # 3. รวมราคาสตูดิโอ (Studios)
        for studio_item in booking_instance.booked_studios.all():
            subtotal += (studio_item.price_at_booking * rental_days)

        # 4. รวมราคาแพ็คเกจ (Packages)
        for pkg_item in booking_instance.booked_packages.all():
             subtotal += PricingService.calculate_item_price(pkg_item.price_at_booking, pkg_item.quantity, rental_days)

        # 5. รวมค่าบริการ (Services)
        for svc_item in booking_instance.booked_services.all():
            subtotal += PricingService.calculate_item_price(svc_item.price_at_booking, svc_item.quantity, rental_days)
        
        # 6. คำนวณส่วนลด (Discount)
        discount = Decimal('0.00')
        
        # 6.1 ส่วนลด Partner (เปอร์เซ็นต์)
        if booking_instance.created_by and hasattr(booking_instance.created_by, 'profile'):
            profile = booking_instance.created_by.profile
            if profile.is_partner:
                partner_discount = subtotal * (Decimal(profile.partner_discount_percent) / Decimal('100.0'))
                discount += partner_discount

        # 6.2 ส่วนลด Promotion Code 
        if booking_instance.promotion and booking_instance.promotion.is_valid():
            if booking_instance.promotion.discount_percent > 0:
                promo_discount = subtotal * (Decimal(booking_instance.promotion.discount_percent) / Decimal('100.0'))
                discount += promo_discount
            elif booking_instance.promotion.discount_amount > 0:
                discount += booking_instance.promotion.discount_amount

        # จำกัดส่วนลดไม่ให้เกินยอดรวม
        if discount > subtotal:
            discount = subtotal

        # 7. ค่าปรับ (จากที่แอดมินหรือระบบใส่ไว้)
        penalty = booking_instance.penalty_amount or Decimal('0.00')

        # 8. คำนวณยอดสุทธิ
        grand_total = (subtotal - discount) + penalty

        if update_db:
            booking_instance.total_price = grand_total
            booking_instance.discount_amount = discount
            booking_instance.deposit_amount = PricingService.calculate_deposit(grand_total)
            booking_instance.save(update_fields=['total_price', 'discount_amount', 'deposit_amount'])

        return {
            'subtotal': subtotal,
            'discount': discount,
            'penalty': penalty,
            'grand_total': grand_total
        }

    @staticmethod
    def calculate_deposit(total_amount, percentage=None):
        """
        คำนวณมัดจำ (Deposit)
        รองรับทั้งรูปแบบ ratio (0.3) และ percentage (30)
        """
        if percentage is None:
            percentage = PricingService.get_deposit_percentage()

        p = Decimal(str(percentage))
        ratio = (p / Decimal('100')) if p > 1 else p
        return total_amount * ratio

    @staticmethod
    def get_deposit_percentage(default=Decimal('30')):
        """Read global deposit percentage from BookingConfig singleton."""
        try:
            from apps.store.models import BookingConfig

            cfg = BookingConfig.objects.order_by('id').first()
            if cfg and cfg.deposit_percent is not None:
                pct = Decimal(str(cfg.deposit_percent))
                if Decimal('0') <= pct <= Decimal('100'):
                    return pct
        except Exception:
            pass

        return Decimal(str(default))
