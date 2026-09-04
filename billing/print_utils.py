"""
Direct print utilities for invoices. Uses pywin32 (win32print) to communicate with printer.
No wkhtmltopdf or SumatraPDF required.
"""
import os
import subprocess
import shutil
import tempfile

# ESC/POS codes for thermal printers
ESC = b'\x1b'
GS = b'\x1d'
INIT = ESC + b'@'
CUT = GS + b'V' + b'\x00'
FEED = b'\n' * 3


def print_pdf_silent_no_dialog(pdf_path, printer_name=None):
    """
    Print PDF with NO popup/dialog. Tries SumatraPDF first (silent), then falls back.
    Returns (success, message).
    """
    if os.name != 'nt':
        return False, "Windows only"
    if not os.path.exists(pdf_path):
        return False, "PDF not found"
    printer_name = (printer_name or "").strip()
    print_settings = "portrait,1x,fit"
    # 1. SumatraPDF: fully silent, no dialog
    sumatra_paths = [
        r'C:\Program Files\SumatraPDF\SumatraPDF.exe',
        r'C:\Program Files (x86)\SumatraPDF\SumatraPDF.exe',
    ]
    for p in sumatra_paths:
        if os.path.exists(p):
            try:
                cmd = [p, '-print-to-default', '-silent', '-print-settings', print_settings, pdf_path]
                if printer_name:
                    cmd = [p, '-print-to', printer_name, '-silent', '-print-settings', print_settings, pdf_path]
                flags = 0x08000000  # CREATE_NO_WINDOW
                subprocess.run(cmd, timeout=15, creationflags=flags)
                return True, "Printed (no dialog)"
            except Exception:
                continue
    if shutil.which('SumatraPDF'):
        try:
            cmd = ['SumatraPDF', '-print-to-default', '-silent', '-print-settings', print_settings, pdf_path]
            if printer_name:
                cmd = ['SumatraPDF', '-print-to', printer_name, '-silent', '-print-settings', print_settings, pdf_path]
            subprocess.run(cmd, timeout=15, creationflags=0x08000000)
            return True, "Printed (no dialog)"
        except Exception:
            pass
    return False, "SumatraPDF not found"


def print_to_printer(pdf_path, printer_name=None):
    """
    Print PDF - may show dialog. Uses ShellExecute/os.startfile.
    Does not require OpenPrinter (avoids "Unable to open printer").
    """
    if os.name != 'nt':
        return False, "Windows only"
    if not os.path.exists(pdf_path):
        return False, "PDF not found"
    printer_name = (printer_name or "").strip()
    try:
        import win32print
        import win32api
        current = None
        if printer_name:
            try:
                current = win32print.GetDefaultPrinter()
                win32print.SetDefaultPrinter(printer_name)
            except Exception:
                pass  # Use current default if configured printer invalid
        try:
            win32api.ShellExecute(0, "print", pdf_path, None, ".", 0)
            return True, "Sent to printer"
        finally:
            if current:
                try:
                    win32print.SetDefaultPrinter(current)
                except Exception:
                    pass
    except ImportError:
        try:
            os.startfile(pdf_path, "print")
            return True, "Sent to printer"
        except Exception as e:
            return False, str(e)
    except Exception as e:
        return False, str(e)


