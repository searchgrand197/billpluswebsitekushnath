from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, Frame
from reportlab.pdfgen import canvas
from reportlab.lib.colors import Color, black, white, red
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from decimal import Decimal
from io import BytesIO
from django.conf import settings
from .models import CompanySettings
import base64
import os
from pathlib import Path
from reportlab.lib.enums import TA_LEFT, TA_RIGHT, TA_CENTER

try:
    from num2words import num2words
except ImportError:
    num2words = None


def company_logo_data_uri():
    """
    Logo as a data URI so print/PDF pages work without /static/ on production.
    Tries billing static, then frontend dist/public.
    """
    base = Path(settings.BASE_DIR)
    candidates = [
        base / "billing" / "static" / "img" / "logo.png",
        base / "frontend" / "dist" / "logo.png",
        base / "frontend" / "public" / "logo.png",
    ]
    for path in candidates:
        if path.is_file():
            encoded = base64.b64encode(path.read_bytes()).decode("ascii")
            return f"data:image/png;base64,{encoded}"
    return ""

class NumberedCanvas(canvas.Canvas):
    def __init__(self, *args, **kwargs):
        canvas.Canvas.__init__(self, *args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_footer(num_pages)
            canvas.Canvas.showPage(self)
        canvas.Canvas.save(self)

    def draw_page_footer(self, page_count):
        self.setFont("Helvetica", 8)
        self.setFillColor(Color(0.5, 0.5, 0.5))
        self.drawRightString(200*mm, 10*mm, f"Page {self._pageNumber} of {page_count}")

def draw_header(canvas, doc):
    # Save canvas state
    canvas.saveState()
    
    # Draw red wave
    canvas.setFillColor(Color(0.9, 0, 0, alpha=0.9))
    p = canvas.beginPath()
    p.moveTo(doc.rightMargin, doc.height + doc.topMargin)
    p.curveTo(doc.width/2, doc.height + doc.topMargin + 30*mm,
              doc.width/2, doc.height + doc.topMargin - 30*mm,
              doc.width - doc.rightMargin, doc.height + doc.topMargin - 20*mm)
    p.lineTo(doc.width - doc.rightMargin, doc.height + doc.topMargin + 50*mm)
    p.lineTo(doc.rightMargin, doc.height + doc.topMargin + 50*mm)
    p.close()
    canvas.drawPath(p, fill=1, stroke=0)
    
    # Draw company info in white on the wave
    canvas.setFillColor(white)
    canvas.setFont("Helvetica-Bold", 12)
    canvas.drawString(doc.rightMargin + 5*mm, doc.height + doc.topMargin + 35*mm, "Your Company Name")
    canvas.setFont("Helvetica", 8)
    canvas.drawString(doc.rightMargin + 5*mm, doc.height + doc.topMargin + 30*mm, "123 Business Street")
    canvas.drawString(doc.rightMargin + 5*mm, doc.height + doc.topMargin + 25*mm, "City, State, ZIP")
    
    # Restore canvas state
    canvas.restoreState()

def get_company_settings():
    """Get the company settings from the database."""
    return CompanySettings.objects.first()

def _rs(value):
    return f"{float(value or 0):.2f}"


def create_invoice_pdf(invoice):
    """GST invoice PDF — same layout as billing/invoice_print.html."""
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=12 * mm,
        leftMargin=12 * mm,
        topMargin=10 * mm,
        bottomMargin=10 * mm,
    )
    company = get_company_settings()
    if not company:
        raise ValueError("Company settings not found")

    styles = getSampleStyleSheet()
    tiny = ParagraphStyle('GstTiny', parent=styles['Normal'], fontSize=8, leading=10, textColor=black)
    tiny_b = ParagraphStyle('GstTinyB', parent=tiny, fontName='Helvetica-Bold')
    co_name = ParagraphStyle('GstCo', parent=styles['Normal'], fontSize=12, leading=14, fontName='Helvetica-Bold')
    mid_title = ParagraphStyle('GstMid', parent=styles['Normal'], fontSize=16, leading=20, fontName='Helvetica-Bold', alignment=TA_CENTER)
    cell = ParagraphStyle('GstCell', parent=styles['Normal'], fontSize=7, leading=9)
    cell_c = ParagraphStyle('GstCellC', parent=cell, alignment=TA_CENTER)
    cell_r = ParagraphStyle('GstCellR', parent=cell, alignment=TA_RIGHT)
    head_cell = ParagraphStyle('GstHead', parent=cell_c, textColor=white, fontName='Helvetica-Bold')
    foot = ParagraphStyle('GstFoot', parent=tiny, fontSize=8, leading=10)

    interstate = float(invoice.igst_amount or 0) > 0
    pos = (invoice.customer_state or company.state or '').strip()
    when = invoice.invoice_date.strftime('%d/%m/%Y')
    if invoice.created_at:
        when = f"{when} {invoice.created_at.strftime('%I:%M %p')}"

    left_bits = [
        Paragraph(company.company_name or '', co_name),
        Paragraph(
            f"{company.address_line1}"
            + (f", {company.address_line2}" if company.address_line2 else ''),
            tiny,
        ),
        Paragraph(f"{company.city}, {company.state} {company.postal_code}", tiny),
    ]
    if company.phone:
        left_bits.append(Paragraph(f"Phone: {company.phone}", tiny))
    if company.email:
        left_bits.append(Paragraph(f"Email: {company.email}", tiny))
    if company.gstin:
        left_bits.append(Paragraph(f"<b>GSTIN:</b> {company.gstin}", tiny))
    if company.pan_number:
        left_bits.append(Paragraph(f"<b>PAN:</b> {company.pan_number}", tiny))

    logo_path = os.path.join(os.path.dirname(__file__), 'static', 'img', 'logo.png')
    if os.path.exists(logo_path):
        logo_img = Image(logo_path)
        max_w, max_h = 28 * mm, 14 * mm
        iw, ih = float(logo_img.imageWidth or 0), float(logo_img.imageHeight or 0)
        if iw > 0 and ih > 0:
            scale = min(max_w / iw, max_h / ih)
            logo_img.drawWidth = iw * scale
            logo_img.drawHeight = ih * scale
        else:
            logo_img.drawWidth = max_w
            logo_img.drawHeight = max_h
        left_cell = [logo_img, Spacer(1, 2), *left_bits]
    else:
        left_cell = left_bits

    right_bits = [
        Paragraph(f"Party Name: {invoice.customer_name or 'Walk-in Customer'}", tiny_b),
    ]
    if invoice.customer_address:
        right_bits.append(Paragraph(f"Party Address: {invoice.customer_address}", tiny))
    if invoice.customer_phone:
        right_bits.append(Paragraph(f"Phone: {invoice.customer_phone}", tiny))
    if invoice.customer_gstin:
        right_bits.append(Paragraph(f"Party GSTIN: {invoice.customer_gstin}", tiny))
    if pos:
        right_bits.append(Paragraph(f"<b>Place of Supply:</b> {pos}", tiny))
    right_bits.append(Paragraph(
        "<b>Tax:</b> Inter-state IGST" if interstate else "<b>Tax:</b> Intra-state CGST + SGST",
        tiny,
    ))
    right_bits.append(Spacer(1, 4))
    right_bits.append(Paragraph(f"<b>Invoice No.:</b> {invoice.invoice_number}", tiny))
    right_bits.append(Paragraph(f"<b>Date:</b> {when}", tiny))

    header = Table(
        [[left_cell, Paragraph('GST INVOICE', mid_title), right_bits]],
        colWidths=[70 * mm, 40 * mm, 70 * mm],
    )
    header.setStyle(TableStyle([
        ('BOX', (0, 0), (-1, -1), 0.8, black),
        ('INNERGRID', (0, 0), (-1, -1), 0.8, black),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('VALIGN', (1, 0), (1, 0), 'MIDDLE'),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))

    if interstate:
        cols = ['SN.', 'Product Name', 'HSN', 'Batch', 'Exp.', 'MRP', 'Disc%', 'Rate', 'GST%', 'IGST', 'Qty', 'Amount']
    else:
        cols = ['SN.', 'Product Name', 'HSN', 'Batch', 'Exp.', 'MRP', 'Disc%', 'Rate', 'GST%', 'SGST', 'CGST', 'Qty', 'Amount']

    rows = [[Paragraph(c, head_cell) for c in cols]]
    items = list(invoice.items.select_related('product').prefetch_related('product__batches').all())
    for i, item in enumerate(items, 1):
        product = item.product
        batch = product.batches.first() if product else None
        br = item.line_breakup()
        hsn = (getattr(product, 'hsn_code', None) or '—')
        batch_no = batch.batch_number if batch else '—'
        exp = batch.exp_date.strftime('%m/%y') if batch and getattr(batch, 'exp_date', None) else '—'
        mrp = _rs(getattr(product, 'price', 0))
        disc = _rs(item.disc_percent())
        rate = _rs(item.unit_price)
        gst = _rs(item.effective_gst_rate())
        line = [
            Paragraph(str(i), cell_c),
            Paragraph(product.name if product else '', cell),
            Paragraph(str(hsn), cell_c),
            Paragraph(str(batch_no), cell_c),
            Paragraph(exp, cell_c),
            Paragraph(mrp, cell_r),
            Paragraph(disc, cell_c),
            Paragraph(rate, cell_r),
            Paragraph(gst, cell_c),
        ]
        if interstate:
            line.append(Paragraph(_rs(br['igst']), cell_r))
        else:
            line.append(Paragraph(_rs(br['sgst']), cell_r))
            line.append(Paragraph(_rs(br['cgst']), cell_r))
        line.append(Paragraph(str(item.quantity), cell_c))
        line.append(Paragraph(_rs(br['total']), cell_r))
        rows.append(line)

    gst_note = (
        f"Taxable Rs {_rs(invoice.subtotal)} — IGST Rs {_rs(invoice.igst_amount)} — GST Rs {_rs(invoice.gst_total)}"
        if interstate else
        f"Taxable Rs {_rs(invoice.subtotal)} — CGST Rs {_rs(invoice.cgst_amount)} — SGST Rs {_rs(invoice.sgst_amount)} — GST Rs {_rs(invoice.gst_total)}"
    )
    span_to = len(cols) - 2
    foot_row = [Paragraph(gst_note, cell)] + [''] * span_to + [Paragraph(f"Total Qty {len(items)}", cell_r)]
    rows.append(foot_row)

    page_w = 180 * mm
    if interstate:
        widths = [8, 32, 12, 14, 10, 12, 10, 14, 10, 14, 10, 24]
    else:
        widths = [8, 28, 11, 12, 10, 12, 10, 12, 10, 12, 12, 9, 24]
    col_w = [page_w * (w / sum(widths)) for w in widths]
    items_table = Table(rows, colWidths=col_w, repeatRows=1)
    items_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), black),
        ('TEXTCOLOR', (0, 0), (-1, 0), white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 7),
        ('GRID', (0, 0), (-1, -2), 0.5, black),
        ('BOX', (0, 0), (-1, -1), 0.8, black),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('SPAN', (0, -1), (span_to, -1)),
        ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#f3f4f6')),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ('LEFTPADDING', (0, 0), (-1, -1), 2),
        ('RIGHTPADDING', (0, 0), (-1, -1), 2),
    ]))

    terms = [
        Paragraph('TERMS & CONDITIONS', tiny_b),
        Paragraph('1. Goods once sold will not be taken back.', foot),
        Paragraph('2. Subject to local jurisdiction.', foot),
    ]
    if invoice.notes:
        terms.append(Paragraph(f"<b>Remark:</b> {invoice.notes}", foot))
    if company.invoice_footer_text:
        terms.append(Paragraph(company.invoice_footer_text, foot))

    bank = [Paragraph('BANK DETAILS', tiny_b)]
    if company.bank_name:
        bank.append(Paragraph(f"Bank: {company.bank_name}", foot))
    if company.bank_account_number:
        bank.append(Paragraph(f"A/C No: {company.bank_account_number}", foot))
    if company.bank_ifsc:
        bank.append(Paragraph(f"IFSC: {company.bank_ifsc}", foot))
    if not company.bank_name and not company.bank_account_number:
        bank.append(Paragraph('—', foot))

    sign = [
        Paragraph(f"For {company.company_name}", ParagraphStyle('Sign', parent=tiny, alignment=TA_CENTER)),
        Spacer(1, 22),
        Paragraph('Authorised Signatory', ParagraphStyle('Sign2', parent=tiny, alignment=TA_CENTER)),
    ]

    tax_rows = [['SUB TOTAL', _rs(invoice.subtotal)]]
    if interstate:
        tax_rows.append(['IGST', _rs(invoice.igst_amount)])
    else:
        tax_rows.append(['CGST', _rs(invoice.cgst_amount)])
        tax_rows.append(['SGST', _rs(invoice.sgst_amount)])
    tax_rows.extend([
        ['PAID', _rs(invoice.advance_paid)],
        ['DUE', _rs(invoice.outstanding_amount)],
        ['GRAND TOTAL', _rs(invoice.total_amount)],
    ])
    totals = Table(tax_rows, colWidths=[28 * mm, 22 * mm])
    totals.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -2), 'Helvetica'),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
        ('BACKGROUND', (0, -1), (-1, -1), black),
        ('TEXTCOLOR', (0, -1), (-1, -1), white),
        ('LINEBELOW', (0, 0), (-1, -2), 0.4, black),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ('LEFTPADDING', (0, 0), (-1, -1), 4),
        ('RIGHTPADDING', (0, 0), (-1, -1), 4),
    ]))

    bottom = Table(
        [[terms, bank, sign, totals]],
        colWidths=[48 * mm, 42 * mm, 38 * mm, 52 * mm],
    )
    bottom.setStyle(TableStyle([
        ('BOX', (0, 0), (-1, -1), 0.8, black),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, black),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))

    story = [
        header,
        items_table,
        bottom,
        Spacer(1, 6),
        Paragraph('Computer Generated Invoice', ParagraphStyle('Cg', parent=tiny, alignment=TA_CENTER, fontSize=7)),
    ]
    doc.build(story)
    buffer.seek(0)
    return buffer
