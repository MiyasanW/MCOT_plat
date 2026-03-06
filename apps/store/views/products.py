from django.shortcuts import render, get_object_or_404
from django.utils import timezone
from apps.store.models import Product, ProductCategory, Studio, Package, ServiceOffer
from apps.store.utils.ratelimit import ratelimit

@ratelimit(key_prefix='catalog', rate=20, period=60, block=True)
def catalog(request):
    """
    หน้าแสดงรายการสินค้าทั้งหมด (Unified Catalog V3)
    รวมทุกหมวดหมู่ไว้ในหน้าเดียว
    """
    from apps.store.models import Product, Studio, Package, ServiceOffer
    from django.db.models import Q
    
    # Get parameters
    search_query = request.GET.get('q', '').strip()
    active_section = request.GET.get('section', 'all')
    category_slug = request.GET.get('category', '').strip()
    
    # Needs ServiceCategory to show service subcategories
    from apps.store.models import ServiceCategory
    
    active_category = None
    if category_slug:
        try:
            active_category = ProductCategory.objects.get(slug=category_slug)
        except ProductCategory.DoesNotExist:
            try:
                active_category = ServiceCategory.objects.get(slug=category_slug)
            except ServiceCategory.DoesNotExist:
                pass
    
    # Initialize querysets
    studios = Studio.objects.none()
    packages = Package.objects.none()
    equipment = Product.objects.none()
    services = ServiceOffer.objects.none()
    
    # 1. Base Querysets based on section
    if active_section in ['all', 'studios']:
        studios = Studio.objects.all().order_by('-id')
    if active_section in ['all', 'packages']:
        packages = Package.objects.filter(is_active=True).order_by('-id')
    if active_section in ['all', 'equipment']:
        equipment = Product.objects.filter(is_active=True).select_related('category')
        if isinstance(active_category, ProductCategory):
            equipment = equipment.filter(category=active_category)
        equipment = equipment.order_by('category__name', '-id')
        
    if active_section in ['all', 'services']:
        services = ServiceOffer.objects.filter(is_active=True).select_related('category')
        if isinstance(active_category, ServiceCategory):
            services = services.filter(category=active_category)
        services = services.order_by('-id')

    # 2. Apply Search Filter
    if search_query:
        if active_section in ['all', 'studios']:
            studios = studios.filter(
                Q(name__icontains=search_query) | 
                Q(description__icontains=search_query)
            )
        if active_section in ['all', 'packages']:
            packages = packages.filter(
                Q(name__icontains=search_query) | 
                Q(description__icontains=search_query)
            )
        if active_section in ['all', 'equipment']:
            equipment = equipment.filter(
                Q(name__icontains=search_query) | 
                Q(description__icontains=search_query) |
                Q(brand__icontains=search_query) if hasattr(Product, 'brand') else Q()
            )
        if active_section in ['all', 'services']:
            services = services.filter(
                Q(name__icontains=search_query) |
                Q(category__name__icontains=search_query) |
                Q(description__icontains=search_query)
            )

    categories = ProductCategory.objects.all().order_by('name')
    service_categories = ServiceCategory.objects.all().order_by('name')

    # Count total results for empty state rendering
    total_results = studios.count() + packages.count() + equipment.count() + services.count()

    context = {
        'studios': studios,
        'packages': packages,
        'equipment': equipment,
        'services': services,
        'categories': categories,
        'equipment_categories': categories,  # Using ProductCategory for Equipment
        'service_categories': service_categories,
        'search_query': search_query,
        'active_section': active_section,
        'active_category': active_category,
        'total_results': total_results,
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
    # 2. Services (Replaces Staff/Crew)
    services = ServiceOffer.objects.filter(is_active=True).select_related('category')

    # 3. Post Production
    post_prod = Product.objects.filter(category__name='Post Production', is_active=True)
    
    context = {
        'services': services,
        'post_prod': post_prod,
        'st_count': services.count(),
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
