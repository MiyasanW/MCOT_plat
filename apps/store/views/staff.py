from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from apps.store.models import Equipment, Product, Booking, BookingItem

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
    items = booking.items.select_related('product', 'equipment').all()
    packages = booking.booked_packages.select_related('package').all()
    studios = booking.booked_studios.select_related('studio').all()

    template_path = 'booking/pdf/equipment_sheet.html'
    context = {
        'booking': booking, 
        'items': items,
        'packages': packages,
        'studios': studios
    }

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

    items = booking.items.select_related('product', 'equipment').all()
    packages = booking.booked_packages.select_related('package').all()
    studios = booking.booked_studios.select_related('studio').all()
    
    # Calculate Remaining Balance
    remaining_balance = booking.total_price - booking.deposit_amount
    
    context = {
        'booking': booking, 
        'items': items,
        'packages': packages,
        'studios': studios,
        'remaining_balance': remaining_balance
    }
    
    return render(request, 'booking/pdf/quotation.html', context)
