from rest_framework import serializers
from django.conf import settings
from .models import Order, OrderItem, OrderStatusHistory
from customer.models import Customer, CustomerAddress, CustomerMobile
from dashboard.models import Product
from dashboard.delhivery_service import (
    DelhiveryError,
    apply_shipment_to_order,
    create_shipment as delhivery_create_shipment,
    get_order_delivery_address,
    is_pincode_serviceable,
    parse_shipment_error,
)
from cart.models import CartDetails, CartItem
from decimal import Decimal
import re
import hmac
import hashlib

def verify_razorpay_payment_signature(razorpay_order_id, razorpay_payment_id, razorpay_signature):
    secret = getattr(settings, 'RAZORPAY_KEY_SECRET', '')
    if not secret:
        return False
    text = f"{razorpay_order_id}|{razorpay_payment_id}"
    expected = hmac.new(
        secret.encode(),
        text.encode(),
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(expected, razorpay_signature)

def normalize_mobile(value):
    digits = re.sub(r'\D', '', str(value or ''))
    return digits[-10:] if len(digits) >= 10 else digits

def find_customer_by_mobile(mobile):
    target = normalize_mobile(mobile)
    if not target:
        return None
    for customer_mobile in CustomerMobile.objects.select_related('customer'):
        if normalize_mobile(customer_mobile.mobile) == target:
            return customer_mobile.customer
    return None

def resolve_customer_for_order(serializer, mobile=None):
    request = serializer.context.get('request')
    if request and request.user.is_authenticated:
        try:
            return Customer.objects.get(user=request.user)
        except Customer.DoesNotExist:
            pass
    return find_customer_by_mobile(mobile)

class OrderItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True)
    product_image = serializers.SerializerMethodField()
    
    class Meta:
        model = OrderItem
        fields = ['id', 'product', 'product_name', 'product_image', 'quantity', 'unit_price', 'total_price']
        read_only_fields = ['unit_price', 'total_price']
    
    def get_product_image(self, obj):
        if obj.product.images.exists():
            image_url = obj.product.images.first().image.url
            request = self.context.get('request')
            if request:
                try:
                    return request.build_absolute_uri(image_url)
                except Exception:
                    return image_url
            return image_url
        return None

class OrderStatusHistorySerializer(serializers.ModelSerializer):
    changed_by_name = serializers.CharField(source='changed_by.username', read_only=True)
    
    class Meta:
        model = OrderStatusHistory
        fields = ['id', 'status', 'changed_by', 'changed_by_name', 'changed_at', 'notes']
        read_only_fields = ['changed_at']

class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    status_history = OrderStatusHistorySerializer(many=True, read_only=True)
    customer_name = serializers.CharField(source='customer.name', read_only=True)
    customer_email = serializers.CharField(source='customer.email', read_only=True)
    
    class Meta:
        model = Order
        fields = [
            'id', 'order_id', 'customer', 'customer_name', 'customer_email', 'customer_mobile',
            'status', 'payment_status', 'payment_method', 'delivery_address', 'delivery_pincode',
            'delivery_city', 'delivery_state', 'delivery_country', 'delivery_address_text',
            'recipient_name', 'recipient_phone',
            'subtotal', 'shipping_cost', 'discount_amount', 'total_amount', 'is_deliverable',
            'shipment_created', 'tracking_number', 'created_at', 'updated_at', 'delivered_at',
            'cancelled_at', 'notes', 'cancellation_reason', 'items', 'status_history'
        ]
        read_only_fields = [
            'order_id', 'subtotal', 'shipping_cost', 'discount_amount', 'total_amount',
            'is_deliverable', 'shipment_created', 'tracking_number', 'created_at', 'updated_at',
            'delivered_at', 'cancelled_at'
        ]

class CreateOrderItemSerializer(serializers.Serializer):
    product_id = serializers.IntegerField()
    quantity = serializers.IntegerField(min_value=1)

