from django.contrib import admin
from .models import Order, OrderItem, OrderStatusHistory

class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ['total_price']

class OrderStatusHistoryInline(admin.TabularInline):
    model = OrderStatusHistory
    extra = 0
    readonly_fields = ['changed_at']
    can_delete = False

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = [
        'order_id', 'customer_name', 'customer_mobile', 'status', 
        'payment_status', 'payment_method', 'total_amount', 'created_at'
    ]
    list_filter = [
        'status', 'payment_status', 'payment_method', 'is_deliverable', 
        'shipment_created', 'created_at'
    ]
    search_fields = ['order_id', 'customer__name', 'customer_mobile', 'recipient_name']
    readonly_fields = [
        'order_id', 'created_at', 'updated_at', 'delivered_at', 'cancelled_at',
        'is_deliverable', 'delivery_api_response', 'shipment_details', 'tracking_number'
    ]
    inlines = [OrderItemInline, OrderStatusHistoryInline]
    
    fieldsets = (
        ('Order Information', {
            'fields': ('order_id', 'customer', 'customer_mobile', 'status', 'payment_status', 'payment_method')
        }),
        ('Delivery Information', {
            'fields': ('delivery_address', 'delivery_pincode', 'delivery_city', 'delivery_state', 'delivery_country')
        }),
        ('Contact Information', {
            'fields': ('recipient_name', 'recipient_phone')
        }),
        ('Financial Information', {
            'fields': ('subtotal', 'shipping_cost', 'discount_amount', 'total_amount')
        }),
        ('Delivery API Information', {
            'fields': ('is_deliverable', 'delivery_api_response', 'shipment_created', 'shipment_details', 'tracking_number'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at', 'delivered_at', 'cancelled_at'),
            'classes': ('collapse',)
        }),
        ('Notes', {
            'fields': ('notes', 'cancellation_reason')
        }),
    )
    
    def customer_name(self, obj):
        return obj.customer.name if obj.customer else '-'
    customer_name.short_description = 'Customer Name'
    
    actions = ['mark_as_confirmed', 'mark_as_processing', 'mark_as_shipped', 'mark_as_delivered', 'mark_as_cancelled']
    
    def mark_as_confirmed(self, request, queryset):
        updated = queryset.update(status='confirmed')
        self.message_user(request, f'{updated} orders marked as confirmed.')
    mark_as_confirmed.short_description = "Mark selected orders as confirmed"
    
    def mark_as_processing(self, request, queryset):
        updated = queryset.update(status='processing')
        self.message_user(request, f'{updated} orders marked as processing.')
    mark_as_processing.short_description = "Mark selected orders as processing"
    
    def mark_as_shipped(self, request, queryset):
        updated = queryset.update(status='shipped')
        self.message_user(request, f'{updated} orders marked as shipped.')
    mark_as_shipped.short_description = "Mark selected orders as shipped"
    
    def mark_as_delivered(self, request, queryset):
        from django.utils import timezone
        updated = queryset.update(status='delivered', delivered_at=timezone.now())
        self.message_user(request, f'{updated} orders marked as delivered.')
    mark_as_delivered.short_description = "Mark selected orders as delivered"
    
    def mark_as_cancelled(self, request, queryset):
        from django.utils import timezone
        updated = queryset.update(status='cancelled', cancelled_at=timezone.now())
        self.message_user(request, f'{updated} orders marked as cancelled.')
    mark_as_cancelled.short_description = "Mark selected orders as cancelled"

@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ['order', 'product', 'quantity', 'unit_price', 'total_price']
    list_filter = ['order__status', 'product__category']
    search_fields = ['order__order_id', 'product__name']
    readonly_fields = ['total_price']

@admin.register(OrderStatusHistory)
class OrderStatusHistoryAdmin(admin.ModelAdmin):
    list_display = ['order', 'status', 'changed_by', 'changed_at']
    list_filter = ['status', 'changed_at']
    search_fields = ['order__order_id', 'changed_by__username']
    readonly_fields = ['changed_at']
    ordering = ['-changed_at']
