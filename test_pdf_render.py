import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.template.loader import render_to_string
from apps.store.models import Booking

booking = Booking.objects.last()
if booking:
    try:
        html = render_to_string('booking/pdf/quotation.html', {
            'booking': booking,
            'items': booking.items.all(),
            'packages': booking.booked_packages.all(),
            'studios': booking.booked_studios.all(),
        })
        print("Render successful!")
    except Exception as e:
        import traceback
        traceback.print_exc()
else:
    print("No bookings found to test.")
