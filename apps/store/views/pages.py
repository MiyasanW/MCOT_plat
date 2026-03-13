from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from apps.store.utils.ratelimit import ratelimit


@login_required
def redirect_after_login(request):
    """หลังล็อกอิน: Staff ไป Dashboard, คนอื่นไปหน้าแรก"""
    if request.user.is_staff or request.user.is_superuser:
        return redirect('store:staff_dashboard')
    return redirect('store:home')

@ratelimit(key_prefix='home', rate=30, period=60, block=True)
def home(request):
    """
    หน้าแรก (Home Page) - Version 2 Unified Catalog
    """
    return render(request, 'pages/landing.html')

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
