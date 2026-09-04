from datetime import timedelta
from django import forms
from django.utils import timezone
from .models import (
    Product,
    ProductCategory,
    Stock,
    Invoice,
    InvoiceItem,
    CompanySettings,
    Customer,
    PaymentReceived,
)
from django.core.validators import MinValueValidator, RegexValidator
from decimal import Decimal



only_letters_validator = RegexValidator(
    regex=r'^[A-Za-z\s]+$',
    message='Use letters and spaces only (no numbers or symbols).',
    code='letters_only',
)


class ProductForm(forms.ModelForm):
    initial_stock = forms.DecimalField(min_value=0, decimal_places=3, required=True)
    low_stock_threshold = forms.DecimalField(min_value=0, decimal_places=3, required=True)

    class Meta:
        model = Product
        fields = [
            'name',
            'description',
            'type',
            'category',
            'uom',
            'cost_price',
            'price',
            'daily_rental_rate',
            'sku',
        ]
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control rounded-3',
                'placeholder': 'Enter product name'
            }),
            'type': forms.Select(attrs={'class': 'form-control rounded-3'}),
            'category': forms.Select(attrs={'class': 'form-control rounded-3'}),
            'uom': forms.Select(attrs={
                'class': 'form-control rounded-3',
            }),
            'cost_price': forms.NumberInput(attrs={
                'min': '0',
                'step': '0.01',
                'class': 'form-control rounded-3',
                'placeholder': 'Enter cost price in Rs'
            }),
            'sku': forms.TextInput(attrs={
                'class': 'form-control rounded-3',
                'placeholder': 'Enter item code'
            }),
            'price': forms.NumberInput(attrs={
                'min': '0',
                'step': '0.01',
                'class': 'form-control rounded-3',
                'placeholder': 'Enter price in Rs'
            }),
            'daily_rental_rate': forms.NumberInput(attrs={
                'min': '0',
                'step': '0.01',
                'class': 'form-control rounded-3',
                'placeholder': 'Enter daily rate in Rs'
            }),
            'description': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['category'].required = False
        self.fields['category'].queryset = ProductCategory.objects.filter(is_active=True).order_by('name')
        self.fields['category'].empty_label = '— No category —'

    def clean(self):
        cleaned_data = super().clean()
        product_type = cleaned_data.get('type')
        daily_rental_rate = cleaned_data.get('daily_rental_rate')
        
        if product_type == 'rent' and not daily_rental_rate:
            price = cleaned_data.get('price')
            if price:
                cleaned_data['daily_rental_rate'] = price * Decimal('0.05')
        
        return cleaned_data

    def save(self, commit=True):
        product = super().save(commit=False)
        if commit:
            product.save()
            # Create associated stock
            Stock.objects.create(
                product=product,
                quantity=self.cleaned_data['initial_stock'],
                low_stock_threshold=self.cleaned_data['low_stock_threshold']
            )
        return product

class StockForm(forms.ModelForm):
    class Meta:
        model = Stock
        fields = ['quantity', 'low_stock_threshold']
        widgets = {
            'quantity': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0'
            }),
            'low_stock_threshold': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0'
            })
        }

