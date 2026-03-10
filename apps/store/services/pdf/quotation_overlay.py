import os
import io
from PyPDF2 import PdfReader, PdfWriter
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from datetime import datetime
from django.conf import settings
from decimal import Decimal

# Register Thai Font
font_path = os.path.join(settings.BASE_DIR, 'static', 'fonts', 'Sarabun-Regular.ttf')
if os.path.exists(font_path):
    pdfmetrics.registerFont(TTFont('Sarabun', font_path))
font_bold_path = os.path.join(settings.BASE_DIR, 'static', 'fonts', 'Sarabun-Bold.ttf')
if os.path.exists(font_bold_path):
    pdfmetrics.registerFont(TTFont('Sarabun-Bold', font_bold_path))

def format_money(amount):
    """Format decimal/float to comma separated 2 decimal places"""
    if amount is None: return "0.00"
    return f"{Decimal(amount):,.2f}"

def generate_overlay(booking, template_path):
    """
    Generate overlay PDF containing text data at specific coordinates.
    The coordinate system in PDF starts from bottom-left (0,0).
    A4 is 595.27 x 841.89 points.
    """
    packet = io.BytesIO()
    can = canvas.Canvas(packet, pagesize=A4)
    
    # We will use Sarabun or default if not found
    try:
        can.setFont("Sarabun", 11)
        font_name = "Sarabun"
        font_bold = "Sarabun-Bold"
    except:
        can.setFont("Helvetica", 11)
        font_name = "Helvetica"
        font_bold = "Helvetica-Bold"

    # --- Coordinates Configuration (Points from bottom-left) ---
    # These coordinates need to be tuned to match the exact PDF template provided
    
    # Header Dates & IDs
    can.drawString(480, 725, booking.created_at.strftime("%d/%m/%Y") if booking.created_at else datetime.now().strftime("%d/%m/%Y"))
    can.drawString(480, 710, f"E - {booking.id:05d}")
    can.drawString(480, 680, booking.start_time.strftime("%d %b %Y") if booking.start_time else "-")

    # Customer Details
    can.drawString(80, 680, str(booking.customer_name))
    can.drawString(80, 665, str(booking.project_name or "-"))
    can.drawString(80, 650, "-") # Address
    can.drawString(80, 620, str(booking.phone or "-"))
    
    # Items (Looping)
    # Origin of table: Left~30, Top~560, LineHeight~20
    start_y = 550
    item_height = 20
    current_y = start_y
    
    items = booking.items.all()
    for idx, item in enumerate(items):
        can.drawString(40, current_y, str(idx+1))
        
        # Details
        desc = f"ค่าเช่าอุปกรณ์ {item.product.name} ต่อวัน"
        if item.equipment:
            desc += f" (S/N: {item.equipment.serial_number})"
        can.drawString(90, current_y, desc)
        
        # Qty
        can.drawRightString(350, current_y, str(item.quantity))
        
        # Price Per Unit
        can.drawRightString(460, current_y, format_money(item.price_at_booking))
        
        # Total
        subtotal = item.quantity * item.price_at_booking * (booking.rental_days or 1)
        can.drawRightString(560, current_y, format_money(subtotal))
        
        current_y -= item_height

    # Summary Totals (Bottom Right)
    # Subtotal
    can.drawRightString(560, 240, format_money(booking.calculated_total or booking.total_price))
    # Discount
    can.drawRightString(560, 225, format_money(booking.discount_amount))
    
    net_price = booking.total_price * Decimal('100') / Decimal('107')
    vat = booking.total_price - net_price
    
    # Net Price
    can.drawRightString(560, 210, format_money(net_price))
    # VAT
    can.drawRightString(560, 195, format_money(vat))
    
    # Grand Total
    can.setFont(font_bold, 12)
    can.drawRightString(560, 180, format_money(booking.total_price))

    # --- Signatures ---
    # Optional dynamic injection
    
    can.save()
    packet.seek(0)
    return packet

def merge_pdf_with_template(booking, template_abspath, output_abspath):
    """
    Takes the template PDF, generates text overlay, and merges them.
    """
    # Create overlay
    overlay_pdf = generate_overlay(booking, template_abspath)
    overlay_reader = PdfReader(overlay_pdf)
    
    # Read template
    template_reader = PdfReader(template_abspath)
    template_page = template_reader.pages[0]
    
    # Merge overlay onto template
    overlay_page = overlay_reader.pages[0]
    template_page.merge_page(overlay_page)
    
    # Write output
    writer = PdfWriter()
    writer.add_page(template_page)
    
    with open(output_abspath, "wb") as output_file:
        writer.write(output_file)
    
    return output_abspath