def generate_raw_invoice_text(invoice, company_settings, include_token=True):
    """Generate plain-text invoice for raw printer output (thermal/standard). include_token: add token line when invoice has token."""
    lines = []
    cs = company_settings
    lines.append("=" * 42)
    lines.append(cs.company_name[:42].center(42))
    lines.append((getattr(cs, 'address_line1', '') or '')[:42])
    lines.append(f"Ph: {cs.phone}"[:42])
    lines.append("=" * 42)
    lines.append("TAX INVOICE")
    lines.append("-" * 42)
    lines.append(f"Invoice: {invoice.invoice_number}")
    lines.append(f"Date: {invoice.invoice_date.strftime('%d/%m/%Y')}")
    lines.append(f"Bill To: {invoice.customer_name[:30]}")
    lines.append("-" * 42)
    lines.append(f"{'Item':<20} {'Qty':>5} {'Amt':>10}")
    lines.append("-" * 42)
    for item in invoice.items.all():
        name = (item.product.name if hasattr(item, 'product') else getattr(item, 'description', ''))[:18]
        qty = item.quantity
        amt = float(item.total if hasattr(item, 'total') else getattr(item, 'amount', 0))
        lines.append(f"{name:<20} {qty:>5} Rs{amt:>8.2f}")
    lines.append("-" * 42)
    if invoice.subtotal:
        lines.append(f"{'Subtotal':>35} Rs{float(invoice.subtotal):>8.2f}")
    if getattr(invoice, 'total_amount', None):
        lines.append(f"{'TOTAL':>35} Rs{float(invoice.total_amount):>8.2f}")
    if getattr(invoice, 'advance_paid', 0):
        lines.append(f"{'Paid':>35} Rs{float(invoice.advance_paid):>8.2f}")
    if getattr(invoice, 'outstanding_amount', 0) is not None:
        lines.append(f"{'Due':>35} Rs{float(invoice.outstanding_amount):>8.2f}")
    lines.append("=" * 42)
    lines.append("Thank you!")
    lines.append("")
    return "\n".join(lines)


def generate_token_only_text(invoice):
    """Generate plain text with only the token number for kitchen slip (compact, minimal paper)."""
    lines = []
    lines.append("=" * 20)
    lines.append("TOKEN".center(20))
    lines.append(str(invoice.token_number).center(20))
    lines.append("=" * 20)
    return "\n".join(lines)


def print_pdf_via_gdi(pdf_bytes, printer_name=None):
    """
    Print PDF with NO dialog - pure Python. Uses pypdfium2 + win32ui.
    PDF → render to image → draw to printer DC. No external apps.
    Requires: pip install pypdfium2 Pillow pywin32
    """
    if os.name != 'nt':
        return False, "Windows only"
    try:
        import pypdfium2
    except ImportError:
        return False, "Install pypdfium2: pip install pypdfium2"
    try:
        import win32ui
        import win32con
        import win32print
    except ImportError:
        return False, "Install pywin32: pip install pywin32"
    try:
        from PIL import Image, ImageWin
    except ImportError:
        return False, "Install Pillow: pip install Pillow"
    printer_name = (printer_name or "").strip() or win32print.GetDefaultPrinter()
    try:
        doc = pypdfium2.PdfDocument(pdf_bytes)
        n_pages = len(doc)
        if n_pages == 0:
            return False, "Empty PDF"
        dc = win32ui.CreateDC()
        dc.CreatePrinterDC(printer_name)
        dc.StartDoc("Invoice")
        max_w = dc.GetDeviceCaps(win32con.HORZRES)
        max_h = dc.GetDeviceCaps(win32con.VERTRES)
        for i in range(n_pages):
            page = doc[i]
            bitmap = page.render(scale=2.0, optimize_mode="print")
            pil_img = bitmap.to_pil()
            bitmap.close()
            page.close()
            w, h = pil_img.size
            scale = min(max_w / w, max_h / h, 1.0)
            nw, nh = int(w * scale), int(h * scale)
            x = (max_w - nw) // 2
            y = (max_h - nh) // 2
            pil_img = pil_img.resize((nw, nh), Image.Resampling.LANCZOS)
            dib = ImageWin.Dib(pil_img)
            dc.StartPage()
            dib.draw(dc.GetHandleOutput(), (0, 0, nw, nh))
            dc.EndPage()
        doc.close()
        dc.EndDoc()
        dc.DeleteDC()
        return True, "Printed (no dialog)"
    except Exception as e:
        return False, str(e)


