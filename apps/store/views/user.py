from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login
from django.contrib import messages
from apps.store.models import Booking, Profile
from apps.store.forms import UserRegisterForm

@login_required
def my_bookings(request):
    """
    หน้า Dashboard ของลูกค้า — แสดงรายการจองทั้งหมดของ User ปัจจุบัน
    """
    bookings = Booking.objects.filter(created_by=request.user).order_by('-created_at').prefetch_related(
        'items__product', 'booked_studios__studio', 'booked_packages__package'
    )
    
    # We no longer need to calculate totals manually here since we added properties to the Booking model:
    # booking.item_total, booking.studio_total, booking.package_total, booking.rental_days, booking.calculated_total_price
    # The template can access them directly or we can attach them to avoid template changes.
    for booking in bookings:
        booking.calculated_total = booking.calculated_total_price
        booking.num_days = booking.rental_days
    
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


@login_required
def complete_profile(request):
    """
    Force Google-registered users to fill in their phone number.
    """
    profile, created = Profile.objects.get_or_create(user=request.user)
    
    if request.method == 'POST':
        phone = request.POST.get('phone', '').strip()
        if phone and len(phone) >= 9 and phone.isdigit():
            profile.phone = phone
            profile.save()
            messages.success(request, 'บันทึกข้อมูลเรียบร้อยแล้ว! ยินดีต้อนรับเข้าสู่ระบบ')
            return redirect('store:home')
        else:
            form_errors = {'phone': ['กรุณากรอกเบอร์โทรศัพท์ที่ถูกต้อง (ตัวเลข 9-10 หลัก)']}
            return render(request, 'store/complete_profile.html', {
                'form': type('Form', (), {'errors': form_errors, 'phone': type('Field', (), {'value': phone})})()
            })
    
    # If user already has a phone number, redirect to home
    if profile.phone:
        return redirect('store:home')
    
    return render(request, 'store/complete_profile.html', {
        'form': type('Form', (), {'errors': {}, 'phone': type('Field', (), {'value': ''})})()
    })
