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
        
        Args:
            booking_instance (Booking): อ็อบเจกต์การจองที่ต้องการคำนวณ
            update_db (bool): (Future Use) ถ้าเป็น True จะบันทึกค่าลงฐานข้อมูล
        """
        # 1. คำนวณจำนวนวัน
        rental_days = PricingService.calculate_rental_days(booking_instance.start_time, booking_instance.end_time)
        grand_total = Decimal('0.00')

        # 2. รวมราคาสินค้ารายชิ้น (Product Items)
        for item in booking_instance.items.all():
            grand_total += PricingService.calculate_item_price(item.price_at_booking, item.quantity, rental_days)

        # 3. รวมราคาสตูดิโอ (Studios)
        for studio_item in booking_instance.booked_studios.all():
            # ใช้ราคาจาก Snapshot (BookingStudio)
            grand_total += (studio_item.price_at_booking * rental_days)

        # 4. รวมราคาแพ็คเกจ (Packages)
        for pkg_item in booking_instance.booked_packages.all():
             grand_total += PricingService.calculate_item_price(pkg_item.price_at_booking, pkg_item.quantity, rental_days)

        # 5. รวมค่าแรงพนักงาน (Staff)
        for staff_item in booking_instance.booked_staff.all():
            # ใช้ราคาจาก Snapshot (BookingStaff)
            grand_total += (staff_item.daily_rate_at_booking * rental_days)
        
        return grand_total

    @staticmethod
    def calculate_deposit(total_amount, percentage=0.3):
        """
        คำนวณมัดจำ (Deposit)
        Default: 30% ของยอดรวม
        """
        return total_amount * Decimal(str(percentage))
