from .pages import home, about, terms, contact, faq
from .products import (
    catalog, studio_list, studio_detail, 
    package_list, package_detail, service_list, product_detail
)
from .booking import (
    cart, check_availability_api, check_cart_availability_api,
    create_booking_api, cancel_booking_api, upload_slip_api
)
from .user import my_bookings, register, booking_detail
from .staff import (
    equipment_history_search, equipment_history_detail,
    download_booking_pdf, download_quotation_pdf
)

# Note: Calendar and Notification views are imported separately in urls.py
# but we can expose them here if needed.
