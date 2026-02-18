from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_POST, require_GET
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from django.contrib.auth.decorators import login_required
from datetime import datetime, timedelta
import json

from django.shortcuts import render, get_object_or_404, redirect
from apps.store.models import Product, ProductCategory, Booking, BookingItem, Studio, BookingStudio, Package, PackageItem, ProductionVehicle, Staff, Notification, Equipment
from apps.store.services.availability import AvailabilityService
from apps.store.services.pricing_service import PricingService
from apps.store.services.notification_service import NotificationService
from django.template.loader import get_template
from decimal import Decimal
from django.contrib.auth.models import Group

def home(request):
    """
    หน้าแรก (Home Page)
    """
    # 1. Hero Product (Featured)
    featured_product = Product.objects.filter(is_active=True, is_featured=True).first()
    if not featured_product:
        # Fallback if no featured product
        featured_product = Product.objects.filter(is_active=True).order_by('-price').first()

    # 2. New Arrivals (Latest 4)
    new_arrivals = Product.objects.filter(is_active=True).order_by('-created_at', '-id')[:4]

    # 3. Facility Status (Live Data)
    today = timezone.now().date()
    
    # A. Pickup Queue (Based on today's bookings)
    bookings_today_count = Booking.objects.filter(start_time__date=today).count()
    if bookings_today_count < 3:
        queue_status = {'label': 'Low Traffic', 'color': 'green'}
    elif bookings_today_count < 7:
        queue_status = {'label': 'Medium Traffic', 'color': 'yellow'}
    else:
        queue_status = {'label': 'High Traffic', 'color': 'red'}

    # B. Studio Status
    studios = Studio.objects.all()
    studio_statuses = []
    for studio in studios:
        is_booked = BookingStudio.objects.filter(
            studio=studio,
            booking__start_time__date__lte=today,
            booking__end_time__date__gte=today,
            booking__status__in=['approved', 'active']
        ).exists()
        studio_statuses.append({
            'name': studio.name,
            'is_occupied': is_booked
        })

    context = {
        'featured_product': featured_product,
        'new_arrivals': new_arrivals,
        'queue_status': queue_status,
        'studio_statuses': studio_statuses,
    }
    return render(request, 'pages/home.html', context)

def about(request):
    """About Us page"""
    return render(request, 'pages/corporate/about.html')

def terms(request):
    """
    หน้าเงื่อนไขการใช้งาน (Terms of Service)
    """
    return render(request, 'pages/terms.html')

def contact(request):
    """Contact Us page"""
    return render(request, 'pages/corporate/contact.html')

def faq(request):
    """FAQ page"""
    return render(request, 'pages/corporate/faq.html')

