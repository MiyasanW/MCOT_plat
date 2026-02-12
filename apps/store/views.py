from django.http import JsonResponse
from django.views.decorators.http import require_POST, require_GET
from django.utils import timezone
from django.contrib.auth.decorators import login_required
from datetime import datetime
import json

from django.shortcuts import render, get_object_or_404
from apps.store.models import Product, ProductCategory, Booking, BookingItem, Studio, BookingStudio, Package, PackageItem, ProductionVehicle, Staff
from apps.store.services.availability import AvailabilityService

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
    except ValueError:
        pass

    context = {
        'product': product,
        'selected_start_date': start_date_str,
        'selected_end_date': end_date_str,
        'is_available': is_available
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

@login_required
@require_POST
def create_booking_api(request):
    """
    API สำหรับสร้างการจอง (Core Booking Logic)
    รับ JSON Data:
    {
        "items": [{"id": 1, "quantity": 2}],
        "start": "2024-02-01",
        "end": "2024-02-02"
    }
    """
    try:
        payload = json.loads(request.body)
        cart_items = payload.get('items', [])
        start_date_str = payload.get('start')
        end_date_str = payload.get('end')
        
        # 1. แปลงวันที่ (Parse Dates & Force Full Day)
        try:
            start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
            end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date()
        except ValueError:
             return JsonResponse({"success": False, "message": "Format วันที่ผิด (ใช้ YYYY-MM-DD)"}, status=400)

        # Force Full Day Range
        booking_start = datetime.combine(start_date, datetime.min.time())
        booking_end = datetime.combine(end_date, datetime.max.time())
        
        if booking_start > booking_end:
            return JsonResponse({"success": False, "message": "วันเวลาไม่ถูกต้อง (วันกลับต้องหลังหรือวันเดียวกับวันรับ)"}, status=400)

        # 2. สร้างใบจองสถานะ Draft (Booking Header)
        new_booking = Booking.objects.create(
            customer_name=request.user.get_full_name() or request.user.username,
            created_by=request.user,
            project_name=payload.get('project_name'),
            phone=payload.get('phone'),
            note=payload.get('note'),
            start_time=booking_start,
            end_time=booking_end,
            status='draft'
        )

        error_messages = []
        
        # 3. วนลูปสร้างรายการสินค้า (Booking Items) และตัดสต็อก
        for item_data in cart_items:
            # Handle item type (Product vs Studio)
            item_type = item_data.get('type', 'product')
            raw_id = item_data.get('id')
            qty_requested = int(item_data.get('quantity', 1))

            # Case 1: Studio
            if item_type == 'studio' or str(raw_id).startswith('studio_'):
                # Extract ID if prefixed
                studio_id = str(raw_id).replace('studio_', '')
                studio_obj = get_object_or_404(Studio, pk=studio_id)

                # Check Studio Availability
                is_valid, conflict = AvailabilityService.check_resource_overlap(
                    'studios', studio_obj, booking_start, booking_end
                )
                
                if not is_valid:
                    error_messages.append(f"สตูดิโอ '{studio_obj.name}' ไม่ว่างในช่วงเวลานี้")
                    continue

                # Create BookingStudio
                BookingStudio.objects.create(
                    booking=new_booking,
                    studio=studio_obj,
                    price_at_booking=studio_obj.daily_rate
                )

            # Case 2: Product (Default)
            else:
                product_id = raw_id
                product_obj = get_object_or_404(Product, id=product_id)
                
                # Check Product Availability
                is_valid, msg = AvailabilityService.check_availability(
                    product_obj, booking_start, booking_end, qty_requested
                )
                
                if not is_valid:
                    error_messages.append(msg)
                    continue
                
                # Create BookingItem
                BookingItem.objects.create(
                    booking=new_booking,
                    product=product_obj,
                    quantity=qty_requested,
                    price_at_booking=product_obj.price
                )
            
        if error_messages:
            # หากมีสินค้าบางตัวจองไม่ได้ ให้ยกเลิกทั้งบิล (Rollback) (หรือจะ Partial ก็ได้ แล้วแต่ business)
            # ในที่นี้เลือก Rollback เพื่อความปลอดภัย
            new_booking.delete()
            return JsonResponse({
                "success": False, 
                "message": "สินค้าบางรายการไม่เพียงพอ", 
                "errors": error_messages
            }, status=400)
            
        return JsonResponse({
            "success": True, 
            "booking_id": new_booking.id, 
            "message": "สร้างการจองสำเร็จ"
        })
        
    except Exception as e:
        return JsonResponse({"success": False, "message": f"Server Error: {str(e)}"}, status=500)
