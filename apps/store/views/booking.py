import json
import re
import logging
from datetime import datetime, timedelta
from decimal import Decimal

from django.shortcuts import render, get_object_or_404
from django.db.models import Q
from django.utils import timezone
from django.http import JsonResponse
from django.core.cache import cache
from django.views.decorators.http import require_POST, require_GET
from django.contrib.auth.decorators import login_required

from apps.store.models import Product, Studio, Package, Booking, BookingItem, PromotionCode, Profile
from apps.store.services.availability import AvailabilityService
from apps.store.services.booking_service import BookingService
from apps.store.services.pricing_service import PricingService

logger = logging.getLogger(__name__)


def _booking_flow_context():
    return {
        'deposit_percent': PricingService.get_deposit_percentage(),
    }

def cart(request):
    """
    หน้าตะกร้าสินค้า (Cart Page) - Step 1/4: รายการสินค้า
    Render template เปล่า โดยข้อมูลสินค้าจะถูกดึงจาก LocalStorage ทางฝั่ง Client
    """
    return render(request, 'booking/cart.html', _booking_flow_context())

def cart_dates(request):
    """
    หน้าตะกร้าสินค้า - Step 2/4: เลือกวันเวลา
    """
    return render(request, 'booking/cart_dates.html', _booking_flow_context())

@login_required
def cart_review(request):
    """
    หน้าตะกร้าสินค้า - Step 3/4: ตรวจสอบและยืนยัน
    """
    return render(request, 'booking/cart_review.html', _booking_flow_context())

@login_required
def cart_checkout(request, booking_id):
    """
    หน้าตะกร้าสินค้า - Step 4/4: ชำระเงิน (Success)
    """
    booking = get_object_or_404(Booking, id=booking_id, created_by=request.user)
    return render(request, 'booking/cart_checkout.html', {'booking': booking})
@require_GET
def check_promo_api(request):
    """
    API ตรวจสอบโค้ดส่วนลดและส่วนลดพาร์ทเนอร์
    รับค่า: code (optional), subtotal
    """
    subtotal_str = request.GET.get('subtotal', '0')
    promo_code = request.GET.get('code', '').strip()
    
    try:
        subtotal = Decimal(subtotal_str)
        if subtotal <= 0:
            logger.warning(f"[CHECK_PROMO] Invalid subtotal: {subtotal}")
            return JsonResponse({"valid": False, "message": "ยอดรวมต้องมากกว่า 0"})
            
        discount = Decimal('0.00')
        messages = []
        is_partner = False

        # 1. เช็ค Partner Discount อัตโนมัติ (ถ้าล็อกอิน)
        if request.user.is_authenticated and hasattr(request.user, 'profile'):
            if request.user.profile.is_partner:
                is_partner = True
                p_discount = subtotal * (Decimal(request.user.profile.partner_discount_percent) / Decimal('100.0'))
                discount += p_discount
                messages.append(f"ส่วนลดพาร์ทเนอร์ {request.user.profile.partner_discount_percent}%")
                logger.debug(f"[CHECK_PROMO] Partner discount applied: {p_discount}")

        # 2. เช็ค Promo Code
        code_valid = False
        promo_discount = Decimal('0.00')
        if promo_code:
            now = timezone.now()
            try:
                promo = PromotionCode.objects.get(code__iexact=promo_code, is_active=True, valid_from__lte=now, valid_to__gte=now)
                code_valid = True
                
                if promo.discount_percent > 0:
                    promo_discount = subtotal * (Decimal(promo.discount_percent) / Decimal('100.0'))
                    messages.append(f"โปรโมชั่นลด {promo.discount_percent}%")
                elif promo.discount_amount > 0:
                    promo_discount = promo.discount_amount
                    messages.append(f"โปรโมชั่นลด ฿{promo.discount_amount:,.2f}")
                
                discount += promo_discount
                logger.info(f"[CHECK_PROMO] Promo code valid: {promo_code} | Discount: ฿{promo_discount}")
            except PromotionCode.DoesNotExist:
                logger.warning(f"[CHECK_PROMO] Invalid/expired promo code: {promo_code}")
                return JsonResponse({"valid": False, "message": "โค้ดส่วนลดไม่ถูกต้องหรือหมดอายุแล้ว"})

        partner_amount = float(discount - promo_discount)

        if discount > subtotal:
            discount = subtotal

        return JsonResponse({
            "valid": True,
            "discount_amount": float(discount),
            "partner_discount": partner_amount,
            "promo_discount": float(promo_discount),
            "messages": messages,
            "code_applied": promo_code if code_valid else None,
            "is_partner": is_partner
        })

    except ValueError as e:
        logger.error(f"[CHECK_PROMO] ValueError: {str(e)}")
        return JsonResponse({"valid": False, "message": "ข้อมูลไม่ถูกต้อง"}, status=400)
    except Exception as e:
        logger.error(f"[CHECK_PROMO] Unexpected error: {str(e)}", exc_info=True)
        return JsonResponse({"valid": False, "message": str(e)}, status=500)

