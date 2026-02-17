from django.urls import path
from . import views, views_calendar

app_name = 'store'

urlpatterns = [
    # Pages
    path('', views.home, name='home'),
    path('about/', views.about, name='about'),
    path('contact/', views.contact, name='contact'),
    path('terms/', views.terms, name='terms'),
    path('register/', views.register, name='register'),

    path('faq/', views.faq, name='faq'),
    path('catalog/', views.catalog, name='catalog'),
    path('cart/', views.cart, name='cart'),
    path('studios/', views.studio_list, name='studio_list'),
    path('studios/<int:studio_id>/', views.studio_detail, name='studio_detail'),
    path('packages/', views.package_list, name='package_list'),
    path('packages/<int:package_id>/', views.package_detail, name='package_detail'),
    path('services/', views.service_list, name='service_list'),
    path('products/<int:product_id>/', views.product_detail, name='product_detail'),
    
    # API endpoints (Core Functions)
    path('api/check-availability/', views.check_availability_api, name='api_check_availability'),
    path('api/check-cart/', views.check_cart_availability_api, name='api_check_cart_availability'),
    path('api/booking/create/', views.create_booking_api, name='api_create_booking'),
    path('api/booking/<int:booking_id>/cancel/', views.cancel_booking_api, name='api_cancel_booking'),
    path('api/calendar/events/', views_calendar.calendar_events_api, name='api_calendar_events'),
    path('api/calendar/staff/', views_calendar.staff_list_api, name='api_staff_list'),
    
    # Calendar Page
    path('calendar/', views_calendar.calendar_view, name='calendar'),
    
    # User Dashboard
    path('my-bookings/', views.my_bookings, name='my_bookings'),
    path('booking/<int:booking_id>/', views.booking_detail, name='booking_detail'),
    path('api/booking/<int:booking_id>/upload-slip/', views.upload_slip_api, name='api_upload_slip'),
]
