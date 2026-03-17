import json
import os
from decimal import Decimal

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.conf import settings
from django.http import HttpResponse, JsonResponse
from django.utils import timezone
from datetime import timedelta
from django.db.models import Q, Sum, Count
from django.db.models.functions import TruncMonth
from django.views.decorators.http import require_POST

from apps.store.models import Equipment, Product, Booking, BookingItem
from apps.store.services.notification_service import NotificationService
from apps.store.services.pricing_service import PricingService
from apps.store.services.dashboard_service import DashboardService

@login_required
def equipment_history_search(request):
    """
    หน้าค้นหาประวัติอุปกรณ์ (Search Equipment History)
    """
    # Requires Staff/Admin
    if not (request.user.is_staff or request.user.is_superuser):
        return redirect('store:home')

    query = request.GET.get('q')
    product_id = request.GET.get('product')
    equipments = None
    
    if query:
        # Search by Serial, Inventory Number, Asset Tag, OR Product Name
        equipments = Equipment.objects.filter(
            Q(serial_number__icontains=query) | 
            Q(inventory_number__icontains=query) |
            Q(asset_tag__icontains=query) |
            Q(product__name__icontains=query)
        )
    elif product_id:
        # Filter by specific Product
        equipments = Equipment.objects.filter(product_id=product_id)

    # If exact match found (1 item), redirect to detail
    if equipments and equipments.count() == 1:
        return redirect('store:equipment_history_detail', equipment_id=equipments.first().id)
            
    products = Product.objects.filter(is_active=True).order_by('name')
    return render(request, 'inventory/history_search.html', {
        'equipments': equipments, 
        'query': query,
        'products': products,
        'selected_product': int(product_id) if product_id else None
    })

@login_required
def equipment_history_detail(request, equipment_id):
    """
    หน้าแสดงประวัติการใช้งานอุปกรณ์ (Equipment History Detail)
    """
    if not (request.user.is_staff or request.user.is_superuser):
        return redirect('store:home')

    equipment = get_object_or_404(Equipment, id=equipment_id)
    
    # ดึงประวัติจาก BookingItem โดยดูจาก product ของอุปกรณ์นี้
    # (equipment FK อาจไม่ได้ assign ทุกครั้ง จึง fallback ไปดูจาก product แทน)
    history_items = BookingItem.objects.filter(
        product=equipment.product
    ).select_related('booking', 'equipment').order_by('-booking__start_time')

    context = {
        'equipment': equipment,
        'history_items': history_items
    }
    return render(request, 'inventory/history_detail.html', context)



@login_required
def booking_summary(request, booking_id):
    """
    หน้า Quick Summary Dashboard สำหรับ Staff
    """
    if not (request.user.is_staff or request.user.is_superuser):
        return redirect('store:home')
        
    booking = get_object_or_404(Booking, id=booking_id)
    items = booking.items.select_related('product', 'equipment').all()
    packages = booking.booked_packages.select_related('package').all()
    studios = booking.booked_studios.select_related('studio').all()
    
    # Calculate penalty preview (if overdue)
    current_penalty = Decimal(0)
    for item in items:
        if item.returned_at and item.returned_at > booking.end_time: # If already returned late
            days_late = (item.returned_at.date() - booking.end_time.date()).days
            if days_late > 0 and item.product.late_fee_per_day:
                current_penalty += Decimal(days_late) * item.product.late_fee_per_day
                
        # Attach available equipment for the dropdown (exclude ones currently rented by others)
        status_to_exclude = ['active', 'approved']
        unavailable_eq_ids = BookingItem.objects.filter(
            booking__status__in=status_to_exclude,
            equipment__isnull=False
        ).exclude(booking=booking).values_list('equipment_id', flat=True)
        
        item.available_equipments = Equipment.objects.filter(
            product=item.product,
            status='available'
        ).exclude(id__in=unavailable_eq_ids)
                
    # 3. Fetch History (Activity Log)
    history_records = booking.history.all().order_by('-history_date')
    history_logs = []
    
    for i in range(len(history_records)):
        new_record = history_records[i]
        old_record = history_records[i + 1] if i + 1 < len(history_records) else None
        
        changes = []
        if old_record:
            if old_record.status != new_record.status:
                changes.append(f"เปลี่ยนสถานะจาก '{old_record.get_status_display()}' เป็น '{new_record.get_status_display()}'")
            if old_record.payment_status != new_record.payment_status:
                changes.append(f"สถานะการเงิน: '{old_record.get_payment_status_display()}' -> '{new_record.get_payment_status_display()}'")
            if old_record.coordinator != new_record.coordinator:
                old_c = (old_record.coordinator.get_full_name() or old_record.coordinator.username) if old_record.coordinator else "None"
                new_c = (new_record.coordinator.get_full_name() or new_record.coordinator.username) if new_record.coordinator else "None"
                changes.append(f"เปลี่ยนผู้ดูแลจาก '{old_c}' เป็น '{new_c}'")
            if old_record.internal_notes != new_record.internal_notes:
                changes.append("อัปเดตบันทึกภายใน (Internal Notes)")
        else:
            changes.append("สร้างใบจองครั้งแรก")
            
        if changes:
            history_logs.append({
                'date': new_record.history_date,
                'user': new_record.history_user.username if new_record.history_user else 'System/Customer',
                'changes': ", ".join(changes)
            })
            
    context = {
        'booking': booking,
        'items': items,
        'packages': packages,
        'studios': studios,
        'preview_penalty': current_penalty,
        'history_logs': history_logs,
    }
    return render(request, 'staff/booking_summary.html', context)

