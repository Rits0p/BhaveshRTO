import datetime
import os
from io import BytesIO

from reportlab.graphics.shapes import Circle, Drawing, String
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    HRFlowable,
    Image,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

NAVY = colors.HexColor('#1e3a5f')
GOLD = colors.HexColor('#eab308')
DARK = colors.HexColor('#0f172a')
MUTED = colors.HexColor('#64748b')
BORDER = colors.HexColor('#e2e8f0')
LIGHT = colors.HexColor('#f8fafc')

SERVICE_LINE = 'RTO \u2022 Insurance \u2022 Fitness \u2022 PUC \u2022 Permit \u2022 License'

# Brand logo (light variant on white) used as a chip in the navy header band.
LOGO_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'assets', 'logo-light.jpeg')

# Helvetica is the guaranteed fallback; TTF fonts (Segoe UI / Arial) add the
# \u20b9 rupee glyph which the built-in Type1 fonts lack.
REGULAR_FONT = 'Helvetica'
BOLD_FONT = 'Helvetica-Bold'


def _setup_fonts():
    """Registers the best available TTF font for the rupee glyph."""
    global REGULAR_FONT, BOLD_FONT
    font_dirs = [
        r'C:\Windows\Fonts',
        '/usr/share/fonts/truetype/dejavu',
        '/usr/share/fonts',
        '/Library/Fonts',
    ]
    for base, reg_name, bold_name in [
        ('SegoeUI', 'segoeui.ttf', 'segoeuib.ttf'),
        ('Arial', 'arial.ttf', 'arialbd.ttf'),
    ]:
        reg_path = bold_path = None
        for directory in font_dirs:
            candidate = os.path.join(directory, reg_name)
            if os.path.exists(candidate):
                reg_path = candidate
                bold_candidate = os.path.join(directory, bold_name)
                bold_path = bold_candidate if os.path.exists(bold_candidate) else None
                break
        if not reg_path:
            continue
        try:
            pdfmetrics.registerFont(TTFont(base, reg_path))
            if bold_path:
                pdfmetrics.registerFont(TTFont(f'{base}-Bold', bold_path))
            REGULAR_FONT = base
            BOLD_FONT = f'{base}-Bold' if bold_path else BOLD_FONT
            return
        except Exception:
            continue


_setup_fonts()


def _inr(value):
    """Formats a number with Indian digit grouping, e.g. \u20b91,23,456.78."""
    amount = f'{float(value):.2f}'
    rupees, paise = amount.split('.')
    if len(rupees) > 3:
        last3 = rupees[-3:]
        body = rupees[:-3]
        groups = []
        while body:
            groups.append(body[-2:])
            body = body[:-2]
        groups.reverse()
        rupees = ','.join(groups + [last3])
    return f'\u20b9{rupees}.{paise}'


def _build_logo(size=34):
    """Vector monogram logo: a gold-ringed white disc with the 'BS' initials.
    Fallback used only when the brand logo image file is unavailable."""
    d = Drawing(size, size)
    cx = size / 2.0
    d.add(Circle(cx, cx, cx - 1, fillColor=colors.white, strokeColor=GOLD, strokeWidth=1.4))
    font_size = size * 0.42
    d.add(String(cx, cx - font_size * 0.36, 'BS', fontName=BOLD_FONT,
                 fontSize=font_size, fillColor=NAVY, textAnchor='middle'))
    return d


def _build_logo_image(size=44):
    """Brand logo image chip (white background) for the navy header band."""
    if os.path.exists(LOGO_PATH):
        img = Image(LOGO_PATH, width=size, height=size)
        img.borderColor = colors.white
        img.borderWidth = 1.5
        img.borderPadding = 1
        return img
    return _build_logo(size)


