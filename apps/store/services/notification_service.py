from django.conf import settings
from django.core.mail import send_mail, EmailMessage
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from apps.store.models import Notification
from decimal import Decimal
import io

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
        
        # 0. กรณี: สร้างใบจองใหม่ (Booking Created)
        if event_type == 'booking_created':
            # แจ้งเตือนเข้า LINE กลุ่ม Staff (มีคนจองเข้ามาใหม่)
            msg = f"📦 New Booking #{booking.id}: {booking.project_name} โดย {booking.customer_name}"
            # send_line_notify(msg) # Disabled
            
            # In-App Notification (For Staff)
            from django.contrib.auth.models import User
            staff_users = User.objects.filter(is_staff=True)
            for staff in staff_users:
                Notification.objects.create(
                    recipient=staff,
                    message=f"📦 ใบจองใหม่ #{booking.id}: กรุณาตรวจสอบและแจ้งยอดชำระ",
                    link=f"/staff/booking/{booking.id}/summary/",
                    notification_type='info'
                )
            
            # ส่งอีเมลยืนยันการรับเรื่อง (Received)
            context = {
                'booking': booking,
                'domain': 'http://127.0.0.1:8000'
            }
            NotificationService.send_email(booking, "ได้รับคำสั่งจองแล้ว (Booking Received)", "rentals/emails/booking_created.html", context)

        # 1. กรณี: แจ้งเตือนการชำระเงิน (Pending Deposit)
        elif event_type == 'pending_deposit':
            # แจ้งเตือนบนเว็บ (ให้ลูกค้า)
            msg = f"Booking #{booking.id}: เจ้าหน้าที่สรุปราคาแล้ว กรุณาชำระเงิน"
            link = f"/booking/{booking.id}/"
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
            # send_line_notify(msg) # Disabled

            # In-App Notification (For Staff)
            from django.contrib.auth.models import User
            staff_users = User.objects.filter(is_staff=True)
            for staff in staff_users:
                Notification.objects.create(
                    recipient=staff,
                    message=f"💰 New Slip Uploaded: Booking #{booking.id}",
                    link=f"/staff/booking/{booking.id}/summary/",
                    notification_type='warning'
                )
            
        # 3. กรณี: อนุมัติการจอง (Approved)
        elif event_type == 'approved':
            # แจ้งเตือนบนเว็บ (ให้ลูกค้า)
            msg = f"Booking #{booking.id}: ยืนยันการจองเรียบร้อยแล้ว เตรียมรับของได้เลย"
            link = f"/booking/{booking.id}/"
            Notification.objects.create(recipient=booking.created_by, message=msg, link=link, notification_type='success')
            
            # ส่งอีเมลยืนยันผลการจอง
            context = {
                'booking': booking,
                'domain': 'http://127.0.0.1:8000'
            }
            NotificationService.send_email(booking, "ยืนยันการจอง (Booking Confirmed)", "rentals/emails/booking_approved.html", context)

        # 4. กรณี: ยกเลิกการจอง (Cancelled)
        elif event_type == 'cancelled':
            # แจ้งเตือนบนเว็บ (ให้ลูกค้า)
            msg = f"Booking #{booking.id}: ถูกยกเลิก"
            link = f"/booking/{booking.id}/"
            Notification.objects.create(recipient=booking.created_by, message=msg, link=link, notification_type='error')
            
            # ส่งอีเมลแจ้งยกเลิก
            context = {
                'booking': booking,
                'domain': 'http://127.0.0.1:8000'
            }
            NotificationService.send_email(booking, "แจ้งยกเลิกการจอง (Booking Cancelled)", "rentals/emails/booking_cancelled.html", context)

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

    @staticmethod
    def send_quotation_email(booking, items, packages, studios):
        """
        ส่งใบเสนอราคาเป็น PDF แนบไปกับอีเมลให้ลูกค้า
        """
        if not booking.customer_email:
            raise ValueError("ลูกค้ายังไม่ได้ระบุอีเมล กรุณาเพิ่มอีเมลก่อนส่งใบเสนอราคา")
        
        try:
            # 1. Render quotation HTML
            remaining_balance = booking.total_price - booking.deposit_amount
            html_content = render_to_string('booking/pdf/quotation.html', {
                'booking': booking,
                'items': items,
                'packages': packages,
                'studios': studios,
                'remaining_balance': remaining_balance,
            })
            
            # 2. Convert HTML to PDF using xhtml2pdf
            pdf_buffer = io.BytesIO()
            try:
                from xhtml2pdf import pisa
                pisa_status = pisa.CreatePDF(html_content, dest=pdf_buffer, encoding='utf-8')
                if pisa_status.err:
                    raise Exception("PDF generation failed")
                pdf_data = pdf_buffer.getvalue()
            except ImportError:
                # xhtml2pdf not installed - send HTML email instead
                print("xhtml2pdf not available, sending HTML-only email")
                pdf_data = None
            finally:
                pdf_buffer.close()
            
            # 3. Compose email
            subject = f"[MCOT Rental] ใบเสนอราคา (Quotation) #{booking.id}"
            body = (
                f"เรียน {booking.customer_name},\n\n"
                f"ขอบคุณที่สนใจใช้บริการเช่าอุปกรณ์ MCOT Rental\n"
                f"แนบใบเสนอราคาสำหรับการจอง #{booking.id} มาพร้อมนี้\n\n"
                f"รายละเอียดโดยสรุป:\n"
                f"- โปรเจกต์: {booking.project_name or '-'}\n"
                f"- ระยะเวลาเช่า: {booking.start_time.strftime('%d/%m/%Y')} - {booking.end_time.strftime('%d/%m/%Y')}\n"
                f"- ยอดรวม: ฿{booking.total_price:,.2f}\n"
                f"- ยอดมัดจำ (30%): ฿{booking.deposit_amount:,.2f}\n\n"
                f"กรุณาตรวจสอบรายละเอียดในไฟล์แนบ\n"
                f"หากมีข้อสงสัยสามารถตอบกลับอีเมลนี้ หรือโทร 02-201-6000\n\n"
                f"ขอแสดงความนับถือ,\n"
                f"MCOT Rental Platform\n"
            )
            
            email = EmailMessage(
                subject=subject,
                body=body,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[booking.customer_email],
            )
            
            # Attach PDF if available
            if pdf_data:
                email.attach(
                    f'MCOT_Quotation_{booking.id}.pdf',
                    pdf_data,
                    'application/pdf'
                )
            
            email.send(fail_silently=False)
            
            # 4. In-App Notification for customer
            Notification.objects.create(
                recipient=booking.created_by,
                message=f"📧 ใบเสนอราคา #{booking.id} ได้ถูกส่งไปที่อีเมลของคุณแล้ว",
                link=f"/booking/{booking.id}/",
                notification_type='info'
            )
            
        except Exception as e:
            print(f"Error sending quotation email: {e}")
            raise