@login_required
@require_POST
def booking_action_api(request, booking_id):
    """
    API สำหรับคำสั่ง Quick Actions ในหน้า Summary
    """
    if not (request.user.is_staff or request.user.is_superuser):
        return JsonResponse({'success': False, 'message': 'Permission Denied'}, status=403)
        
    booking = get_object_or_404(Booking, id=booking_id)
    
    try:
        data = json.loads(request.body)
        action = data.get('action')
        
        if action == 'send_quotation':
            if booking.status != 'draft':
                raise ValueError("ใบจองไม่ได้อยู่ในสถานะรอตรวจสอบ")
            # Send quotation PDF via email
            items = booking.items.select_related('product', 'equipment').all()
            packages = booking.booked_packages.select_related('package').all()
            studios = booking.booked_studios.select_related('studio').all()
            NotificationService.send_quotation_email(booking, items, packages, studios)
            # Change status to pending
            booking.status = 'pending'
            booking.expires_at = timezone.now() + timedelta(hours=24)
            booking.save(update_fields=['status', 'expires_at'])
            
        elif action == 'confirm_payment':
            if booking.payment_status != 'pending':
                raise ValueError("ไม่มีสลิปให้ยืนยัน หรือยืนยันไปแล้ว")
            booking.payment_status = 'paid'
            booking.save(update_fields=['payment_status'])
            # Status doesn't automatically become 'active' yet, depending on flow. Sometimes staff manually sets active.

        elif action == 'skip_deposit':
            # ข้ามขั้นตอนมัดจำ (บางรายไม่เก็บค่ามัดจำ)
            if booking.status not in ('draft', 'pending'):
                raise ValueError("ใช้ได้เฉพาะใบจองที่รอตรวจสอบหรือรออนุมัติ")
            booking.payment_status = 'waived'
            booking.save(update_fields=['payment_status'])
            
        elif action == 'mark_active':
            if booking.status == 'pending' and booking.payment_status not in ('paid', 'waived'):
                raise ValueError("ต้องยืนยันการชำระเงินหรือข้ามมัดจำก่อนปล่อยของ")
            if booking.status not in ('pending', 'approved'):
                raise ValueError("เปลี่ยนเป็นกำลังใช้งานได้เฉพาะใบจองที่รออนุมัติ/อนุมัติแล้วเท่านั้น")
            booking.status = 'active'
            booking.save(update_fields=['status'])
            
        elif action == 'mark_completed':
            if booking.status not in ('active', 'overdue'):
                raise ValueError("ปิดงานได้เฉพาะใบจองที่กำลังใช้งานหรือเกินกำหนด")
            booking.status = 'completed'
            booking.save(update_fields=['status'])
            
        elif action == 'cancel':
            reason = data.get('reason', '')
            if reason:
                booking.internal_notes = (booking.internal_notes or '') + f"\\nยกเลิก: {reason}"
            booking.status = 'cancelled'
            booking.save(update_fields=['status', 'internal_notes'])
            NotificationService.send_notification(booking, 'cancelled')
            
        elif action == 'update_notes':
            notes = data.get('notes', '')
            booking.internal_notes = notes
            booking.save(update_fields=['internal_notes'])
            
        elif action == 'save_penalty':
            penalty = Decimal(data.get('amount', 0))
            booking.penalty_amount = penalty
            booking.total_price = booking.calculate_total_price()
            booking.save(update_fields=['penalty_amount', 'total_price'])
            
        elif action == 'assign_equipment':
            item_id = data.get('item_id')
            asset_tag = data.get('asset_tag')
            if not asset_tag:
                 # Clear assignment
                 BookingItem.objects.filter(id=item_id, booking=booking).update(equipment=None)
            else:
                 # Find equipment
                 eq = Equipment.objects.filter(asset_tag=asset_tag, product__bookingitem__id=item_id).first()
                 if not eq:
                     raise ValueError(f"ไม่พบอุปกรณ์รหัส {asset_tag} ในสินค้านี้")
                 BookingItem.objects.filter(id=item_id, booking=booking).update(equipment=eq)

        elif action == 'update_dates':
            # เจ้าหน้าที่แก้วันที่ (ขยายระยะเวลา) — ระวังไม่ให้ทับกับ overdue
            from datetime import datetime as dt
            start_str = data.get('start')
            end_str = data.get('end')
            if not start_str or not end_str:
                raise ValueError("กรุณาระบุวันเริ่มและวันสิ้นสุด (start, end รูปแบบ YYYY-MM-DD)")
            try:
                new_start = timezone.make_aware(dt.strptime(start_str[:10], "%Y-%m-%d").replace(hour=0, minute=0, second=0, microsecond=0))
                new_end = timezone.make_aware(dt.strptime(end_str[:10], "%Y-%m-%d").replace(hour=23, minute=59, second=59, microsecond=999999))
            except (ValueError, TypeError):
                raise ValueError("รูปแบบวันที่ไม่ถูกต้อง ใช้ YYYY-MM-DD")
            if new_end < new_start:
                raise ValueError("วันคืนของต้องไม่ก่อนวันรับของ")
            booking.start_time = new_start
            booking.end_time = new_end
            # ถ้าเดิม overdue แต่เลื่อนวันคืนไปข้างหน้าแล้วเกินวันนี้ → กลับเป็น active
            now = timezone.now()
            if booking.status == 'overdue' and new_end >= now:
                booking.status = 'active'
                booking.save(update_fields=['start_time', 'end_time', 'status'])
            else:
                booking.save(update_fields=['start_time', 'end_time'])

        elif action == 'set_item_return_status':
            # ตอนคืนของ: เจ้าหน้าที่กดว่าคืนแล้ว หรือ ชำรุด (เก็บ log)
            item_id = data.get('item_id')
            status = data.get('status')  # 'returned' | 'damaged'
            notes = data.get('notes', '')
            if not item_id or status not in ('returned', 'damaged'):
                raise ValueError("ระบุ item_id และ status (returned หรือ damaged)")
            bi = BookingItem.objects.filter(id=item_id, booking=booking).first()
            if not bi:
                raise ValueError("ไม่พบรายการนี้ในใบจอง")
            bi.status = status
            bi.returned_at = timezone.now()
            if notes:
                bi.notes = (bi.notes or '') + (' ' + notes).strip()
            bi.save(update_fields=['status', 'returned_at', 'notes'])
            
        else:
            return JsonResponse({'success': False, 'message': 'Invalid Action'}, status=400)
            
        return JsonResponse({'success': True, 'message': 'บันทึกสำเร็จ'})
        
    except ValueError as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=400)
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'System Error: {str(e)}'}, status=500)