class CreateOrderSerializer(serializers.ModelSerializer):
    # Cart-based order (optional)
    cart_id = serializers.IntegerField(write_only=True, required=False)
    
    # Direct order creation (alternative to cart)
    order_items = CreateOrderItemSerializer(many=True, required=False)
    
    # Delivery info (required)
    delivery_pincode = serializers.CharField()
    delivery_city = serializers.CharField()
    delivery_state = serializers.CharField()
    delivery_country = serializers.CharField(default='India')
    delivery_address_text = serializers.CharField()
    
    # Required fields
    payment_method = serializers.ChoiceField(choices=Order.PAYMENT_METHOD_CHOICES)
    customer_mobile = serializers.CharField(required=False, allow_blank=True)

    # Razorpay prepaid confirmation (required when payment_method is prepaid)
    razorpay_payment_id = serializers.CharField(write_only=True, required=False, allow_blank=True)
    razorpay_order_id = serializers.CharField(write_only=True, required=False, allow_blank=True)
    razorpay_signature = serializers.CharField(write_only=True, required=False, allow_blank=True)
    
    class Meta:
        model = Order
        fields = [
            'customer_mobile', 'cart_id', 'payment_method',
            'recipient_name', 'recipient_phone', 'notes',
            'delivery_pincode', 'delivery_city', 'delivery_state', 
            'delivery_country', 'delivery_address_text', 'order_items',
            'razorpay_payment_id', 'razorpay_order_id', 'razorpay_signature',
        ]
    
    def validate(self, data):
        cart_id = data.get('cart_id')
        delivery_address_id = data.get('delivery_address_id')
        delivery_pincode = data.get('delivery_pincode')
        order_items = data.get('order_items', [])

        customer = resolve_customer_for_order(self, data.get('customer_mobile'))
        if not customer:
            raise serializers.ValidationError({
                'customer_mobile': 'No customer profile found. Please update your profile and phone number first.'
            })

        primary_mobile = customer.mobiles.first()
        if primary_mobile:
            data['customer_mobile'] = primary_mobile.mobile
        elif data.get('customer_mobile'):
            data['customer_mobile'] = data['customer_mobile']
        elif customer.user.username:
            data['customer_mobile'] = customer.user.username
        else:
            raise serializers.ValidationError({
                'customer_mobile': 'No phone number found on your profile.'
            })

        self._resolved_customer = customer
        
        # Must have either cart_id OR order_items
        if not cart_id and not order_items:
            raise serializers.ValidationError("Either cart_id or order_items must be provided")
        
        if cart_id and order_items:
            raise serializers.ValidationError("Cannot use both cart_id and order_items")
        
        # If no cart_id provided, delivery info is required
        if not cart_id:
            if not delivery_pincode:
                raise serializers.ValidationError("delivery_pincode is required when not using cart_id")
            if not data.get('delivery_city'):
                raise serializers.ValidationError("delivery_city is required when not using cart_id")
            if not data.get('delivery_state'):
                raise serializers.ValidationError("delivery_state is required when not using cart_id")
            if not order_items:
                raise serializers.ValidationError("order_items is required when not using cart_id")
        
        # Validate cart if provided
        if cart_id:
            try:
                cart = CartDetails.objects.get(id=cart_id)
                if not cart.items.exists():
                    raise serializers.ValidationError("Cart is empty.")
            except CartDetails.DoesNotExist:
                raise serializers.ValidationError("Cart not found.")
        
        # Validate delivery address if provided
        if delivery_address_id:
            try:
                CustomerAddress.objects.get(id=delivery_address_id)
            except CustomerAddress.DoesNotExist:
                raise serializers.ValidationError("Delivery address not found.")
        
        # Validate order items if provided
        if order_items:
            for item in order_items:
                try:
                    product = Product.objects.get(id=item['product_id'])
                    if not product.available:
                        raise serializers.ValidationError(f"Product {product.name} is not available")
                    if product.stock < item['quantity']:
                        raise serializers.ValidationError(f"Insufficient stock for {product.name}")
                except Product.DoesNotExist:
                    raise serializers.ValidationError(f"Product with id {item['product_id']} not found")

        payment_method = data.get('payment_method')
        if payment_method == 'prepaid':
            razorpay_payment_id = data.get('razorpay_payment_id') or self.initial_data.get('razorpay_payment_id')
            razorpay_order_id = data.get('razorpay_order_id') or self.initial_data.get('razorpay_order_id')
            razorpay_signature = data.get('razorpay_signature') or self.initial_data.get('razorpay_signature')

            if not all([razorpay_payment_id, razorpay_order_id, razorpay_signature]):
                raise serializers.ValidationError({
                    'payment': 'Razorpay payment confirmation is required for prepaid orders.'
                })

            if not verify_razorpay_payment_signature(
                razorpay_order_id, razorpay_payment_id, razorpay_signature
            ):
                raise serializers.ValidationError({
                    'payment': 'Invalid Razorpay payment signature. Payment could not be verified.'
                })

            self._razorpay_verified = True
            self._razorpay_payment_id = razorpay_payment_id
            self._razorpay_order_id = razorpay_order_id
        
        return data
    
    def validate_customer_mobile(self, value):
        return value
    
    def check_delivery_pincode(self, pincode, payment_method='cod'):
        is_deliverable, api_response = is_pincode_serviceable(pincode, payment_method=payment_method)
        return is_deliverable, api_response
    
    def create(self, validated_data):
        cart_id = validated_data.pop('cart_id', None)
        delivery_address_id = validated_data.pop('delivery_address_id', None)
        order_items_data = validated_data.pop('order_items', [])
        validated_data.pop('razorpay_payment_id', None)
        validated_data.pop('razorpay_order_id', None)
        validated_data.pop('razorpay_signature', None)
        
        # Get customer from authenticated user or mobile lookup
        customer = getattr(self, '_resolved_customer', None) or resolve_customer_for_order(
            self, validated_data.get('customer_mobile')
        )
        if not customer:
            raise serializers.ValidationError({
                'customer_mobile': 'No customer profile found. Please update your profile first.'
            })
        
        # Handle delivery address
        delivery_address = None
        delivery_pincode = None
        
        if delivery_address_id:
            delivery_address = CustomerAddress.objects.get(id=delivery_address_id)
            delivery_pincode = delivery_address.pincode
            delivery_city = delivery_address.city
            delivery_state = delivery_address.state
            delivery_country = delivery_address.country
            delivery_address_text = delivery_address.address
        else:
            delivery_pincode = validated_data['delivery_pincode']
            delivery_city = validated_data['delivery_city']
            delivery_state = validated_data['delivery_state']
            delivery_country = validated_data.get('delivery_country', 'India')
            delivery_address_text = validated_data.get('delivery_address_text', '')
        
        # Check delivery pincode with Delhivery
        is_deliverable, delivery_api_response = self.check_delivery_pincode(
            delivery_pincode,
            payment_method=validated_data.get('payment_method', 'cod'),
        )
        
        if not is_deliverable:
            raise serializers.ValidationError(
                f"Delivery not available for pincode {delivery_pincode} via Delhivery."
            )
        
        # Calculate totals
        subtotal = Decimal('0.00')
        
        if cart_id:
            # Calculate from cart
            cart = CartDetails.objects.get(id=cart_id)
            for cart_item in cart.items.all():
                product = cart_item.product
                price = product.price
                if product.discount > 0:
                    if product.discount_type == 'percent':
                        discount_amount = (price * product.discount) / 100
                    else:
                        discount_amount = product.discount
                    price = price - discount_amount
                subtotal += price * cart_item.quantity
        else:
            # Calculate from direct order items
            for item_data in order_items_data:
                product = Product.objects.get(id=item_data['product_id'])
                price = product.price
                if product.discount > 0:
                    if product.discount_type == 'percent':
                        discount_amount = (price * product.discount) / 100
                    else:
                        discount_amount = product.discount
                    price = price - discount_amount
                subtotal += price * item_data['quantity']
        
        # Create order
        is_prepaid_verified = (
            validated_data.get('payment_method') == 'prepaid'
            and getattr(self, '_razorpay_verified', False)
        )
        order = Order.objects.create(
            customer=customer,
            customer_mobile=validated_data['customer_mobile'],
            payment_method=validated_data['payment_method'],
            payment_status='paid' if is_prepaid_verified else 'pending',
            status='confirmed' if is_prepaid_verified else 'pending',
            delivery_address=delivery_address,
            delivery_pincode=delivery_pincode,
            delivery_city=delivery_city,
            delivery_state=delivery_state,
            delivery_country=delivery_country,
            delivery_address_text=delivery_address_text,
            recipient_name=validated_data.get('recipient_name', customer.name),
            recipient_phone=validated_data.get('recipient_phone', validated_data['customer_mobile']),
            subtotal=subtotal,
            total_amount=subtotal,
            is_deliverable=is_deliverable,
            delivery_api_response=delivery_api_response,
            notes=validated_data.get('notes', '')
        )
        
        # Create order items
        if cart_id:
            # Create from cart
            cart = CartDetails.objects.get(id=cart_id)
            for cart_item in cart.items.all():
                product = cart_item.product
                price = product.price
                if product.discount > 0:
                    if product.discount_type == 'percent':
                        discount_amount = (price * product.discount) / 100
                    else:
                        discount_amount = product.discount
                    price = price - discount_amount
                
                OrderItem.objects.create(
                    order=order,
                    product=product,
                    quantity=cart_item.quantity,
                    unit_price=price,
                    total_price=price * cart_item.quantity
                )
            
            # Clear cart
            cart.items.all().delete()
        else:
            # Create from direct order items
            for item_data in order_items_data:
                product = Product.objects.get(id=item_data['product_id'])
                price = product.price
                if product.discount > 0:
                    if product.discount_type == 'percent':
                        discount_amount = (price * product.discount) / 100
                    else:
                        discount_amount = product.discount
                    price = price - discount_amount
                
                OrderItem.objects.create(
                    order=order,
                    product=product,
                    quantity=item_data['quantity'],
                    unit_price=price,
                    total_price=price * item_data['quantity']
                )
        
        # Create initial status history
        initial_notes = 'Order created'
        if is_prepaid_verified:
            initial_notes = (
                f'Prepaid order confirmed via Razorpay. '
                f'Payment ID: {getattr(self, "_razorpay_payment_id", "N/A")}'
            )

        OrderStatusHistory.objects.create(
            order=order,
            status=order.status,
            notes=initial_notes
        )
        
        return order

