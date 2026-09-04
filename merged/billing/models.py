from django.db import models
from django.core.validators import MinValueValidator
from decimal import Decimal
from django.core.exceptions import ValidationError
from django.utils import timezone

# Create your models here.


class ProductCategory(models.Model):
    name = models.CharField(max_length=200, unique=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class Product(models.Model):
    PRODUCT_TYPES = [
        ('rent', 'Rental'),
        ('sale', 'Sale'),
    ]
    UOM_CHOICES = [
        ('unit', 'Units / Pieces'),
        ('mg', 'Milligram (mg)'),
        ('g', 'Gram (g)'),
        ('kg', 'Kg'),
    ]
    
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    cost_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    type = models.CharField(max_length=10, choices=PRODUCT_TYPES, default='sale')
    uom = models.CharField(max_length=10, choices=UOM_CHOICES, default='unit')
    daily_rental_rate = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    sku = models.CharField(max_length=50, unique=True)
    hsn_code = models.CharField(max_length=20, blank=True)
    gst_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    category = models.ForeignKey(
        ProductCategory,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='products',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if self.type == 'rent' and not self.daily_rental_rate:
            self.daily_rental_rate = self.price * Decimal('0.05')
        super().save(*args, **kwargs)

    class Meta:
        ordering = ['-created_at']

class Stock(models.Model):
    product = models.OneToOneField(Product, on_delete=models.CASCADE, related_name='stock')
    quantity = models.DecimalField(max_digits=12, decimal_places=3, default=0, validators=[MinValueValidator(0)])
    low_stock_threshold = models.DecimalField(max_digits=12, decimal_places=3, default=10, validators=[MinValueValidator(0)])
    created_at = models.DateTimeField(auto_now_add=True, null=True)
    updated_at = models.DateTimeField(auto_now=True, null=True)

    def __str__(self):
        return f"{self.product.name} - {self.quantity}"

    def is_low_stock(self):
        return self.quantity <= self.low_stock_threshold


class Supplier(models.Model):
    GST_TYPES = (
        ('registered', 'Registered'),
        ('unregistered', 'Unregistered'),
        ('composition', 'Composition'),
    )
    name = models.CharField(max_length=200)
    gstin = models.CharField(max_length=15, blank=True)
    gst_type = models.CharField(max_length=20, choices=GST_TYPES, default='registered')
    contact_person = models.CharField(max_length=200, blank=True)
    phone = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    address = models.TextField(blank=True)
    state = models.CharField(max_length=100, blank=True)
    state_code = models.CharField(max_length=2, blank=True)
    payment_terms = models.CharField(max_length=50, blank=True, default='30 Days')
    notes = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        gstin = (self.gstin or '').strip().upper()
        self.gstin = gstin
        if gstin and len(gstin) >= 2:
            self.state_code = gstin[:2]
        super().save(*args, **kwargs)


class PurchaseOrder(models.Model):
    STATUS_CHOICES = (
        ('draft', 'Draft'),
        ('ordered', 'Ordered'),
        ('partially_received', 'Partially Received'),
        ('received', 'Fully Received'),
        ('cancelled', 'Cancelled'),
        ('closed', 'Closed'),
    )
    PAYMENT_TERM_CHOICES = (
        ('advance', 'Advance'),
        ('cod', 'Cash on Delivery'),
        ('7', '7 Days'),
        ('15', '15 Days'),
        ('30', '30 Days'),
        ('45', '45 Days'),
        ('60', '60 Days'),
        ('custom', 'Custom'),
    )

    order_number = models.CharField(max_length=50, unique=True)
    supplier = models.ForeignKey('Supplier', on_delete=models.SET_NULL, null=True, blank=True, related_name='purchase_orders')
    supplier_name = models.CharField(max_length=200)
    supplier_phone = models.CharField(max_length=50, blank=True)
    supplier_address = models.TextField(blank=True)
    supplier_gstin = models.CharField(max_length=15, blank=True)
    order_date = models.DateField(default=timezone.localdate)
    expected_delivery_date = models.DateField(null=True, blank=True)
    received_date = models.DateField(null=True, blank=True)
    warehouse = models.CharField(max_length=200, blank=True)
    payment_terms = models.CharField(max_length=20, default='30')
    payment_due_date = models.DateField(null=True, blank=True)
    payment_notes = models.CharField(max_length=255, blank=True)
    reference_number = models.CharField(max_length=100, blank=True)
    delivery_address = models.TextField(blank=True)
    transporter = models.CharField(max_length=200, blank=True)
    vehicle_number = models.CharField(max_length=50, blank=True)
    lr_number = models.CharField(max_length=100, blank=True)
    delivery_instructions = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    is_interstate = models.BooleanField(default=False)
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    discount_total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    taxable_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    cgst_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    sgst_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    igst_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    other_charges = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    extra_charges = models.JSONField(default=list, blank=True)
    round_off = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    notes = models.TextField(blank=True)
    terms = models.TextField(blank=True)
    cancelled_reason = models.TextField(blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"PO {self.order_number} - {self.supplier_name}"

    def calculate_totals(self, update_status=True):
        from .procurement import money
        items = list(self.items.all())
        subtotal = sum((item.quantity * item.unit_cost for item in items), Decimal('0'))
        discount_total = sum((item.discount for item in items), Decimal('0'))
        taxable = sum((item.taxable_amount for item in items), Decimal('0'))
        cgst = sum((item.cgst for item in items), Decimal('0'))
        sgst = sum((item.sgst for item in items), Decimal('0'))
        igst = sum((item.igst for item in items), Decimal('0'))
        extra = Decimal('0')
        extra_cgst = Decimal('0')
        extra_sgst = Decimal('0')
        extra_igst = Decimal('0')
        for ch in (self.extra_charges or []):
            extra += Decimal(str(ch.get('amount') or 0))
            extra_cgst += Decimal(str(ch.get('cgst') or 0))
            extra_sgst += Decimal(str(ch.get('sgst') or 0))
            extra_igst += Decimal(str(ch.get('igst') or 0))
        self.subtotal = money(subtotal)
        self.discount_total = money(discount_total)
        self.taxable_amount = money(taxable)
        self.cgst_amount = money(cgst + extra_cgst)
        self.sgst_amount = money(sgst + extra_sgst)
        self.igst_amount = money(igst + extra_igst)
        self.other_charges = money(extra)
        grand = money(
            self.taxable_amount + self.cgst_amount + self.sgst_amount + self.igst_amount + self.other_charges + self.round_off
        )
        self.total_amount = grand
        self.save(update_fields=[
            'subtotal', 'discount_total', 'taxable_amount', 'cgst_amount', 'sgst_amount',
            'igst_amount', 'other_charges', 'total_amount', 'updated_at',
        ])


class PurchaseOrderItem(models.Model):
    purchase_order = models.ForeignKey(PurchaseOrder, related_name='items', on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.PROTECT, null=True, blank=True)
    raw_material = models.ForeignKey('RawMaterial', on_delete=models.PROTECT, null=True, blank=True, related_name='po_items')
    hsn_code = models.CharField(max_length=20, blank=True)
    specification = models.CharField(max_length=200, blank=True)
    uom = models.CharField(max_length=10, default='kg')
    quantity = models.DecimalField(max_digits=12, decimal_places=3, validators=[MinValueValidator(Decimal('0.001'))])
    received_quantity = models.DecimalField(max_digits=12, decimal_places=3, default=0)
    unit_cost = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal('0'))])
    discount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    taxable_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    gst_rate = models.DecimalField(max_digits=5, decimal_places=2, default=18)
    cgst = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    sgst = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    igst = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        name = self.raw_material.name if self.raw_material_id else (self.product.name if self.product_id else 'Item')
        return f"{self.purchase_order.order_number} - {name} x{self.quantity}"

    @property
    def remaining_quantity(self):
        return max(Decimal('0'), Decimal(str(self.quantity)) - Decimal(str(self.received_quantity or 0)))

    def save(self, *args, **kwargs):
        recalc = kwargs.pop('recalc_po', True)
        super().save(*args, **kwargs)
        if recalc:
            self.purchase_order.calculate_totals()