class InvoiceForm(forms.ModelForm):
    customer_phone = forms.CharField(
        required=False,
        max_length=10,
        validators=[
            RegexValidator(
                regex=r'^\d{10}$',
                message='Enter a valid 10‑digit mobile number',
                code='invalid_mobile',
            )
        ],
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Phone (for A/R ledger)',
            'maxlength': '10',
            'inputmode': 'numeric',
            'pattern': r'\d*',
        })
    )
    # Optional: strict GSTIN format (15 chars, Indian GST)
    GSTIN_REGEX = r'^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z][1-9A-Z]Z[0-9A-Z]$'

    customer_gstin = forms.CharField(
        required=False,
        max_length=15,
        validators=[
            RegexValidator(
                regex=GSTIN_REGEX,
                message='Enter a valid 15‑character GSTIN (e.g. 27ABCDE1234F1Z5)',
                code='invalid_gstin',
            )
        ],
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter GSTIN (optional)',
            'maxlength': '15',
            'style': 'text-transform: uppercase;',
        })
    )

    PAYMENT_TYPE_CHOICES = [
        ('full_payment', 'Full Payment (collect now)'),
        ('full_credit', 'Full Credit (pay later)'),
        ('partial_credit', 'Partial Credit (pay some now, rest later)'),
    ]
    payment_type = forms.ChoiceField(
        choices=PAYMENT_TYPE_CHOICES,
        initial='full_payment',
        widget=forms.RadioSelect(attrs={'class': 'form-check-input'}),
        required=True
    )
    amount_paid_now = forms.DecimalField(
        required=False,
        min_value=0,
        decimal_places=2,
        initial=0,
        label='Amount to collect now (Rs)',
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Amount collected now',
            'step': '0.01',
            'min': '0'
        })
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Allow anonymous / walk‑in customers: name and phone are optional
        self.fields['customer_name'].required = False
        self.fields['customer_phone'].required = False
        if not self.instance.pk:
            inv_date = timezone.localdate()
            self.initial.setdefault('invoice_date', inv_date)
            cs = CompanySettings.objects.first()
            dues_days = getattr(cs, 'dues_days', 7) if cs else 7
            self.initial.setdefault('due_date', inv_date + timedelta(days=dues_days))

    class Meta:
        model = Invoice
        fields = ['customer_name', 'customer_phone', 'customer_address', 'customer_gstin', 'invoice_date', 'due_date', 'notes']
        widgets = {
            'customer_name': forms.TextInput(attrs={
                'class': 'form-control customer-name-input',
                'placeholder': 'Customer name (optional)',
                'autocomplete': 'off',
                'pattern': '[A-Za-z\\s]+',
                'title': 'Use letters and spaces only',
            }),
            'customer_address': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter customer address (optional)'
            }),
            'invoice_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'due_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'notes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Enter any additional notes'
            }),
        }

    def clean(self):
        cleaned_data = super().clean()
        payment_type = cleaned_data.get('payment_type', 'full_payment')
        amount_paid_now = cleaned_data.get('amount_paid_now') or Decimal('0')
        invoice_date = cleaned_data.get('invoice_date')
        due_date = cleaned_data.get('due_date')

        # Business rule: due date cannot be before invoice date
        if invoice_date and due_date and due_date < invoice_date:
            raise forms.ValidationError('Due date cannot be earlier than invoice date.')

        if payment_type == 'partial_credit' and amount_paid_now <= 0:
            raise forms.ValidationError('For partial credit, please enter the amount to collect now.')
        return cleaned_data


class PaymentReceivedForm(forms.Form):
    """Form for recording payments received from customers."""
    party_name = forms.CharField(
        max_length=200,
        validators=[only_letters_validator],
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Customer name',
            'id': 'id_party_name',
            'pattern': '[A-Za-z\\s]+',
            'title': 'Use letters and spaces only',
        })
    )
    party_phone = forms.CharField(
        required=False,
        max_length=10,
        validators=[
            RegexValidator(
                regex=r'^\d{10}$',
                message='Enter a valid 10‑digit mobile number (or leave blank).',
                code='invalid_mobile',
            )
        ],
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Phone (for matching)',
            'maxlength': '10',
            'inputmode': 'numeric',
            'pattern': r'\d{10}',
            'title': 'Enter a 10-digit mobile number (or leave blank)',
        })
    )
    invoice = forms.ModelChoiceField(
        queryset=Invoice.objects.none(),
        required=False,
        empty_label='-- General payment (no invoice) --',
        widget=forms.Select(attrs={'class': 'form-select', 'id': 'id_invoice'})
    )
    amount = forms.DecimalField(
        min_value=Decimal('0.01'),
        decimal_places=2,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Amount received', 'step': '0.01'})
    )
    payment_method = forms.ChoiceField(
        choices=PaymentReceived.PAYMENT_METHODS,
        initial='cash',
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    payment_date = forms.DateField(
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'})
    )
    notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Notes or reference number'})
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Invoices with outstanding > 0
        self.fields['invoice'].queryset = Invoice.objects.filter(
            status__in=('credit', 'partially_paid'),
            outstanding_amount__gt=0
        ).order_by('-invoice_date')