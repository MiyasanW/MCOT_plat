from decimal import Decimal
from apps.store.models import Booking

class DocumentService:
    """
    Service สำหรับจัดการเอกสาร (Documents)
    เช่น ใบเสนอราคา (Quotation) และใบเบิกของ (Work Order)
    """

    @staticmethod
    def generate_quotation_context(booking_id):
        """
        สร้าง Context (ข้อมูล) สำหรับแสดงผลใบเสนอราคา
        
        Args:
            booking_id: ID ของ Booking
            
        Returns:
            dict: Context ที่ประกอบด้วย booking, items, days, subtotal, vat, grand_total
        """
        # ดึงข้อมูล Booking
        # Note: เราใช้ get() แล้วให้ View handle 404 ดีกว่า หรือ raise exception ที่นี่
        # แต่เพื่อความง่ายในการ Refactor ให้ใช้ Logic เดิมคือ assume booking exists หรือ handle error ใน View
        booking = Booking.objects.get(id=booking_id)
        
        # คำนวณจำนวนวัน (Duration)
        duration = booking.end_time - booking.start_time
        days = duration.total_seconds() / (24 * 3600)
        if days < 1:
            days = 1
        else:
            # ปัดเศษวันขึ้น
            days = int(days) + (1 if days % 1 > 0 else 0)
        
        items = []
        
        # 1. รายการอุปกรณ์ (Equipment)
        # กรณีมีการ Assign Serial Number แล้ว
        for eq in booking.equipment.all():
            product_name = eq.product.name if eq.product else "Unknown Item"
            product_price = eq.product.price if eq.product else 0
            items.append({
                'name': product_name,
                'details': f"S/N: {eq.serial_number}",
                'price': product_price,
                'total': product_price * days,
                'type': 'Equipment'
            })
            
        # กรณีจองแบบระบุจำนวน (BookingItem) แต่ยังไม่ได้ Assign Serial
        # หรือถ้าเราต้องการแสดงตามที่จองมา (ถ้ายังไม่มี Equipment assigned)
        if not booking.equipment.exists():
            for item in booking.items.all():
                items.append({
                    'name': item.product.name,
                    'details': f"Quantity: {item.quantity}",
                    'price': item.price_at_booking or item.product.price,
                    'total': item.total_price() * days,
                    'type': 'Product'
                })
            
        # 2. รายการสตูดิโอ (Studios)
        for st in booking.studios.all():
            items.append({
                'name': st.name,
                'details': "Studio rental",
                'price': st.daily_rate,
                'total': st.daily_rate * days,
                'type': 'Studio'
            })

        # คำนวณยอดรวม (Totals)
        subtotal = sum(item['total'] for item in items)
        vat = subtotal * Decimal('0.07') # VAT 7%
        grand_total = subtotal + vat
        
        return {
            'booking': booking,
            'items': items,
            'days': int(days),
            'subtotal': subtotal,
            'vat': vat,
            'grand_total': grand_total,
        }

    @staticmethod
    def generate_work_order_context(booking_id):
        """
        สร้าง Context (ข้อมูล) สำหรับใบเบิกของ (Work Order)
        เน้นข้อมูล Serial Number และจำนวนที่ต้องเตรียม
        """
        booking = Booking.objects.get(id=booking_id)
        
        # คำนวณจำนวนวัน
        duration = booking.end_time - booking.start_time
        days = duration.total_seconds() / (24 * 3600)
        days = 1 if days < 1 else int(days) + (1 if days % 1 > 0 else 0)
        
        items = []
        
        # 1. รายการอุปกรณ์ (Equipment - Serial Number)
        for eq in booking.equipment.all():
            product_name = eq.product.name if eq.product else "Unknown Item"
            items.append({
                'name': product_name,
                'details': f"S/N: {eq.serial_number}",
                'type': 'Equipment',
                'qty': 1,
                'unit': 'ชุด/ชิ้น'
            })

        # ถ้ายังไม่ได้ Assign Serial ให้แสดงรายการจาก BookingItem
        if not booking.equipment.exists():
            for item in booking.items.all():
                items.append({
                    'name': item.product.name,
                    'details': "Waiting for assignment",
                    'type': 'Product',
                    'qty': item.quantity,
                    'unit': 'ชุด/ชิ้น'
                })
            
        # 2. รายการสตูดิโอ (Studios)
        for st in booking.studios.all():
            items.append({
                'name': st.name,
                'details': "Studio Set",
                'type': 'Studio',
                'qty': 1,
                'unit': 'ห้อง'
            })

        return {
            'booking': booking,
            'items': items,
            'days': int(days),
        }
