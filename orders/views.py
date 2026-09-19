from django.shortcuts import render
from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.authentication import JWTAuthentication
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q
from django.utils import timezone
from .models import Order, OrderItem, OrderStatusHistory
from .serializers import (
    OrderSerializer, CreateOrderSerializer, UpdateOrderStatusSerializer,
    CreateShipmentSerializer, OrderStatusHistorySerializer
)

# Create your views here.

class OrderViewSet(viewsets.ModelViewSet):
    queryset = Order.objects.all()
    serializer_class = OrderSerializer
    authentication_classes = [JWTAuthentication]  # JWT only — avoid session CSRF on storefront
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['status', 'payment_status', 'payment_method', 'customer_mobile', 'is_deliverable', 'shipment_created']
    search_fields = ['order_id', 'customer__name', 'recipient_name', 'delivery_pincode']
    ordering_fields = ['created_at', 'updated_at', 'total_amount']
    ordering = ['-created_at']
    
    def get_serializer_class(self):
        if self.action == 'create':
            return CreateOrderSerializer
        elif self.action in ['update_status', 'partial_update']:
            return UpdateOrderStatusSerializer
        elif self.action == 'create_shipment':
            return CreateShipmentSerializer
        return OrderSerializer
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Filter by customer mobile number if provided
        customer_mobile = self.request.query_params.get('customer_mobile', None)
        if customer_mobile:
            queryset = queryset.filter(customer_mobile=customer_mobile)
        
        # Filter by date range
        start_date = self.request.query_params.get('start_date', None)
        end_date = self.request.query_params.get('end_date', None)
        
        if start_date:
            queryset = queryset.filter(created_at__date__gte=start_date)
        if end_date:
            queryset = queryset.filter(created_at__date__lte=end_date)
        
        # Filter by amount range
        min_amount = self.request.query_params.get('min_amount', None)
        max_amount = self.request.query_params.get('max_amount', None)
        
        if min_amount:
            queryset = queryset.filter(total_amount__gte=min_amount)
        if max_amount:
            queryset = queryset.filter(total_amount__lte=max_amount)
        
        return queryset
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        order = serializer.save()

        from dashboard.delhivery_service import try_create_shipment_for_order

        shipment_result = try_create_shipment_for_order(order)
        order.refresh_from_db()

        response_serializer = OrderSerializer(order, context={'request': request})
        response_data = response_serializer.data
        response_data['shipment_result'] = shipment_result
        return Response(response_data, status=status.HTTP_201_CREATED)
    
    @action(detail=True, methods=['patch'])
    def update_status(self, request, pk=None):
        """Update order status"""
        order = self.get_object()
        serializer = self.get_serializer(order, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        updated_order = serializer.save()
        
        response_serializer = OrderSerializer(updated_order, context={'request': request})
        return Response(response_serializer.data)
    
    @action(detail=True, methods=['post'])
    def create_shipment(self, request, pk=None):
        """Create shipment for the order"""
        order = self.get_object()
        serializer = self.get_serializer(order, data=request.data)
        serializer.is_valid(raise_exception=True)
        updated_order = serializer.save()
        
        response_serializer = OrderSerializer(updated_order, context={'request': request})
        return Response(response_serializer.data)
    
    @action(detail=True, methods=['post'])
    def cancel_order(self, request, pk=None):
        """Cancel order with optional refund for prepaid orders"""
        order = self.get_object()
        
        if order.status in ['cancelled', 'delivered']:
            return Response(
                {'error': 'Order cannot be cancelled in current status.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        cancellation_reason = request.data.get('cancellation_reason', '')
        
        # Update order status
        order.status = 'cancelled'
        order.cancelled_at = timezone.now()
        order.cancellation_reason = cancellation_reason
        
        # Handle refund for prepaid orders
        if order.payment_method == 'prepaid' and order.payment_status == 'paid':
            order.payment_status = 'refunded'
        
        order.save()
        
        # Create status history
        OrderStatusHistory.objects.create(
            order=order,
            status='cancelled',
            changed_by=request.user,
            notes=f"Order cancelled. Reason: {cancellation_reason}"
        )
        
        response_serializer = OrderSerializer(order, context={'request': request})
        return Response(response_serializer.data)
    
    @action(detail=True, methods=['post'])
    def refund_order(self, request, pk=None):
        """Refund prepaid order"""
        order = self.get_object()
        
        if order.payment_method != 'prepaid':
            return Response(
                {'error': 'Only prepaid orders can be refunded.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if order.payment_status == 'refunded':
            return Response(
                {'error': 'Order already refunded.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        refund_reason = request.data.get('refund_reason', '')
        
        # Update payment status
        order.payment_status = 'refunded'
        order.save()
        
        # Create status history
        OrderStatusHistory.objects.create(
            order=order,
            status='refunded',
            changed_by=request.user,
            notes=f"Order refunded. Reason: {refund_reason}"
        )
        
        response_serializer = OrderSerializer(order, context={'request': request})
        return Response(response_serializer.data)
    
    @action(detail=False, methods=['get'])
    def dashboard_stats(self, request):
        """Get dashboard statistics"""
        total_orders = Order.objects.count()
        pending_orders = Order.objects.filter(status='pending').count()
        processing_orders = Order.objects.filter(status='processing').count()
        shipped_orders = Order.objects.filter(status='shipped').count()
        delivered_orders = Order.objects.filter(status='delivered').count()
        cancelled_orders = Order.objects.filter(status='cancelled').count()
        
        # Revenue statistics
        total_revenue = sum([order.total_amount for order in Order.objects.filter(status='delivered')])
        today_revenue = sum([
            order.total_amount for order in Order.objects.filter(
                status='delivered',
                delivered_at__date=timezone.now().date()
            )
        ])
        
        # Payment method distribution
        cod_orders = Order.objects.filter(payment_method='cod').count()
        prepaid_orders = Order.objects.filter(payment_method='prepaid').count()
        
        stats = {
            'total_orders': total_orders,
            'pending_orders': pending_orders,
            'processing_orders': processing_orders,
            'shipped_orders': shipped_orders,
            'delivered_orders': delivered_orders,
            'cancelled_orders': cancelled_orders,
            'total_revenue': total_revenue,
            'today_revenue': today_revenue,
            'cod_orders': cod_orders,
            'prepaid_orders': prepaid_orders,
        }
        
        return Response(stats)
    
    @action(detail=False, methods=['get'])
    def recent_orders(self, request):
        """Get recent orders for dashboard"""
        limit = int(request.query_params.get('limit', 10))
        orders = Order.objects.all()[:limit]
        serializer = OrderSerializer(orders, many=True, context={'request': request})
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def orders_by_customer(self, request):
        """Get all orders for a specific customer mobile number or authenticated user."""
        from customer.models import Customer, CustomerMobile
        from orders.serializers import normalize_mobile

        customer_mobile = request.query_params.get('customer_mobile')
        orders = Order.objects.none()

        if request.user.is_authenticated:
            try:
                customer = Customer.objects.get(user=request.user)
                mobiles = list(customer.mobiles.values_list('mobile', flat=True))
                if mobiles:
                    orders = Order.objects.filter(customer_mobile__in=mobiles)
                if not orders.exists():
                    orders = Order.objects.filter(customer=customer)
            except Customer.DoesNotExist:
                pass

        if customer_mobile and not orders.exists():
            normalized = normalize_mobile(customer_mobile)
            matching_mobiles = [
                mobile for mobile in CustomerMobile.objects.values_list('mobile', flat=True)
                if normalize_mobile(mobile) == normalized
            ]
            if matching_mobiles:
                orders = Order.objects.filter(customer_mobile__in=matching_mobiles)
            else:
                orders = Order.objects.filter(customer_mobile=customer_mobile)

        serializer = OrderSerializer(orders.order_by('-created_at'), many=True, context={'request': request})
        return Response(serializer.data)

class OrderStatusHistoryViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = OrderStatusHistory.objects.all()
    serializer_class = OrderStatusHistorySerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['order', 'status', 'changed_by']
    ordering = ['-changed_at']
    
    def get_queryset(self):
        queryset = super().get_queryset()
        order_id = self.request.query_params.get('order_id')
        if order_id:
            queryset = queryset.filter(order__order_id=order_id)
        return queryset