def catalog(request):
    """
    หน้าแสดงรายการสินค้า (Catalog Page)
    รองรับการ Filter ตาม Category ผ่าน Query Param
    """
    category_slug = request.GET.get('category')
    search_query = request.GET.get('q')
    
    from .filters import ProductFilter

    # Initial Queryset
    queryset = Product.objects.filter(is_active=True).select_related('category')
    
    # Apply Filter (Category & Search)
    product_filter = ProductFilter(request.GET, queryset=queryset)
    products = product_filter.qs
    
    # Get Active Category object for display context
    active_category = None
    if category_slug:
        active_category = get_object_or_404(ProductCategory, slug=category_slug)

    # --- Date Availability Filtering ---
    # รับค่าวันที่จาก Query Parameter (เช่น ?start_date=2024-02-01&end_date=2024-02-02)
    filter_start_date_str = request.GET.get('start_date')
    filter_end_date_str = request.GET.get('end_date')
    filtering_by_date = False

    # Default to Today if no dates provided (Requirement: Auto-check Today)
    if not filter_start_date_str or not filter_end_date_str:
        today_str = timezone.now().strftime("%Y-%m-%d")
        filter_start_date_str = today_str
        filter_end_date_str = today_str

    if filter_start_date_str and filter_end_date_str:
        try:
            # Parse Date (YYYY-MM-DD)
            filter_start_date = datetime.strptime(filter_start_date_str, "%Y-%m-%d").date()
            filter_end_date = datetime.strptime(filter_end_date_str, "%Y-%m-%d").date()
            
            # Convert to DateTime (Full Day Range)
            filter_start_datetime = datetime.combine(filter_start_date, datetime.min.time())
            filter_end_datetime = datetime.combine(filter_end_date, datetime.max.time())
            
            filtering_by_date = True
            
            # Iterate
            for product in products:
                # Check real-time availability
                is_available, _ = AvailabilityService.check_availability(
                    product, 
                    filter_start_datetime, 
                    filter_end_datetime
                )
                product.is_available_for_selected_dates = is_available
                
        except ValueError:
            pass 

    # Separate Categories for Sidebar
    service_slugs = ['vehicle', 'crew']
    studio_slugs = ['studio'] # If any exist as products
    
    all_categories = ProductCategory.objects.all().order_by('name')
    service_categories = all_categories.filter(slug__in=service_slugs)
    equipment_categories = all_categories.exclude(slug__in=service_slugs + studio_slugs)

    context = {
        'products': products,
        'equipment_categories': equipment_categories,
        'service_categories': service_categories,
        'active_category': active_category,
        'search_query': search_query,
        'selected_start_date': filter_start_date_str,
        'selected_end_date': filter_end_date_str,
        'is_date_filtered': filtering_by_date
    }
    return render(request, 'store/catalog.html', context)
    
def cart(request):
    """
    หน้าตะกร้าสินค้า (Shopping Cart)
    Render template 'booking/cart.html'
    """
    return render(request, 'booking/cart.html')


def studio_list(request):
    """
    หน้าแสดงรายการสตูดิโอ (Studio List)
    """
    studios = Studio.objects.all()
    context = {
        'studios': studios
    }
    return render(request, 'store/studio_list.html', context)


def studio_detail(request, studio_id):
    """
    หน้าละเอียดสตูดิโอ (Studio Detail)
    """
    studio = get_object_or_404(Studio, pk=studio_id)
    context = {
        'studio': studio
    }
    return render(request, 'store/studio_detail.html', context)

def package_list(request):
    """
    หน้าแสดงรายการแพ็คเกจ (Package List)
    """
    packages = Package.objects.filter(is_active=True)
    return render(request, 'store/package_list.html', {'packages': packages})

def package_detail(request, package_id):
    """
    หน้าละเอียดแพ็คเกจ (Package Detail)
    """
    package = get_object_or_404(Package, pk=package_id)
    return render(request, 'store/package_detail.html', {'package': package})

def service_list(request):
    """
    หน้าแสดงบริการ (Services: Crew Only for now)
    Redesigned: Vehicles moved to Packages
    """
    # 2. Crew (Staff)
    staffs = Staff.objects.filter(is_active=True).select_related('position')

    # 3. Post Production
    post_prod = Product.objects.filter(category__name='Post Production', is_active=True)
    
    context = {
        'staffs': staffs,
        'post_prod': post_prod,
        'st_count': staffs.count(),
        'pp_count': post_prod.count(),
    }
    return render(request, 'store/service_list.html', context)

def product_detail(request, product_id):
    """
    หน้าละเอียดสินค้า (Product Detail)
    """
    product = get_object_or_404(Product, pk=product_id)
    
    # Check availability context from Query Params (if passed from Catalog)
    start_date_str = request.GET.get('start_date')
    end_date_str = request.GET.get('end_date')
    is_available = True # Default
    
    if not start_date_str or not end_date_str:
        # Default to Today
        today_str = timezone.now().strftime("%Y-%m-%d")
        start_date_str = today_str
        end_date_str = today_str
        
    try:
        start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
        end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date()
        start_dt = datetime.combine(start_date, datetime.min.time())
        end_dt = datetime.combine(end_date, datetime.max.time())
        
        is_available, _ = AvailabilityService.check_availability(product, start_dt, end_dt)
        available_qty = AvailabilityService.get_available_quantity(product, start_dt, end_dt)
    except ValueError:
        available_qty = 0

    context = {
        'product': product,
        'selected_start_date': start_date_str,
        'selected_end_date': end_date_str,
        'is_available': is_available,
        'available_qty': available_qty
    }
    return render(request, 'store/product_detail.html', context)

