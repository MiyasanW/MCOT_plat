from django.shortcuts import render, get_object_or_404
from django.utils import timezone
from datetime import datetime
from apps.store.models import Product, ProductCategory, Studio, Package, Staff
from apps.store.services.availability import AvailabilityService
from apps.store.utils.ratelimit import ratelimit

@ratelimit(key_prefix='catalog', rate=20, period=60, block=True)
def catalog(request):
    """
    หน้าแสดงรายการสินค้าทั้งหมด (Unified Catalog V3)
    รวมทุกหมวดหมู่ไว้ในหน้าเดียว
    """
    from apps.store.models import Product, Studio, Package, Staff
    
    # Fetch all active items - Sorted by newest (id descending)
    studios = Studio.objects.all().order_by('-id')
    packages = Package.objects.filter(is_active=True).order_by('-id')
    equipment = Product.objects.filter(is_active=True).select_related('category').order_by('category__name', '-id')
    staff_members = Staff.objects.filter(is_active=True).select_related('position').order_by('-id')
    categories = ProductCategory.objects.all().order_by('name')

    context = {
        'studios': studios,
        'packages': packages,
        'equipment': equipment,
        'staff_members': staff_members,
        'categories': categories,
    }
    return render(request, 'store/catalog_v3.html', context)

@ratelimit(key_prefix='studio_list', rate=30, period=60, block=True)
def studio_list(request):
    """
    หน้าแสดงรายการสตูดิโอ (Studio List)
    """
    studios = Studio.objects.all()
    context = {
        'studios': studios
    }
    return render(request, 'store/studio_list.html', context)


@ratelimit(key_prefix='studio_detail', rate=30, period=60, block=True)
def studio_detail(request, studio_id):
    """
    หน้าละเอียดสตูดิโอ (Studio Detail)
    """
    studio = get_object_or_404(Studio, pk=studio_id)
    context = {
        'studio': studio
    }
    return render(request, 'store/studio_detail.html', context)

@ratelimit(key_prefix='package_list', rate=30, period=60, block=True)
def package_list(request):
    """
    หน้าแสดงรายการแพ็คเกจ (Package List)
    พร้อมเช็คคิวว่างเบื้องต้น (ถ้ามีการเลือกวันที่)
    """
    packages = Package.objects.filter(is_active=True).prefetch_related('packageitem_set__product')
    
    # --- Date Availability Filtering ---
    filter_start_date_str = request.GET.get('start_date')
    filter_end_date_str = request.GET.get('end_date')
    filtering_by_date = False

    if not filter_start_date_str or not filter_end_date_str:
        today_str = timezone.now().strftime("%Y-%m-%d")
        filter_start_date_str = today_str
        filter_end_date_str = today_str

    if filter_start_date_str and filter_end_date_str:
        try:
            filter_start_date = datetime.strptime(filter_start_date_str, "%Y-%m-%d").date()
            filter_end_date = datetime.strptime(filter_end_date_str, "%Y-%m-%d").date()
            filter_start_datetime = datetime.combine(filter_start_date, datetime.min.time())
            filter_end_datetime = datetime.combine(filter_end_date, datetime.max.time())
            filtering_by_date = True
            
            for package in packages:
                is_avail, _ = AvailabilityService.check_package_availability(
                    package, 
                    filter_start_datetime, 
                    filter_end_datetime
                )
                package.is_available_for_selected_dates = is_avail
        except ValueError:
            pass 

    context = {
        'packages': packages,
        'selected_start_date': filter_start_date_str,
        'selected_end_date': filter_end_date_str,
        'is_date_filtered': filtering_by_date
    }
    return render(request, 'store/package_list.html', context)


def package_detail(request, package_id):
    """
    หน้าละเอียดแพ็คเกจ (Package Detail)
    """
    package = get_object_or_404(Package, pk=package_id)
    
    start_date_str = request.GET.get('start_date')
    end_date_str = request.GET.get('end_date')
    is_available = True
    
    if not start_date_str or not end_date_str:
        today_str = timezone.now().strftime("%Y-%m-%d")
        start_date_str = today_str
        end_date_str = today_str
        
    try:
        start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
        end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date()
        start_dt = datetime.combine(start_date, datetime.min.time())
        end_dt = datetime.combine(end_date, datetime.max.time())
        
        is_available, availability_error = AvailabilityService.check_package_availability(package, start_dt, end_dt)
    except ValueError:
        is_available = False
        availability_error = "รูปแบบวันที่ไม่ถูกต้อง"

    context = {
        'package': package,
        'selected_start_date': start_date_str,
        'selected_end_date': end_date_str,
        'is_available': is_available,
        'availability_error': availability_error
    }
    return render(request, 'store/package_detail.html', context)

@ratelimit(key_prefix='service_list', rate=30, period=60, block=True)
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

@ratelimit(key_prefix='product_detail', rate=30, period=60, block=True)
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
