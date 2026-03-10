import json
import re
from datetime import datetime, timedelta
from decimal import Decimal

from django.shortcuts import render, get_object_or_404
from django.db.models import Q
from django.utils import timezone
from django.http import JsonResponse
from django.views.decorators.http import require_POST, require_GET
from django.contrib.auth.decorators import login_required

from apps.store.models import Product, Studio, Package, Booking, BookingItem, PromotionCode, Profile
from apps.store.services.availability import AvailabilityService
from apps.store.services.booking_service import BookingService

def cart(request):
    """
    หน้าตะกร้าสินค้า (Cart Page) - Step 1/4: รายการสินค้า
    Render template เปล่า โดยข้อมูลสินค้าจะถูกดึงจาก LocalStorage ทางฝั่ง Client
    """
    return render(request, 'booking/cart.html')

def cart_dates(request):
    """
    หน้าตะกร้าสินค้า - Step 2/4: เลือกวันเวลา
    """
    return render(request, 'booking/cart_dates.html')

@login_required
def cart_review(request):
    """
    หน้าตะกร้าสินค้า - Step 3/4: ตรวจสอบและยืนยัน
    """
    return render(request, 'booking/cart_review.html')

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
            except PromotionCode.DoesNotExist:
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

    except ValueError:
        return JsonResponse({"valid": False, "message": "ข้อมูลไม่ถูกต้อง"}, status=400)
    except Exception as e:
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
        
        return JsonResponse({
            "available": is_available,
            "message": status_message,
            "remaining": remaining_stock,
            "product_name": target_product.name
        })
    except ValueError:
        return JsonResponse({"available": False, "message": "Invalid Date Format. Use YYYY-MM-DD"}, status=400)
    except Exception as e:
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
        
        phone = payload.get('customer_phone') or payload.get('phone')
        if phone and not re.match(r'^[0-9\-\+\s\(\)]+$', phone):
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
            booking_data['start_time'] = datetime.combine(start_date, datetime.min.time())
            booking_data['end_time'] = datetime.combine(end_date, datetime.max.time())
        except Exception as e:
            return JsonResponse({"success": False, "message": "Invalid Date Format"}, status=400)
            
        try:
            booking = BookingService.create_booking_from_cart(
                cart=cart_items,
                booking_data=booking_data,
                user=request.user
            )

            return JsonResponse({
                "success": True, 
                "booking_id": booking.id,
                "message": "Booking Created Successfully"
            })
            
        except ValueError as e:
            return JsonResponse({"success": False, "message": str(e)}, status=400)
        except Exception as e:
            # Service might raise other exceptions for DB errors
            return JsonResponse({"success": False, "message": f"System Error: {str(e)}"}, status=500)

    except json.JSONDecodeError:
        return JsonResponse({"success": False, "message": "Invalid JSON"}, status=400)
    except Exception as e:
        return JsonResponse({"success": False, "message": f"Server Error: {str(e)}"}, status=500)

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