@require_GET
def check_availability_api(request):
    """
    API สำหรับตรวจสอบความพร้อมของสินค้า/สตูดิโอ (Core Function)
    รับค่า queryString: product_id, start, end
    """
    product_id = request.GET.get('product_id')
    start_date_str = request.GET.get('start') # คาดหวัง format "YYYY-MM-DD"
    end_date_str = request.GET.get('end')     # คาดหวัง format "YYYY-MM-DD"
    
    if not (product_id and start_date_str and end_date_str):
        logger.warning(f"[CHECK_AVAIL] Missing params: product_id={product_id}, start={start_date_str}, end={end_date_str}")
        return JsonResponse({"available": False, "message": "Missing parameters (product_id, start, end)"}, status=400)
    
    try:
        # แปลง string เป็น conversion (ตัดเวลาทิ้ง เอาแค่วันที่)
        # ตัวอย่าง: "2024-02-01" -> Start 00:00:00, End 23:59:59
        start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
        end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date()
        
        # Combine with min/max time to cover full day
        start_datetime = datetime.combine(start_date, datetime.min.time())
        end_datetime = datetime.combine(end_date, datetime.max.time())
        
        target_product = get_object_or_404(Product, id=product_id)
        
        # 1. เช็คจำนวนคงเหลือ (Stock)
        remaining_stock = AvailabilityService.get_available_quantity(target_product, start_datetime, end_datetime)
        
        # 2. เช็คว่าพอให้จองไหม (Boolean Logic)
        is_available, status_message = AvailabilityService.check_availability(target_product, start_datetime, end_datetime)
        
        logger.debug(f"[CHECK_AVAIL] Product: {product_id} ({target_product.name}) | Dates: {start_date} to {end_date} | Available: {is_available} | Remaining: {remaining_stock}")
        
        return JsonResponse({
            "available": is_available,
            "message": status_message,
            "remaining": remaining_stock,
            "product_name": target_product.name
        })
    except ValueError as e:
        logger.error(f"[CHECK_AVAIL] Date parse error: {str(e)} | Start: {start_date_str} | End: {end_date_str}")
        return JsonResponse({"available": False, "message": "Invalid Date Format. Use YYYY-MM-DD"}, status=400)
    except Exception as e:
        logger.error(f"[CHECK_AVAIL] Error: {str(e)}", exc_info=True)
        return JsonResponse({"available": False, "message": f"Server Error: {str(e)}"}, status=500)

@require_POST
def check_cart_availability_api(request):
    """
    API สำหรับเช็คความพร้อมของสินค้าในตะกร้า (Batch Check)
    Refactored to use AvailabilityService
    """
    try:
        payload = json.loads(request.body)
        start_date_str = payload.get('start')
        end_date_str = payload.get('end')
        items = payload.get('items', [])
        
        # Call Service
        conflicts = AvailabilityService.check_cart_for_api(items, start_date_str, end_date_str)
        
        return JsonResponse({
            "valid": len(conflicts) == 0,
            "conflicts": conflicts
        })

    except ValueError:
         return JsonResponse({"valid": False, "message": "Invalid Date Format"}, status=400)
    except Exception as e:
        return JsonResponse({"valid": False, "message": str(e)}, status=500)