class PurchaseReceipt(models.Model):
    receipt_number = models.CharField(max_length=50, unique=True)
    purchase_order = models.ForeignKey(PurchaseOrder, on_delete=models.PROTECT, related_name='receipts')
    supplier = models.ForeignKey(Supplier, on_delete=models.SET_NULL, null=True, blank=True)
    receipt_date = models.DateField(default=timezone.localdate)
    warehouse = models.CharField(max_length=200, blank=True)
    received_by = models.CharField(max_length=100, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.receipt_number


class PurchaseReceiptItem(models.Model):
    receipt = models.ForeignKey(PurchaseReceipt, on_delete=models.CASCADE, related_name='items')
    po_item = models.ForeignKey(PurchaseOrderItem, on_delete=models.PROTECT, related_name='receipt_lines')
    raw_material = models.ForeignKey('RawMaterial', on_delete=models.PROTECT, null=True, blank=True)
    quantity = models.DecimalField(max_digits=12, decimal_places=3, validators=[MinValueValidator(Decimal('0.001'))])
    unit_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    batch_number = models.CharField(max_length=100, blank=True)
    supplier_batch_number = models.CharField(max_length=100, blank=True)
    mfg_date = models.DateField(null=True, blank=True)
    expiry_date = models.DateField(null=True, blank=True)
    location = models.CharField(max_length=100, blank=True)

    def __str__(self):
        return f"{self.receipt.receipt_number} +{self.quantity}"

class BackupHistory(models.Model):
    TYPE_CHOICES = [('backup', 'Backup'), ('restore', 'Restore')]
    STATUS_CHOICES = [('success', 'Success'), ('failed', 'Failed'), ('in_progress', 'In Progress')]
    date = models.DateTimeField(auto_now_add=True)
    type = models.CharField(max_length=10, choices=TYPE_CHOICES)
    location = models.CharField(max_length=255)
    size = models.CharField(max_length=50)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES)
    details = models.TextField(blank=True)
    file_path = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ['-date']


