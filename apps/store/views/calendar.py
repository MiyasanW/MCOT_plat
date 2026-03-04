from django.http import JsonResponse
from django.shortcuts import render
from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import Q
from apps.store.models import Booking
from django.contrib.auth.models import User

@staff_member_required
def calendar_view(request):
    return render(request, 'pages/calendar.html')

@staff_member_required
def staff_list_api(request):
    # Fetch active staff
    staffs = User.objects.filter(groups__name='staff', is_active=True).values('id', 'first_name', 'last_name')
    data = []
    for s in staffs:
        name = f"{s['first_name']} {s['last_name']}".strip()
        if not name:
             name = f"Staff ID {s['id']}"
        
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
    
    # --- Role-Based Access Control ---
    from apps.store.admin import is_web_admin, is_staff_role
    
    if request.user.is_superuser or is_web_admin(request.user):
        # Admins can optionally filter by a specific staff_id
        staff_id = request.GET.get('staff_id')
        if staff_id and staff_id != 'all':
            if staff_id == 'me':
                if hasattr(request.user, 'staff_profile'):
                    bookings = bookings.filter(
                        Q(coordinator=request.user.staff_profile) | 
                        Q(created_by=request.user)
                    )
                else:
                    bookings = bookings.filter(created_by=request.user)
            else:
                bookings = bookings.filter(coordinator_id=staff_id)
    elif is_staff_role(request.user):
        # Staff ALAYWS only sees their assigned bookings, regardless of filter params
        bookings = bookings.filter(
            Q(coordinator__user=request.user) |
            Q(assigned_staff__staff__user=request.user)
        ).distinct()
    else:
        # Others see nothing
        bookings = Booking.objects.none()
    
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
            # coordinator is now a User
            coord_name = f"{b.coordinator.first_name} {b.coordinator.last_name}".strip() or b.coordinator.username

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
