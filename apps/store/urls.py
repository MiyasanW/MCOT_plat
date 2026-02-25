from django.urls import path
from .views import (
    pages, products, booking, user, staff, calendar, notification
)

app_name = 'store'

urlpatterns = [
    # Pages
    path('', pages.home, name='home'),
    path('about/', pages.about, name='about'),
    path('contact/', pages.contact, name='contact'),
    path('terms/', pages.terms, name='terms'),
    path('register/', user.register, name='register'),

    path('faq/', pages.faq, name='faq'),
    path('catalog/', products.catalog, name='catalog'),
    path('cart/', booking.cart, name='cart'),
    path('studios/', products.studio_list, name='studio_list'),
    path('studios/<int:studio_id>/', products.studio_detail, name='studio_detail'),
    path('packages/', products.package_list, name='package_list'),
    path('packages/<int:package_id>/', products.package_detail, name='package_detail'),
    path('services/', products.service_list, name='service_list'),
    path('products/<int:product_id>/', products.product_detail, name='product_detail'),
    
    path('staff/history/', staff.equipment_history_search, name='equipment_history_search'),
    path('staff/history/<int:equipment_id>/', staff.equipment_history_detail, name='equipment_history_detail'),
    path('staff/booking/<int:booking_id>/summary/', staff.booking_summary, name='staff_booking_summary'),
    path('api/staff/booking/<int:booking_id>/action/', staff.booking_action_api, name='api_staff_booking_action'),
    path('staff/analytics/', staff.staff_analytics, name='staff_analytics'),
    
    # API endpoints (Core Functions)
    path('api/check-availability/', booking.check_availability_api, name='api_check_availability'),
    path('api/check-cart/', booking.check_cart_availability_api, name='api_check_cart_availability'),
    path('api/check-promo/', booking.check_promo_api, name='api_check_promo'),
    path('api/booking/create/', booking.create_booking_api, name='api_create_booking'),
    path('api/booking/<int:booking_id>/cancel/', booking.cancel_booking_api, name='api_cancel_booking'),
    path('api/calendar/events/', calendar.calendar_events_api, name='api_calendar_events'),
    path('api/calendar/staff/', calendar.staff_list_api, name='api_staff_list'),
    
    # Calendar Page
    path('calendar/', calendar.calendar_view, name='calendar'),
    
    # User Dashboard
    path('my-bookings/', user.my_bookings, name='my_bookings'),
    path('booking/<int:booking_id>/', user.booking_detail, name='booking_detail'),
    path('api/booking/<int:booking_id>/upload-slip/', booking.upload_slip_api, name='api_upload_slip'),
    path('api/booking/<int:booking_id>/pdf/', staff.download_booking_pdf, name='download_booking_pdf'),
    path('api/booking/<int:booking_id>/quotation/', staff.download_quotation_pdf, name='download_quotation_pdf'),
    
    # Notifications
    path('api/notifications/', notification.get_notifications_api, name='api_get_notifications'),
    path('api/notifications/read/', notification.mark_notification_read_api, name='api_read_all_notifications'),
    path('api/notifications/<int:notification_id>/read/', notification.mark_notification_read_api, name='api_read_notification'),
]
