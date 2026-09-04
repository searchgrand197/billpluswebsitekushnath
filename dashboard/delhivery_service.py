import json
import logging

import requests
from django.conf import settings

logger = logging.getLogger(__name__)

DELHIVERY_BASE_URL = getattr(settings, 'DELHIVERY_BASE_URL', 'https://track.delhivery.com')
DELHIVERY_API_TOKEN = getattr(settings, 'DELHIVERY_API_TOKEN', '')
DELHIVERY_PICKUP_NAME = getattr(settings, 'DELHIVERY_PICKUP_NAME', 'Quirckart')


class DelhiveryError(Exception):
    def __init__(self, message, response=None):
        super().__init__(message)
        self.response = response


def _headers(content_type='application/x-www-form-urlencoded'):
    return {
        'Authorization': f'Token {DELHIVERY_API_TOKEN}',
        'Accept': 'application/json',
        'Content-Type': content_type,
    }


def check_pincode(pincode):
    """Check if a pincode is serviceable via Delhivery."""
    if not DELHIVERY_API_TOKEN:
        raise DelhiveryError('Delhivery API token is not configured')

    url = f'{DELHIVERY_BASE_URL}/c/api/pin-codes/json/'
    params = {
        'token': DELHIVERY_API_TOKEN,
        'filter_codes': str(pincode).strip(),
    }

    try:
        response = requests.get(url, params=params, timeout=15)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as exc:
        logger.exception('Delhivery pincode check failed for %s', pincode)
        raise DelhiveryError(f'Pincode serviceability check failed: {exc}') from exc


def is_pincode_serviceable(pincode, payment_method='cod'):
    """
    Return True when Delhivery can deliver to the pincode.
    Falls back to True if the API is unreachable so checkout is not blocked.
    """
    try:
        api_response = check_pincode(pincode)
    except DelhiveryError:
        logger.warning('Allowing pincode %s after Delhivery API failure', pincode)
        return True, {'fallback': True, 'pincode': str(pincode)}

    delivery_codes = api_response.get('delivery_codes') or []
    for code in delivery_codes:
        postal_code = code.get('postal_code', {})
        is_cod_available = postal_code.get('cod') == 'Y'
        is_prepaid_available = postal_code.get('pre_paid') == 'Y'
        is_deliverable = postal_code.get('deliverable') in (True, 'Y', 'y')

        if payment_method == 'cod' and is_cod_available:
            return True, api_response
        if payment_method in ('prepaid', 'razorpay') and is_prepaid_available:
            return True, api_response
        if is_cod_available or is_prepaid_available or is_deliverable:
            return True, api_response

    return False, api_response


def get_order_delivery_address(order, override_address=None):
    if override_address:
        return override_address
    if getattr(order, 'delivery_address_text', None):
        return order.delivery_address_text
    if order.delivery_address_id and order.delivery_address:
        return order.delivery_address.address
    return 'Address not provided'


def build_shipment_payload(order, pickup_location, return_details, delivery_address=None, overrides=None):
    overrides = overrides or {}

    if order.payment_method == 'prepaid':
        payment_mode = 'Pre-paid'
        cod_amount = ''
    else:
        payment_mode = 'COD'
        cod_amount = str(order.total_amount)

    products_desc = ', '.join(
        f'{item.product.name} x {item.quantity}' for item in order.items.all()
    ) or 'Ayurveda Products'
    total_qty = sum(item.quantity for item in order.items.all()) or 1
    address_text = get_order_delivery_address(order, delivery_address)

    payload = {
        'pickup_location': {
            'name': pickup_location.name or DELHIVERY_PICKUP_NAME,
        },
        'shipments': [
            {
                'name': order.recipient_name or 'Customer',
                'add': address_text,
                'pin': str(order.delivery_pincode),
                'city': order.delivery_city,
                'state': order.delivery_state,
                'country': order.delivery_country or 'India',
                'phone': str(order.recipient_phone),
                'order': f'ORD{order.id}',
                'payment_mode': payment_mode,
                'cod_amount': cod_amount,
                'return_name': return_details.name,
                'return_add': return_details.address,
                'return_city': return_details.city,
                'return_state': return_details.state,
                'return_pin': str(return_details.pin),
                'return_phone': str(return_details.phone),
                'return_country': return_details.country or 'India',
                'products_desc': products_desc,
                'hsn_code': '',
                'order_date': order.created_at.strftime('%Y-%m-%d'),
                'total_amount': str(order.total_amount),
                'seller_add': pickup_location.address,
                'seller_name': 'Kushnath Ayurveda',
                'seller_inv': f'ORD{order.id}',
                'quantity': str(total_qty),
                'waybill': '',
                'shipment_width': overrides.get('shipment_width', '10'),
                'shipment_height': overrides.get('shipment_height', '10'),
                'weight': overrides.get('weight', '0.5'),
                'shipping_mode': overrides.get('shipping_mode', 'Surface'),
                'address_type': overrides.get('address_type', 'Home'),
            }
        ],
    }
    return payload