def _draw_page_frame(canvas, doc):
    """Drawn on every page: a clean navy frame with a gold inner line."""
    canvas.saveState()
    w, h = A4
    m = 20
    canvas.setStrokeColor(NAVY)
    canvas.setLineWidth(1.8)
    canvas.roundRect(m, m, w - 2 * m, h - 2 * m, radius=8, stroke=1, fill=0)
    canvas.setStrokeColor(GOLD)
    canvas.setLineWidth(0.9)
    canvas.roundRect(m + 4, m + 4, w - 2 * (m + 4), h - 2 * (m + 4), radius=5, stroke=1, fill=0)
    canvas.restoreState()


def generate_pdf_receipt(customer, payments, total_paid, total_pending, admin_name='Bhavesh Solanki'):
    """Renders a professional, printable A4 payment receipt PDF and returns the raw bytes."""
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        rightMargin=36, leftMargin=36, topMargin=42, bottomMargin=34,
        title=f'Receipt \u2014 {customer.name}',
        author=admin_name,
        onFirstPage=_draw_page_frame,
        onLaterPages=_draw_page_frame,
    )
    elements = []

    today = datetime.date.today().strftime('%d-%m-%Y')
    receipt_no = payments[0].receipt_number if payments else '\u2014'

    # ── Styles ──────────────────────────────────────────────────────────────
    brand_name = ParagraphStyle('BrandName', fontName=BOLD_FONT, fontSize=19,
                                textColor=colors.white, leading=22)
    brand_tag = ParagraphStyle('BrandTag', fontName=REGULAR_FONT, fontSize=9.5,
                               textColor=colors.HexColor('#cbd5e1'), leading=13)
    receipt_title = ParagraphStyle('ReceiptTitle', fontName=BOLD_FONT, fontSize=13,
                                   textColor=GOLD, alignment=TA_RIGHT, leading=16)
    receipt_meta = ParagraphStyle('ReceiptMeta', fontName=REGULAR_FONT, fontSize=8.5,
                                  textColor=colors.HexColor('#e2e8f0'), alignment=TA_RIGHT, leading=13)
    section_heading = ParagraphStyle('SectionHeading', fontName=BOLD_FONT, fontSize=11,
                                     textColor=NAVY, leading=14, spaceBefore=2)
    label_style = ParagraphStyle('Label', fontName=BOLD_FONT, fontSize=9.5,
                                 textColor=NAVY, leading=13)
    value_style = ParagraphStyle('Value', fontName=REGULAR_FONT, fontSize=9.5,
                                 textColor=DARK, leading=13)

    # ── Header band (logo + company + receipt meta) ──────────────────────────
    header = Table(
        [[
            _build_logo_image(),
            [
                Paragraph('Bhavesh Solanki', brand_name),
                Paragraph('RTO &amp; Insurance Advisor', brand_tag),
            ],
            [
                Paragraph('PAYMENT RECEIPT', receipt_title),
                Paragraph(
                    f'Receipt No: {receipt_no}<br/>'
                    f'Issued On: {today}<br/>'
                    f'Prepared by: {admin_name}',
                    receipt_meta,
                ),
            ],
        ]],
        colWidths=[64, 282, 180],
    )
    header.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), NAVY),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 14),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 14),
        ('LEFTPADDING', (0, 0), (-1, -1), 10),
        ('RIGHTPADDING', (0, 0), (-1, -1), 10),
        ('LINEBELOW', (0, 0), (-1, -1), 2.5, GOLD),
    ]))
    elements.append(header)
    elements.append(Spacer(1, 14))

    # ── Customer / billing details box ───────────────────────────────────────
    elements.append(Paragraph('BILLED TO / CUSTOMER DETAILS', section_heading))
    elements.append(Spacer(1, 5))
    cust_rows = [
        [Paragraph('Customer Name', label_style), Paragraph(customer.name, value_style),
         Paragraph('Contact', label_style), Paragraph(customer.contact_number or '\u2014', value_style)],
        [Paragraph('Category', label_style), Paragraph(customer.get_category_display(), value_style),
         Paragraph('Vehicle No.', label_style), Paragraph(customer.vehicle_number or '\u2014', value_style)],
        [Paragraph('Start Date', label_style),
         Paragraph(customer.start_date.strftime('%d-%m-%Y') if customer.start_date else '\u2014', value_style),
         Paragraph('Expiry Date', label_style),
         Paragraph(customer.end_date.strftime('%d-%m-%Y') if customer.end_date else '\u2014', value_style)],
    ]
    t1 = Table(cust_rows, colWidths=[82, 165, 82, 165])
    t1.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), LIGHT),
        ('BOX', (0, 0), (-1, -1), 1, BORDER),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, BORDER),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 7),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 7),
        ('LEFTPADDING', (0, 0), (-1, -1), 10),
    ]))
    elements.append(t1)
    elements.append(Spacer(1, 16))

    # ── Payment history table ────────────────────────────────────────────────
    elements.append(Paragraph('PAYMENT HISTORY', section_heading))
    elements.append(Spacer(1, 5))
    pay_rows = [['#', 'Date', 'Receipt No.', 'Method', 'Amount']]
    for idx, p in enumerate(payments, 1):
        pay_rows.append([
            str(idx),
            p.payment_date.strftime('%d-%m-%Y') if p.payment_date else '\u2014',
            p.receipt_number or '\u2014',
            p.get_method_display() if p.method else '\u2014',
            _inr(p.amount),
        ])
    if not payments:
        pay_rows.append(['\u2014', 'No payments recorded yet', '', '', '\u2014'])

    t2 = Table(pay_rows, colWidths=[36, 105, 150, 105, 130])
    t2.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), NAVY),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), BOLD_FONT),
        ('FONTNAME', (0, 1), (-1, -1), REGULAR_FONT),
        ('ALIGN', (0, 0), (0, -1), 'CENTER'),
        ('ALIGN', (1, 0), (1, -1), 'CENTER'),
        ('ALIGN', (3, 0), (3, -1), 'CENTER'),
        ('ALIGN', (4, 0), (4, -1), 'RIGHT'),
        ('GRID', (0, 0), (-1, -1), 0.5, BORDER),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
    ]))
    for i in range(2, len(pay_rows)):
        if i % 2 == 0:
            t2.setStyle(TableStyle([('BACKGROUND', (0, i), (-1, i), LIGHT)]))
    elements.append(t2)
    elements.append(Spacer(1, 16))

    # ── Summary boxes ────────────────────────────────────────────────────────
    elements.append(Paragraph('PAYMENT SUMMARY', section_heading))
    elements.append(Spacer(1, 6))
    summary_items = [
        ('Total Amount', _inr(customer.amount_total), colors.HexColor('#dbeafe'), NAVY),
        ('Amount Collected', _inr(total_paid), colors.HexColor('#d1fae5'), colors.HexColor('#065f46')),
        ('Amount Pending', _inr(total_pending), colors.HexColor('#fef3c7'), colors.HexColor('#92400e')),
    ]
    box_rows = [[
        [Paragraph(label, ParagraphStyle('SumLabel', fontName=BOLD_FONT, fontSize=9, textColor=color, alignment=TA_CENTER, leading=12)),
         Paragraph(value, ParagraphStyle('SumValue', fontName=BOLD_FONT, fontSize=13, textColor=color, alignment=TA_CENTER, leading=16))]
        for label, value, bg, color in summary_items
    ]]
    t3 = Table(box_rows, colWidths=[172, 172, 172])
    t3.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 9),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 9),
        ('BOX', (0, 0), (0, 0), 1, BORDER),
        ('BOX', (1, 0), (1, 0), 1, BORDER),
        ('BOX', (2, 0), (2, 0), 1, BORDER),
        ('BACKGROUND', (0, 0), (0, 0), summary_items[0][2]),
        ('BACKGROUND', (1, 0), (1, 0), summary_items[1][2]),
        ('BACKGROUND', (2, 0), (2, 0), summary_items[2][2]),
    ]))
    elements.append(t3)
    elements.append(Spacer(1, 18))

    # ── Signature block ──────────────────────────────────────────────────────
    sign_table = Table(
        [
            ['', HRFlowable(width=165, thickness=1, color=NAVY, hAlign='RIGHT')],
            ['', Paragraph('Authorized Signatory', ParagraphStyle(
                'Sign', fontName=REGULAR_FONT, fontSize=9.5, textColor=MUTED, alignment=TA_RIGHT))],
        ],
        colWidths=[300, 165],
    )
    sign_table.setStyle(TableStyle([
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ('TOPPADDING', (0, 0), (-1, -1), 0),
        ('BOTTOMPADDING', (0, 1), (-1, 1), 0),
    ]))
    elements.append(sign_table)
    elements.append(Spacer(1, 14))

    # ── Footer strip ─────────────────────────────────────────────────────────
    footer = Table(
        [[Paragraph(SERVICE_LINE, ParagraphStyle('FLine', fontName=REGULAR_FONT, fontSize=8.5,
                                                 textColor=MUTED, alignment=TA_CENTER, leading=12))],
         [Paragraph('We value your trust \u2014 and look forward to serving you again.', ParagraphStyle('FThanks', fontName=BOLD_FONT,
                                                                   fontSize=10, textColor=NAVY, alignment=TA_CENTER, leading=14))]],
        colWidths=[494],
    )
    footer.setStyle(TableStyle([
        ('TOPPADDING', (0, 0), (-1, 0), 8),
        ('BOTTOMPADDING', (0, 1), (-1, 1), 8),
        ('LINEABOVE', (0, 0), (-1, 0), 0.5, BORDER),
    ]))
    elements.append(footer)

    doc.build(elements)
    buffer.seek(0)
    return buffer.getvalue()


