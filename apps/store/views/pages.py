from django.shortcuts import render
from apps.store.models import Product, Booking, BookingStudio, Studio
from django.utils import timezone
from apps.store.utils.ratelimit import ratelimit

@ratelimit(key_prefix='home', rate=30, period=60, block=True)
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

    # 3. Facility Status (Live Data) via Service Layer
    from apps.store.services.dashboard_service import DashboardService
    queue_status, studio_statuses = DashboardService.get_home_page_stats()

    context = {
        'featured_product': featured_product,
        'new_arrivals': new_arrivals,
        'queue_status': queue_status,
        'studio_statuses': studio_statuses,
    }
    return render(request, 'pages/home.html', context)

@ratelimit(key_prefix='about', rate=30, period=60, block=True)
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
