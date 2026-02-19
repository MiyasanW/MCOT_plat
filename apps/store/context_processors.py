from apps.store.models import Booking, Product
from django.contrib.auth.models import User

def admin_dashboard_stats(request):
    """
    Injects stats for the custom Admin Dashboard.
    Only runs if on the admin index page to save performance.
    """
    if request.path == '/admin/':
        return {
            'total_bookings': Booking.objects.count(),
            'total_products': Product.objects.count(),
            'total_users': User.objects.count(),
        }
    return {}
