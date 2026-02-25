from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from apps.store.models import Equipment, Product, Booking, BookingItem

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
    
    # ดึงประวัติจาก BookingItem โดยเรียงจากล่าสุดไปเก่าสุด
    history_items = BookingItem.objects.filter(equipment=equipment).select_related('booking').order_by('-booking__start_time')

    context = {
        'equipment': equipment,
        'history_items': history_items
    }
    return render(request, 'inventory/history_detail.html', context)


from django.http import JsonResponse
from django.utils import timezone
from datetime import timedelta
from django.db.models import Sum, Count
from django.db.models.functions import TruncMonth
from django.views.decorators.http import require_POST
import json
from apps.store.services.notification_service import NotificationService
from apps.store.services.pricing_service import PricingService
from decimal import Decimal

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
                old_c = old_record.coordinator.name if old_record.coordinator else "None"
                new_c = new_record.coordinator.name if new_record.coordinator else "None"
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
        
        if action == 'request_payment':
            if booking.status != 'draft':
                raise ValueError("ใบจองไม่ได้อยู่ในสถานะรอตรวจสอบ")
            booking.status = 'pending'
            booking.expires_at = timezone.now() + timedelta(hours=24)
            booking.save(update_fields=['status', 'expires_at'])
            NotificationService.send_notification(booking, 'pending_deposit')
            
        elif action == 'confirm_payment':
            if booking.payment_status != 'pending':
                raise ValueError("ไม่มีสลิปให้ยืนยัน หรือยืนยันไปแล้ว")
            booking.payment_status = 'paid'
            booking.save(update_fields=['payment_status'])
            # Status doesn't automatically become 'active' yet, depending on flow. Sometimes staff manually sets active.
            
        elif action == 'mark_active':
            booking.status = 'active'
            booking.save(update_fields=['status'])
            
        elif action == 'mark_completed':
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
            booking.calculate_total_price() # Update grand total
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
def download_quotation_pdf(request, booking_id):
    """
    Generate PDF Quotation for Customer
    """
    booking = get_object_or_404(Booking, id=booking_id)

    # Permission check: Owner or Staff can download
    if booking.created_by != request.user and not (request.user.is_staff or request.user.is_superuser):
        return redirect('store:home')

    items = booking.items.select_related('product', 'equipment').all()
    packages = booking.booked_packages.select_related('package').all()
    studios = booking.booked_studios.select_related('studio').all()
    
    # Calculate Remaining Balance
    remaining_balance = booking.total_price - booking.deposit_amount
    
    context = {
        'booking': booking, 
        'items': items,
        'packages': packages,
        'studios': studios,
        'remaining_balance': remaining_balance
    }
    
    return render(request, 'booking/pdf/quotation.html', context)

from django.db.models import Sum, Count
from django.db.models.functions import TruncMonth

@login_required
def staff_analytics(request):
    """
    หน้า Dashboard รายงานสถิติสำหรับผู้บริหาร/ทีมงาน
    """
    if not (request.user.is_staff or request.user.is_superuser):
        return redirect('store:home')

    # 1. ภาพรวมรายได้และยอดจอง (เฉพาะที่จ่ายเงินแล้วหรืออนุมัติแล้ว)
    valid_status = ['approved', 'active', 'completed']
    bookings = Booking.objects.filter(status__in=valid_status)
    
    total_revenue = bookings.aggregate(Sum('total_price'))['total_price__sum'] or 0
    total_bookings = bookings.count()
    completed_bookings = bookings.filter(status='completed').count()
    active_bookings = bookings.filter(status='active').count()

    # 2. รายได้รายเดือน (ย้อนหลัง 6 เดือน)
    six_months_ago = timezone.now() - timedelta(days=180)
    monthly_revenue = bookings.filter(created_at__gte=six_months_ago)\
        .annotate(month=TruncMonth('created_at'))\
        .values('month')\
        .annotate(revenue=Sum('total_price'))\
        .order_by('month')

    months = [entry['month'].strftime('%b %Y') for entry in monthly_revenue]
    revenues = [float(entry['revenue'] or 0) for entry in monthly_revenue]

    # 3. สินค้าที่ถูกเช่าบ่อยที่สุด (Top 5 Products)
    top_products = BookingItem.objects.filter(booking__status__in=valid_status)\
        .values('product__name')\
        .annotate(total_rented=Sum('quantity'))\
        .order_by('-total_rented')[:5]

    product_names = [item['product__name'] for item in top_products]
    product_counts = [item['total_rented'] for item in top_products]

    context = {
        'total_revenue': total_revenue,
        'total_bookings': total_bookings,
        'completed_bookings': completed_bookings,
        'active_bookings': active_bookings,
        
        # สำหรับ Chart.js
        'months_json': json.dumps(months),
        'revenues_json': json.dumps(revenues),
        'product_names_json': json.dumps(product_names),
        'product_counts_json': json.dumps(product_counts),
    }

    return render(request, 'staff/analytics.html', context)