@login_required
@require_POST
def create_booking_api(request):
    """
    API สำหรับสร้าง Booking จาก Cart (Refactored to use BookingService)
    """
    try:
        payload = json.loads(request.body)
        cart_items = payload.get('items', [])
        request_id = (payload.get('request_id') or '').strip()

        logger.info(f"[CREATE_BOOKING] User: {request.user.id} ({request.user.username}) | Request ID: {request_id}")
        logger.debug(f"[CREATE_BOOKING] Cart items: {len(cart_items)} items | Start: {payload.get('start')} | End: {payload.get('end')}")

        lock_key = None
        result_key = None
        if request_id:
            result_key = f"booking_create_result:{request.user.id}:{request_id}"
            lock_key = f"booking_create_lock:{request.user.id}:{request_id}"

            existing_booking_id = cache.get(result_key)
            if existing_booking_id:
                logger.info(f"[CREATE_BOOKING] Idempotent hit: booking {existing_booking_id} already created for request {request_id}")
                return JsonResponse({
                    "success": True,
                    "booking_id": existing_booking_id,
                    "message": "Booking already created",
                    "idempotent": True,
                })

            if not cache.add(lock_key, 1, timeout=30):
                # Another request with same idempotency key is in-flight.
                logger.warning(f"[CREATE_BOOKING] Lock exists: request {request_id} is already processing")
                return JsonResponse({
                    "success": False,
                    "message": "กำลังดำเนินการสร้างใบจองอยู่ กรุณารอสักครู่",
                    "processing": True,
                }, status=409)
        
        phone = payload.get('customer_phone') or payload.get('phone')
        if phone and not re.match(r'^[0-9\-\+\s\(\)]+$', phone):
            logger.warning(f"[CREATE_BOOKING] Invalid phone: {phone}")
            return JsonResponse({"success": False, "message": "เบอร์โทรศัพท์ไม่ถูกต้อง กรุณากรอกเฉพาะตัวเลข"}, status=400)
            
        # Prepare Data
        booking_data = {
            'customer_name': payload.get('customer_name') or request.user.get_full_name() or request.user.username,
            'customer_email': payload.get('customer_email') or (request.user.email if request.user.is_authenticated else ''),
            'customer_phone': phone,
            'project_name': payload.get('project_name'),
            'note': payload.get('note'),
            'promotion_code': payload.get('promotion_code'),
            'start_time': None,
            'end_time': None
        }

        # Parse Dates
        try:
            # Use strict YYYY-MM-DD parsing, as sent by frontend
            start_date = datetime.strptime(payload.get('start')[:10], "%Y-%m-%d").date()
            end_date = datetime.strptime(payload.get('end')[:10], "%Y-%m-%d").date()
            
            # Combine to full datetimes (covering the whole start day to the end of the end day)
            booking_data['start_time'] = timezone.make_aware(datetime.combine(start_date, datetime.min.time()))
            booking_data['end_time'] = timezone.make_aware(datetime.combine(end_date, datetime.max.time()))
        except Exception as e:
            logger.error(f"[CREATE_BOOKING] Date parse error: {str(e)} | Start: {payload.get('start')} | End: {payload.get('end')}")
            return JsonResponse({"success": False, "message": "Invalid Date Format"}, status=400)
            
        try:
            booking = BookingService.create_booking_from_cart(
                cart=cart_items,
                booking_data=booking_data,
                user=request.user
            )

            logger.info(f"[CREATE_BOOKING] Success: Booking {booking.id} created for user {request.user.id} | Items: {len(cart_items)} | Amount: ฿{booking.total_price}")

            if result_key:
                cache.set(result_key, booking.id, timeout=600)

            return JsonResponse({
                "success": True,
                "booking_id": booking.id,
                "message": "Booking Created Successfully"
            })

        except ValueError as e:
            logger.warning(f"[CREATE_BOOKING] Validation error: {str(e)}")
            return JsonResponse({"success": False, "message": str(e)}, status=400)
        except Exception as e:
            # Service might raise other exceptions for DB errors
            logger.error(f"[CREATE_BOOKING] Service error: {str(e)}", exc_info=True)
            return JsonResponse({"success": False, "message": f"System Error: {str(e)}"}, status=500)
        finally:
            if lock_key:
                cache.delete(lock_key)

    except json.JSONDecodeError as e:
        logger.error(f"[CREATE_BOOKING] JSON decode error: {str(e)}")
        return JsonResponse({"success": False, "message": "Invalid JSON"}, status=400)
    except Exception as e:
        logger.error(f"[CREATE_BOOKING] Unexpected error: {str(e)}", exc_info=True)
        return JsonResponse({"success": False, "message": f"Server Error: {str(e)}"}, status=500)


