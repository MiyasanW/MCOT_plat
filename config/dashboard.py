from django.utils.translation import gettext_lazy as _
from apps.store.models import Booking, Product, IssueReport, Studio

def dashboard_callback(request, context):
    try:
        # Total Bookings
        total_bookings = Booking.objects.count()
        
        # Pending Bookings
        pending_bookings = Booking.objects.filter(status='pending').count()
        
        # Active Issues
        active_issues = IssueReport.objects.filter(status__in=['open', 'in_progress']).count()
        
        # Total Products
        total_products = Product.objects.filter(is_active=True).count()

        context.update({
            "kpi": [
                {
                    "title": "Total Bookings",
                    "metric": total_bookings,
                    "footer": "All time",
                },
                {
                    "title": "Pending Approval",
                    "metric": pending_bookings,
                    "footer": "Action required",
                    "color": "warning",
                },
                {
                    "title": "Active Issues",
                    "metric": active_issues,
                    "footer": "Open reports",
                    "color": "danger",    # Fixed from error
                },
                {
                    "title": "Active Equipment",
                    "metric": total_products,
                    "footer": "In catalog",
                    "color": "success",
                },
            ],
        })
    except Exception as e:
        print(f"Dashboard Error: {e}")
    
    return context
