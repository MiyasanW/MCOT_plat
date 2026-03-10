"""
Template tags สำหรับ store — ใช้เช็ค/สร้าง URL ล็อกอินด้วย Google โดยไม่ error
"""
from django import template
from django.urls import reverse

register = template.Library()


@register.simple_tag(takes_context=True)
def get_google_login_url(context):
    """
    คืนค่า URL สำหรับล็อกอินด้วย Google ถ้ามี Social Application (Google) ที่ผูกกับ Site ปัจจุบัน
    คืนค่าว่างถ้าไม่มี → ใช้เช็คก่อนแสดงปุ่ม
    """
    request = context.get('request')
    if not request:
        return ''
    try:
        from django.contrib.sites.shortcuts import get_current_site
        from allauth.socialaccount.models import SocialApp
        site = get_current_site(request)
        if SocialApp.objects.filter(provider='google', sites=site).exists():
            return request.build_absolute_uri(reverse('google_login'))
    except Exception:
        pass
    return ''