def parse_shipment_error(shipment_response):
    if shipment_response.get('rmk'):
        return shipment_response['rmk']

    packages = shipment_response.get('packages') or []
    if packages:
        remarks = packages[0].get('remarks') or []
        if remarks and remarks[0]:
            return remarks[0]
        if packages[0].get('status') == 'Fail':
            return 'Delhivery rejected the shipment request.'

    return 'Delhivery shipment creation failed.'


def create_shipment(order, pickup_location, return_details, delivery_address=None, overrides=None):
    if not DELHIVERY_API_TOKEN:
        raise DelhiveryError('Delhivery API token is not configured')

    payload = build_shipment_payload(
        order,
        pickup_location,
        return_details,
        delivery_address=delivery_address,
        overrides=overrides,
    )

    url = f'{DELHIVERY_BASE_URL}/api/cmu/create.json'
    body = f'format=json&data={json.dumps(payload)}'

    try:
        response = requests.post(
            url,
            headers=_headers(),
            data=body,
            timeout=30,
        )
        response.raise_for_status()
        return response.json()
    except requests.RequestException as exc:
        logger.exception('Delhivery shipment creation failed for order %s', order.order_id)
        raise DelhiveryError(f'Shipment creation failed: {exc}') from exc


def extract_waybill(shipment_response):
    packages = shipment_response.get('packages') or []
    if packages and packages[0].get('waybill'):
        return packages[0]['waybill']
    return None


def track_shipment(waybill):
    if not DELHIVERY_API_TOKEN:
        raise DelhiveryError('Delhivery API token is not configured')

    url = f'{DELHIVERY_BASE_URL}/api/v1/packages/json/'
    params = {
        'waybill': waybill,
        'token': DELHIVERY_API_TOKEN,
    }

    try:
        response = requests.get(url, params=params, timeout=15)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as exc:
        logger.exception('Delhivery tracking failed for waybill %s', waybill)
        raise DelhiveryError(f'Tracking lookup failed: {exc}') from exc


def apply_shipment_to_order(order, shipment_response):
    order.shipment_created = True
    order.shipment_details = shipment_response
    order.status = 'shipped'
    waybill = extract_waybill(shipment_response)
    if waybill:
        order.tracking_number = waybill
    order.save(
        update_fields=[
            'shipment_created',
            'shipment_details',
            'status',
            'tracking_number',
            'updated_at',
        ]
    )
    return order


def try_create_shipment_for_order(order):
    """
    Attempt to book a Delhivery shipment for a newly created order.
    Returns a result dict; does not raise — order placement should still succeed.
    """
    from orders.models import OrderStatusHistory

    result = {
        'success': False,
        'shipment_status': 'Not Attempted',
        'tracking_number': None,
        'message': '',
        'delhivery_response': None,
    }

    if order.shipment_created and order.tracking_number:
        result.update({
            'success': True,
            'shipment_status': 'Shipment Already Created',
            'tracking_number': order.tracking_number,
            'message': 'Shipment was already booked for this order.',
            'delhivery_response': order.shipment_details,
        })
        return result

    from dashboard.models import PickupLocation, ReturnDetails

    pickup_location = PickupLocation.objects.first()
    return_details = ReturnDetails.objects.first()
    if not pickup_location or not return_details:
        result['shipment_status'] = 'Shipment Failed'
        result['message'] = 'Pickup location or return details are not configured in admin.'
        return result

    delivery_address = get_order_delivery_address(order)
    if delivery_address == 'Address not provided':
        result['shipment_status'] = 'Shipment Failed'
        result['message'] = 'Order does not have a delivery address.'
        return result

    try:
        shipment_response = create_shipment(
            order,
            pickup_location,
            return_details,
            delivery_address=delivery_address,
        )
    except DelhiveryError as exc:
        result['shipment_status'] = 'Shipment Failed'
        result['message'] = str(exc)
        return result

    result['delhivery_response'] = shipment_response

    if shipment_response.get('success'):
        apply_shipment_to_order(order, shipment_response)
        waybill = extract_waybill(shipment_response)
        OrderStatusHistory.objects.create(
            order=order,
            status='shipped',
            notes=f'Shipment auto-created via Delhivery. AWB: {waybill or "N/A"}',
        )
        result.update({
            'success': True,
            'shipment_status': 'Shipment Created',
            'tracking_number': waybill,
            'message': 'Your package has been booked with Delhivery.',
        })
    else:
        result['shipment_status'] = 'Shipment Failed'
        result['message'] = parse_shipment_error(shipment_response)

    return result
