from rest_framework import serializers
from decimal import Decimal
from .procurement import money as money_q, GSTIN_RE

try:
    from num2words import num2words
except Exception:
    num2words = None
import re

from .models import (
    ProductCategory,
    Product,
    Stock,
    Invoice,
    InvoiceItem,
    Customer,
    PaymentReceived,
    CompanySettings,
    PurchaseOrder,
    PurchaseOrderItem,
    PurchaseReceipt,
    PurchaseReceiptItem,
    Supplier,
    RawMaterial,
    Recipe,
    RecipeItem,
    ManufacturingLog,
    ManufacturingItemLog,
    ProductBatch,
    StockMovementLog,
)

class ProductCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductCategory
        fields = ['id', 'name', 'description', 'is_active', 'created_at']

class ProductBatchSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductBatch
        fields = [
            'id', 'product', 'manufacturing', 'batch_number',
            'produced_quantity', 'remaining_quantity', 'mfg_date', 'exp_date',
            'unit_cost', 'created_at',
        ]


class StockSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True)
    batches = serializers.SerializerMethodField()

    class Meta:
        model = Stock
        fields = [
            'id', 'product', 'product_name', 'quantity', 'low_stock_threshold',
            'updated_at', 'is_low_stock', 'batches',
        ]
        read_only_fields = ['updated_at', 'is_low_stock']

    def get_batches(self, obj):
        batches = obj.product.batches.all() if obj.product_id else []
        return ProductBatchSerializer(batches, many=True).data

class ProductSerializer(serializers.ModelSerializer):
    stock = StockSerializer(read_only=True)
    category_name = serializers.CharField(source='category.name', read_only=True)
    batches = ProductBatchSerializer(many=True, read_only=True)
    gst_amount = serializers.SerializerMethodField()
    selling_price_after_gst = serializers.SerializerMethodField()
    selling_price_before_gst = serializers.DecimalField(source='price', max_digits=10, decimal_places=2, read_only=True)
    purchase_price_before_gst = serializers.DecimalField(source='cost_price', max_digits=10, decimal_places=2, read_only=True)

    class Meta:
        model = Product
        fields = [
            'id',
            'name',
            'description',
            'uom',
            'cost_price',
            'price',
            'sku',
            'hsn_code',
            'gst_rate',
            'gst_amount',
            'selling_price_before_gst',
            'selling_price_after_gst',
            'purchase_price_before_gst',
            'category',
            'category_name',
            'created_at',
            'updated_at',
            'stock',
            'batches',
        ]
        read_only_fields = ['created_at', 'updated_at']

    def _breakdown(self, price, gst_rate):
        from .procurement import selling_breakdown
        return selling_breakdown(price or 0, gst_rate or 0)

    def get_gst_amount(self, obj):
        return self._breakdown(obj.price, obj.gst_rate)[1]

    def get_selling_price_after_gst(self, obj):
        return self._breakdown(obj.price, obj.gst_rate)[2]

    def validate(self, attrs):
        from .procurement import before_from_inclusive, company_default_gst, money
        request = self.context.get('request')
        data = getattr(request, 'data', {}) if request else {}
        gst = attrs.get('gst_rate', getattr(self.instance, 'gst_rate', None))
        if gst is None:
            gst = company_default_gst()
            attrs['gst_rate'] = gst
        gst = Decimal(str(gst))
        if gst < 0:
            raise serializers.ValidationError({'gst_rate': 'GST rate must be 0 or greater.'})
        attrs['gst_rate'] = gst
        mode = str(data.get('price_mode') or 'before').lower()
        if mode in ('after', 'inclusive', 'after_gst'):
            after = data.get('selling_price_after_gst', attrs.get('price'))
            before, _, _ = before_from_inclusive(after, gst)
            attrs['price'] = before
        price = Decimal(str(attrs.get('price', getattr(self.instance, 'price', 0) or 0)))
        if price < 0:
            raise serializers.ValidationError({'price': 'Selling price must be 0 or greater.'})
        attrs['price'] = money(price)
        return attrs

class InvoiceItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True)
    
    class Meta:
        model = InvoiceItem
        fields = ['id', 'product', 'product_name', 'quantity', 'unit_price', 'total_amount']

class InvoiceSerializer(serializers.ModelSerializer):
    items = InvoiceItemSerializer(many=True, read_only=True)
    payment_status = serializers.CharField(source='status', read_only=True)
    payment_method = serializers.SerializerMethodField()

    class Meta:
        model = Invoice
        fields = [
            'id', 'invoice_number', 'invoice_date', 'due_date', 'customer_name',
            'customer_phone', 'customer_address', 'customer_gstin', 'customer_state', 'status', 'payment_status',
            'subtotal', 'cgst_amount', 'sgst_amount', 'igst_amount', 'total_amount',
            'advance_paid', 'outstanding_amount', 'notes', 'items', 'created_at',
            'payment_method',
        ]

    def get_payment_method(self, obj):
        blob = f'{obj.notes or ""} {obj.status or ""}'.lower()
        if obj.status == 'credit':
            return 'credit'
        if 'upi' in blob:
            return 'upi'
        if 'bank' in blob:
            return 'bank'
        if 'card' in blob:
            return 'card'
        if 'cash' in blob:
            return 'cash'
        if obj.status == 'paid':
            return 'cash'
        if obj.status in ('partially_paid',):
            return 'credit'
        return 'other'

class CustomerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Customer
        fields = [
            'id', 'name', 'phone', 'email', 'address', 'state', 'city', 'pincode', 'gstin',
            'outstanding_balance', 'created_at', 'updated_at',
        ]

    def validate_state(self, value):
        state = (value or '').strip()
        if not state:
            raise serializers.ValidationError('State is required.')
        return state

    def validate_gstin(self, value):
        gstin = (value or '').strip().upper()
        if gstin and not re.fullmatch(GSTIN_RE, gstin):
            raise serializers.ValidationError('Enter a valid 15-character GSTIN (e.g. 06ABCDE1234F1Z5).')
        return gstin

class PaymentReceivedSerializer(serializers.ModelSerializer):
    customer_name = serializers.CharField(source='customer.name', read_only=True)
    invoice_number = serializers.CharField(source='invoice.invoice_number', read_only=True)

    class Meta:
        model = PaymentReceived
        fields = [
            'id', 'customer', 'customer_name', 'invoice', 'invoice_number',
            'amount', 'payment_method', 'payment_date', 'notes', 'reference_number', 'created_at'
        ]

class CompanySettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = CompanySettings
        fields = '__all__'

class PurchaseOrderItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True)
    raw_material_name = serializers.CharField(source='raw_material.name', read_only=True)
    remaining_quantity = serializers.DecimalField(max_digits=12, decimal_places=3, read_only=True)

    class Meta:
        model = PurchaseOrderItem
        fields = [
            'id', 'product', 'product_name', 'raw_material', 'raw_material_name',
            'hsn_code', 'specification', 'uom', 'quantity', 'received_quantity',
            'remaining_quantity', 'unit_cost', 'discount', 'taxable_amount',
            'gst_rate', 'cgst', 'sgst', 'igst', 'total',
        ]


class PurchaseReceiptItemSerializer(serializers.ModelSerializer):
    raw_material_name = serializers.CharField(source='raw_material.name', read_only=True)

    class Meta:
        model = PurchaseReceiptItem
        fields = [
            'id', 'po_item', 'raw_material', 'raw_material_name', 'quantity', 'unit_cost',
            'batch_number', 'supplier_batch_number', 'mfg_date', 'expiry_date', 'location',
        ]


class PurchaseReceiptSerializer(serializers.ModelSerializer):
    items = PurchaseReceiptItemSerializer(many=True, read_only=True)

    class Meta:
        model = PurchaseReceipt
        fields = [
            'id', 'receipt_number', 'purchase_order', 'supplier', 'receipt_date',
            'warehouse', 'received_by', 'notes', 'items', 'created_at',
        ]


class PurchaseOrderSerializer(serializers.ModelSerializer):
    items = PurchaseOrderItemSerializer(many=True, read_only=True)
    receipts = PurchaseReceiptSerializer(many=True, read_only=True)
    item_count = serializers.SerializerMethodField()
    gst_total = serializers.SerializerMethodField()
    pending_amount = serializers.SerializerMethodField()
    received_amount = serializers.SerializerMethodField()
    amount_in_words = serializers.SerializerMethodField()

    class Meta:
        model = PurchaseOrder
        fields = [
            'id', 'order_number', 'supplier', 'supplier_name', 'supplier_phone',
            'supplier_address', 'supplier_gstin', 'order_date', 'expected_delivery_date',
            'received_date', 'warehouse', 'payment_terms', 'payment_due_date',
            'payment_notes', 'reference_number', 'delivery_address', 'transporter',
            'vehicle_number', 'lr_number', 'delivery_instructions', 'status',
            'is_interstate', 'subtotal', 'discount_total', 'taxable_amount',
            'cgst_amount', 'sgst_amount', 'igst_amount', 'other_charges',
            'extra_charges', 'round_off', 'total_amount', 'notes', 'terms',
            'cancelled_reason', 'cancelled_at', 'items', 'receipts', 'item_count',
            'gst_total', 'pending_amount', 'received_amount', 'amount_in_words',
            'created_at', 'updated_at',
        ]

    def get_item_count(self, obj):
        return obj.items.count()

    def get_gst_total(self, obj):
        return (obj.cgst_amount or 0) + (obj.sgst_amount or 0) + (obj.igst_amount or 0)

    def _received_ratio(self, obj):
        items = list(obj.items.all())
        if not items:
            return Decimal('0'), Decimal(str(obj.total_amount or 0))
        ordered = sum((Decimal(str(i.quantity or 0)) for i in items), Decimal('0'))
        received = sum((Decimal(str(i.received_quantity or 0)) for i in items), Decimal('0'))
        if ordered <= 0:
            return Decimal('0'), Decimal(str(obj.total_amount or 0))
        received_amt = money_q(Decimal(str(obj.total_amount or 0)) * (received / ordered))
        pending = money_q(Decimal(str(obj.total_amount or 0)) - received_amt)
        return received_amt, pending

    def get_pending_amount(self, obj):
        return self._received_ratio(obj)[1]

    def get_received_amount(self, obj):
        return self._received_ratio(obj)[0]

    def get_amount_in_words(self, obj):
        total = Decimal(str(obj.total_amount or 0))
        if num2words:
            try:
                return num2words(float(total), to='currency', lang='en_IN').replace(
                    'euro', 'Rupees'
                ).replace('cents', 'paise').title() + ' Only'
            except Exception:
                pass
        return f'Rupees {total:.2f} Only'