class Invoice(models.Model):

    INVOICE_STATUS = (
        ('draft', 'Draft'),
        ('credit', 'Credit'),
        ('partially_paid', 'Partially Paid'),
        ('paid', 'Paid'),
        ('cancelled', 'Cancelled'),
    )

    invoice_number = models.CharField(max_length=50, unique=True)
    # Allow blank customer name for privacy / walk‑in customers
    customer_name = models.CharField(max_length=200, blank=True)
    customer_phone = models.CharField(max_length=20, blank=True, help_text='For A/R ledger matching')
    customer_address = models.TextField(blank=True)
    customer_gstin = models.CharField(max_length=15, blank=True)
    customer_state = models.CharField(max_length=100, blank=True, help_text='Place of supply (customer state)')
    invoice_date = models.DateField()
    due_date = models.DateField()
    status = models.CharField(max_length=20, choices=INVOICE_STATUS, default='draft')

    subtotal = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    cgst_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    sgst_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    igst_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    advance_paid = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    outstanding_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Invoice {self.invoice_number}"

    def resolved_customer_state(self):
        state = (self.customer_state or '').strip()
        if state:
            return state
        name = (self.customer_name or '').strip()
        if not name:
            return ''
        qs = Customer.objects.filter(name=name)
        phone = (self.customer_phone or '').strip()
        cust = qs.filter(phone=phone).first() if phone else None
        if not cust:
            cust = qs.first()
        return (cust.state or '') if cust else ''

    def sale_is_interstate(self):
        from .procurement import is_interstate
        settings = CompanySettings.objects.first()
        return is_interstate(
            self.customer_gstin or '',
            (settings.gstin or '') if settings else '',
            self.resolved_customer_state(),
            (settings.state or '') if settings else '',
        )

    def calculate_totals(self, update_status=True):
        from .procurement import calc_line, money

        items = list(self.items.select_related('product').all())
        settings = CompanySettings.objects.first()
        default_gst = settings.gst_percentage if settings and settings.gst_percentage is not None else Decimal('0')
        interstate = self.sale_is_interstate()

        subtotal = Decimal('0')
        cgst = Decimal('0')
        sgst = Decimal('0')
        igst = Decimal('0')
        for item in items:
            rate = default_gst
            if item.gst_rate is not None:
                rate = item.gst_rate
            elif item.product_id and item.product.gst_rate is not None:
                rate = item.product.gst_rate
            line = calc_line(item.quantity, item.unit_price, item.discount or 0, rate, interstate)
            subtotal += line['taxable_amount']
            cgst += line['cgst']
            sgst += line['sgst']
            igst += line['igst']

        self.subtotal = money(subtotal)
        self.cgst_amount = money(cgst)
        self.sgst_amount = money(sgst)
        self.igst_amount = money(igst)
        self.total_amount = money(self.subtotal + self.cgst_amount + self.sgst_amount + self.igst_amount)
        self.outstanding_amount = money(self.total_amount - (self.advance_paid or 0))
        if not (self.customer_state or '').strip():
            resolved = self.resolved_customer_state()
            if resolved:
                self.customer_state = resolved

        if update_status:
            if self.outstanding_amount <= 0:
                self.status = 'paid'
            elif self.advance_paid == 0:
                self.status = 'credit'
            else:
                self.status = 'partially_paid'

        self.save()

    @property
    def gst_total(self):
        from .procurement import money
        return money((self.cgst_amount or 0) + (self.sgst_amount or 0) + (self.igst_amount or 0))