@login_required
@require_GET
def booking_create_status_api(request):
    """Check create-booking request status by idempotency request_id for refresh recovery."""
    request_id = (request.GET.get('request_id') or '').strip()
    if not request_id:
        logger.warning(f"[BOOKING_STATUS] Missing request_id for user {request.user.id}")
        return JsonResponse({"success": False, "message": "Missing request_id"}, status=400)

    result_key = f"booking_create_result:{request.user.id}:{request_id}"
    lock_key = f"booking_create_lock:{request.user.id}:{request_id}"

    booking_id = cache.get(result_key)
    if booking_id:
        booking_exists = Booking.objects.filter(id=booking_id, created_by=request.user).exists()
        if booking_exists:
            logger.info(f"[BOOKING_STATUS] Status: CREATED | User: {request.user.id} | Request: {request_id} | Booking: {booking_id}")
            return JsonResponse({
                "success": True,
                "created": True,
                "booking_id": booking_id,
            })
        cache.delete(result_key)

    if cache.get(lock_key):
        logger.debug(f"[BOOKING_STATUS] Status: PROCESSING | User: {request.user.id} | Request: {request_id}")
        return JsonResponse({
            "success": True,
            "created": False,
            "processing": True,
        })

    logger.debug(f"[BOOKING_STATUS] Status: NO_STATE | User: {request.user.id} | Request: {request_id}")
    return JsonResponse({
        "success": True,
        "created": False,
        "processing": False,
    })

@login_required
@require_POST
def cancel_booking_api(request, booking_id):
    """
    API สำหรับยกเลิกการจอง (เฉพาะ draft/pending เท่านั้น)
    Refactored to use BookingService
    """
    try:
        booking = BookingService.cancel_booking(booking_id, request.user)

        return JsonResponse({
            "success": True, 
            "message": f"ยกเลิกการจอง #{booking.id} เรียบร้อยแล้ว"
        })
        
    except PermissionError as e:
        return JsonResponse({"success": False, "message": str(e)}, status=403)
    except ValueError as e:
        return JsonResponse({"success": False, "message": str(e)}, status=400)
    except Exception as e:
        return JsonResponse({"success": False, "message": f"Server Error: {str(e)}"}, status=500)

@login_required
@require_POST
def upload_slip_api(request, booking_id):
    """
    API สำหรับอัปโหลดสลิปโอนเงิน Update Booking -> Pending
    Refactored to use BookingService
    """
    try:
        if 'slip' not in request.FILES:
             return JsonResponse({'success': False, 'message': 'No file uploaded'}, status=400)
             
        slip_file = request.FILES['slip']
        
        BookingService.process_payment_slip(booking_id, request.user, slip_file)
            
        return JsonResponse({'success': True, 'message': 'Slip uploaded successfully. Waiting for verification.'})
        
    except ValueError as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=400)
    except PermissionError as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=403)
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=500)
