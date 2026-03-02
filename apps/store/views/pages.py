from django.shortcuts import render
from apps.store.models import Product, Booking, BookingStudio, Studio
from django.utils import timezone
from apps.store.utils.ratelimit import ratelimit

@ratelimit(key_prefix='home', rate=30, period=60, block=True)
def home(request):
    """
    หน้าแรก (Home Page) - Version 2 Unified Catalog
    """
    return render(request, 'pages/landing.html')

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