class Token(Invoice):
    """Proxy model for admin: invoices that have a token_number (kitchen tokens)."""
    class Meta:
        proxy = True
        verbose_name = 'Token'
        verbose_name_plural = 'Tokens'


class InvoiceItem(models.Model):
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.IntegerField(validators=[MinValueValidator(1)], default=1)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    total = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0, blank=True)
    description = models.TextField(blank=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2, default=0, blank=True)
    days = models.IntegerField(default=1, blank=True)
    discount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    gst_rate = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if self.quantity and self.unit_price:
            taxable = Decimal(str(self.quantity)) * self.unit_price - (self.discount or 0)
            if taxable < 0:
                taxable = Decimal('0')
            self.total = taxable
            self.total_amount = self.total
        super().save(*args, **kwargs)

    def effective_gst_rate(self):
        if self.gst_rate is not None:
            return self.gst_rate
        if self.product_id and self.product.gst_rate is not None:
            return self.product.gst_rate
        return Decimal('0')

    def line_taxable(self):
        taxable = Decimal(str(self.quantity or 0)) * (self.unit_price or 0) - (self.discount or 0)
        return taxable if taxable > 0 else Decimal('0')

    def line_breakup(self):
        from .procurement import calc_line
        interstate = False
        if self.invoice_id:
            if (self.invoice.igst_amount or 0) > 0:
                interstate = True
            elif (self.invoice.cgst_amount or 0) > 0 or (self.invoice.sgst_amount or 0) > 0:
                interstate = False
            else:
                interstate = self.invoice.sale_is_interstate()
        return calc_line(
            self.quantity, self.unit_price, self.discount or 0, self.effective_gst_rate(), interstate
        )

    def line_cgst(self):
        return self.line_breakup()['cgst']

    def line_sgst(self):
        return self.line_breakup()['sgst']

    def line_igst(self):
        return self.line_breakup()['igst']

    def line_total_with_gst(self):
        return self.line_breakup()['total']

    def disc_percent(self):
        gross = Decimal(str(self.quantity or 0)) * (self.unit_price or 0)
        if gross <= 0:
            return Decimal('0')
        return ((self.discount or 0) * Decimal('100')) / gross

    def __str__(self):
        return f"{self.invoice.invoice_number} - {self.product.name}"


class Customer(models.Model):
    name = models.CharField(max_length=200)
    phone = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    address = models.TextField(blank=True)
    state = models.CharField(max_length=100, default='', help_text='Required when creating a customer')
    city = models.CharField(max_length=100, blank=True)
    pincode = models.CharField(max_length=10, blank=True)
    gstin = models.CharField(max_length=15, blank=True, help_text='Customer GSTIN (optional)')
    outstanding_balance = models.DecimalField(
        max_digits=12, decimal_places=2, default=0,
        help_text='Total amount owed by customer (A/R)'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        unique_together = [['name', 'phone']]

    def __str__(self):
        return f"{self.name} ({self.phone or 'No phone'})"

    def update_balance(self):
        last_entry = self.ledger_entries.order_by('-id').first()
        self.outstanding_balance = last_entry.balance_after if last_entry else Decimal('0')
        self.save(update_fields=['outstanding_balance', 'updated_at'])


class PaymentReceived(models.Model):
    """Record payments received from customers against outstanding credit."""
    PAYMENT_METHODS = (
        ('cash', 'Cash'),
        ('upi', 'UPI'),
        ('bank_transfer', 'Bank Transfer'),
        ('card', 'Card'),
        ('other', 'Other'),
    )
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='payments_received')
    invoice = models.ForeignKey(
        Invoice, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='payments_received',
        help_text='Optional: link to specific invoice'
    )
    amount = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal('0.01'))])
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHODS, default='cash')
    payment_date = models.DateField(default=timezone.localdate)
    notes = models.TextField(blank=True)
    reference_number = models.CharField(max_length=100, blank=True, help_text='Cheque no, UPI ref, etc.')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-payment_date', '-id']
        verbose_name_plural = 'Payments received'

    def __str__(self):
        return f"Rs{self.amount} from {self.customer.name} on {self.payment_date}"


