"""
รายงานใบจอง (Staff Reports) — หน้ารายงานหลักสำหรับ Staff
- /staff/reports/ : กรองช่วงวันที่, แสดงตาราง, ลิงก์ไปสรุปแต่ละใบ
- /staff/reports/export/ : Export CSV ตาม start & end
"""
import csv
from datetime import timedelta, datetime

from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import HttpResponse
from django.utils import timezone

from apps.store.models import Booking


@login_required
def staff_reports(request):
    """
    หน้ารายงาน: รายการจองตามช่วงวันที่ พร้อมปุ่ม Export CSV
    """
    if not (request.user.is_staff or request.user.is_superuser):
        return redirect('store:home')

    # ค่าเริ่มต้น: 30 วันย้อนหลัง
    today = timezone.now().date()
    start_default = (today - timedelta(days=30)).strftime('%Y-%m-%d')
    end_default = today.strftime('%Y-%m-%d')
    start_str = request.GET.get('start', start_default)
    end_str = request.GET.get('end', end_default)

    try:
        start_date = datetime.strptime(start_str, '%Y-%m-%d').date()
        end_date = datetime.strptime(end_str, '%Y-%m-%d').date()
        if start_date > end_date:
            start_date, end_date = end_date, start_date
    except (ValueError, TypeError):
        start_date = today - timedelta(days=30)
        end_date = today

    bookings = Booking.objects.filter(
        Q(created_at__date__gte=start_date, created_at__date__lte=end_date) |
        Q(start_time__date__gte=start_date, start_time__date__lte=end_date)
    ).select_related('coordinator', 'created_by').distinct().order_by('-created_at')[:500]

    context = {
        'bookings': bookings,
        'start_date': start_date.strftime('%Y-%m-%d'),
        'end_date': end_date.strftime('%Y-%m-%d'),
    }
    return render(request, 'staff/reports.html', context)


@login_required
def staff_reports_export_csv(request):
    """
    Export รายการจองเป็น CSV ตามช่วงวันที่ (GET start, end)
    """
    if not (request.user.is_staff or request.user.is_superuser):
        return redirect('store:home')

    today = timezone.now().date()
    start_str = request.GET.get('start', (today - timedelta(days=30)).strftime('%Y-%m-%d'))
    end_str = request.GET.get('end', today.strftime('%Y-%m-%d'))
    try:
        start_date = datetime.strptime(start_str, '%Y-%m-%d').date()
        end_date = datetime.strptime(end_str, '%Y-%m-%d').date()
    except (ValueError, TypeError):
        start_date = today - timedelta(days=30)
        end_date = today

    bookings = Booking.objects.filter(
        Q(created_at__date__gte=start_date, created_at__date__lte=end_date) |
        Q(start_time__date__gte=start_date, start_time__date__lte=end_date)
    ).distinct().order_by('-created_at')

    response = HttpResponse(content_type='text/csv; charset=utf-8-sig')
    response['Content-Disposition'] = f'attachment; filename="bookings_{start_date}_{end_date}.csv"'
    writer = csv.writer(response)
    writer.writerow([
        'ID', 'ลูกค้า', 'อีเมล', 'โปรเจกต์', 'เบอร์', 'วันรับ', 'วันคืน', 'สถานะ', 'สถานะเงิน', 'ยอดรวม', 'มัดจำ', 'สร้างเมื่อ'
    ])
    for b in bookings:
        writer.writerow([
            b.id,
            b.customer_name or '',
            b.customer_email or '',
            b.project_name or '',
            b.phone or '',
            b.start_time.strftime('%Y-%m-%d') if b.start_time else '',
            b.end_time.strftime('%Y-%m-%d') if b.end_time else '',
            b.get_status_display(),
            b.get_payment_status_display(),
            b.total_price,
            b.deposit_amount,
            b.created_at.strftime('%Y-%m-%d %H:%M') if b.created_at else '',
        ])
    return response
