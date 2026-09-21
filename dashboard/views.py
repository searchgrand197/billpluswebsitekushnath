from django.shortcuts import render
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.decorators import api_view, permission_classes
from .models import Category, Tag, Benefit, Product, ProductImage, RazorpayOrder
from .serializers import (
    CategorySerializer, TagSerializer, BenefitSerializer,
    ProductSerializer, ProductImageSerializer, RazorpayOrderSerializer
)
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
import json
import random
import requests
import razorpay
import hashlib
import hmac
from .models import PickupLocation, ReturnDetails, OrderDashboard
from dashboard.delhivery_service import (
    DelhiveryError,
    apply_shipment_to_order,
    create_shipment as delhivery_create_shipment,
    get_order_delivery_address,
    is_pincode_serviceable,
    parse_shipment_error,
    track_shipment,
)
from django.views.decorators.http import require_POST
from django.conf import settings

# Razorpay configuration — live mode (from settings)
RAZORPAY_KEY_ID = getattr(settings, "RAZORPAY_KEY_ID", "rzp_live_RFVSx4eax0xMjW")
RAZORPAY_KEY_SECRET = getattr(settings, "RAZORPAY_KEY_SECRET", "aMrwajwB1bKan4upU3ukXT24")
RAZORPAY_MODE = getattr(settings, "RAZORPAY_MODE", "live")

razorpay_client = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))

# Create your views here.

class CategoryListView(generics.ListCreateAPIView):
    queryset = Category.objects.all().order_by('name')
    serializer_class = CategorySerializer

    def get_permissions(self):
        if self.request.method in ('GET', 'HEAD', 'OPTIONS'):
            return [AllowAny()]
        return [IsAuthenticated()]


class CategoryDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer

    def get_permissions(self):
        if self.request.method in ('GET', 'HEAD', 'OPTIONS'):
            return [AllowAny()]
        return [IsAuthenticated()]

class TagListView(generics.ListCreateAPIView):
    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    permission_classes = [IsAuthenticated]

class TagDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    permission_classes = [IsAuthenticated]

class BenefitListView(generics.ListCreateAPIView):
    queryset = Benefit.objects.all()
    serializer_class = BenefitSerializer
    permission_classes = [IsAuthenticated]

class BenefitDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Benefit.objects.all()
    serializer_class = BenefitSerializer
    permission_classes = [IsAuthenticated]

class ProductListView(generics.ListCreateAPIView):
    queryset = Product.objects.all().select_related('category').prefetch_related('images', 'tags', 'benefits')
    serializer_class = ProductSerializer

    def get_permissions(self):
        if self.request.method in ('GET', 'HEAD', 'OPTIONS'):
            return [AllowAny()]
        return [IsAuthenticated()]

    def get_queryset(self):
        qs = super().get_queryset()
        search = self.request.query_params.get('search') or self.request.query_params.get('q')
        category = self.request.query_params.get('category')
        if search:
            from django.db.models import Q
            qs = qs.filter(Q(name__icontains=search) | Q(sku__icontains=search) | Q(description__icontains=search))
        if category:
            qs = qs.filter(category_id=category)
        return qs.order_by('name')


class ProductDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Product.objects.all().select_related('category').prefetch_related('images', 'tags', 'benefits')
    serializer_class = ProductSerializer

    def get_permissions(self):
        if self.request.method in ('GET', 'HEAD', 'OPTIONS'):
            return [AllowAny()]
        return [IsAuthenticated()]

class ProductImageListView(generics.ListCreateAPIView):
    queryset = ProductImage.objects.all()
    serializer_class = ProductImageSerializer
    permission_classes = [IsAuthenticated]

class ProductImageDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = ProductImage.objects.all()
    serializer_class = ProductImageSerializer
    permission_classes = [IsAuthenticated]

