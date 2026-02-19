from django.shortcuts import render
from apps.store.models import Product, Booking, BookingStudio, Studio
from django.utils import timezone

def home(request):
    """
    หน้าแรก (Home Page)
    """
    # 1. Hero Product (Featured)
    featured_product = Product.objects.filter(is_active=True, is_featured=True).first()
    if not featured_product:
        # Fallback if no featured product
        featured_product = Product.objects.filter(is_active=True).order_by('-price').first()

    # 2. New Arrivals (Latest 4)
    new_arrivals = Product.objects.filter(is_active=True).order_by('-created_at', '-id')[:4]

    # 3. Facility Status (Live Data)
    today = timezone.now().date()
    
    # A. Pickup Queue (Based on today's bookings)
    bookings_today_count = Booking.objects.filter(start_time__date=today).count()
    if bookings_today_count < 3:
        queue_status = {'label': 'Low Traffic', 'color': 'green'}
    elif bookings_today_count < 7:
        queue_status = {'label': 'Medium Traffic', 'color': 'yellow'}
    else:
        queue_status = {'label': 'High Traffic', 'color': 'red'}

    # B. Studio Status
    studios = Studio.objects.all()
    studio_statuses = []
    for studio in studios:
        is_booked = BookingStudio.objects.filter(
            studio=studio,
            booking__start_time__date__lte=today,
            booking__end_time__date__gte=today,
            booking__status__in=['approved', 'active']
        ).exists()
        studio_statuses.append({
            'name': studio.name,
            'is_occupied': is_booked
        })

    context = {
        'featured_product': featured_product,
        'new_arrivals': new_arrivals,
        'queue_status': queue_status,
        'studio_statuses': studio_statuses,
    }
    return render(request, 'pages/home.html', context)

def about(request):
    """About Us page"""
    return render(request, 'pages/corporate/about.html')

def terms(request):
    """
    หน้าเงื่อนไขการใช้งาน (Terms of Service)
    """
    return render(request, 'pages/terms.html')

def contact(request):
    """Contact Us page"""
    return render(request, 'pages/corporate/contact.html')

def faq(request):
    """FAQ page"""
    return render(request, 'pages/corporate/faq.html')
