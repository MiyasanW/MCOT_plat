from django.urls import path
from . import views

app_name = 'store'

urlpatterns = [
    # Pages
    path('', views.home, name='home'),
    path('about/', views.about, name='about'),
    path('contact/', views.contact, name='contact'),
    path('faq/', views.faq, name='faq'),
    path('catalog/', views.catalog, name='catalog'),
    path('cart/', views.cart, name='cart'),
    path('studios/', views.studio_list, name='studio_list'),
    path('studios/<int:studio_id>/', views.studio_detail, name='studio_detail'),
    path('products/<int:product_id>/', views.product_detail, name='product_detail'),
    
    # API endpoints (Core Functions)
    path('api/check-availability/', views.check_availability_api, name='api_check_availability'),
    path('api/booking/create/', views.create_booking_api, name='api_create_booking'),
]
