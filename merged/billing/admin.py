from django.contrib import admin

from .models import (
    BackupHistory,
    CompanySettings,
    Customer,
    CustomerLedgerEntry,
    Invoice,
    InvoiceItem,
    ManufacturingItemLog,
    ManufacturingLog,
    PaymentReceived,
    Product,
    ProductBatch,
    ProductCategory,
    PurchaseOrder,
    PurchaseOrderItem,
    PurchaseReceipt,
    PurchaseReceiptItem,
    RawMaterial,
    Recipe,
    RecipeItem,
    Stock,
    StockMovementLog,
    Supplier,
)

admin.site.site_header = 'Billvice Admin'
admin.site.site_title = 'Billvice'
admin.site.index_title = 'All records'


class RecipeItemInline(admin.TabularInline):
    model = RecipeItem
    extra = 1
    autocomplete_fields = ('raw_material',)


class ManufacturingItemLogInline(admin.TabularInline):
    model = ManufacturingItemLog
    extra = 0
    autocomplete_fields = ('raw_material',)


class LedgerInline(admin.TabularInline):
    model = CustomerLedgerEntry
    extra = 0
    fields = ('entry_date', 'entry_type', 'invoice', 'debit', 'credit', 'balance_after', 'description')
    autocomplete_fields = ('invoice',)


class InvoiceItemInline(admin.TabularInline):
    model = InvoiceItem
    extra = 0
    fields = ('product', 'quantity', 'unit_price', 'discount', 'gst_rate', 'total_amount')
    autocomplete_fields = ('product',)


class PurchaseOrderItemInline(admin.TabularInline):
    model = PurchaseOrderItem
    extra = 0
    autocomplete_fields = ('product', 'raw_material')


class PurchaseReceiptItemInline(admin.TabularInline):
    model = PurchaseReceiptItem
    extra = 0
    autocomplete_fields = ('po_item', 'raw_material')


@admin.register(ProductCategory)
class ProductCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_active', 'description', 'created_at')
    list_editable = ('is_active',)
    list_filter = ('is_active',)
    search_fields = ('name', 'description')


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'sku', 'category', 'hsn_code', 'gst_rate', 'cost_price', 'price', 'uom', 'get_stock_quantity')
    list_editable = ('hsn_code', 'gst_rate', 'cost_price', 'price')
    search_fields = ('name', 'sku', 'hsn_code', 'description', 'category__name')
    list_filter = ('category', 'uom', 'type')
    autocomplete_fields = ('category',)
    list_per_page = 50

    def get_stock_quantity(self, obj):
        return obj.stock.quantity if hasattr(obj, 'stock') else 0
    get_stock_quantity.short_description = 'Stock'


@admin.register(Stock)
class StockAdmin(admin.ModelAdmin):
    list_display = ('product', 'quantity', 'low_stock_threshold', 'updated_at')
    list_editable = ('quantity', 'low_stock_threshold')
    search_fields = ('product__name', 'product__sku')
    autocomplete_fields = ('product',)


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = (
        'invoice_number', 'invoice_date', 'customer_name', 'customer_phone',
        'status', 'total_amount', 'advance_paid', 'outstanding_amount',
    )
    list_editable = ('status', 'advance_paid', 'outstanding_amount')
    list_filter = ('status', 'invoice_date')
    search_fields = ('invoice_number', 'customer_name', 'customer_phone', 'customer_gstin', 'notes')
    inlines = [InvoiceItemInline]
    fieldsets = (
        ('Invoice', {
            'fields': ('invoice_number', 'invoice_date', 'due_date', 'status', 'notes'),
        }),
        ('Customer', {
            'fields': ('customer_name', 'customer_phone', 'customer_address', 'customer_gstin', 'customer_state'),
        }),
        ('Amounts', {
            'fields': (
                'subtotal', 'cgst_amount', 'sgst_amount', 'igst_amount',
                'total_amount', 'advance_paid', 'outstanding_amount',
            ),
        }),
    )


