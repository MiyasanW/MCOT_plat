import os
import io
from PyPDF2 import PdfReader, PdfWriter
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from django.conf import settings
from decimal import Decimal

# ── Thai Font Registration ──────────────────────────────────────────────────
_font_dir = os.path.join(settings.BASE_DIR, 'static', 'fonts')
_font_regular = os.path.join(_font_dir, 'Sarabun-Regular.ttf')
_font_bold    = os.path.join(_font_dir, 'Sarabun-Bold.ttf')
if os.path.exists(_font_regular):
    pdfmetrics.registerFont(TTFont('Sarabun', _font_regular))
if os.path.exists(_font_bold):
    pdfmetrics.registerFont(TTFont('Sarabun-Bold', _font_bold))

# ── Coordinate helpers ──────────────────────────────────────────────────────
# Coordinates are calibrated against quotation_template.pdf (595 × 842 pts).
# pdfplumber measures "top" from the top-left corner.
# ReportLab measures y from the bottom-left corner.
# Conversion: RL_y = PAGE_H - pdfplumber_top
PAGE_H = 842
TEXT_BASELINE_OFFSET = 8

def _rl(top):
    """Convert pdfplumber top-from-top to ReportLab y-from-bottom."""
    return PAGE_H - top

def _text_y(top):
    """Compensate font baseline so visual top aligns with template top."""
    return _rl(top + TEXT_BASELINE_OFFSET)

def format_money(amount):
    if amount is None:
        return "0.00"
    return f"{Decimal(str(amount)):,.2f}"

# ── Max rows that fit in the table area (top 308 → 510, ~20 pt/row) ─────────
MAX_ROWS = 10
ITEM_TABLE_TOP = 320
PRICE_VALUE_Y_NUDGE = 0
UNIT_PRICE_RIGHT_X = 462
AMOUNT_RIGHT_X = 568
TOTALS_RIGHT_X = 567

# Header block (customer identity) near top section of quotation template.
HEADER_LABEL_X = 45
HEADER_VALUE_X = 120
HEADER_CUSTOMER_TOP = 166
HEADER_PROJECT_TOP = 184
HEADER_PHONE_TOP = 202

def generate_overlay(booking):
    """
    Build a transparent overlay PDF whose text lands exactly on the
    MCOT quotation template fields.

        Field positions (verified with pdfplumber on quotation_template.pdf):
            Table row 1    y=_text_y(332), row_h=20

        Important: per user request we write
            - rented equipment items
            - prices
            - totals block (total/discount/remaining/vat/net total)
    """
    packet = io.BytesIO()
    can = canvas.Canvas(packet, pagesize=A4)

    try:
        can.setFont("Sarabun", 10)
        fn, fb = "Sarabun", "Sarabun-Bold"
    except Exception:
        can.setFont("Helvetica", 10)
        fn, fb = "Helvetica", "Helvetica-Bold"

    def normal(size=10):
        can.setFont(fn, size)

    def mask(x, y, w, h):
        can.setFillColorRGB(1, 1, 1)
        can.rect(x, y, w, h, fill=1, stroke=0)
        can.setFillColorRGB(0, 0, 0)

    normal(10)

    # ── Header: Customer identity ───────────────────────────────────────────
    customer_name = (booking.customer_name or "-").strip() or "-"
    project_name = (booking.project_name or "-").strip() or "-"
    phone = (booking.phone or "-").strip() or "-"

    can.setFont(fb, 10)
    can.drawString(HEADER_LABEL_X, _text_y(HEADER_CUSTOMER_TOP), "ชื่อลูกค้า")
    can.drawString(HEADER_LABEL_X, _text_y(HEADER_PROJECT_TOP), "ชื่องาน")
    can.drawString(HEADER_LABEL_X, _text_y(HEADER_PHONE_TOP), "โทร")

    normal(10)
    can.drawString(HEADER_VALUE_X, _text_y(HEADER_CUSTOMER_TOP), customer_name[:70])
    can.drawString(HEADER_VALUE_X, _text_y(HEADER_PROJECT_TOP), project_name[:70])
    can.drawString(HEADER_VALUE_X, _text_y(HEADER_PHONE_TOP), phone[:30])

    # ── Item Table ───────────────────────────────────────────────────────────
    items    = list(booking.items.select_related('product').all())
    rental_days = booking.rental_days or 1

    rows = []
    for item in items:
        desc = f"ค่าเช่า {item.product.name}"
        rows.append((desc, item.quantity, item.price_at_booking))

    start_y = _text_y(ITEM_TABLE_TOP)
    row_h   = 20

    for idx, (desc, qty, unit_price) in enumerate(rows[:MAX_ROWS]):
        y = start_y - idx * row_h
        subtotal = Decimal(str(qty)) * Decimal(str(unit_price)) * rental_days
        can.drawString(45, y, str(idx + 1))
        can.drawString(90, y, desc[:62])
        can.drawRightString(370, y, str(qty))
        can.drawRightString(UNIT_PRICE_RIGHT_X, y + PRICE_VALUE_Y_NUDGE, format_money(unit_price))
        can.drawRightString(AMOUNT_RIGHT_X, y + PRICE_VALUE_Y_NUDGE, format_money(subtotal))

    # ── Totals Block (bottom-right) ─────────────────────────────────────────
    # Template rows:
    # 516: TOTAL PRICE, 535: Discount, 552: Remaining, 570: VAT 7%, 588: NET TOTAL
    total_price = sum(
        Decimal(str(qty)) * Decimal(str(unit_price)) * rental_days
        for _, qty, unit_price in rows
    )
    discount = Decimal(str(booking.discount_amount or 0))
    remaining = max(total_price - discount, Decimal("0"))
    vat = (remaining * Decimal("0.07")).quantize(Decimal("0.01"))
    net_total = remaining + vat

    y_total = _text_y(516)
    y_discount = _text_y(535)
    y_remaining = _text_y(552)
    y_vat = _text_y(570)
    y_net = _text_y(588)

    # Clear placeholder values from template before drawing dynamic amounts.
    for y_pos in (y_total, y_discount, y_remaining, y_vat, y_net):
        mask(520, y_pos - 2, 48, 13)

    can.drawRightString(TOTALS_RIGHT_X, y_total, format_money(total_price))
    can.drawRightString(TOTALS_RIGHT_X, y_discount, format_money(discount))
    can.drawRightString(TOTALS_RIGHT_X, y_remaining, format_money(remaining))
    can.drawRightString(TOTALS_RIGHT_X, y_vat, format_money(vat))
    can.drawRightString(TOTALS_RIGHT_X, y_net, format_money(net_total))

    can.save()
    packet.seek(0)
    return packet


def generate_quotation_pdf(booking, template_abspath):
    """
    Merge the text overlay onto the MCOT quotation template PDF and return
    the final PDF as bytes.
    """
    overlay_reader  = PdfReader(generate_overlay(booking))
    template_reader = PdfReader(template_abspath)

    page = template_reader.pages[0]
    page.merge_page(overlay_reader.pages[0])

    writer = PdfWriter()
    writer.add_page(page)

    out = io.BytesIO()
    writer.write(out)
    out.seek(0)
    return out.read()


# ── Legacy alias (kept for backwards compatibility) ─────────────────────────
def merge_pdf_with_template(booking, template_abspath, output_abspath):
    pdf_bytes = generate_quotation_pdf(booking, template_abspath)
    with open(output_abspath, "wb") as f:
        f.write(pdf_bytes)
    return output_abspath
