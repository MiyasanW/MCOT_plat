from .pages import home, terms, contact, faq, redirect_after_login
from .products import (
    catalog, studio_list, studio_detail,
    package_list, package_detail, service_list, product_detail,
)
from .booking import (
    cart, cart_dates, cart_review, cart_checkout,
    check_availability_api, check_cart_availability_api,
    check_promo_api, create_booking_api, cancel_booking_api,
    upload_slip_api,
)
from .user import my_bookings, register, booking_detail, complete_profile
from .staff import (
    equipment_history_search, equipment_history_detail,
    booking_summary, booking_action_api,
    download_booking_pdf, download_quotation_pdf, download_checklist_pdf,
    staff_dashboard,
)
from . import calendar, notification, reports