class UpdateOrderStatusSerializer(serializers.ModelSerializer):
    new_status = serializers.ChoiceField(choices=Order.ORDER_STATUS_CHOICES, write_only=True)
    notes = serializers.CharField(required=False, allow_blank=True)
    
    class Meta:
        model = Order
        fields = ['new_status', 'notes']
    
    def update(self, instance, validated_data):
        new_status = validated_data.pop('new_status')
        notes = validated_data.get('notes', '')
        
        # Update order status
        instance.status = new_status
        
        # Handle specific status changes
        if new_status == 'delivered':
            from django.utils import timezone
            instance.delivered_at = timezone.now()
            instance.payment_status = 'paid'
        elif new_status == 'cancelled':
            from django.utils import timezone
            instance.cancelled_at = timezone.now()
            if instance.payment_method == 'prepaid':
                instance.payment_status = 'refunded'
        
        instance.save()
        
        # Create status history
        OrderStatusHistory.objects.create(
            order=instance,
            status=new_status,
            changed_by=self.context['request'].user,
            notes=notes
        )
        
        return instance

class CreateShipmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Order
        fields = ['id']
    
    def update(self, instance, validated_data):
        if instance.shipment_created:
            raise serializers.ValidationError("Shipment already created for this order.")
        
        if instance.status in ['cancelled', 'delivered', 'refunded']:
            raise serializers.ValidationError("Cannot create shipment for this order status.")
        
        from dashboard.models import PickupLocation, ReturnDetails

        pickup_location = PickupLocation.objects.first()
        return_details = ReturnDetails.objects.first()
        if not pickup_location or not return_details:
            raise serializers.ValidationError(
                "Pickup location or return details are not configured in admin."
            )

        delivery_address = get_order_delivery_address(instance)
        if delivery_address == 'Address not provided':
            raise serializers.ValidationError("Order does not have a delivery address.")

        try:
            shipment_response = delhivery_create_shipment(
                instance,
                pickup_location,
                return_details,
                delivery_address=delivery_address,
            )
        except DelhiveryError as exc:
            raise serializers.ValidationError(str(exc)) from exc

        if not shipment_response.get('success'):
            raise serializers.ValidationError(parse_shipment_error(shipment_response))

        apply_shipment_to_order(instance, shipment_response)

        OrderStatusHistory.objects.create(
            order=instance,
            status='shipped',
            changed_by=self.context['request'].user,
            notes=f"Shipment created via Delhivery. Response: {shipment_response}",
        )

        return instance 