def cart(request):
    """
    หน้าตะกร้าสินค้า (Cart Page)
    Render template เปล่า โดยข้อมูลสินค้าจะถูกดึงจาก LocalStorage ทางฝั่ง Client
    """
    return render(request, 'booking/cart.html')

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
    รับ JSON:
    {
        "start": "2024-02-01",
        "end": "2024-02-02",
        "items": [
            {"id": 1, "quantity": 2, "type": "product"},
            {"id": "studio_1", "quantity": 1, "type": "studio"}
        ]
    }
    """
    try:
        payload = json.loads(request.body)
        start_date_str = payload.get('start')
        end_date_str = payload.get('end')
        items = payload.get('items', [])

        if not (start_date_str and end_date_str):
            return JsonResponse({"valid": False, "message": "Missing dates"}, status=400)

        # Parse Dates
        try:
            start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
            end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date()
            start_dt = datetime.combine(start_date, datetime.min.time())
            end_dt = datetime.combine(end_date, datetime.max.time())
        except ValueError:
            return JsonResponse({"valid": False, "message": "Invalid Date Format"}, status=400)

        conflicts = []
        
        for item in items:
            item_id = item.get('id')
            qty = int(item.get('quantity', 1))
            item_type = item.get('type', 'product')
            
            # 1. Product
            if item_type == 'product' or (isinstance(item_id, int)):
                 try:
                    product = Product.objects.get(pk=item_id)
                    is_avail, msg = AvailabilityService.check_availability(product, start_dt, end_dt, qty)
                    
                    if not is_avail:
                        # Get remaining stock for helpful message
                        remaining = AvailabilityService.get_available_quantity(product, start_dt, end_dt)
                        conflicts.append({
                            "id": item_id,
                            "name": product.name,
                            "message": f"เหลือเพียง {remaining} ชิ้น (คุณต้องการ {qty})",
                            "remaining": remaining,
                            "type": "product"
                        })
                 except Product.DoesNotExist:
                     pass

            # 2. Studio
            elif item_type == 'studio' or str(item_id).startswith('studio_'):
                s_id = str(item_id).replace('studio_', '')
                try:
                    studio = Studio.objects.get(pk=s_id)
                    is_valid, _ = AvailabilityService.check_resource_overlap('studios', studio, start_dt, end_dt)
                    if not is_valid:
                         conflicts.append({
                            "id": item_id,
                            "name": studio.name,
                            "message": "ไม่ว่างในช่วงเวลานี้",
                            "remaining": 0,
                            "type": "studio"
                        })
                except Studio.DoesNotExist:
                    pass

            # 3. Package
            elif item_type == 'package' or str(item_id).startswith('pkg_'):
                p_id = str(item_id).replace('pkg_', '')
                try:
                    pkg = Package.objects.get(pk=p_id)
                    is_valid, msg = AvailabilityService.check_package_availability(pkg, start_dt, end_dt, qty)
                    if not is_valid:
                         conflicts.append({
                            "id": item_id,
                            "name": pkg.name,
                            "message": msg,
                            "remaining": 0, # Logic complex for package
                            "type": "package"
                        })
                except Package.DoesNotExist:
                    pass

        return JsonResponse({
            "valid": len(conflicts) == 0,
            "conflicts": conflicts
        })

    except Exception as e:
        return JsonResponse({"valid": False, "message": str(e)}, status=500)

@login_required
@require_POST
def create_booking_api(request):
    """
    API สำหรับสร้าง Booking จาก Cart (Refactored to use BookingService)
    """
    try:
        import json
        payload = json.loads(request.body)
        cart_items = payload.get('items', [])
        
        # Prepare Data
        booking_data = {
            'customer_name': payload.get('customer_name') or (request.user.get_full_name() if request.user.is_authenticated else 'Guest'),
            'customer_email': payload.get('customer_email') or (request.user.email if request.user.is_authenticated else ''),
            'customer_phone': payload.get('phone'),
            'project_name': payload.get('project_name'),
            'note': payload.get('note'),
            'start_time': None,
            'end_time': None
        }

        # Parse Dates
        try:
            from django.utils.dateparse import parse_datetime
            booking_data['start_time'] = parse_datetime(payload.get('start'))
            booking_data['end_time'] = parse_datetime(payload.get('end'))
        except:
            return JsonResponse({"success": False, "message": "Invalid Date Format"}, status=400)
            
        # Call Service (No Transaction Here, Service handles it)
        from apps.store.services.booking_service import BookingService
        
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
def my_bookings(request):
    """
    หน้า Dashboard ของลูกค้า — แสดงรายการจองทั้งหมดของ User ปัจจุบัน
    """
    bookings = Booking.objects.filter(created_by=request.user).order_by('-created_at').prefetch_related(
        'items__product', 'booked_studios__studio', 'booked_packages__package'
    )
    
    # คำนวณ total สำหรับแต่ละ booking
    for booking in bookings:
        item_total = sum(
            item.price_at_booking * item.quantity 
            for item in booking.items.all()
        )
        studio_total = sum(
            bs.price_at_booking 
            for bs in booking.booked_studios.all()
        )
        package_total = sum(
            bp.price_at_booking * bp.quantity 
            for bp in booking.booked_packages.all()
        )
        
        # จำนวนวัน
        days = max(1, (booking.end_time.date() - booking.start_time.date()).days + 1)
        booking.calculated_total = (item_total + studio_total + package_total) * days
        booking.num_days = days
    
    context = {
        'bookings': bookings,
    }
    return render(request, 'booking/my_bookings.html', context)


@login_required
@require_POST
def cancel_booking_api(request, booking_id):
    """
    API สำหรับยกเลิกการจอง (เฉพาะ draft/pending เท่านั้น)
    ตรวจสอบว่า User เป็นเจ้าของ Booking จริงก่อนยกเลิก (Object-Level Permission)
    """
    try:
        booking = get_object_or_404(Booking, pk=booking_id, created_by=request.user)
        
        if booking.status not in ('draft', 'pending'):
            return JsonResponse({
                "success": False, 
                "message": "ไม่สามารถยกเลิกได้ — การจองนี้ได้รับการอนุมัติแล้ว"
            }, status=400)
        
        booking.status = 'cancelled'
        booking.save()
        
        return JsonResponse({
            "success": True, 
            "message": f"ยกเลิกการจอง #{booking.id} เรียบร้อยแล้ว"
        })
        
    except Exception as e:
        return JsonResponse({"success": False, "message": f"Server Error: {str(e)}"}, status=500)


# Authentication
from django.contrib.auth import login
from .forms import UserRegisterForm

def register(request):
    if request.method == 'POST':
        form = UserRegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('store:home')
    else:
        form = UserRegisterForm()
    return render(request, 'registration/register.html', {'form': form})

@login_required
def booking_detail(request, booking_id):
    """
    หน้าละเอียดการจอง & อัปโหลดสลิป
    """
    booking = get_object_or_404(Booking, id=booking_id)
    
    # Permission Check: Owner or Staff (Web Admin)
    # Note: Staff/Admin should check via Admin Panel mostly, but this view is for User
    if booking.created_by != request.user and not request.user.is_staff:
        return redirect('store:home') # Forbidden
        
    return render(request, 'booking/detail.html', {'booking': booking})

@login_required
@require_POST
def upload_slip_api(request, booking_id):
    """
    API สำหรับอัปโหลดสลิปโอนเงิน Update Booking -> Pending
    """
    booking = get_object_or_404(Booking, id=booking_id, created_by=request.user)
    
    if 'slip' not in request.FILES:
         return JsonResponse({'success': False, 'message': 'No file uploaded'}, status=400)
         
    slip_file = request.FILES['slip']
    
    # Basic Validation (Image)
    if not slip_file.content_type.startswith('image/'):
        return JsonResponse({'success': False, 'message': 'File must be an image'}, status=400)

    try:
        booking.payment_slip = slip_file
        booking.payment_status = 'pending'
        booking.save()
        
        # Admin Notification
        try:
            admin_group = Group.objects.get(name='web_admin')
            admins = admin_group.user_set.all()
            for admin in admins:
                Notification.objects.create(
                    recipient=admin,
                    message=f"💰 New Slip Uploaded: Booking #{booking.id}",
                    link=f"/admin/store/booking/{booking.id}/change/",
                    notification_type='info'
                )
        except Group.DoesNotExist:
            print("Warning: 'web_admin' group not found. detailed notification skipped.")
            
        return JsonResponse({'success': True, 'message': 'Slip uploaded successfully. Waiting for verification.'})
        
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=500)

@login_required
def equipment_history_search(request):
    """
    หน้าค้นหาประวัติอุปกรณ์ (Search Equipment History)
    """
    # Requires Staff/Admin
    if not (request.user.is_staff or request.user.is_superuser):
        return redirect('store:home')

    query = request.GET.get('q')
    product_id = request.GET.get('product')
    equipments = None
    
    if query:
        # Search by Serial, Inventory Number, Asset Tag, OR Product Name
        equipments = Equipment.objects.filter(
            Q(serial_number__icontains=query) | 
            Q(inventory_number__icontains=query) |
            Q(asset_tag__icontains=query) |
            Q(product__name__icontains=query)
        )
    elif product_id:
        # Filter by specific Product
        equipments = Equipment.objects.filter(product_id=product_id)

    # If exact match found (1 item), redirect to detail
    if equipments and equipments.count() == 1:
        return redirect('store:equipment_history_detail', equipment_id=equipments.first().id)
            
    products = Product.objects.filter(is_active=True).order_by('name')
    return render(request, 'inventory/history_search.html', {
        'equipments': equipments, 
        'query': query,
        'products': products,
        'selected_product': int(product_id) if product_id else None
    })

@login_required
def equipment_history_detail(request, equipment_id):
    """
    หน้าแสดงประวัติการใช้งานอุปกรณ์ (Equipment History Detail)
    """
    if not (request.user.is_staff or request.user.is_superuser):
        return redirect('store:home')

    equipment = get_object_or_404(Equipment, id=equipment_id)
    
    # ดึงประวัติจาก BookingItem โดยเรียงจากล่าสุดไปเก่าสุด
    history_items = BookingItem.objects.filter(equipment=equipment).select_related('booking').order_by('-booking__start_time')

    context = {
        'equipment': equipment,
        'history_items': history_items
    }
    return render(request, 'inventory/history_detail.html', context)

@login_required
def download_booking_pdf(request, booking_id):
    """
    Generate PDF Equipment Sheet for Staff
    """
    # Permission check: Staff only
    if not (request.user.is_staff or request.user.is_superuser):
        return redirect('store:home')

    booking = get_object_or_404(Booking, id=booking_id)
    items = BookingItem.objects.filter(booking=booking).select_related('product', 'equipment')

    template_path = 'booking/pdf/equipment_sheet.html'
    context = {'booking': booking, 'items': items}

    # Fallback to HTML Print due to xhtml2pdf installation issues
    return render(request, template_path, context)

@login_required
def download_quotation_pdf(request, booking_id):
    """
    Generate PDF Quotation for Customer
    """
    booking = get_object_or_404(Booking, id=booking_id)

    # Permission check: Owner or Staff can download
    if booking.created_by != request.user and not (request.user.is_staff or request.user.is_superuser):
        return redirect('store:home')

    items = BookingItem.objects.filter(booking=booking).select_related('product', 'equipment')
    context = {'booking': booking, 'items': items}
    
    return render(request, 'booking/pdf/quotation.html', context)