def print_raw_text_to_printer(text, printer_name=None):
    """Send raw text via win32print.WritePrinter. Tries default printer if configured one fails."""
    if os.name != 'nt':
        return False, "Windows only"
    try:
        import win32print
    except ImportError:
        return False, "pywin32 not available. Run Django with: .venv\\Scripts\\python manage.py runserver"
    if isinstance(text, str):
        data = text.encode('utf-8', errors='replace')
    else:
        data = text
    candidates = [(printer_name or "").strip(), win32print.GetDefaultPrinter()]
    candidates = [n for n in candidates if n]
    last_err = None
    for name in candidates:
        try:
            hprinter = win32print.OpenPrinter(name)
            try:
                win32print.StartDocPrinter(hprinter, 1, ("Invoice", None, "RAW"))
                try:
                    win32print.StartPagePrinter(hprinter)
                    win32print.WritePrinter(hprinter, data)
                    win32print.EndPagePrinter(hprinter)
                finally:
                    win32print.EndDocPrinter(hprinter)
            finally:
                win32print.ClosePrinter(hprinter)
            return True, "Printed"
        except Exception as e:
            last_err = str(e)
    return False, last_err or "Unable to open printer"


try:
    import pdfkit
except ImportError:
    pdfkit = None

WKHTMLTOPDF_PATHS = [
    r'C:\Program Files\wkhtmltopdf\bin\wkhtmltopdf.exe',
    r'C:\Program Files (x86)\wkhtmltopdf\bin\wkhtmltopdf.exe',
    'wkhtmltopdf',
]


def get_wkhtmltopdf_config():
    if not pdfkit:
        return None
    for path in WKHTMLTOPDF_PATHS:
        if path == 'wkhtmltopdf':
            if shutil.which('wkhtmltopdf'):
                try:
                    return pdfkit.configuration(wkhtmltopdf='wkhtmltopdf')
                except Exception:
                    continue
        elif os.path.exists(path):
            try:
                return pdfkit.configuration(wkhtmltopdf=path)
            except Exception:
                continue
    return None


def get_pdf_options(printer_type):
    """Return pdfkit options for portrait, correct page size."""
    pt = (printer_type or 'thermal_80mm').strip().lower()
    opts = {'orientation': 'Portrait', 'quiet': ''}
    if pt == 'a4':
        opts['page-size'] = 'A4'
        opts['margin-top'] = '10mm'
        opts['margin-bottom'] = '10mm'
        opts['margin-left'] = '12mm'
        opts['margin-right'] = '12mm'
    elif pt == 'thermal_58mm':
        opts['page-width'] = '58mm'
        opts['page-height'] = '297mm'
        opts['margin-top'] = '5mm'
        opts['margin-bottom'] = '5mm'
        opts['margin-left'] = '5mm'
        opts['margin-right'] = '5mm'
    else:
        opts['page-width'] = '80mm'
        opts['page-height'] = '297mm'
        opts['margin-top'] = '5mm'
        opts['margin-bottom'] = '5mm'
        opts['margin-left'] = '5mm'
        opts['margin-right'] = '5mm'
    return opts


def print_pdf_silent(pdf_path, printer_name=None):
    """Print PDF without dialog. Portrait, 1 copy. Tries SumatraPDF, then os.startfile."""
    if not os.path.exists(pdf_path):
        return False, "PDF file not found"
    printer_name = (printer_name or "").strip()
    print_settings = "portrait,1x,fit"
    sumatra_paths = [
        r'C:\Program Files\SumatraPDF\SumatraPDF.exe',
        r'C:\Program Files (x86)\SumatraPDF\SumatraPDF.exe',
    ]
    sumatra_exe = None
    for p in sumatra_paths:
        if os.path.exists(p):
            sumatra_exe = p
            break
    if not sumatra_exe and shutil.which('SumatraPDF'):
        sumatra_exe = 'SumatraPDF'
    if sumatra_exe:
        try:
            cmd = [sumatra_exe, '-print-to-default', '-silent', '-print-settings', print_settings, pdf_path]
            if printer_name:
                cmd = [sumatra_exe, '-print-to', printer_name, '-silent', '-print-settings', print_settings, pdf_path]
            flags = 0x08000000 if os.name == 'nt' else 0
            subprocess.run(cmd, timeout=15, creationflags=flags)
            return True, "Printed via SumatraPDF"
        except Exception:
            pass
    try:
        os.startfile(pdf_path, "print")
        return True, "Print sent"
    except Exception as e:
        return False, str(e)
