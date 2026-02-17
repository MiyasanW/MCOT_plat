from django.http import JsonResponse
from django.shortcuts import render
from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import Q
from .models import Booking, Staff

@staff_member_required
def calendar_view(request):
    return render(request, 'pages/calendar.html')

@staff_member_required
def staff_list_api(request):
    # Fetch active staff
    staffs = Staff.objects.filter(is_active=True).values('id', 'name', 'user__first_name', 'user__last_name')
    data = []
    for s in staffs:
        # Prefer Staff Name, fallback to User Name
        name = s['name']
        if not name and s.get('user__first_name'):
             name = f"{s['user__first_name']} {s['user__last_name']}"
        
        data.append({'id': s['id'], 'name': name})
    return JsonResponse(data, safe=False)

@staff_member_required
def calendar_events_api(request):
    """API สำหรับ FullCalendar — ดึง booking ทั้งหมด"""
    start = request.GET.get('start')  # FullCalendar ส่งมาเป็น ISO date (e.g. 2026-02-01T00:00:00)
    end = request.GET.get('end')
    
    bookings = Booking.objects.exclude(status='cancelled')
    
    if start and end:
        bookings = bookings.filter(
            start_time__lte=end,
            end_time__gte=start
        )
    
    # Filter by Staff (Coordinator) if provided
    staff_id = request.GET.get('staff_id')
    if staff_id and staff_id != 'all':
        if staff_id == 'me':
            # See my coordinated OR my created bookings
            if hasattr(request.user, 'staff_profile'):
                bookings = bookings.filter(
                    Q(coordinator=request.user.staff_profile) | 
                    Q(created_by=request.user)
                )
            else:
                bookings = bookings.filter(created_by=request.user)
        else:
            # See specific staff's bookings (Coordinator)
            bookings = bookings.filter(coordinator_id=staff_id)
    
    events = []
    for b in bookings:
        # สีตาม status
        color_map = {
            'draft': '#6b7280',      # เทา
            'pending': '#f59e0b',    # เหลือง
            'approved': '#3b82f6',   # น้ำเงิน
            'active': '#10b981',     # เขียว
            'completed': '#8b5cf6',  # ม่วง
        }
        
        coord_name = 'ยังไม่ assign'
        if hasattr(b, 'coordinator') and b.coordinator:
            coord_name = b.coordinator.name

        events.append({
            'id': b.id,
            'title': f"#{b.id} {b.project_name or b.customer_name}",
            'start': b.start_time.isoformat() if b.start_time else None,
            'end': b.end_time.isoformat() if b.end_time else None,
            'color': color_map.get(b.status, '#6b7280'),
            'url': f"/admin/store/booking/{b.id}/change/",
            'extendedProps': {
                'customer': b.customer_name,
                'status': b.get_status_display(),
                'coordinator': coord_name,
                'phone': b.phone or '-',
            }
        })
    
    return JsonResponse(events, safe=False)