@admin.register(InvoiceItem)
class InvoiceItemAdmin(admin.ModelAdmin):
    list_display = ('invoice', 'product', 'quantity', 'unit_price', 'discount', 'gst_rate', 'total_amount')
    list_editable = ('quantity', 'unit_price', 'discount', 'gst_rate', 'total_amount')
    search_fields = ('invoice__invoice_number', 'product__name')
    autocomplete_fields = ('invoice', 'product')


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ('name', 'phone', 'gstin', 'state', 'city', 'pincode', 'email', 'outstanding_balance')
    list_editable = ('phone', 'gstin', 'state', 'city', 'pincode', 'outstanding_balance')
    search_fields = ('name', 'phone', 'email', 'gstin', 'state', 'city', 'pincode')
    inlines = [LedgerInline]


@admin.register(CustomerLedgerEntry)
class CustomerLedgerEntryAdmin(admin.ModelAdmin):
    list_display = ('entry_date', 'customer', 'entry_type', 'invoice', 'debit', 'credit', 'balance_after', 'description')
    list_editable = ('entry_type', 'debit', 'credit', 'balance_after', 'description')
    list_filter = ('entry_type', 'entry_date')
    search_fields = ('customer__name', 'description', 'invoice__invoice_number')
    autocomplete_fields = ('customer', 'invoice')


@admin.register(PaymentReceived)
class PaymentReceivedAdmin(admin.ModelAdmin):
    list_display = ('payment_date', 'customer', 'invoice', 'amount', 'payment_method', 'reference_number', 'notes')
    list_editable = ('amount', 'payment_method', 'reference_number')
    list_filter = ('payment_method', 'payment_date')
    search_fields = ('customer__name', 'notes', 'reference_number', 'invoice__invoice_number')
    autocomplete_fields = ('customer', 'invoice')


@admin.register(CompanySettings)
class CompanySettingsAdmin(admin.ModelAdmin):
    fieldsets = (
        ('Company', {
            'fields': (
                'company_name', 'address_line1', 'address_line2', 'city',
                'state', 'postal_code', 'phone', 'email', 'website',
            ),
        }),
        ('Tax', {
            'fields': ('gstin', 'gst_percentage', 'pan_number', 'dues_days'),
        }),
        ('Bank', {
            'fields': ('bank_name', 'bank_account_number', 'bank_ifsc'),
        }),
        ('Print', {
            'fields': (
                'invoice_footer_text', 'printer_type', 'printer_name',
                'auto_print_dialog', 'use_direct_print', 'print_service_url', 'print_bill_enabled',
            ),
        }),
        ('Legacy rental (unused)', {
            'classes': ('collapse',),
            'fields': (
                'min_rental_days', 'max_rental_days', 'default_rental_days',
                'daily_late_fee', 'grace_period', 'max_late_fee',
                'security_deposit_percentage', 'min_security_deposit', 'max_security_deposit',
                'weekly_discount', 'monthly_discount', 'max_discount',
            ),
        }),
    )

    def has_add_permission(self, request):
        return not CompanySettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display = ('name', 'gstin', 'gst_type', 'phone', 'email', 'state', 'is_active', 'payment_terms')
    list_editable = ('gst_type', 'phone', 'is_active')
    search_fields = ('name', 'gstin', 'phone', 'email')
    list_filter = ('gst_type', 'is_active')


@admin.register(PurchaseOrder)
class PurchaseOrderAdmin(admin.ModelAdmin):
    list_display = ('order_number', 'supplier_name', 'order_date', 'status', 'is_interstate', 'total_amount')
    list_editable = ('status',)
    list_filter = ('status', 'order_date', 'is_interstate')
    search_fields = ('order_number', 'supplier_name', 'supplier_phone', 'supplier_gstin', 'notes')
    autocomplete_fields = ('supplier',)
    inlines = [PurchaseOrderItemInline]


@admin.register(PurchaseOrderItem)
class PurchaseOrderItemAdmin(admin.ModelAdmin):
    list_display = ('purchase_order', 'raw_material', 'product', 'quantity', 'received_quantity', 'unit_cost', 'gst_rate', 'total')
    list_editable = ('quantity', 'received_quantity', 'unit_cost', 'gst_rate')
    search_fields = ('purchase_order__order_number', 'raw_material__name', 'product__name')
    autocomplete_fields = ('purchase_order', 'product', 'raw_material')


@admin.register(PurchaseReceipt)
class PurchaseReceiptAdmin(admin.ModelAdmin):
    list_display = ('receipt_number', 'purchase_order', 'supplier', 'receipt_date', 'warehouse', 'received_by')
    list_editable = ('receipt_date', 'received_by')
    search_fields = ('receipt_number', 'purchase_order__order_number')
    autocomplete_fields = ('purchase_order', 'supplier')
    inlines = [PurchaseReceiptItemInline]


