from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from apps.store.models import Notification
from apps.store.services.notify import send_line_notify
from decimal import Decimal

class NotificationService:
    """
    Service รวมศูนย์สำหรับจัดการระบบแจ้งเตือน (Notification System)
    ครอบคลุมทั้ง In-App Notification (Web), Lite Notify (Line Group), และ Email
    """
    
    @staticmethod
    def send_notification(booking, event_type):
        """
        ส่งการแจ้งเตือนผ่านช่องทางต่างๆ ตามประเภทของเหตุการณ์ (Event Type)
        
        Event Types:
        - 'pending_deposit': Admin สรุปราคาแล้ว -> แจ้งลูกค้าให้จ่ายเงิน
        - 'verification_pending': ลูกค้าแนบสลิป -> แจ้ง Admin ให้ตรวจสอบ
        - 'approved': Admin อนุมัติ -> แจ้งลูกค้าว่าจองสำเร็จ (พร้อมรับของ)
        """
        
        # 1. กรณี: แจ้งเตือนการชำระเงิน (Pending Deposit)
        if event_type == 'pending_deposit':
            # แจ้งเตือนบนเว็บ (ให้ลูกค้า)
            msg = f"Booking #{booking.id}: เจ้าหน้าที่สรุปราคาแล้ว กรุณาชำระเงิน"
            link = f"/rentals/booking/{booking.id}/"
            Notification.objects.create(recipient=booking.created_by, message=msg, link=link, notification_type='info')
            
            # ส่งอีเมลยอดชำระเงิน
            total_price = booking.calculate_total_price() or 0
            deposit_amount = total_price * Decimal('0.3') # มัดจำ 30%
            context = {
                'booking': booking,
                'deposit_amount': f"{deposit_amount:,.2f}",
                'domain': 'http://127.0.0.1:8000' # TODO: ควรดึงจาก settings ในอนาคต
            }
            NotificationService.send_email(booking, "แจ้งสรุปยอดชำระเงิน (Payment Required)", "rentals/emails/pending_deposit.html", context)
            
        # 2. กรณี: รอตรวจสอบสลิป (Verification Pending)
        elif event_type == 'verification_pending':
            # แจ้งเตือนเข้า LINE กลุ่ม Staff (ให้ Admin รู้ทันที)
            msg = f"💸 แจ้งโอนเงินใหม่: Booking #{booking.id} ({booking.customer_name}) รอตรวจสอบสลิป"
            send_line_notify(msg)
            
        # 3. กรณี: อนุมัติการจอง (Approved)
        elif event_type == 'approved':
            # แจ้งเตือนบนเว็บ (ให้ลูกค้า)
            msg = f"Booking #{booking.id}: ยืนยันการจองเรียบร้อยแล้ว เตรียมรับของได้เลย"
            link = f"/rentals/booking/{booking.id}/"
            Notification.objects.create(recipient=booking.created_by, message=msg, link=link, notification_type='success')
            
            # ส่งอีเมลยืนยันผลการจอง
            context = {
                'booking': booking,
                'domain': 'http://127.0.0.1:8000'
            }
            NotificationService.send_email(booking, "ยืนยันการจอง (Booking Confirmed)", "rentals/emails/booking_approved.html", context)

    @staticmethod
    def send_email(booking, subject, template_path, context=None):
        """
        ฟังก์ชัน Helper สำหรับส่งอีเมล (รองรับ Template HTML)
        """
        if not booking.customer_email:
            return
            
        if context is None:
            context = {'booking': booking}
            
        try:
            html_message = render_to_string(template_path, context)
            plain_message = strip_tags(html_message)
            
            send_mail(
                subject=f"[MCOT Rental] {subject} #{booking.id}",
                message=plain_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[booking.customer_email],
                html_message=html_message,
                fail_silently=False,
            )
        except Exception as e:
            # Log error ไว้แต่ไม่ให้ระบบพัง
            print(f"Error sending email: {e}")