def generate_manual_pdf_receipt(form_data, admin_name='Bhavesh Solanki'):
    """Renders the same A4 receipt PDF but from manually entered form data
    (no DB customer object). ``form_data`` is a plain dict with keys:
        name, contact_number, vehicle_number, service, date,
        amount_total, amount_paid, amount_pending, method
    The PDF layout and styling are identical to ``generate_pdf_receipt``.
    """
    import datetime as _dt

    buffer = BytesIO()

    # Use the DB-assigned receipt number when available (preferred); fall back
    # to a timestamp-based number for cases where the PDF is generated without
    # first saving to the DB.
    receipt_no = form_data.get('receipt_number') or f"MNL-{_dt.datetime.now().strftime('%Y%m%d%H%M%S')}"

    # Parse the date supplied by the form (ISO string "YYYY-MM-DD" or None).
    raw_date = form_data.get('date') or ''
    try:
        pay_date = _dt.datetime.strptime(raw_date, '%Y-%m-%d').date()
    except (ValueError, TypeError):
        pay_date = _dt.date.today()

    today_str = _dt.date.today().strftime('%d-%m-%Y')
    pay_date_str = pay_date.strftime('%d-%m-%Y')

    amount_total = float(form_data.get('amount_total') or 0)
    amount_paid = float(form_data.get('amount_paid') or 0)
    amount_pending = float(form_data.get('amount_pending') or 0)

    service = form_data.get('service') or '—'
    method_display = form_data.get('method') or '—'
    name = form_data.get('name') or '—'
    contact = form_data.get('contact_number') or '—'
    vehicle = form_data.get('vehicle_number') or '—'

    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        rightMargin=36, leftMargin=36, topMargin=42, bottomMargin=34,
        title=f'Manual Receipt — {name}',
        author=admin_name,
        onFirstPage=_draw_page_frame,
        onLaterPages=_draw_page_frame,
    )
    elements = []

    # ── Styles (identical to generate_pdf_receipt) ───────────────────────────
    brand_name = ParagraphStyle('BrandName', fontName=BOLD_FONT, fontSize=19,
                                textColor=colors.white, leading=22)
    brand_tag = ParagraphStyle('BrandTag', fontName=REGULAR_FONT, fontSize=9.5,
                               textColor=colors.HexColor('#cbd5e1'), leading=13)
    receipt_title = ParagraphStyle('ReceiptTitle', fontName=BOLD_FONT, fontSize=13,
                                   textColor=GOLD, alignment=TA_RIGHT, leading=16)
    receipt_meta = ParagraphStyle('ReceiptMeta', fontName=REGULAR_FONT, fontSize=8.5,
                                  textColor=colors.HexColor('#e2e8f0'), alignment=TA_RIGHT, leading=13)
    section_heading = ParagraphStyle('SectionHeading', fontName=BOLD_FONT, fontSize=11,
                                     textColor=NAVY, leading=14, spaceBefore=2)
    label_style = ParagraphStyle('Label', fontName=BOLD_FONT, fontSize=9.5,
                                 textColor=NAVY, leading=13)
    value_style = ParagraphStyle('Value', fontName=REGULAR_FONT, fontSize=9.5,
                                 textColor=DARK, leading=13)

    # ── Header band ──────────────────────────────────────────────────────────
    header = Table(
        [[
            _build_logo_image(),
            [
                Paragraph('Bhavesh Solanki', brand_name),
                Paragraph('RTO &amp; Insurance Advisor', brand_tag),
            ],
            [
                Paragraph('PAYMENT RECEIPT', receipt_title),
                Paragraph(
                    f'Receipt No: {receipt_no}<br/>'
                    f'Issued On: {today_str}<br/>'
                    f'Prepared by: {admin_name}',
                    receipt_meta,
                ),
            ],
        ]],
        colWidths=[64, 282, 180],
    )
    header.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), NAVY),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 14),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 14),
        ('LEFTPADDING', (0, 0), (-1, -1), 10),
        ('RIGHTPADDING', (0, 0), (-1, -1), 10),
        ('LINEBELOW', (0, 0), (-1, -1), 2.5, GOLD),
    ]))
    elements.append(header)
    elements.append(Spacer(1, 14))

    # ── Customer / billing details box ───────────────────────────────────────
    elements.append(Paragraph('BILLED TO / CUSTOMER DETAILS', section_heading))
    elements.append(Spacer(1, 5))
    cust_rows = [
        [Paragraph('Customer Name', label_style), Paragraph(name, value_style),
         Paragraph('Contact', label_style), Paragraph(contact, value_style)],
        [Paragraph('Service', label_style), Paragraph(service, value_style),
         Paragraph('Vehicle No.', label_style), Paragraph(vehicle, value_style)],
        [Paragraph('Date', label_style), Paragraph(pay_date_str, value_style),
         Paragraph('Payment Method', label_style), Paragraph(method_display, value_style)],
    ]
    t1 = Table(cust_rows, colWidths=[82, 165, 82, 165])
    t1.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), LIGHT),
        ('BOX', (0, 0), (-1, -1), 1, BORDER),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, BORDER),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 7),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 7),
        ('LEFTPADDING', (0, 0), (-1, -1), 10),
    ]))
    elements.append(t1)
    elements.append(Spacer(1, 16))

    # ── Payment entry table ───────────────────────────────────────────────────
    elements.append(Paragraph('PAYMENT DETAILS', section_heading))
    elements.append(Spacer(1, 5))
    pay_rows = [['#', 'Date', 'Receipt No.', 'Method', 'Amount']]
    if amount_paid > 0:
        pay_rows.append(['1', pay_date_str, receipt_no, method_display, _inr(amount_paid)])
    else:
        pay_rows.append(['—', 'No payment recorded', '', '', '—'])

    t2 = Table(pay_rows, colWidths=[36, 105, 150, 105, 130])
    t2.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), NAVY),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), BOLD_FONT),
        ('FONTNAME', (0, 1), (-1, -1), REGULAR_FONT),
        ('ALIGN', (0, 0), (0, -1), 'CENTER'),
        ('ALIGN', (1, 0), (1, -1), 'CENTER'),
        ('ALIGN', (3, 0), (3, -1), 'CENTER'),
        ('ALIGN', (4, 0), (4, -1), 'RIGHT'),
        ('GRID', (0, 0), (-1, -1), 0.5, BORDER),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
        ('BACKGROUND', (0, 1), (-1, 1), LIGHT),
    ]))
    elements.append(t2)
    elements.append(Spacer(1, 16))

    # ── Summary boxes ────────────────────────────────────────────────────────
    elements.append(Paragraph('PAYMENT SUMMARY', section_heading))
    elements.append(Spacer(1, 6))
    summary_items = [
        ('Total Amount', _inr(amount_total), colors.HexColor('#dbeafe'), NAVY),
        ('Amount Collected', _inr(amount_paid), colors.HexColor('#d1fae5'), colors.HexColor('#065f46')),
        ('Amount Pending', _inr(amount_pending), colors.HexColor('#fef3c7'), colors.HexColor('#92400e')),
    ]
    box_rows = [[
        [Paragraph(label, ParagraphStyle('SumLabel', fontName=BOLD_FONT, fontSize=9, textColor=color, alignment=TA_CENTER, leading=12)),
         Paragraph(value, ParagraphStyle('SumValue', fontName=BOLD_FONT, fontSize=13, textColor=color, alignment=TA_CENTER, leading=16))]
        for label, value, bg, color in summary_items
    ]]
    t3 = Table(box_rows, colWidths=[172, 172, 172])
    t3.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 9),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 9),
        ('BOX', (0, 0), (0, 0), 1, BORDER),
        ('BOX', (1, 0), (1, 0), 1, BORDER),
        ('BOX', (2, 0), (2, 0), 1, BORDER),
        ('BACKGROUND', (0, 0), (0, 0), summary_items[0][2]),
        ('BACKGROUND', (1, 0), (1, 0), summary_items[1][2]),
        ('BACKGROUND', (2, 0), (2, 0), summary_items[2][2]),
    ]))
    elements.append(t3)
    elements.append(Spacer(1, 18))

    # ── Signature block ──────────────────────────────────────────────────────
    sign_table = Table(
        [
            ['', HRFlowable(width=165, thickness=1, color=NAVY, hAlign='RIGHT')],
            ['', Paragraph('Authorized Signatory', ParagraphStyle(
                'Sign', fontName=REGULAR_FONT, fontSize=9.5, textColor=MUTED, alignment=TA_RIGHT))],
        ],
        colWidths=[300, 165],
    )
    sign_table.setStyle(TableStyle([
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ('TOPPADDING', (0, 0), (-1, -1), 0),
        ('BOTTOMPADDING', (0, 1), (-1, 1), 0),
    ]))
    elements.append(sign_table)
    elements.append(Spacer(1, 14))

    # ── Footer strip ─────────────────────────────────────────────────────────
    footer = Table(
        [[Paragraph(SERVICE_LINE, ParagraphStyle('FLine', fontName=REGULAR_FONT, fontSize=8.5,
                                                 textColor=MUTED, alignment=TA_CENTER, leading=12))],
         [Paragraph('We value your trust \u2014 and look forward to serving you again.', ParagraphStyle('FThanks', fontName=BOLD_FONT,
                                                                   fontSize=10, textColor=NAVY, alignment=TA_CENTER, leading=14))]],
        colWidths=[494],
    )
    footer.setStyle(TableStyle([
        ('TOPPADDING', (0, 0), (-1, 0), 8),
        ('BOTTOMPADDING', (0, 1), (-1, 1), 8),
        ('LINEABOVE', (0, 0), (-1, 0), 0.5, BORDER),
    ]))
    elements.append(footer)

    doc.build(elements)
    buffer.seek(0)
    return buffer.getvalue()