class CustomerLedgerEntry(models.Model):
    ENTRY_TYPES = (
        ('invoice', 'Invoice / Bill'),
        ('payment', 'Payment Received'),
        ('adjustment', 'Adjustment'),
    )
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='ledger_entries')
    invoice = models.ForeignKey(
        Invoice, on_delete=models.SET_NULL, null=True, blank=True, related_name='ledger_entries'
    )
    entry_type = models.CharField(max_length=20, choices=ENTRY_TYPES)
    debit = models.DecimalField(max_digits=12, decimal_places=2, default=0, help_text='Amount added to balance (bill)')
    credit = models.DecimalField(max_digits=12, decimal_places=2, default=0, help_text='Amount deducted from balance (payment)')
    balance_after = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    entry_date = models.DateField(default=timezone.localdate)
    description = models.CharField(max_length=500, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-entry_date', '-id']
        verbose_name_plural = 'Customer ledger entries'

    def __str__(self):
        return f"{self.customer.name} - {self.entry_type} {self.entry_date}"


class CompanySettings(models.Model):
    company_name = models.CharField(max_length=200)
    address_line1 = models.CharField(max_length=200)
    address_line2 = models.CharField(max_length=200, blank=True)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    postal_code = models.CharField(max_length=20)
    phone = models.CharField(max_length=50)
    email = models.EmailField()
    website = models.URLField(blank=True)
    gstin = models.CharField(max_length=15, blank=True)
    gst_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=5.00,
                                       help_text="Default GST percentage used on invoices, products, and purchase orders")
    dues_days = models.IntegerField(default=7, help_text='Default number of days for invoice due date (used when creating invoices)')
    pan_number = models.CharField(max_length=10, blank=True)
    bank_name = models.CharField(max_length=200, blank=True)
    bank_account_number = models.CharField(max_length=50, blank=True)
    bank_ifsc = models.CharField(max_length=20, blank=True)
    invoice_footer_text = models.TextField(blank=True)
    min_rental_days = models.IntegerField(default=1, help_text='Minimum number of days for rental')
    max_rental_days = models.IntegerField(default=30, help_text='Maximum number of days for rental')
    default_rental_days = models.IntegerField(default=7, help_text='Default number of days for rental')
    daily_late_fee = models.DecimalField(max_digits=5, decimal_places=2, default=5.0, help_text='Daily late fee percentage')
    grace_period = models.IntegerField(default=1, help_text='Grace period in days before late fees apply')
    max_late_fee = models.DecimalField(max_digits=5, decimal_places=2, default=100.0, help_text='Maximum late fee percentage')
    security_deposit_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=50.0, help_text='Security deposit as percentage of rental value')
    min_security_deposit = models.DecimalField(max_digits=10, decimal_places=2, default=100.0, help_text='Minimum security deposit amount')
    max_security_deposit = models.DecimalField(max_digits=10, decimal_places=2, default=1000.0, help_text='Maximum security deposit amount')
    weekly_discount = models.DecimalField(max_digits=5, decimal_places=2, default=5.0, help_text='Discount percentage for weekly rentals')
    monthly_discount = models.DecimalField(max_digits=5, decimal_places=2, default=10.0, help_text='Discount percentage for monthly rentals')
    max_discount = models.DecimalField(max_digits=5, decimal_places=2, default=20.0, help_text='Maximum discount percentage')

    # Printer Settings (used when printing invoices)
    PRINTER_TYPE_CHOICES = (
        ('thermal_80mm', 'Thermal 80mm (e.g. POS-80)'),
        ('thermal_58mm', 'Thermal 58mm'),
        ('a4', 'A4 / Letter (standard)'),
    )
    printer_type = models.CharField(
        max_length=20,
        choices=PRINTER_TYPE_CHOICES,
        default='thermal_80mm',
        help_text='Invoice layout when printing'
    )
    printer_name = models.CharField(
        max_length=200,
        blank=True,
        help_text='Exact Windows printer name (e.g. "POS-80 Series Printer"). Leave blank to use default printer.'
    )
    auto_print_dialog = models.BooleanField(
        default=True,
        help_text='When enabled, print dialog opens automatically when you click Print (one less step).'
    )
    use_direct_print = models.BooleanField(
        default=False,
        help_text='When enabled, bills print silently to configured printer (no dialog). Requires local print service to be running.'
    )
    print_service_url = models.CharField(
        max_length=255,
        blank=True,
        default='http://localhost:8765',
        help_text='URL of the local print service (e.g. http://localhost:8765). Only used when Direct Print is enabled.'
    )
    print_bill_enabled = models.BooleanField(
        default=True,
        help_text='When on, bill/invoice is included when printing.'
    )

    class Meta:
        verbose_name = 'Company Settings'
        verbose_name_plural = 'Company Settings'