@admin.register(PurchaseReceiptItem)
class PurchaseReceiptItemAdmin(admin.ModelAdmin):
    list_display = ('receipt', 'raw_material', 'quantity', 'unit_cost', 'batch_number', 'expiry_date')
    list_editable = ('quantity', 'unit_cost', 'batch_number')
    search_fields = ('receipt__receipt_number', 'raw_material__name', 'batch_number')
    autocomplete_fields = ('receipt', 'po_item', 'raw_material')


@admin.register(RawMaterial)
class RawMaterialAdmin(admin.ModelAdmin):
    list_display = (
        'material_code', 'name', 'category', 'unit', 'current_stock', 'minimum_stock',
        'purchase_price', 'hsn_code', 'gst_rate', 'is_active',
    )
    list_editable = ('current_stock', 'minimum_stock', 'purchase_price', 'gst_rate', 'is_active')
    list_filter = ('category', 'unit', 'is_active')
    search_fields = ('material_code', 'name', 'hsn_code', 'supplier')


@admin.register(Recipe)
class RecipeAdmin(admin.ModelAdmin):
    list_display = ('product', 'yield_quantity', 'notes', 'updated_at')
    list_editable = ('yield_quantity',)
    search_fields = ('product__name',)
    autocomplete_fields = ('product',)
    inlines = [RecipeItemInline]


@admin.register(RecipeItem)
class RecipeItemAdmin(admin.ModelAdmin):
    list_display = ('recipe', 'raw_material', 'quantity_required', 'input_unit')
    list_editable = ('quantity_required', 'input_unit')
    search_fields = ('recipe__product__name', 'raw_material__name')
    autocomplete_fields = ('recipe', 'raw_material')


@admin.register(ManufacturingLog)
class ManufacturingLogAdmin(admin.ModelAdmin):
    list_display = (
        'manufacturing_id', 'product', 'production_quantity', 'batch_number',
        'mfg_date', 'status', 'total_cost', 'unit_cost', 'operator',
    )
    list_editable = ('status', 'operator')
    list_filter = ('status', 'mfg_date')
    search_fields = ('manufacturing_id', 'batch_number', 'product__name', 'operator')
    autocomplete_fields = ('product', 'recipe')
    inlines = [ManufacturingItemLogInline]


@admin.register(ManufacturingItemLog)
class ManufacturingItemLogAdmin(admin.ModelAdmin):
    list_display = ('manufacturing', 'raw_material', 'quantity_consumed', 'unit_cost', 'total_cost')
    list_editable = ('quantity_consumed', 'unit_cost', 'total_cost')
    search_fields = ('manufacturing__manufacturing_id', 'raw_material__name')
    autocomplete_fields = ('manufacturing', 'raw_material')


@admin.register(ProductBatch)
class ProductBatchAdmin(admin.ModelAdmin):
    list_display = (
        'batch_number', 'product', 'produced_quantity', 'remaining_quantity',
        'mfg_date', 'exp_date', 'unit_cost',
    )
    list_editable = ('remaining_quantity', 'exp_date', 'unit_cost')
    search_fields = ('batch_number', 'product__name')
    autocomplete_fields = ('product', 'manufacturing')
    list_filter = ('mfg_date',)


@admin.register(StockMovementLog)
class StockMovementLogAdmin(admin.ModelAdmin):
    list_display = (
        'created_at', 'movement_type', 'item_type', 'raw_material', 'product',
        'quantity', 'previous_balance', 'new_balance', 'unit_cost', 'amount', 'reason',
    )
    list_editable = ('quantity', 'reason')
    list_filter = ('movement_type', 'item_type', 'created_at')
    search_fields = ('reason', 'reference_id', 'raw_material__name', 'product__name')
    autocomplete_fields = ('raw_material', 'product')


@admin.register(BackupHistory)
class BackupHistoryAdmin(admin.ModelAdmin):
    list_display = ('date', 'type', 'status', 'location', 'size', 'details')
    list_editable = ('status',)
    list_filter = ('type', 'status')
    search_fields = ('location', 'details', 'file_path')
