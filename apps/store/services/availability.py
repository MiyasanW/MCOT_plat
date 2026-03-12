from django.utils import timezone
from django.db.models import Sum, Q
from django.core.cache import cache
from datetime import timedelta

# Import models inside functions to avoid circular imports if strictly necessary, 
# but usually service layers are imported by views/forms, so importing models here is fine.
from apps.store.models import BookingItem, Booking

class AvailabilityService:
    """
    บริการสำหรับตรวจสอบสินค้าคงเหลือ (Stock) และการจองทับซ้อน
    ใช้แทน Logic ที่กระจัดกระจายอยู่ใน views และ models
    """

    @staticmethod
    def get_booked_quantity(product, start_time, end_time, exclude_booking_id=None):
        """
        คำนวณจำนวนสินค้าที่ถูกจองไปแล้วในช่วงเวลาที่กำหนด
        
        Args:
            product: สินค้าที่ต้องการเช็ค
            start_time: เวลาเริ่มต้น (inclusive)
            end_time: เวลาสิ้นสุด (exclusive)
            exclude_booking_id: (Optional) ID ของการจองที่ต้องการยกเว้น (ใช้ตอนแก้ไขจองเดิม)
            
        Returns:
            int: จำนวนรวมที่ถูกจองไปแล้ว
        """
        if not start_time or not end_time:
            return 0

        # Query หาการจองที่ทับซ้อนกับช่วงเวลาที่เลือก
        # สถานะที่ถือว่า 'ตัดสต็อก':
        # - draft (จองชั่วคราว - ตัดสต็อกเพื่อกันคนแย่ง)
        # - quotation_sent (ส่งใบเสนอราคา)
        # - pending_deposit (รอจ่ายมัดจำ)
        # - approved (ยืนยันแล้ว)
        # - active (กำลังเช่าอยู่)
        # (ส่วน completed/cancelled จะคืนสต็อกแล้ว ไม่นับรวม)
        
        # เงื่อนไขการหมดอายุของ Draft (Passive Expiry):
        # - Draft จะหมดอายุและคืนสต็อกอัตโนมัติถ้าผ่านไป 6 ชั่วโมง
        # - สถานะอื่น (Approved/Active) จะไม่หมดอายุที่นี่
        
        expiry_time = timezone.now() - timedelta(hours=6)
        
        # การจองที่นำมาคิดคำนวณ:
        # 1. เป็นสถานะ 'draft' และสร้างหลัง expiry_time (Draft ใหม่ๆ)
        # 2. เป็นสถานะอื่นๆ ที่ไม่ใช่ draft (Confirmed/Active etc.)
        
        status_filter = Q(booking__status='draft', booking__created_at__gte=expiry_time) | \
                        Q(booking__status__in=['pending', 'approved', 'active', 'overdue'])
        
        # สูตรหาการทับซ้อนของช่วงเวลา (Overlap Logic):
        # จองเริ่ม < เวลาที่เช็คจบ AND จองจบ > เวลาที่เช็คเริ่ม
        query = status_filter & \
                Q(product=product) & \
                Q(booking__start_time__lt=end_time) & \
                Q(booking__end_time__gt=start_time)

        if exclude_booking_id:
            query &= ~Q(booking__id=exclude_booking_id)

        # 1. รวมจำนวน (Sum) จากทุก BookingItem ที่เข้าเงื่อนไข (สินค้าชิ้นเดี่ยว)
        booked_qty_direct = BookingItem.objects.filter(query).aggregate(Sum('quantity'))['quantity__sum'] or 0
        
        return booked_qty_direct

    @staticmethod
    def get_available_quantity(product, start_time, end_time, exclude_booking_id=None):
        """
        คืนค่าจำนวนสินค้าที่ 'ว่างจริง' ในช่วงเวลานั้น
        
        สูตร: สต็อกทั้งหมด - จำนวนที่ถูกจองสูงสุดในช่วงเวลานั้น
        """
        booked_qty = AvailabilityService.get_booked_quantity(product, start_time, end_time, exclude_booking_id)
        available = max(0, product.quantity - booked_qty)
        
        return available

    @staticmethod
    def invalidate_availability_cache(product_id):
        """
        ล้าง Cache ของสินค้า (ปัจจุบันยังไม่ได้ใช้ Cache เนื่องจากต้องการความ Real-time สูงสุด)
        """
        pass

    @staticmethod
    def check_availability(product, start_time, end_time, requested_quantity=1, exclude_booking_id=None):
        """
        ตรวจสอบว่าสินค้าพอให้จองหรือไม่
        
        Returns:
            (bool, str): (True, "") ถ้าว่าง, (False, "ข้อความแจ้งเตือน") ถ้าไม่ว่าง
        """
        available = AvailabilityService.get_available_quantity(product, start_time, end_time, exclude_booking_id)
        if available >= requested_quantity:
            return True, ""
        
        msg = f"สินค้า '{product.name}' ไม่พอสำหรับการจองในช่วงเวลานี้ (เหลือ {available} ชิ้น)"
        return False, msg

    @staticmethod
    def check_resource_overlap(resource_field, resource_instance, start_time, end_time, exclude_booking_id=None):
        """
        ตรวจสอบทรัพยากรเฉพาะชิ้น (เช่น ห้องสตูดิโอ หรือ อุปกรณ์รายชิ้นที่มี S/N) ว่าว่างหรือไม่
        
        Args:
            resource_field: ชื่อฟิลด์ใน Booking model (เช่น 'equipment', 'studios', 'staff')
            resource_instance: Object ที่ต้องการเช็ค
            
        Returns:
            (bool, Booking/None): (True, None) ถ้าว่าง
                                  (False, ConflictingBooking) ถ้ามีการจองซ้อน
        """
        expiry_time = timezone.now() - timedelta(hours=6)
        status_filter = Q(status='draft', created_at__gte=expiry_time) | \
                Q(status__in=['pending', 'approved', 'active', 'overdue'])

        query = status_filter & \
                Q(start_time__lt=end_time) & \
                Q(end_time__gt=start_time)

        # Dynamic field lookup (ใช้ **kwargs เพื่อระบุชื่อฟิลด์แบบ dynamic)
        kwargs = {resource_field: resource_instance}
        query &= Q(**kwargs)

        if exclude_booking_id:
            query &= ~Q(id=exclude_booking_id)

        conflict = Booking.objects.filter(query).first()
        if conflict:
            return False, conflict
            
        return True, None

    @staticmethod
    def check_package_availability(package, start_time, end_time, requested_quantity=1, exclude_booking_id=None):
        """
        ตรวจสอบความพร้อมของ 'แพ็คเกจ'
        โดยการ Loop เช็คสินค้าทุกชิ้นที่อยู่ในแพ็คเกจนั้นว่าว่างพอหรือไม่
        """
        errors = []
        pkg_items = package.packageitem_set.select_related('product').all()
        
        if not pkg_items:
            # Treat package as a standalone rentable item when no child products are defined.
            return True, ""
            
        for pkg_item in pkg_items:
            # จำนวนที่ต้องใช้ = (จำนวนในแพ็คเกจ x จำนวนชุดที่ลูกค้าจอง)
            required_qty = pkg_item.quantity * requested_quantity
            is_valid, msg = AvailabilityService.check_availability(
                pkg_item.product, 
                start_time, 
                end_time, 
                required_qty, 
                exclude_booking_id
            )
            if not is_valid:
                errors.append(msg)
        
        if errors:
            # รวมรายการที่ขาดทั้งหมดไว้ในข้อความเดียว
            return False, f"แพ็คเกจไม่พร้อม: {'; '.join(errors)}"
        
        return True, ""

    @staticmethod
    def validate_cart(cart, start_time, end_time):
        """
        ตรวจสอบตะกร้าสินค้าทั้งหมดรอบเดียว (ใช้ตอนกด Checkout)
        รองรับทั้งสินค้าเดี่ยวและแพ็คเกจ
        """
        if not start_time or not end_time:
            return False, "กรุณาระบุวันเวลารับ-คืนของ"
            
        errors = []
        for item in cart:
            quantity = item['quantity']
            
            if item.get('type') == 'package':
                # กรณีเป็นแพ็คเกจ
                package = item['package']
                is_valid, error_msg = AvailabilityService.check_package_availability(package, start_time, end_time, quantity)
            else:
                # กรณีเป็นสินค้าปกติ
                product = item['product']
                is_valid, error_msg = AvailabilityService.check_availability(product, start_time, end_time, quantity)

            if not is_valid:
                errors.append(error_msg)
                
        if errors:
            return False, "เกิดข้อผิดพลาด: " + "; ".join(errors)
            
        return True, ""

    @staticmethod
    def check_cart_for_api(items, start_date, end_date):
        """
        ตรวจสอบความพร้อมของสินค้าในตะกร้าสำหรับ API Response
        
        Args:
            items: List[dict] รายการสินค้าจาก Payload (ต้องมี id, quantity, type)
            start_date: object datetime/date
            end_date: object datetime/date
            
        Returns:
            conflicts: List[dict] รายการที่มีปัญหา
        """
        from apps.store.models import Product, Studio, Package
        from datetime import datetime

        # Combine Date to DateTime (Start of day / End of day)
        if isinstance(start_date, str):
             start_date = datetime.strptime(start_date, "%Y-%m-%d").date()
        if isinstance(end_date, str):
             end_date = datetime.strptime(end_date, "%Y-%m-%d").date()

        # Ensure datetime for comparison
        start_dt = datetime.combine(start_date, datetime.min.time()) if not hasattr(start_date, 'time') else start_date
        end_dt = datetime.combine(end_date, datetime.max.time()) if not hasattr(end_date, 'time') else end_date

        conflicts = []
        
        for item in items:
            item_id = item.get('id')
            qty = int(item.get('quantity', 1))
            item_type = item.get('type', 'product')
            
            # 1. Product
            if item_type == 'product' or (isinstance(item_id, int)):
                 try:
                    product = Product.objects.get(pk=item_id)
                    is_avail, msg = AvailabilityService.check_availability(product, start_dt, end_dt, qty)
                    
                    if not is_avail:
                        # Get remaining stock for helpful message
                        remaining = AvailabilityService.get_available_quantity(product, start_dt, end_dt)
                        conflicts.append({
                            "id": item_id,
                            "name": product.name,
                            "message": f"เหลือเพียง {remaining} ชิ้น (คุณต้องการ {qty})",
                            "remaining": remaining,
                            "type": "product"
                        })
                 except Product.DoesNotExist:
                     pass

            # 2. Studio
            elif item_type == 'studio' or str(item_id).startswith('studio_'):
                s_id = str(item_id).replace('studio_', '')
                try:
                    studio = Studio.objects.get(pk=s_id)
                    is_valid, _ = AvailabilityService.check_resource_overlap('studios', studio, start_dt, end_dt)
                    if not is_valid:
                         conflicts.append({
                            "id": item_id,
                            "name": studio.name,
                            "message": "ไม่ว่างในช่วงเวลานี้",
                            "remaining": 0,
                            "type": "studio"
                        })
                except Studio.DoesNotExist:
                    pass

            # 3. Package
            elif item_type == 'package' or str(item_id).startswith('pkg_'):
                p_id = str(item_id).replace('pkg_', '')
                try:
                    pkg = Package.objects.get(pk=p_id)
                    is_valid, msg = AvailabilityService.check_package_availability(pkg, start_dt, end_dt, qty)
                    if not is_valid:
                         conflicts.append({
                            "id": item_id,
                            "name": pkg.name,
                            "message": msg,
                            "remaining": 0, 
                            "type": "package"
                        })
                except Package.DoesNotExist:
                    pass

            # 4. ServiceOffer
            elif item_type == 'service' or str(item_id).startswith('srv_') or str(item_id).startswith('svc_'):
                from apps.store.models import ServiceOffer
                svc_id = str(item_id).replace('srv_', '').replace('svc_', '')
                try:
                    service = ServiceOffer.objects.get(pk=svc_id)
                    # Services generally don't have strict physical overlap, but we verify they exist and are active
                    if not service.is_active:
                         conflicts.append({
                            "id": item_id,
                            "name": service.name,
                            "message": "บริการนี้ถูกระงับชั่วคราว",
                            "remaining": 0,
                            "type": "service"
                        })
                except ServiceOffer.DoesNotExist:
                    pass

        return conflicts