@api_view(['GET'])
@permission_classes([AllowAny])
def check_delivery_pincode(request):
    pincode = request.query_params.get('pincode')
    payment_method = request.query_params.get('payment_method', 'cod')

    if not pincode:
        return Response({'success': False, 'message': 'pincode is required'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        serviceable, api_response = is_pincode_serviceable(pincode, payment_method=payment_method)
        return Response({
            'success': True,
            'pincode': pincode,
            'serviceable': serviceable,
            'data': api_response,
        })
    except DelhiveryError as exc:
        return Response({'success': False, 'message': str(exc)}, status=status.HTTP_503_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def track_delivery(request):
    waybill = request.query_params.get('waybill')
    if not waybill:
        return Response({'success': False, 'message': 'waybill is required'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        tracking_data = track_shipment(waybill)
        return Response({'success': True, 'waybill': waybill, 'data': tracking_data})
    except DelhiveryError as exc:
        return Response({'success': False, 'message': str(exc)}, status=status.HTTP_503_BAD_REQUEST)


@csrf_exempt
@require_POST
def createshipment(request):
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON payload"}, status=400)

    # --- Get the Order from the orders app ---
    order_id = data.get("order_id")
    if not order_id:
        return JsonResponse({"error": "order_id is required"}, status=400)

    try:
        from orders.models import Order
        order = Order.objects.prefetch_related('items__product').get(id=order_id)
    except Order.DoesNotExist:
        return JsonResponse({"error": "Order not found"}, status=404)

    # --- Get pickup & return locations ---
    pickup_location_id = data.get("pickup_location_id", 1)
    return_details_id = data.get("return_details_id", 1)

    try:
        pickup_location = PickupLocation.objects.get(id=pickup_location_id)
    except PickupLocation.DoesNotExist:
        return JsonResponse({"error": "Invalid pickup location ID"}, status=404)

    try:
        return_details = ReturnDetails.objects.get(id=return_details_id)
    except ReturnDetails.DoesNotExist:
        return JsonResponse({"error": "Invalid return details ID"}, status=404)

    delivery_address = get_order_delivery_address(
        order,
        override_address=data.get("delivery_address"),
    )
    if delivery_address == 'Address not provided':
        return JsonResponse({"error": "Order does not have a delivery address"}, status=400)

    if order.shipment_created and order.tracking_number:
        return JsonResponse({
            "shipment_status": "Shipment Already Created",
            "tracking_number": order.tracking_number,
            "delhivery_response": order.shipment_details or {},
        })

    overrides = {
        "shipment_width": data.get("shipment_width", "10"),
        "shipment_height": data.get("shipment_height", "10"),
        "weight": data.get("weight", "0.5"),
        "shipping_mode": data.get("shipping_mode", "Surface"),
        "address_type": data.get("address_type", "Home"),
    }

    try:
        res_json = delhivery_create_shipment(
            order,
            pickup_location,
            return_details,
            delivery_address=delivery_address,
            overrides=overrides,
        )
    except DelhiveryError as exc:
        return JsonResponse({
            "shipment_status": "Shipment Failed",
            "error": str(exc),
        }, status=503)

    if res_json.get("success"):
        shipment_status = "Shipment Created"
        apply_shipment_to_order(order, res_json)
        return JsonResponse({
            "shipment_status": shipment_status,
            "tracking_number": order.tracking_number,
            "delhivery_response": res_json,
        })

    error_message = parse_shipment_error(res_json)
    return JsonResponse({
        "shipment_status": "Shipment Failed",
        "error": error_message,
        "delhivery_response": res_json,
    }, status=400)

# Sample JSON for frontend usage
# POST /api/dashboard/createshipment/
# Content-Type: application/json
# {
#   "pickup_location_id": 1,
#   "return_details_id": 1,
#   "order_id": 1,
#   "shipments": [
#     {
#       "name": "Consignee Name",
#       "add": "789 Pine Street",
#       "pin": "67890",
#       "city": "Chicago",
#       "state": "IL",
#       "country": "USA",
#       "phone": "1111111111",
#       "products_desc": "Product 1 x 2, Product 2 x 1",
#       "payment_mode": "COD",
#       "total_amount": "499.00",
#       "quantity": "3",
#       "shipment_width": "10",
#       "shipment_height": "10",
#       "weight": "1",
#       "shipping_mode": "Surface",
#       "address_type": "Home"
#     }
#   ]
# }

@api_view(['POST'])
@permission_classes([AllowAny])
def create_razorpay_order(request):
    """
    Create a Razorpay order
    Expected payload:
    {
        "amount": 50000,  // Amount in paise (500.00 INR)
        "currency": "INR",
        "receipt": "order_receipt_123"
    }
    """
    try:
        data = request.data
        
        # Validate required fields
        amount = data.get('amount')
        currency = data.get('currency', 'INR')
        receipt = data.get('receipt')
        
        if not amount:
            return Response({
                'error': 'Amount is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Convert amount to paise if it's in rupees
        if isinstance(amount, float) or isinstance(amount, str):
            try:
                amount = int(float(amount) * 100)  # Convert to paise
            except ValueError:
                return Response({
                    'error': 'Invalid amount format'
                }, status=status.HTTP_400_BAD_REQUEST)
        
        # Prepare order data
        order_data = {
            'amount': amount,
            'currency': currency,
        }
        
        if receipt:
            order_data['receipt'] = receipt
        
        # Create order with Razorpay
        razorpay_order = razorpay_client.order.create(data=order_data)
        
        # Save order to database
        db_order = RazorpayOrder.objects.create(
            order_id=razorpay_order['id'],
            amount=amount / 100,  # Store in rupees
            currency=currency,
            receipt=receipt,
            status=razorpay_order['status']
        )
        
        # Return response with live/test mode information
        response_data = {
            'success': True,
            'order_id': razorpay_order['id'],
            'amount': razorpay_order['amount'],
            'currency': razorpay_order['currency'],
            'receipt': razorpay_order.get('receipt'),
            'status': razorpay_order['status'],
            'key_id': RAZORPAY_KEY_ID,
            'mode': RAZORPAY_MODE,
            'environment': 'live' if RAZORPAY_MODE == 'live' or 'live' in RAZORPAY_KEY_ID else 'test',
            'checkout_url': 'https://checkout.razorpay.com/v1/checkout.html'
        }
        
        return Response(response_data, status=status.HTTP_201_CREATED)
        
    except Exception as e:
        return Response({
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
@permission_classes([AllowAny])
def razorpay_config(request):
    """
    Get Razorpay configuration details for frontend
    """
    config_data = {
        'key_id': RAZORPAY_KEY_ID,
        'mode': RAZORPAY_MODE,
        'environment': 'live' if RAZORPAY_MODE == 'live' or 'live' in RAZORPAY_KEY_ID else 'test',
        'checkout_url': 'https://checkout.razorpay.com/v1/checkout.html',
        'api_url': 'https://api.razorpay.com/v1/',
        'is_test_mode': RAZORPAY_MODE != 'live' and 'live' not in RAZORPAY_KEY_ID
    }
    
    return Response(config_data)

@api_view(['GET'])
@permission_classes([AllowAny])
def get_razorpay_order(request, order_id):
    """
    Get Razorpay order details
    """
    try:
        order = RazorpayOrder.objects.get(order_id=order_id)
        serializer = RazorpayOrderSerializer(order)
        return Response(serializer.data)
    except RazorpayOrder.DoesNotExist:
        return Response({
            'error': 'Order not found'
        }, status=status.HTTP_404_NOT_FOUND)

@api_view(['POST'])
@permission_classes([AllowAny])
def verify_razorpay_payment(request):
    """
    Verify Razorpay payment signature
    """
    try:
        data = request.data
        razorpay_payment_id = data.get('razorpay_payment_id')
        razorpay_order_id = data.get('razorpay_order_id')
        razorpay_signature = data.get('razorpay_signature')
        
        if not all([razorpay_payment_id, razorpay_order_id, razorpay_signature]):
            return Response({
                'error': 'Missing payment verification parameters'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Verify signature
        text = f"{razorpay_order_id}|{razorpay_payment_id}"
        signature = hmac.new(
            RAZORPAY_KEY_SECRET.encode(),
            text.encode(),
            hashlib.sha256
        ).hexdigest()
        
        if signature != razorpay_signature:
            return Response({
                'error': 'Invalid payment signature'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Update order status
        try:
            order = RazorpayOrder.objects.get(order_id=razorpay_order_id)
            order.status = 'paid'
            order.save()
        except RazorpayOrder.DoesNotExist:
            pass
        
        return Response({
            'success': True,
            'message': 'Payment verified successfully'
        })
        
    except Exception as e:
        return Response({
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
