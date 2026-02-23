from django.contrib.auth.models import User
from django.db import transaction
from django.utils import timezone
from django.shortcuts import get_object_or_404
from datetime import timedelta

from apps.store.models import (
    Booking, BookingItem, BookingStudio, BookingPackage, 
    Product, Studio, Package, Notification, PromotionCode
)
from apps.store.services.availability import AvailabilityService
from apps.store.services.pricing_service import PricingService
from apps.store.services.notification_service import NotificationService

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
            cart: List[dict] รายการสินค้าจาก Frontend Cart
            booking_data: Dictionary ข้อมูลผู้จอง (ชื่อ, เบอร์, อีเมล, วันที่)
            user: (Optional) User instance ถ้าจองในขณะล็อกอิน
            
        Returns:
            Booking: อ็อบเจกต์ Booking ที่สร้างสำเร็จ
            
        Raises:
            ValueError: ถ้าตะกร้าว่างหรือข้อมูลไม่ครบ
            Exception: ถ้ามีปัญหาระหว่าง Transaction
        """
        if not cart or len(cart) == 0:
            raise ValueError("Cart is empty")
            
        # ตรวจสอบข้อมูลที่จำเป็น (Validate required fields)
        required_fields = ['customer_name', 'customer_phone', 'start_time', 'end_time']
        for field in required_fields:
            if not booking_data.get(field):
                raise ValueError(f"Missing required field: {field}")
        
        booking_start = booking_data['start_time']
        booking_end = booking_data['end_time']
        
        if booking_start > booking_end:
            raise ValueError("วันเวลาไม่ถูกต้อง (วันกลับต้องหลังหรือวันเดียวกับวันรับ)")

        # ตรวจสอบ Promotion Code
        promotion_obj = None
        promo_code = booking_data.get('promotion_code')
        if promo_code:
            try:
                # ตรวจสอบโค้ดที่ Active และไม่หมดอายุ
                now = timezone.now()
                promotion_obj = PromotionCode.objects.get(code__iexact=promo_code, is_active=True, valid_from__lte=now, valid_to__gte=now)
            except PromotionCode.DoesNotExist:
                pass # ถ้าไม่เจอ หรือหมดอายุ ให้ข้ามไป

        # เตรียมข้อมูล Booking Header
        create_payload = {
            'customer_name': booking_data['customer_name'],
            'customer_email': booking_data.get('customer_email'),  # New Field
            'phone': booking_data['customer_phone'],
            'project_name': booking_data.get('project_name'),
            'note': booking_data.get('note'),
            'start_time': booking_start,
            'end_time': booking_end,
            'status': booking_data.get('status', 'draft'),
            'created_by': user if (user and user.is_authenticated) else None,
            'promotion': promotion_obj
        }

        # สร้าง Booking หรือย้อนกลับทั้งหมดถ้ามีปัญหา (Atomic Transaction)
        try:
            with transaction.atomic():
                # 1. สร้าง Header
                new_booking = Booking.objects.create(**create_payload)
                
                error_messages = []

                # 2. วนลูปสร้างรายการสินค้า (Booking Items) และตัดสต็อก
                # ควร Sort items เพื่อป้องกัน Deadlock (ถ้าซีเรียสมาก)
                
                for item_data in cart:
                    item_type = item_data.get('type', 'product')
                    raw_id = item_data.get('id')
                    qty_requested = int(item_data.get('quantity', 1))

                    # --- Case 1: Studio ---
                    if item_type == 'studio' or str(raw_id).startswith('studio_'):
                        studio_id = str(raw_id).replace('studio_', '')
                        
                        # Lock Studio Row
                        studio_obj = get_object_or_404(Studio.objects.select_for_update(), pk=studio_id)

                        # Check Availability
                        is_valid, conflict = AvailabilityService.check_resource_overlap(
                            'studios', studio_obj, booking_start, booking_end
                        )
                        
                        if not is_valid:
                            error_messages.append(f"สตูดิโอ '{studio_obj.name}' ไม่ว่างในช่วงเวลานี้")
                            continue

                        BookingStudio.objects.create(
                            booking=new_booking,
                            studio=studio_obj,
                            price_at_booking=studio_obj.daily_rate
                        )

                    # --- Case 2: Package ---
                    elif item_type == 'package' or str(raw_id).startswith('pkg_'):
                        pkg_id = str(raw_id).replace('pkg_', '')
                        
                        # Lock Package Row
                        package_obj = get_object_or_404(Package.objects.select_for_update(), pk=pkg_id)
                        
                        # Check Availability
                        is_valid, msg = AvailabilityService.check_package_availability(
                            package_obj, booking_start, booking_end, qty_requested
                        )
                        
                        if not is_valid:
                            error_messages.append(msg)
                            continue

                        BookingPackage.objects.create(
                            booking=new_booking,
                            package=package_obj,
                            quantity=qty_requested,
                            price_at_booking=package_obj.price
                        )

                    # --- Case 3: Product (Default) ---
                    else:
                        product_id = raw_id
                        
                        # --- CRITICAL: LOCK PRODUCT ROW ---
                        product_obj = get_object_or_404(Product.objects.select_for_update(), id=product_id)
                        
                        # Check Availability
                        is_valid, msg = AvailabilityService.check_availability(
                            product_obj, booking_start, booking_end, qty_requested
                        )
                        
                        if not is_valid:
                            error_messages.append(msg)
                            continue
                        
                        BookingItem.objects.create(
                            booking=new_booking,
                            product=product_obj,
                            quantity=qty_requested,
                            price_at_booking=product_obj.price
                        )
                
                # ถ้ามี Error แม้แต่รายการเดียว ให้ Rollback ทั้งหมด
                if error_messages:
                    raise ValueError(f"Conflict: {', '.join(error_messages)}")
                
                # 3. Calculate Totals, Discounts, & Deposit
                totals = PricingService.calculate_booking_total(new_booking)
                new_booking.total_price = totals['grand_total']
                new_booking.discount_amount = totals['discount']
                new_booking.deposit_amount = PricingService.calculate_deposit(totals['grand_total']) # 30%
                
                # Set Expiration (24h)
                new_booking.expires_at = timezone.now() + timedelta(hours=24)
                new_booking.save()
                
        except Exception as e:
            # ส่ง Error ต่อให้ View ไปจัดการ
            raise e
        
        # ส่งการแจ้งเตือน Notification System
        try:
            NotificationService.send_notification(new_booking, 'booking_created')
        except Exception as e:
            print(f"Notification Error: {e}")
        
        return new_booking

    @staticmethod
    def cancel_booking(booking_id, user):
        """
        ยกเลิกการจอง (Cancel Booking)
        
        Args:
            booking_id: ID ของ Booking
            user: User ที่ทำการขอยกเลิก (ต้องเป็นเจ้าของ หรือ Staff)
            
        Returns:
            Booking: อ็อบเจกต์ Booking ที่ถูกยกเลิกแล้ว
            
        Raises:
            PermissionError: ถ้าไม่ใช่เจ้าของและไม่ใช่ Staff
            ValueError: ถ้าสถานะไม่ถูกต้อง
        """
        booking = get_object_or_404(Booking, pk=booking_id)
        
        # Permission Check
        if booking.created_by != user and not user.is_staff:
             raise PermissionError("คุณไม่มีสิทธิ์ยกเลิกการจองนี้")

        # Status Check
        if booking.status not in ('draft', 'pending'):
             raise ValueError("ไม่สามารถยกเลิกได้ — การจองนี้ได้รับการอนุมัติแล้ว")
        
        # Update Status
        booking.status = 'cancelled'
        booking.save()
        
        # Trigger Notification
        try:
           NotificationService.send_notification(booking, 'cancelled')
        except Exception as e:
           print(f"Notification Logic Error: {e}")
           
        return booking

    @staticmethod
    def process_payment_slip(booking_id, user, slip_file):
        """
        อัปโหลดและบันทึกสลิปโอนเงิน (Process Payment Slip)
        
        Args:
            booking_id: ID ของ Booking
            user: User ที่ทำการอัปโหลด
            slip_file: File Object จาก request.FILES
            
        Returns:
            Booking: อ็อบเจกต์ Booking ที่อัปเดตแล้ว
            
        Raises:
            PermissionError: ถ้าไม่ใช่เจ้าของ
            ValueError: ถ้าไฟล์ไม่ใช่รูปภาพ หรือ ไม่มีไฟล์
        """
        if not slip_file:
             raise ValueError("กรุณาเลือกไฟล์รูปภาพ")
             
        # Validate Image
        if not slip_file.content_type.startswith('image/'):
            raise ValueError("อนุญาตเฉพาะไฟล์รูปภาพจ้ะ (jpg, png)")

        booking = get_object_or_404(Booking, id=booking_id)

        # Permission Check
        if booking.created_by != user:
             raise PermissionError("คุณไม่มีสิทธิ์อัปโหลดสลิปสำหรับการจองนี้")

        # Update
        booking.payment_slip = slip_file
        booking.payment_status = 'pending'
        booking.save()
        
        # Trigger Notification
        try:
            NotificationService.send_notification(booking, 'verification_pending')
        except Exception as notif_err:
            print(f"Notification Error: {notif_err}")
            
        return booking
