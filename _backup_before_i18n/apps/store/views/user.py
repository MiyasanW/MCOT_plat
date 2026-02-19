from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login
from apps.store.models import Booking
from apps.store.forms import UserRegisterForm

@login_required
def my_bookings(request):
    """
    หน้า Dashboard ของลูกค้า — แสดงรายการจองทั้งหมดของ User ปัจจุบัน
    """
    bookings = Booking.objects.filter(created_by=request.user).order_by('-created_at').prefetch_related(
        'items__product', 'booked_studios__studio', 'booked_packages__package'
    )
    
    # คำนวณ total สำหรับแต่ละ booking
    for booking in bookings:
        item_total = sum(
            item.price_at_booking * item.quantity 
            for item in booking.items.all()
        )
        studio_total = sum(
            bs.price_at_booking 
            for bs in booking.booked_studios.all()
        )
        package_total = sum(
            bp.price_at_booking * bp.quantity 
            for bp in booking.booked_packages.all()
        )
        
        # จำนวนวัน
        days = max(1, (booking.end_time.date() - booking.start_time.date()).days + 1)
        booking.calculated_total = (item_total + studio_total + package_total) * days
        booking.num_days = days
    
    context = {
        'bookings': bookings,
    }
    return render(request, 'booking/my_bookings.html', context)

def register(request):
    if request.method == 'POST':
        form = UserRegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('store:home')
    else:
        form = UserRegisterForm()
    return render(request, 'registration/register.html', {'form': form})

@login_required
def booking_detail(request, booking_id):
    """
    หน้าละเอียดการจอง & อัปโหลดสลิป
    """
    booking = get_object_or_404(Booking, id=booking_id)
    
    # Permission Check: Owner or Staff (Web Admin)
    # Note: Staff/Admin should check via Admin Panel mostly, but this view is for User
    if booking.created_by != request.user and not request.user.is_staff:
        return redirect('store:home') # Forbidden
        
    return render(request, 'booking/detail.html', {'booking': booking})