class SupplierSerializer(serializers.ModelSerializer):
    class Meta:
        model = Supplier
        fields = '__all__'

class RawMaterialSerializer(serializers.ModelSerializer):
    is_low_stock = serializers.SerializerMethodField()

    class Meta:
        model = RawMaterial
        fields = '__all__'

    def get_is_low_stock(self, obj):
        return obj.is_low_stock()


class RecipeItemSerializer(serializers.ModelSerializer):
    raw_material_name = serializers.CharField(source='raw_material.name', read_only=True)
    raw_material_unit = serializers.CharField(source='raw_material.unit', read_only=True)
    raw_material_price = serializers.DecimalField(source='raw_material.purchase_price', max_digits=10, decimal_places=2, read_only=True)
    quantity_required = serializers.DecimalField(max_digits=14, decimal_places=6)

    class Meta:
        model = RecipeItem
        fields = [
            'id', 'recipe', 'raw_material', 'raw_material_name', 'raw_material_unit',
            'raw_material_price', 'quantity_required', 'input_unit',
        ]


class RecipeSerializer(serializers.ModelSerializer):
    items = RecipeItemSerializer(many=True, read_only=True)
    product_name = serializers.CharField(source='product.name', read_only=True)

    class Meta:
        model = Recipe
        fields = [
            'id', 'product', 'product_name', 'yield_quantity', 'extra_charges',
            'notes', 'items', 'created_at', 'updated_at',
        ]


class ManufacturingItemLogSerializer(serializers.ModelSerializer):
    raw_material_name = serializers.CharField(source='raw_material.name', read_only=True)
    raw_material_unit = serializers.CharField(source='raw_material.unit', read_only=True)

    class Meta:
        model = ManufacturingItemLog
        fields = ['id', 'manufacturing', 'raw_material', 'raw_material_name', 'raw_material_unit', 'quantity_consumed', 'unit_cost', 'total_cost']


class ManufacturingLogSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True)
    consumed_items = ManufacturingItemLogSerializer(many=True, read_only=True)
    remaining_quantity = serializers.SerializerMethodField()
    estimated_quantity = serializers.DecimalField(
        source='production_quantity', max_digits=10, decimal_places=2, read_only=True
    )

    class Meta:
        model = ManufacturingLog
        fields = [
            'id', 'manufacturing_id', 'product', 'product_name', 'recipe',
            'production_quantity', 'estimated_quantity', 'actual_quantity', 'wastage_quantity',
            'batch_number', 'mfg_date', 'exp_date',
            'status', 'operator', 'raw_material_cost', 'labor_cost', 'packaging_cost',
            'other_overhead_cost', 'total_cost', 'unit_cost', 'notes', 'consumed_items',
            'remaining_quantity', 'created_at'
        ]

    def get_remaining_quantity(self, obj):
        batch = getattr(obj, 'finished_batch', None)
        if batch is None:
            return None
        return batch.remaining_quantity


class StockMovementLogSerializer(serializers.ModelSerializer):
    raw_material_name = serializers.CharField(source='raw_material.name', read_only=True)
    product_name = serializers.CharField(source='product.name', read_only=True)
    unit = serializers.SerializerMethodField()
    amount_display = serializers.SerializerMethodField()

    class Meta:
        model = StockMovementLog
        fields = [
            'id', 'item_type', 'raw_material', 'raw_material_name', 'product',
            'product_name', 'movement_type', 'quantity', 'previous_balance',
            'new_balance', 'unit_cost', 'amount', 'amount_display', 'unit',
            'reference_id', 'reason', 'created_at'
        ]

    def get_unit(self, obj):
        if obj.raw_material_id and obj.raw_material:
            return obj.raw_material.unit
        if obj.product_id and obj.product:
            return getattr(obj.product, 'uom', 'unit')
        return ''

    def get_amount_display(self, obj):
        stored = obj.amount or Decimal('0')
        if stored != 0:
            return stored
        unit_cost = obj.unit_cost or Decimal('0')
        if unit_cost != 0:
            return (obj.quantity * unit_cost).quantize(Decimal('0.01'))
        if obj.raw_material_id and obj.raw_material:
            price = obj.raw_material.purchase_price or Decimal('0')
            return (abs(obj.quantity) * price).quantize(Decimal('0.01'))
        return Decimal('0')