"""Balance sheet and financial snapshot calculations (shared by API + Django views)."""
from datetime import date
from decimal import Decimal

from django.db.models import F, Sum, Value
from django.db.models.functions import Coalesce
from django.utils import timezone

from .models import (
    CompanySettings,
    Customer,
    Invoice,
    PaymentReceived,
    Product,
    PurchaseOrder,
    RawMaterial,
    Stock,
)
from .procurement import money

FINAL_INVOICE_STATUSES = ('paid', 'credit', 'partially_paid')
OPEN_PO_STATUSES = ('draft', 'ordered', 'partially_received')


def _parse_as_of(value):
    if not value:
        return timezone.localdate()
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value)[:10])
    except (TypeError, ValueError):
        return timezone.localdate()


def _invoice_qs(as_of):
    return Invoice.objects.filter(invoice_date__lte=as_of).exclude(status__in=('cancelled', 'draft'))


def compute_balance_sheet(as_of=None):
    as_of = _parse_as_of(as_of)
    company = CompanySettings.objects.first()

    finished_inventory = Product.objects.aggregate(
        total=Coalesce(
            Sum(F('cost_price') * Coalesce(F('stock__quantity'), Value(Decimal('0')))),
            Value(Decimal('0')),
        )
    )['total'] or Decimal('0')

    raw_inventory = RawMaterial.objects.filter(is_active=True).aggregate(
        total=Coalesce(
            Sum(F('current_stock') * F('purchase_price')),
            Value(Decimal('0')),
        )
    )['total'] or Decimal('0')

    accounts_receivable = Customer.objects.aggregate(
        total=Coalesce(Sum('outstanding_balance'), Value(Decimal('0')))
    )['total'] or Decimal('0')

    cash_collected = PaymentReceived.objects.filter(payment_date__lte=as_of).aggregate(
        total=Coalesce(Sum('amount'), Value(Decimal('0')))
    )['total'] or Decimal('0')

    inv_qs = _invoice_qs(as_of)
    total_sales = inv_qs.aggregate(
        total=Coalesce(Sum('total_amount'), Value(Decimal('0')))
    )['total'] or Decimal('0')

    sales_gst = inv_qs.aggregate(
        total=Coalesce(
            Sum(F('cgst_amount') + F('sgst_amount') + F('igst_amount')),
            Value(Decimal('0')),
        )
    )['total'] or Decimal('0')

    total_outstanding = inv_qs.aggregate(
        total=Coalesce(Sum('outstanding_amount'), Value(Decimal('0')))
    )['total'] or Decimal('0')

    received_po_qs = PurchaseOrder.objects.filter(status='received', order_date__lte=as_of)
    total_purchases = received_po_qs.aggregate(
        total=Coalesce(Sum('total_amount'), Value(Decimal('0')))
    )['total'] or Decimal('0')

    purchase_gst = received_po_qs.aggregate(
        total=Coalesce(
            Sum(F('cgst_amount') + F('sgst_amount') + F('igst_amount')),
            Value(Decimal('0')),
        )
    )['total'] or Decimal('0')

    open_po_qs = PurchaseOrder.objects.filter(status__in=OPEN_PO_STATUSES, order_date__lte=as_of)
    supplier_payables = open_po_qs.aggregate(
        total=Coalesce(Sum('total_amount'), Value(Decimal('0')))
    )['total'] or Decimal('0')

    gst_payable = max(Decimal('0'), money(sales_gst - purchase_gst))
    gst_credit = max(Decimal('0'), money(purchase_gst - sales_gst))

    inventory_finished = money(finished_inventory)
    inventory_raw = money(raw_inventory)
    ar = money(accounts_receivable)
    cash = money(cash_collected)
    payables = money(supplier_payables)

    total_assets = money(inventory_finished + inventory_raw + ar + cash)
    total_liabilities = money(payables + gst_payable)
    owners_equity = money(total_assets - total_liabilities)
    total_equity_side = money(total_liabilities + owners_equity)

    gross_profit = money(total_sales - total_purchases)

    return {
        'as_of': str(as_of),
        'company_name': company.company_name if company else 'Your Business',
        'assets': {
            'items': [
                {'key': 'finished_inventory', 'label': 'Finished Goods Inventory (at cost)', 'amount': str(inventory_finished)},
                {'key': 'raw_inventory', 'label': 'Raw Material Inventory (at cost)', 'amount': str(inventory_raw)},
                {'key': 'accounts_receivable', 'label': 'Accounts Receivable (Customer Dues)', 'amount': str(ar)},
                {'key': 'cash_collected', 'label': 'Cash / Bank (Payments Received)', 'amount': str(cash)},
            ],
            'total': str(total_assets),
        },
        'liabilities': {
            'items': [
                {'key': 'supplier_payables', 'label': 'Supplier Payables (Open Purchase Orders)', 'amount': str(payables)},
                {'key': 'gst_payable', 'label': 'GST Payable (Net Output GST)', 'amount': str(gst_payable)},
            ],
            'total': str(total_liabilities),
        },
        'equity': {
            'items': [
                {'key': 'owners_equity', 'label': "Owner's Equity / Retained Earnings", 'amount': str(owners_equity)},
            ],
            'total': str(owners_equity),
        },
        'totals': {
            'total_assets': str(total_assets),
            'total_liabilities': str(total_liabilities),
            'total_equity': str(owners_equity),
            'liabilities_plus_equity': str(total_equity_side),
            'is_balanced': total_assets == total_equity_side,
        },
        'pl_summary': {
            'total_sales': str(money(total_sales)),
            'total_purchases_received': str(money(total_purchases)),
            'gross_profit': str(gross_profit),
            'total_collections': str(cash),
            'total_outstanding': str(money(total_outstanding)),
            'sales_gst': str(money(sales_gst)),
            'purchase_gst': str(money(purchase_gst)),
            'gst_input_credit': str(gst_credit),
        },
        'notes': [
            'Inventory is valued at cost price (finished goods + raw materials).',
            'Accounts receivable uses customer outstanding balances.',
            'Supplier payables are open PO totals (draft / ordered / partially received).',
            'GST payable is net output GST after purchase GST on received POs.',
            "Owner's equity is the balancing figure (Assets − Liabilities).",
        ],
    }