@login_required
def download_booking_pdf(request, booking_id):
    """
    Generate PDF Equipment Sheet for Staff
    """
    # Permission check: Staff only
    if not (request.user.is_staff or request.user.is_superuser):
        return redirect('store:home')

    booking = get_object_or_404(Booking, id=booking_id)
    items = booking.items.select_related('product', 'equipment').all()
    packages = booking.booked_packages.select_related('package').all()
    studios = booking.booked_studios.select_related('studio').all()

    template_path = 'booking/pdf/equipment_sheet.html'
    context = {
        'booking': booking, 
        'items': items,
        'packages': packages,
        'studios': studios
    }

    # Fallback to HTML Print due to xhtml2pdf installation issues
    return render(request, template_path, context)


@login_required
def download_checklist_pdf(request, booking_id):
    """
    PDF Checklist รายการของที่จอง (สำหรับเจ้าหน้าที่ใช้ตอนส่งของ/คืนของ)
    """
    if not (request.user.is_staff or request.user.is_superuser):
        return redirect('store:home')
    booking = get_object_or_404(Booking, id=booking_id)
    items = booking.items.select_related('product', 'equipment').all()
    packages = booking.booked_packages.select_related('package').all()
    studios = booking.booked_studios.select_related('studio').all()
    return render(request, 'booking/pdf/checklist_return.html', {
        'booking': booking,
        'items': items,
        'packages': packages,
        'studios': studios,
    })

@login_required
def download_quotation_pdf(request, booking_id):
    """
    Generate and stream a PDF Quotation by overlaying booking data onto
    the MCOT quotation template (quotation_template.pdf).
    """
    booking = get_object_or_404(Booking, id=booking_id)

    # Permission check: draft bookings are not yet ready for customer download
    if booking.created_by == request.user and booking.status == 'draft':
        return redirect('store:booking_detail', booking_id=booking.id)

    if booking.created_by != request.user and not (request.user.is_staff or request.user.is_superuser):
        return redirect('store:home')

    template_path = os.path.join(
        settings.BASE_DIR, 'apps', 'store', 'services', 'pdf', 'quotation_template.pdf'
    )

    from apps.store.services.pdf.quotation_overlay import generate_quotation_pdf
    pdf_bytes = generate_quotation_pdf(booking, template_path)

    response = HttpResponse(pdf_bytes, content_type='application/pdf')
    response['Content-Disposition'] = (
        f'inline; filename="MCOT_Quotation_{booking.id:05d}.pdf"'
    )
    return response


@login_required
def staff_dashboard(request):
    """
    หน้า Dashboard ภาพรวมสำหรับ Staff (จุดเข้าแรกหลังล็อกอิน)
    """
    if not (request.user.is_staff or request.user.is_superuser):
        return redirect('store:home')
    stats = DashboardService.get_admin_dashboard_stats()
    return render(request, 'staff/dashboard.html', stats)


