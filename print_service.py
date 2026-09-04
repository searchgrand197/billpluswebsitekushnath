"""
Local Print Service for BMS
Sends invoices directly to the configured printer without showing a dialog.
Run this script alongside your Django app when using Direct Print.

Usage: python print_service.py
       (Run from the project root, with venv activated)

The service listens on http://localhost:8765 by default.
"""

import os
import sys
import tempfile
import subprocess
import shutil

# Add project to path and setup Django
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'billmanageement.settings')

try:
    import django
    django.setup()
except Exception as e:
    print("Error: Could not setup Django. Run from project root with venv activated.")
    print(e)
    sys.exit(1)

# Now we can import Django stuff
from django.template.loader import render_to_string
from django.conf import settings as django_settings
from billing.models import Invoice, CompanySettings, PaymentReceived
from num2words import num2words
from decimal import Decimal

# Try flask for HTTP server
try:
    from flask import Flask, request, jsonify
except ImportError:
    print("Installing Flask... (pip install flask)")
    subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'flask'])
    from flask import Flask, request, jsonify

# Try pdfkit for HTML to PDF
try:
    import pdfkit
except ImportError:
    print("Installing pdfkit... (pip install pdfkit)")
    subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'pdfkit'])
    import pdfkit

app = Flask(__name__)

# Allow CORS from localhost (Django app)
@app.after_request
def add_cors(response):
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'POST, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
    return response

# Find wkhtmltopdf
WKHTMLTOPDF_PATHS = [
    r'C:\Program Files\wkhtmltopdf\bin\wkhtmltopdf.exe',
    r'C:\Program Files (x86)\wkhtmltopdf\bin\wkhtmltopdf.exe',
    'wkhtmltopdf',  # if in PATH
]

def get_wkhtmltopdf_config():
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

def print_pdf_silent(pdf_path, printer_name=None):
    """Print PDF without dialog. Portrait, 1 copy, no popup. Tries SumatraPDF first."""
    if not os.path.exists(pdf_path):
        return False, "PDF file not found"
    
    printer_name = (printer_name or "").strip()
    # SumatraPDF: portrait orientation, 1 copy, fit to page - no dialog
    print_settings = "portrait,1x,fit"
    
    # Try SumatraPDF (silent print) - common for receipt/thermal printing
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
            flags = 0x08000000 if os.name == 'nt' else 0  # CREATE_NO_WINDOW on Windows
            subprocess.run(cmd, timeout=15, creationflags=flags)
            return True, "Printed via SumatraPDF"
        except Exception:
            pass  # fall through to os.startfile
    
    # Fallback: os.startfile with "print" - may show dialog on some systems
    try:
        os.startfile(pdf_path, "print")
        return True, "Print sent (may show dialog)"
    except Exception as e:
        return False, str(e)

def get_pdf_options(printer_type):
    """Return pdfkit options for portrait, 1 copy, correct page size."""
    pt = (printer_type or 'thermal_80mm').strip().lower()
    opts = {'orientation': 'Portrait', 'quiet': ''}
    if pt == 'a4':
        opts['page-size'] = 'A4'
        opts['margin-top'] = '10mm'
        opts['margin-bottom'] = '10mm'
        opts['margin-left'] = '10mm'
        opts['margin-right'] = '10mm'
    elif pt == 'thermal_58mm':
        opts['page-width'] = '58mm'
        opts['page-height'] = '297mm'
        opts['margin-top'] = '5mm'
        opts['margin-bottom'] = '5mm'
        opts['margin-left'] = '5mm'
        opts['margin-right'] = '5mm'
    else:
        # thermal_80mm default
        opts['page-width'] = '80mm'
        opts['page-height'] = '297mm'
        opts['margin-top'] = '5mm'
        opts['margin-bottom'] = '5mm'
        opts['margin-left'] = '5mm'
        opts['margin-right'] = '5mm'
    return opts

def render_invoice_html(invoice_id):
    """Render invoice print template to HTML string."""
    invoice = Invoice.objects.get(pk=invoice_id)
    company_settings = CompanySettings.objects.first()
    
    if not company_settings:
        raise ValueError("Company settings not found")
    
    if not invoice.total_amount:
        invoice.calculate_totals()
    
    payments = list(PaymentReceived.objects.filter(invoice=invoice).order_by('-payment_date'))
    
    try:
        amount_in_words = num2words(float(invoice.total_amount), to='currency', lang='en_IN').replace(
            'euro', 'Rupees'
        ).replace('cents', 'paise').title() + " Only"
    except Exception:
        amount_in_words = "Not Provided"
    
    printer_type = getattr(company_settings, 'printer_type', 'thermal_80mm')
    thermal = printer_type in ('thermal_80mm', 'thermal_58mm')
    
    context = {
        'invoice': invoice,
        'company_settings': company_settings,
        'payments': payments,
        'amount_in_words': amount_in_words,
        'thermal': thermal,
        'printer_type': printer_type,
        'auto_print': False,
        'printer_name': getattr(company_settings, 'printer_name', '') or None,
    }
    html = render_to_string('billing/invoice_print.html', context)
    return html

@app.route('/print', methods=['POST', 'OPTIONS'])
def do_print():
    if request.method == 'OPTIONS':
        return '', 204
    
    if request.method != 'POST':
        return jsonify({'success': False, 'message': 'POST required'}), 405
    
    try:
        data = request.get_json() or {}
        invoice_id = data.get('invoice_id')
        printer_name = data.get('printer_name', '').strip()
        
        if not invoice_id:
            return jsonify({'success': False, 'message': 'invoice_id required'}), 400
        
        # Get settings for printer and page layout
        settings = CompanySettings.objects.first()
        if not printer_name and settings:
            printer_name = getattr(settings, 'printer_name', '') or ''
        printer_type = getattr(settings, 'printer_type', 'thermal_80mm') if settings else 'thermal_80mm'
        
        # Render HTML
        html = render_invoice_html(invoice_id)
        
        # Convert to PDF (portrait, correct page size for thermal/A4)
        config = get_wkhtmltopdf_config()
        if not config:
            return jsonify({
                'success': False,
                'message': 'wkhtmltopdf not found. Install from https://wkhtmltopdf.org/downloads.html'
            }), 500
        
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as f:
            pdf_path = f.name
        
        try:
            pdf_options = get_pdf_options(printer_type)
            pdfkit.from_string(html, pdf_path, configuration=config, options=pdf_options)
            ok, msg = print_pdf_silent(pdf_path, printer_name or None)
            if ok:
                return jsonify({'success': True, 'message': msg})
            else:
                return jsonify({'success': False, 'message': msg}), 500
        finally:
            if os.path.exists(pdf_path):
                try:
                    os.unlink(pdf_path)
                except Exception:
                    pass
    
    except Invoice.DoesNotExist:
        return jsonify({'success': False, 'message': 'Invoice not found'}), 404
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'ok', 'service': 'bms-print-service'})

def main():
    port = 8765
    print("=" * 50)
    print("BMS Print Service")
    print("=" * 50)
    print(f"Listening on http://localhost:{port}")
    print("Keep this window open while using Direct Print.")
    print("Press Ctrl+C to stop.")
    print("=" * 50)
    app.run(host='127.0.0.1', port=port, debug=False, use_reloader=False)

if __name__ == '__main__':
    main()