class RawMaterial(models.Model):
    UNIT_CHOICES = [
        ('mg', 'Milligram (mg)'),
        ('g', 'Gram (g)'),
        ('kg', 'Kilogram (kg)'),
        ('l', 'Liter (l)'),
        ('ml', 'Milliliter (ml)'),
        ('unit', 'Units/Pieces'),
    ]

    material_code = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=200)
    category = models.CharField(max_length=100, default='Herbs')
    unit = models.CharField(max_length=10, choices=UNIT_CHOICES, default='g')
    current_stock = models.DecimalField(max_digits=12, decimal_places=3, default=0, validators=[MinValueValidator(0)])
    minimum_stock = models.DecimalField(max_digits=12, decimal_places=3, default=5, validators=[MinValueValidator(0)])
    purchase_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    supplier = models.CharField(max_length=200, blank=True)
    batch_number = models.CharField(max_length=100, blank=True)
    expiry_date = models.DateField(null=True, blank=True)
    location = models.CharField(max_length=100, blank=True)
    notes = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    hsn_code = models.CharField(max_length=20, blank=True)
    gst_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return f"{self.name} ({self.material_code})"

    def is_low_stock(self):
        return self.current_stock <= self.minimum_stock


class Recipe(models.Model):
    """Bill of Materials (BOM) for manufacturing Finished Ayurvedic Products."""
    product = models.OneToOneField(Product, on_delete=models.CASCADE, related_name='recipe')
    yield_quantity = models.DecimalField(max_digits=10, decimal_places=2, default=1, help_text="Units of product created per batch")
    extra_charges = models.JSONField(default=list, blank=True, help_text="Dynamic recipe charges e.g. labour, electricity")
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"BOM for {self.product.name}"


def convert_quantity_units(qty, from_unit, to_unit):
    """Convert mass (kg/g/mg) or volume (l/ml) quantities. Unknown pairs are returned unchanged."""
    from_unit = (from_unit or '').lower()
    to_unit = (to_unit or '').lower()
    if not from_unit or not to_unit or from_unit == to_unit:
        return qty
    mass = {'kg': Decimal('1000000'), 'g': Decimal('1000'), 'mg': Decimal('1')}
    volume = {'l': Decimal('1000'), 'ml': Decimal('1')}
    qty = Decimal(str(qty))
    if from_unit in mass and to_unit in mass:
        return qty * mass[from_unit] / mass[to_unit]
    if from_unit in volume and to_unit in volume:
        return qty * volume[from_unit] / volume[to_unit]
    return qty


class RecipeItem(models.Model):
    recipe = models.ForeignKey(Recipe, on_delete=models.CASCADE, related_name='items')
    raw_material = models.ForeignKey(RawMaterial, on_delete=models.CASCADE)
    quantity_required = models.DecimalField(
        max_digits=14, decimal_places=6, validators=[MinValueValidator(Decimal('0.000001'))]
    )
    input_unit = models.CharField(max_length=10, blank=True, help_text="Unit the user entered (e.g. g, ml)")

    def __str__(self):
        return f"{self.recipe.product.name} needs {self.quantity_required} {self.raw_material.unit} of {self.raw_material.name}"


class ManufacturingLog(models.Model):
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]

    manufacturing_id = models.CharField(max_length=50, unique=True)
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    recipe = models.ForeignKey(Recipe, on_delete=models.SET_NULL, null=True, blank=True)
    production_quantity = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal('0.01'))])
    batch_number = models.CharField(max_length=100)
    mfg_date = models.DateField(default=timezone.localdate)
    exp_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='completed')
    operator = models.CharField(max_length=100, blank=True)
    raw_material_cost = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    labor_cost = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    packaging_cost = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    other_overhead_cost = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_cost = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    unit_cost = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.manufacturing_id} - {self.product.name} ({self.production_quantity} units)"


