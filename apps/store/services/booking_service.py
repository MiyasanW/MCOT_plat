from django.contrib.auth.models import User
from django.db import transaction
from rentals.models import Booking, BookingItem, Notification
from .notify import send_line_notify


class BookingService:
    """
    Service สำหรับจัดการการจอง (Booking)
    รวม Logic การสร้างจองจากตะกร้าสินค้า, การคำนวณราคา, และการแจ้งเตือน
    """
    
    @staticmethod
    def create_booking_from_cart(cart, booking_data, user=None):
        """
        สร้าง Booking ใหม่จากข้อมูลในตะกร้าสินค้า
        
        Args:
            cart: Object ของ Cart ที่เก็บรายการสินค้าที่เลือก
            booking_data: Dictionary ข้อมูลผู้จอง (ชื่อ, เบอร์, อีเมล, วันที่)
            user: (Optional) User instance ถ้าจองในขณะล็อกอิน
            
        Returns:
            Booking: อ็อบเจกต์ Booking ที่สร้างสำเร็จ
            
        Raises:
            ValueError: ถ้าตะกร้าว่างหรือข้อมูลไม่ครบ
        """
        if not cart or len(cart) == 0:
            raise ValueError("Cart is empty")
            
        # ตรวจสอบข้อมูลที่จำเป็น (Validate required fields)
        required_fields = ['customer_name', 'customer_phone', 'customer_email', 
                          'start_time', 'end_time']
        for field in required_fields:
            if field not in booking_data:
                raise ValueError(f"Missing required field: {field}")
        
        # ตั้งค่าสถานะเริ่มต้น (Default Status)
        if 'status' not in booking_data:
            booking_data['status'] = 'draft'
            
        # ผูก User ถ้ามีการล็อกอิน
        if user and user.is_authenticated:
            booking_data['created_by'] = user
            
        # สร้าง Booking หรือย้อนกลับทั้งหมดถ้ามีปัญหา (Atomic Transaction)
        try:
            with transaction.atomic():
                # DOUBLE CHECK: ตรวจสอบสต็อกอีกครั้งใน Transaction เพื่อกัน Race Condition
                from rentals.services.availability import AvailabilityService
                is_valid, error_msg = AvailabilityService.validate_cart(cart, booking_data['start_time'], booking_data['end_time'])
                
                if not is_valid:
                    raise ValueError(f"Booking Error: {error_msg}")
                    
                booking = Booking.objects.create(**booking_data)
                
                # สร้างรายการสินค้าใน Booking (จาก Cart)
                # รองรับการจองทั้งแบบสินค้าเดี่ยวและแพ็คเกจ
                from rentals.models import BookingPackage

                for item in cart:
                    if item.get('type') == 'package':
                        # บันทึกแพ็คเกจ
                        BookingPackage.objects.create(
                            booking=booking,
                            package=item['package'],
                            quantity=item['quantity'],
                            price_at_booking=item['price']
                        )
                    else:
                        # บันทึกสินค้าเดี่ยว
                        BookingItem.objects.create(
                            booking=booking,
                            product=item['product'],
                            quantity=item['quantity'],
                            price_at_booking=item['price']
                        )
                
                # ล้าง Cache (ถ้ามี)
                # AvailabilityService.invalidate_availability_cache(...)
                
        except Exception as e:
            # ส่ง Error ต่อให้ View ไปจัดการ
            raise e
        
        # ส่งการแจ้งเตือน (อยู่นอก Transaction เพื่อประสิทธิภาพ)
        BookingService._send_booking_notifications(booking)
        
        return booking
    
    @staticmethod
    def _send_booking_notifications(booking):
        """
        ส่งการแจ้งเตือนไปยัง LINE และ In-App Notification
        
        Args:
            booking: Booking instance ที่สร้างเสร็จแล้ว
        """
        # LINE Notification (ส่งเข้ากลุ่ม Staff)
        message = (
            f"\n📦 มีรายการจองใหม่ #{booking.id}\n"
            f"ลูกค้า: {booking.customer_name}\n"
            f"จำนวนรายการ: {booking.items.count()} รายการ\n"
            f"วันที่: {booking.start_time.strftime('%d/%m')} - {booking.end_time.strftime('%d/%m')}"
        )
        send_line_notify(message)
        
        # In-App Notification (แจ้งเตือน Staff ทุกคนในหน้า Admin)
        staff_users = User.objects.filter(is_staff=True)
        for staff in staff_users:
            Notification.objects.create(
                recipient=staff,
                message=f"📦 มีรายการจองใหม่ #{booking.id} โดย {booking.customer_name}",
                link=f"/admin/rentals/booking/{booking.id}/change/",
                notification_type='info'
            )