class ManufacturingItemLog(models.Model):
    manufacturing = models.ForeignKey(ManufacturingLog, on_delete=models.CASCADE, related_name='consumed_items')
    raw_material = models.ForeignKey(RawMaterial, on_delete=models.PROTECT)
    quantity_consumed = models.DecimalField(max_digits=12, decimal_places=3)
    unit_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_cost = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    def __str__(self):
        return f"{self.manufacturing.manufacturing_id}: Consumed {self.quantity_consumed} of {self.raw_material.name}"


class ProductBatch(models.Model):
    """Finished-goods remaining stock attributed to a manufacturing batch."""
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='batches')
    manufacturing = models.OneToOneField(
        ManufacturingLog, on_delete=models.CASCADE, related_name='finished_batch', null=True, blank=True
    )
    batch_number = models.CharField(max_length=100)
    produced_quantity = models.DecimalField(max_digits=12, decimal_places=3, default=0)
    remaining_quantity = models.DecimalField(max_digits=12, decimal_places=3, default=0, validators=[MinValueValidator(0)])
    mfg_date = models.DateField(null=True, blank=True)
    exp_date = models.DateField(null=True, blank=True)
    unit_cost = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['mfg_date', 'id']

    def __str__(self):
        return f"{self.batch_number} · {self.product.name} · {self.remaining_quantity} left"


def consume_product_batches(product, qty):
    """FIFO deduct remaining finished-goods from the oldest batches."""
    remaining = Decimal(str(qty or 0))
    if remaining <= 0:
        return
    batches = ProductBatch.objects.select_for_update().filter(
        product=product, remaining_quantity__gt=0
    ).order_by('mfg_date', 'id')
    for batch in batches:
        if remaining <= 0:
            break
        take = min(batch.remaining_quantity, remaining)
        batch.remaining_quantity = batch.remaining_quantity - take
        batch.save(update_fields=['remaining_quantity'])
        remaining -= take


def restore_product_batches(product, qty):
    """Put cancelled sale qty back into newest batches that still have room."""
    remaining = Decimal(str(qty or 0))
    if remaining <= 0:
        return
    batches = ProductBatch.objects.select_for_update().filter(product=product).order_by('-mfg_date', '-id')
    for batch in batches:
        if remaining <= 0:
            break
        space = (batch.produced_quantity or Decimal('0')) - (batch.remaining_quantity or Decimal('0'))
        if space <= 0:
            continue
        add = min(space, remaining)
        batch.remaining_quantity = batch.remaining_quantity + add
        batch.save(update_fields=['remaining_quantity'])
        remaining -= add


class StockMovementLog(models.Model):
    ITEM_TYPE_CHOICES = [
        ('raw_material', 'Raw Material'),
        ('finished_product', 'Finished Product'),
    ]
    MOVEMENT_TYPE_CHOICES = [
        ('opening_stock', 'Opening Stock'),
        ('purchase', 'Purchase Entry'),
        ('manufacturing_consumption', 'Manufacturing Consumption'),
        ('manufacturing_output', 'Manufacturing Output'),
        ('sale', 'Invoice Sale'),
        ('sale_cancellation', 'Sale Restored / Cancelled'),
        ('adjustment', 'Manual Adjustment'),
        ('return', 'Return'),
    ]

    item_type = models.CharField(max_length=20, choices=ITEM_TYPE_CHOICES)
    raw_material = models.ForeignKey(RawMaterial, on_delete=models.SET_NULL, null=True, blank=True, related_name='movements')
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True, blank=True, related_name='movements')
    movement_type = models.CharField(max_length=30, choices=MOVEMENT_TYPE_CHOICES)
    quantity = models.DecimalField(max_digits=12, decimal_places=3)
    previous_balance = models.DecimalField(max_digits=12, decimal_places=3, default=0)
    new_balance = models.DecimalField(max_digits=12, decimal_places=3, default=0)
    unit_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    reference_id = models.CharField(max_length=100, blank=True)
    reason = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        item_name = self.raw_material.name if self.raw_material else (self.product.name if self.product else 'Item')
        return f"{self.movement_type} | {item_name} | Qty: {self.quantity}"