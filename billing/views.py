from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from rest_framework import viewsets, status, permissions
from rest_framework.response import Response
from rest_framework.decorators import action, api_view
from django.db import models, IntegrityError
from django.db.models import Sum, F, Count, Max, Value, ProtectedError, ExpressionWrapper, DecimalField, Q
from django.db.models.functions import Coalesce
from .models import (
    Product,
    ProductCategory,
    Stock,
    Invoice,
    InvoiceItem,
    CompanySettings,
    BackupHistory,
    PurchaseOrder,
    PurchaseOrderItem,
    Customer,
    CustomerLedgerEntry,
    PaymentReceived,
    RawMaterial,
    Recipe,
    RecipeItem,
    convert_quantity_units,
    ManufacturingLog,
    ManufacturingItemLog,
    ProductBatch,
    consume_product_batches,
    restore_product_batches,
    StockMovementLog,
)
from .serializers import (
    ProductCategorySerializer,
    ProductSerializer,
    StockSerializer,
    InvoiceSerializer,
    InvoiceItemSerializer,
    CustomerSerializer,
    PaymentReceivedSerializer,
    CompanySettingsSerializer,
    PurchaseOrderSerializer,
    PurchaseOrderItemSerializer,
    RawMaterialSerializer,
    RecipeSerializer,
    RecipeItemSerializer,
    ManufacturingLogSerializer,
    ManufacturingItemLogSerializer,
    StockMovementLogSerializer,
)
from .forms import ProductForm, StockForm, InvoiceForm, PaymentReceivedForm
from datetime import datetime, timedelta
from django.utils import timezone
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from django.db import transaction
from .utils import create_invoice_pdf
from .print_utils import get_wkhtmltopdf_config, get_pdf_options
from decimal import Decimal, InvalidOperation
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from pdf2image import convert_from_bytes
import io
import os
from django.conf import settings
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from io import BytesIO
from django.urls import reverse
import json
import shutil
import zipfile
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.core.files.storage import default_storage
import tempfile
import base64
from django.core.cache import cache
from uuid import uuid4
from django.template.loader import render_to_string



def _parse_coupon_server_response(resp, *, endpoint_hint=None):
    """
    Parse JSON from a requests.Response from the coupon server.
    If the body is HTML (common for 404/500) or not JSON, return a dict with
    success=False and a clear error for the UI instead of failing opaquely.

    endpoint_hint: path for messages, e.g. coupon_api.apply_coupon_path or redeem_coupon_path.
    """
    path_hint = endpoint_hint or coupon_api.apply_coupon_path
    try:
        data = resp.json()
    except ValueError:
        text = (resp.text or '')
        stripped = text.strip()
        status = resp.status_code
        base = coupon_api.base_url.rstrip('/')
        if not stripped:
            return {
                'success': False,
                'error': (
                    f'Coupon server returned empty response (HTTP {status}). '
                    f'Check that the service is running and `base_url` in billing/coupon_api.py '
                    f'matches the server (currently {coupon_api.base_url!r}).'
                ),
            }
        low = stripped[:1200].lower()
        if '<html' in low or stripped.lstrip().startswith('<!') or '<body' in low:
            return {
                'success': False,
                'error': (
                    f'Coupon server sent a web page (HTTP {status}), not JSON — often a 404 or proxy error. '
                    f'Confirm POST {path_hint} exists on {base} and restart the coupon server.'
                ),
            }
        snippet = stripped.replace('\n', ' ')[:220]
        return {
            'success': False,
            'error': (
                f'Coupon server response was not valid JSON (HTTP {status}). {snippet}'
            ),
        }

    if not isinstance(data, dict):
        return {
            'success': False,
            'error': f'Coupon server returned unexpected JSON (HTTP {resp.status_code}).',
        }
    return data


def _coupon_app_public_base_url():
    """Public base URL of the Node coupon app (where /scanner and /api/bms-session live)."""
    url = getattr(settings, 'COUPON_APP_PUBLIC_BASE_URL', None) or coupon_api.base_url
    return (url or '').strip().rstrip('/')


def register_coupon_scan_session_on_node(sid, bms_scan_submit_url, bms_user_identifier=None, pairing_code=None):
    """
    Tell the coupon Node app to remember (sid -> BMS submit URL) so the browser can open
    /scanner?sid=... without putting the Billvice URL in the address bar.
    """
    secret = getattr(settings, 'COUPON_NODE_REGISTER_SECRET', '') or ''
    if not secret:
        return False
    import requests

    base = _coupon_app_public_base_url()
    if not base or not sid or not bms_scan_submit_url:
        return False
    try:
        r = requests.post(
            f'{base}/api/bms-session/register',
            json={
                'sid': sid, 
                'bmsScanSubmitUrl': bms_scan_submit_url, 
                'bmsUserIdentifier': bms_user_identifier,
                'pairingCode': pairing_code
            },
            headers={'X-Bms-Internal-Secret': secret},
            timeout=8,
            verify=coupon_api.verify_ssl,
        )
        if not r.ok:
            print(f"[views.register] FAILED: HTTP {r.status_code} - {r.text}")
            return False
        try:
            data = r.json()
        except ValueError:
            return True
        return bool(data.get('success', True))
    except Exception as e:
        print(f"[views.register] EXCEPTION: {e}")
        return False


def build_app_scanner_url(scanner_base_url, sid, bms_scan_submit_url, bms_user_identifier=None, pairing_code=None):
    """Prefer clean /scanner?sid=... when the coupon server accepts registration."""
    from urllib.parse import quote

    if register_coupon_scan_session_on_node(sid, bms_scan_submit_url, bms_user_identifier, pairing_code):
        return f'{scanner_base_url}/scanner?sid={sid}'
    return (
        f'{scanner_base_url}/scanner'
        f'?sid={sid}'
        f'&bmsScanSubmitUrl={quote(bms_scan_submit_url, safe="")}'
    )


from num2words import num2words
import re

class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer

    def get_queryset(self):
        queryset = Product.objects.all()
        category_id = self.request.query_params.get('category_id')
        search = self.request.query_params.get('search') or self.request.query_params.get('q')
        if category_id:
            queryset = queryset.filter(category_id=category_id)
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) | Q(sku__icontains=search) | Q(category__name__icontains=search)
            )
        return queryset.select_related('stock', 'category').prefetch_related('batches')

    @action(detail=True, methods=['post'])
    def update_stock(self, request, pk=None):
        product = self.get_object()
        stock = product.stock
        quantity = request.data.get('quantity')
        
        if quantity is not None:
            stock.quantity = Decimal(str(quantity))
            stock.save()
            return Response(StockSerializer(stock).data)
        return Response({'error': 'quantity is required'}, status=400)

    def destroy(self, request, *args, **kwargs):
        try:
            return super().destroy(request, *args, **kwargs)
        except ProtectedError:
            return Response(
                {'error': 'Cannot delete this product because it is used on bills or purchase orders.'},
                status=400,
            )


class ProductCategoryViewSet(viewsets.ModelViewSet):
    queryset = ProductCategory.objects.all()
    serializer_class = ProductCategorySerializer
class CustomerViewSet(viewsets.ModelViewSet):
    queryset = Customer.objects.all()
    serializer_class = CustomerSerializer
    def get_queryset(self):
        queryset = Customer.objects.all()
        search = self.request.query_params.get('search') or self.request.query_params.get('q')
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) | Q(phone__icontains=search) | Q(email__icontains=search)
            )
        return queryset

    def destroy(self, request, *args, **kwargs):
        try:
            return super().destroy(request, *args, **kwargs)
        except ProtectedError:
            return Response(
                {'error': 'Cannot delete this customer because related records still exist.'},
                status=400,
            )

class PaymentReceivedViewSet(viewsets.ModelViewSet):
    queryset = PaymentReceived.objects.all().order_by('-created_at')
    serializer_class = PaymentReceivedSerializer
    @transaction.atomic
    def perform_create(self, serializer):
        payment = serializer.save()
        customer = payment.customer
        
        last_entry = customer.ledger_entries.order_by('-id').first()
        prev_balance = last_entry.balance_after if last_entry else customer.outstanding_balance
        new_balance = prev_balance - payment.amount
        
        CustomerLedgerEntry.objects.create(
            customer=customer,
            invoice=payment.invoice,
            entry_type='payment',
            debit=Decimal('0'),
            credit=payment.amount,
            balance_after=new_balance,
            entry_date=payment.payment_date,
            description=f"Payment Received ({payment.get_payment_method_display()}) {payment.reference_number}".strip()
        )
        
        customer.outstanding_balance = new_balance
        customer.save(update_fields=['outstanding_balance', 'updated_at'])

        discount = Decimal(str(self.request.data.get('discount') or 0))
        if discount > 0:
            last_entry = customer.ledger_entries.order_by('-id').first()
            prev_balance = last_entry.balance_after if last_entry else customer.outstanding_balance
            adj_balance = prev_balance - discount
            CustomerLedgerEntry.objects.create(
                customer=customer,
                invoice=payment.invoice,
                entry_type='adjustment',
                debit=Decimal('0'),
                credit=discount,
                balance_after=adj_balance,
                entry_date=payment.payment_date,
                description=f'Discount allowed on payment ₹{discount}',
            )
            customer.outstanding_balance = adj_balance
            customer.save(update_fields=['outstanding_balance', 'updated_at'])

class CompanySettingsViewSet(viewsets.ModelViewSet):
    queryset = CompanySettings.objects.all()
    serializer_class = CompanySettingsSerializer
class RawMaterialViewSet(viewsets.ModelViewSet):
    queryset = RawMaterial.objects.all()
    serializer_class = RawMaterialSerializer
    def get_queryset(self):
        queryset = RawMaterial.objects.filter(is_active=True)
        search = self.request.query_params.get('search') or self.request.query_params.get('q')
        category = self.request.query_params.get('category')
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) | Q(material_code__icontains=search) | Q(category__icontains=search)
            )
        if category:
            queryset = queryset.filter(category=category)
        return queryset

    @action(detail=True, methods=['post'])
    def adjust_stock(self, request, pk=None):
        material = self.get_object()
        quantity_change = Decimal(str(request.data.get('quantity_change', '0')))
        reason = request.data.get('reason', 'Manual Adjustment')
        
        prev_balance = material.current_stock
        new_balance = prev_balance + quantity_change
        if new_balance < 0:
            return Response({'error': 'Stock balance cannot be negative.'}, status=status.HTTP_400_BAD_REQUEST)
        
        material.current_stock = new_balance
        material.save()

        unit_cost = material.purchase_price or Decimal('0')
        reason_l = (reason or '').lower()
        if quantity_change > 0 and ('purchase' in reason_l or 'entry' in reason_l):
            movement_type = 'purchase'
        elif quantity_change == 0:
            movement_type = 'opening_stock'
        else:
            movement_type = 'adjustment'

        StockMovementLog.objects.create(
            item_type='raw_material',
            raw_material=material,
            movement_type=movement_type,
            quantity=quantity_change,
            previous_balance=prev_balance,
            new_balance=new_balance,
            unit_cost=unit_cost,
            amount=(quantity_change * unit_cost).quantize(Decimal('0.01')),
            reason=reason
        )

        return Response(RawMaterialSerializer(material).data)

    @action(detail=True, methods=['get'])
    def history(self, request, pk=None):
        material = self.get_object()
        movements = (
            StockMovementLog.objects.filter(raw_material=material)
            .select_related('raw_material', 'product')
            .order_by('-created_at')
        )
        serialized = StockMovementLogSerializer(movements, many=True).data

        qty_in = Decimal('0')
        qty_consumed = Decimal('0')
        spent_into_finished = Decimal('0')
        for row in serialized:
            qty = Decimal(str(row.get('quantity') or 0))
            if qty > 0:
                qty_in += qty
            if row.get('movement_type') == 'manufacturing_consumption':
                qty_consumed += abs(qty)
                spent_into_finished += abs(Decimal(str(row.get('amount_display') or 0)))

        return Response({
            'material_id': material.id,
            'material_name': material.name,
            'material_code': material.material_code,
            'unit': material.unit,
            'current_stock': material.current_stock,
            'purchase_price': material.purchase_price,
            'qty_in': qty_in,
            'qty_consumed': qty_consumed,
            'spent_into_finished_products': spent_into_finished,
            'movements': serialized,
        })


class RecipeViewSet(viewsets.ModelViewSet):
    queryset = Recipe.objects.all()
    serializer_class = RecipeSerializer
    @transaction.atomic
    def create(self, request, *args, **kwargs):
        product_id = request.data.get('product')
        if not product_id:
            return Response({'error': 'Product is required.'}, status=status.HTTP_400_BAD_REQUEST)

        product = get_object_or_404(Product, id=product_id)
        yield_qty = Decimal(str(request.data.get('yield_quantity', '1') or '1'))
        notes = request.data.get('notes', '')
        items_data = request.data.get('items', [])

        if not items_data:
            return Response({'error': 'At least one valid raw material ingredient is required.'}, status=status.HTTP_400_BAD_REQUEST)

        extra_charges = request.data.get('extra_charges') or []
        if not isinstance(extra_charges, list):
            extra_charges = []
        cleaned_charges = []
        for charge in extra_charges:
            if not isinstance(charge, dict):
                continue
            name = str(charge.get('name', '') or '').strip()
            try:
                amount = Decimal(str(charge.get('amount', '0') or '0'))
            except Exception:
                amount = Decimal('0')
            if name:
                cleaned_charges.append({'name': name, 'amount': str(amount.quantize(Decimal('0.01')))})

        recipe, _ = Recipe.objects.update_or_create(
            product=product,
            defaults={'yield_quantity': yield_qty, 'notes': notes, 'extra_charges': cleaned_charges}
        )
        recipe.items.all().delete()

        for item in items_data:
            rm_id = item.get('raw_material')
            qty_entered = Decimal(str(item.get('quantity_required', '1') or '1'))
            rm = get_object_or_404(RawMaterial, id=rm_id)
            input_unit = str(item.get('input_unit', '') or rm.unit).lower()
            qty_stock = convert_quantity_units(qty_entered, input_unit, rm.unit)
            if qty_stock <= 0:
                continue
            RecipeItem.objects.create(
                recipe=recipe,
                raw_material=rm,
                quantity_required=qty_stock,
                input_unit=input_unit,
            )

        return Response(RecipeSerializer(recipe).data, status=status.HTTP_201_CREATED)


class ManufacturingViewSet(viewsets.ModelViewSet):
    queryset = ManufacturingLog.objects.all().order_by('-created_at')
    serializer_class = ManufacturingLogSerializer

    def get_queryset(self):
        queryset = ManufacturingLog.objects.all().order_by('-created_at')
        search = self.request.query_params.get('search') or self.request.query_params.get('q')
        if search:
            queryset = queryset.filter(
                Q(manufacturing_id__icontains=search) |
                Q(batch_number__icontains=search) |
                Q(product__name__icontains=search)
            )
        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        return queryset.select_related('product', 'finished_batch')

    def _parse_payload(self, data):
        product_id = data.get('product')
        if not product_id:
            return None, 'Please select a finished product to manufacture.'
        prod_qty = Decimal(str(data.get('production_quantity', '1') or '1'))
        if prod_qty <= 0:
            return None, 'Production quantity must be greater than zero.'
        batch_no = (data.get('batch_number') or '').strip() or f"BATCH-{int(datetime.now().timestamp())}"
        return {
            'product': get_object_or_404(Product, id=product_id),
            'prod_qty': prod_qty,
            'batch_no': batch_no,
            'mfg_date': data.get('mfg_date') or timezone.localdate(),
            'exp_date': data.get('exp_date') or None,
            'operator': data.get('operator', ''),
            'notes': data.get('notes', ''),
            'labor_cost': Decimal(str(data.get('labor_cost', '0') or '0')),
            'packaging_cost': Decimal(str(data.get('packaging_cost', '0') or '0')),
            'other_overhead_cost': Decimal(str(data.get('other_overhead_cost', '0') or '0')),
            'update_cost_price': data.get('update_product_cost_price', True),
        }, None

    def _manufacturing_plan(self, product, prod_qty, check_stock=False):
        recipe = getattr(product, 'recipe', None)
        if not recipe or not recipe.items.exists():
            return recipe, [], Decimal('0'), []

        batch_scale = prod_qty / (recipe.yield_quantity or Decimal('1'))
        shortages = []
        consumed_plan = []
        raw_material_cost = Decimal('0')

        for item in recipe.items.all():
            rm = item.raw_material
            required_qty = item.quantity_required * batch_scale
            cost = required_qty * rm.purchase_price
            raw_material_cost += cost
            consumed_plan.append({
                'raw_material': rm,
                'required_qty': required_qty,
                'unit_cost': rm.purchase_price,
                'total_cost': cost,
            })
            if check_stock and rm.current_stock < required_qty:
                shortages.append({
                    'material': rm.name,
                    'required': float(required_qty),
                    'available': float(rm.current_stock),
                    'shortage': float(required_qty - rm.current_stock),
                    'unit': rm.unit,
                })

        return recipe, consumed_plan, raw_material_cost, shortages

    def _execute_manufacturing_batch(self, mfg_log, product, consumed_plan, prod_qty, batch_no, mfg_date, exp_date, unit_cost, update_cost_price):
        mfg_id = mfg_log.manufacturing_id

        for plan in consumed_plan:
            rm = plan['raw_material']
            qty = plan['required_qty']
            prev_stk = rm.current_stock
            new_stk = prev_stk - qty
            rm.current_stock = new_stk
            rm.save()

            ManufacturingItemLog.objects.create(
                manufacturing=mfg_log,
                raw_material=rm,
                quantity_consumed=qty,
                unit_cost=plan['unit_cost'],
                total_cost=plan['total_cost'],
            )

            StockMovementLog.objects.create(
                item_type='raw_material',
                raw_material=rm,
                product=product,
                movement_type='manufacturing_consumption',
                quantity=-qty,
                previous_balance=prev_stk,
                new_balance=new_stk,
                unit_cost=plan['unit_cost'],
                amount=plan['total_cost'],
                reference_id=mfg_id,
                reason=f"Consumed for manufacturing {prod_qty} units of {product.name}",
            )

        stock, _ = Stock.objects.get_or_create(product=product)
        prev_prod_stk = stock.quantity
        new_prod_stk = prev_prod_stk + prod_qty
        stock.quantity = new_prod_stk
        stock.save()

        StockMovementLog.objects.create(
            item_type='finished_product',
            product=product,
            movement_type='manufacturing_output',
            quantity=prod_qty,
            previous_balance=prev_prod_stk,
            new_balance=new_prod_stk,
            reference_id=mfg_id,
            reason=f"Batch {batch_no} manufactured",
        )

        ProductBatch.objects.create(
            product=product,
            manufacturing=mfg_log,
            batch_number=batch_no,
            produced_quantity=prod_qty,
            remaining_quantity=prod_qty,
            mfg_date=mfg_date,
            exp_date=exp_date or None,
            unit_cost=unit_cost,
        )

        if update_cost_price and unit_cost > 0:
            product.cost_price = unit_cost
            product.save(update_fields=['cost_price', 'updated_at'])

    def _apply_costs(self, mfg_log, raw_material_cost, labor_cost, packaging_cost, other_overhead_cost, prod_qty):
        mfg_log.raw_material_cost = raw_material_cost
        mfg_log.labor_cost = labor_cost
        mfg_log.packaging_cost = packaging_cost
        mfg_log.other_overhead_cost = other_overhead_cost
        mfg_log.total_cost = raw_material_cost + labor_cost + packaging_cost + other_overhead_cost
        mfg_log.unit_cost = (mfg_log.total_cost / prod_qty) if prod_qty > 0 else Decimal('0')

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        payload, err = self._parse_payload(request.data)
        if err:
            return Response({'error': err}, status=status.HTTP_400_BAD_REQUEST)

        save_as_draft = request.data.get('save_as_draft') or request.data.get('status') == 'draft'
        product = payload['product']
        prod_qty = payload['prod_qty']
        check_stock = not save_as_draft

        recipe, consumed_plan, raw_material_cost, shortages = self._manufacturing_plan(product, prod_qty, check_stock=check_stock)

        if not save_as_draft:
            if not recipe or not recipe.items.exists():
                return Response(
                    {'error': f"No Recipe (Bill of Materials) defined for product '{product.name}'. Please define recipe first."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            if shortages:
                return Response(
                    {'error': 'Insufficient raw material stock for production batch.', 'shortages': shortages},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        mfg_id = f"MFG-{int(datetime.now().timestamp())}"
        mfg_log = ManufacturingLog.objects.create(
            manufacturing_id=mfg_id,
            product=product,
            recipe=recipe,
            production_quantity=prod_qty,
            batch_number=payload['batch_no'],
            mfg_date=payload['mfg_date'],
            exp_date=payload['exp_date'],
            status='draft' if save_as_draft else 'completed',
            operator=payload['operator'],
            labor_cost=payload['labor_cost'],
            packaging_cost=payload['packaging_cost'],
            other_overhead_cost=payload['other_overhead_cost'],
            notes=payload['notes'],
            raw_material_cost=Decimal('0'),
            total_cost=Decimal('0'),
            unit_cost=Decimal('0'),
        )
        self._apply_costs(
            mfg_log, raw_material_cost,
            payload['labor_cost'], payload['packaging_cost'], payload['other_overhead_cost'],
            prod_qty,
        )
        mfg_log.save()

        if not save_as_draft:
            self._execute_manufacturing_batch(
                mfg_log, product, consumed_plan, prod_qty,
                payload['batch_no'], payload['mfg_date'], payload['exp_date'],
                mfg_log.unit_cost, payload['update_cost_price'],
            )

        return Response(ManufacturingLogSerializer(mfg_log).data, status=status.HTTP_201_CREATED)

    @transaction.atomic
    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        data = request.data
        finalize = request.data.get('finalize') or request.data.get('complete_batch')

        if instance.status == 'draft':
            payload, err = self._parse_payload({**{
                'product': instance.product_id,
                'production_quantity': instance.production_quantity,
                'batch_number': instance.batch_number,
                'mfg_date': instance.mfg_date,
                'exp_date': instance.exp_date,
                'operator': instance.operator,
                'notes': instance.notes,
                'labor_cost': instance.labor_cost,
                'packaging_cost': instance.packaging_cost,
                'other_overhead_cost': instance.other_overhead_cost,
                'update_product_cost_price': True,
            }, **data})
            if err:
                return Response({'error': err}, status=status.HTTP_400_BAD_REQUEST)

            product = payload['product']
            prod_qty = payload['prod_qty']
            instance.product = product
            instance.production_quantity = prod_qty
            instance.batch_number = payload['batch_no']
            instance.mfg_date = payload['mfg_date']
            instance.exp_date = payload['exp_date']
            instance.operator = payload['operator']
            instance.notes = payload['notes']

            recipe, consumed_plan, raw_material_cost, shortages = self._manufacturing_plan(
                product, prod_qty, check_stock=bool(finalize),
            )
            instance.recipe = recipe
            self._apply_costs(
                instance, raw_material_cost,
                payload['labor_cost'], payload['packaging_cost'], payload['other_overhead_cost'],
                prod_qty,
            )
            instance.save()

            if finalize:
                if not recipe or not recipe.items.exists():
                    return Response(
                        {'error': f"No Recipe (Bill of Materials) defined for product '{product.name}'. Please define recipe first."},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
                if shortages:
                    return Response(
                        {'error': 'Insufficient raw material stock for production batch.', 'shortages': shortages},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
                instance.status = 'completed'
                instance.save(update_fields=['status', 'updated_at'])
                self._execute_manufacturing_batch(
                    instance, product, consumed_plan, prod_qty,
                    payload['batch_no'], payload['mfg_date'], payload['exp_date'],
                    instance.unit_cost, payload['update_cost_price'],
                )

            return Response(ManufacturingLogSerializer(instance).data)

        if finalize:
            return Response({'error': 'Only draft batches can be finalized.'}, status=status.HTTP_400_BAD_REQUEST)

        editable_fields = {
            'batch_number': lambda v: str(v or '').strip(),
            'mfg_date': lambda v: v,
            'exp_date': lambda v: v or None,
            'operator': lambda v: str(v or '').strip(),
            'notes': lambda v: str(v or '').strip(),
            'labor_cost': lambda v: Decimal(str(v or '0')),
            'packaging_cost': lambda v: Decimal(str(v or '0')),
            'other_overhead_cost': lambda v: Decimal(str(v or '0')),
        }

        for field, parser in editable_fields.items():
            if field in data:
                setattr(instance, field, parser(data[field]))

        if not str(instance.batch_number or '').strip():
            return Response({'error': 'Batch number is required.'}, status=status.HTTP_400_BAD_REQUEST)

        self._apply_costs(
            instance, instance.raw_material_cost,
            instance.labor_cost, instance.packaging_cost, instance.other_overhead_cost,
            instance.production_quantity,
        )
        instance.save()

        batch = getattr(instance, 'finished_batch', None)
        if batch:
            batch.batch_number = instance.batch_number
            batch.mfg_date = instance.mfg_date
            batch.exp_date = instance.exp_date
            batch.unit_cost = instance.unit_cost
            batch.save(update_fields=['batch_number', 'mfg_date', 'exp_date', 'unit_cost'])

        return Response(ManufacturingLogSerializer(instance).data)

    def partial_update(self, request, *args, **kwargs):
        kwargs['partial'] = True
        return self.update(request, *args, **kwargs)

    @transaction.atomic
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.status != 'draft':
            return Response({'error': 'Only draft manufacturing batches can be deleted.'}, status=status.HTTP_400_BAD_REQUEST)
        instance.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['post'])
    @transaction.atomic
    def finalize(self, request, pk=None):
        instance = self.get_object()
        if instance.status != 'draft':
            return Response({'error': 'Only draft batches can be finalized.'}, status=status.HTTP_400_BAD_REQUEST)

        payload, err = self._parse_payload({
            'product': instance.product_id,
            'production_quantity': instance.production_quantity,
            'batch_number': instance.batch_number,
            'mfg_date': instance.mfg_date,
            'exp_date': instance.exp_date,
            'operator': instance.operator,
            'notes': instance.notes,
            'labor_cost': instance.labor_cost,
            'packaging_cost': instance.packaging_cost,
            'other_overhead_cost': instance.other_overhead_cost,
            'update_product_cost_price': request.data.get('update_product_cost_price', True),
            **request.data,
        })
        if err:
            return Response({'error': err}, status=status.HTTP_400_BAD_REQUEST)

        product = payload['product']
        prod_qty = payload['prod_qty']
        recipe, consumed_plan, raw_material_cost, shortages = self._manufacturing_plan(product, prod_qty, check_stock=True)

        if not recipe or not recipe.items.exists():
            return Response(
                {'error': f"No Recipe (Bill of Materials) defined for product '{product.name}'. Please define recipe first."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if shortages:
            return Response(
                {'error': 'Insufficient raw material stock for production batch.', 'shortages': shortages},
                status=status.HTTP_400_BAD_REQUEST,
            )

        instance.product = product
        instance.production_quantity = prod_qty
        instance.batch_number = payload['batch_no']
        instance.mfg_date = payload['mfg_date']
        instance.exp_date = payload['exp_date']
        instance.operator = payload['operator']
        instance.notes = payload['notes']
        instance.recipe = recipe
        instance.status = 'completed'
        self._apply_costs(
            instance, raw_material_cost,
            payload['labor_cost'], payload['packaging_cost'], payload['other_overhead_cost'],
            prod_qty,
        )
        instance.save()

        self._execute_manufacturing_batch(
            instance, product, consumed_plan, prod_qty,
            payload['batch_no'], payload['mfg_date'], payload['exp_date'],
            instance.unit_cost, payload['update_cost_price'],
        )

        return Response(ManufacturingLogSerializer(instance).data)


class StockMovementLogViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = StockMovementLog.objects.all().order_by('-created_at')
    serializer_class = StockMovementLogSerializer
    def get_queryset(self):
        queryset = StockMovementLog.objects.select_related('raw_material', 'product').order_by('-created_at')
        raw_material = self.request.query_params.get('raw_material')
        item_type = self.request.query_params.get('item_type')
        movement_type = self.request.query_params.get('movement_type')
        if raw_material:
            queryset = queryset.filter(raw_material_id=raw_material)
        if item_type:
            queryset = queryset.filter(item_type=item_type)
        if movement_type:
            queryset = queryset.filter(movement_type=movement_type)
        return queryset

@api_view(['GET'])
def api_global_search(request):
    """
    Unified global search endpoint across Products, Customers, Invoices, and Purchase Orders.
    Returns categorized JSON results.
    """
    query = request.query_params.get('q', '').strip()
    if not query:
        return Response({
            'products': [],
            'customers': [],
            'invoices': [],
            'purchase_orders': [],
            'query': query
        })

    products_qs = Product.objects.filter(
        Q(name__icontains=query) |
        Q(sku__icontains=query) |
        Q(category__name__icontains=query)
    ).select_related('category', 'stock')[:8]

    products_data = []
    for p in products_qs:
        stock_qty = p.stock.quantity if hasattr(p, 'stock') and p.stock else 0
        products_data.append({
            'id': p.id,
            'name': p.name,
            'sku': p.sku or '',
            'price': float(p.price),
            'category': p.category.name if p.category else '',
            'uom': p.uom or 'Unit',
            'stock': stock_qty,
        })

    customers_qs = Customer.objects.filter(
        Q(name__icontains=query) |
        Q(phone__icontains=query) |
        Q(email__icontains=query) |
        Q(address__icontains=query)
    )[:8]

    customers_data = []
    for c in customers_qs:
        customers_data.append({
            'id': c.id,
            'name': c.name,
            'phone': c.phone or '',
            'email': c.email or '',
            'outstanding_balance': float(c.outstanding_balance or 0),
        })

    invoices_qs = Invoice.objects.filter(
        Q(invoice_number__icontains=query) |
        Q(customer_name__icontains=query) |
        Q(customer_phone__icontains=query)
    ).order_by('-created_at')[:8]

    invoices_data = []
    for inv in invoices_qs:
        invoices_data.append({
            'id': inv.id,
            'invoice_number': inv.invoice_number,
            'customer_name': inv.customer_name or 'Walk-in Customer',
            'customer_phone': inv.customer_phone or '',
            'total_amount': float(inv.total_amount),
            'payment_status': inv.status,
            'created_at': inv.created_at.strftime('%Y-%m-%d %H:%M') if inv.created_at else '',
        })

    po_qs = PurchaseOrder.objects.filter(
        Q(order_number__icontains=query) |
        Q(supplier_name__icontains=query)
    ).order_by('-created_at')[:8]

    po_data = []
    for po in po_qs:
        po_data.append({
            'id': po.id,
            'po_number': po.order_number,
            'supplier_name': po.supplier_name,
            'status': po.status,
            'total_amount': float(po.total_amount),
            'created_at': po.created_at.strftime('%Y-%m-%d %H:%M') if po.created_at else '',
        })

    return Response({
        'products': products_data,
        'customers': customers_data,
        'invoices': invoices_data,
        'purchase_orders': po_data,
        'query': query
    })

@api_view(['GET'])
def api_dashboard_summary(request):
    """DRF endpoint providing complete Ayurvedic ERP dashboard KPIs for React SPA."""
    today = timezone.localdate()

    today_invoices_qs = Invoice.objects.filter(invoice_date=today)
    today_sales = today_invoices_qs.aggregate(total=Coalesce(Sum('total_amount'), Value(Decimal('0')), output_field=DecimalField()))['total']
    today_bills = today_invoices_qs.count()

    total_products = Product.objects.count()
    total_customers = Customer.objects.count()

    low_stock_finished_products = Stock.objects.filter(quantity__lte=F('low_stock_threshold')).count()
    low_stock_raw_materials = RawMaterial.objects.filter(current_stock__lte=F('minimum_stock'), is_active=True).count()

    total_finished_stock_value = Stock.objects.aggregate(
        total=Coalesce(Sum(F('quantity') * F('product__cost_price')), Value(Decimal('0')), output_field=DecimalField())
    )['total']

    total_raw_material_stock_value = RawMaterial.objects.filter(is_active=True).aggregate(
        total=Coalesce(Sum(F('current_stock') * F('purchase_price')), Value(Decimal('0')), output_field=DecimalField())
    )['total']

    today_mfg_count = ManufacturingLog.objects.filter(mfg_date=today, status='completed').count()

    total_sales = Invoice.objects.aggregate(total=Coalesce(Sum('total_amount'), Value(Decimal('0')), output_field=DecimalField()))['total']
    total_invoices = Invoice.objects.count()
    total_dues = Invoice.objects.aggregate(total=Coalesce(Sum('outstanding_amount'), Value(Decimal('0')), output_field=DecimalField()))['total']

    recent_invoices = InvoiceSerializer(Invoice.objects.order_by('-created_at')[:5], many=True).data
    recent_mfg = ManufacturingLogSerializer(ManufacturingLog.objects.filter(status='completed').order_by('-created_at')[:5], many=True).data
    recent_movements = StockMovementLogSerializer(StockMovementLog.objects.order_by('-created_at')[:5], many=True).data

    return Response({
        'today_sales': today_sales,
        'today_bills': today_bills,
        'total_products': total_products,
        'total_customers': total_customers,
        'low_stock_finished_products': low_stock_finished_products,
        'low_stock_raw_materials': low_stock_raw_materials,
        'total_finished_stock_value': total_finished_stock_value,
        'total_raw_material_stock_value': total_raw_material_stock_value,
        'today_mfg_count': today_mfg_count,
        'total_sales': total_sales,
        'total_invoices': total_invoices,
        'total_dues': total_dues,
        'recent_invoices': recent_invoices,
        'recent_mfg': recent_mfg,
        'recent_movements': recent_movements,
    })

@api_view(['GET'])
def api_reports_summary(request):
    """DRF endpoint providing sales reports & profit metrics for React SPA."""
    total_sales = Invoice.objects.aggregate(total=Coalesce(Sum('total_amount'), Value(Decimal('0')), output_field=DecimalField()))['total']
    total_orders = Invoice.objects.count()
    total_customers = Customer.objects.count()
    total_dues = Invoice.objects.aggregate(total=Coalesce(Sum('outstanding_amount'), Value(Decimal('0')), output_field=DecimalField()))['total']

    items_sold = InvoiceItem.objects.aggregate(total=Coalesce(Sum('quantity'), Value(Decimal('0')), output_field=DecimalField()))['total']

    recent_invoices = InvoiceSerializer(Invoice.objects.order_by('-created_at')[:10], many=True).data

    return Response({
        'total_sales': total_sales,
        'total_orders': total_orders,
        'total_customers': total_customers,
        'total_dues': total_dues,
        'total_products_sold': items_sold,
        'recent_invoices': recent_invoices,
    })

@api_view(['GET'])
def api_balance_sheet(request):
    """Financial balance sheet snapshot for SPA."""
    from .financial_reports import compute_balance_sheet
    as_of = request.query_params.get('as_of')
    return Response(compute_balance_sheet(as_of))


@api_view(['GET'])
def api_dues_summary(request):
    """DRF endpoint providing outstanding dues and party balances for React SPA."""
    customers_with_dues = Customer.objects.filter(outstanding_balance__gt=0)
    serializer = CustomerSerializer(customers_with_dues, many=True)
    total_outstanding = customers_with_dues.aggregate(total=Coalesce(Sum('outstanding_balance'), Value(Decimal('0')), output_field=DecimalField()))['total']
    return Response({
        'total_outstanding': total_outstanding,
        'customers': serializer.data,
    })

def _infer_payment_mode(entry):
    blob = f'{entry.description or ""} {(entry.invoice.notes if entry.invoice_id else "") or ""}'.lower()
    if 'upi' in blob:
        return 'upi', 'UPI'
    if 'bank' in blob:
        return 'bank', 'Bank'
    if 'card' in blob:
        return 'card', 'Card'
    if 'cash' in blob:
        return 'cash', 'Cash'
    if 'credit' in blob:
        return 'credit', 'Credit'
    if 'other' in blob:
        return 'other', 'Other'
    if entry.entry_type == 'invoice':
        return 'credit', 'Credit'
    if entry.entry_type == 'adjustment':
        return 'other', 'Other'
    return 'other', 'Other'


@api_view(['GET'])
def api_customer_ledger(request, customer_id):
    """DRF endpoint providing customer ledger transaction history for React SPA."""
    customer = get_object_or_404(Customer, pk=customer_id)
    entries = CustomerLedgerEntry.objects.filter(customer=customer).select_related('invoice').order_by('id')

    entries_data = []
    for entry in entries:
        debit = entry.debit or Decimal('0')
        credit = entry.credit or Decimal('0')
        signed = debit - credit
        when = entry.created_at or entry.entry_date
        if hasattr(when, 'strftime'):
            when_str = when.strftime('%Y-%m-%d %H:%M') if hasattr(when, 'hour') else when.strftime('%Y-%m-%d')
        else:
            when_str = str(when)
        mode_key, mode_label = _infer_payment_mode(entry)
        entries_data.append({
            'id': entry.id,
            'entry_type': entry.entry_type,
            'debit': debit,
            'credit': credit,
            'amount': signed,
            'balance_after': entry.balance_after,
            'description': entry.description or (
                f"Invoice #{entry.invoice.invoice_number}" if entry.invoice_id else entry.get_entry_type_display()
            ),
            'invoice_id': entry.invoice_id,
            'invoice_number': entry.invoice.invoice_number if entry.invoice_id else '',
            'payment_mode': mode_key,
            'payment_mode_label': mode_label,
            'created_at': when_str,
            'entry_date': str(entry.entry_date) if entry.entry_date else when_str,
        })

    return Response({
        'customer': CustomerSerializer(customer).data,
        'ledger_entries': entries_data,
        'summary': {
            'outstanding': customer.outstanding_balance,
            'total_sales': Invoice.objects.filter(customer_name=customer.name)
                .exclude(status__in=['cancelled', 'draft'])
                .aggregate(t=Sum('total_amount'))['t'] or Decimal('0'),
            'bill_count': Invoice.objects.filter(customer_name=customer.name)
                .exclude(status__in=['cancelled', 'draft'])
                .count(),
            'last_purchase': (
                Invoice.objects.filter(customer_name=customer.name)
                .exclude(status__in=['cancelled', 'draft'])
                .order_by('-invoice_date', '-id')
                .values_list('invoice_date', flat=True)
                .first()
            ),
        },
    })

@api_view(['POST'])
def api_create_invoice_pos(request):
    """DRF endpoint for creating POS invoices directly from React SPA."""
    try:
        with transaction.atomic():
            data = request.data
            customer_name = data.get('customer_name', 'Walk-in Customer')
            customer_phone = data.get('customer_phone', '')
            customer_address = data.get('customer_address', '')
            customer_gstin = data.get('customer_gstin', '')
            customer_state = (data.get('customer_state') or '').strip()
            invoice_date = data.get('invoice_date', timezone.now().date().isoformat())
            due_date = data.get('due_date', timezone.now().date().isoformat())
            payment_type = data.get('payment_type', 'full_payment')
            amount_paid_now = Decimal(str(data.get('amount_paid_now', 0) or 0))
            payment_method = str(data.get('payment_method', 'cash') or 'cash').lower()
            if payment_method not in ('cash', 'upi', 'bank_transfer', 'card', 'other'):
                payment_method = 'cash'
            notes = data.get('notes', '')
            items_data = data.get('items', [])

            if not items_data:
                return Response({'error': 'Invoice must contain at least one item.'}, status=400)

            # Generate unique invoice number
            company_settings = CompanySettings.objects.first()
            prefix = "INV"
            year = datetime.now().year
            last_invoice = Invoice.objects.filter(invoice_number__startswith=f"{prefix}-{year}-").order_by('-id').first()
            if last_invoice:
                try:
                    last_seq = int(last_invoice.invoice_number.split('-')[-1])
                    seq = last_seq + 1
                except ValueError:
                    seq = 1
            else:
                seq = 1
            inv_number = f"{prefix}-{year}-{seq:04d}"

            party = None
            if (customer_name or '').strip():
                qs = Customer.objects.filter(name=(customer_name or '').strip())
                phone = (customer_phone or '').strip()
                party = qs.filter(phone=phone).first() if phone else None
                if not party:
                    party = qs.first()
            if party:
                if not customer_state:
                    customer_state = party.state or ''
                if not customer_gstin:
                    customer_gstin = party.gstin or ''

            customer_gstin = (customer_gstin or '').strip().upper()

            invoice = Invoice.objects.create(
                invoice_number=inv_number,
                customer_name=customer_name,
                customer_phone=customer_phone,
                customer_address=customer_address,
                customer_gstin=customer_gstin,
                customer_state=customer_state,
                invoice_date=invoice_date,
                due_date=due_date,
                notes=notes,
                status='draft'
            )

            for item in items_data:
                product = get_object_or_404(Product, pk=item['product_id'])
                qty = Decimal(str(item.get('quantity', 1)))
                unit_price = Decimal(str(item.get('unit_price', product.price)))
                discount = Decimal(str(item.get('discount', 0) or 0))
                gst_raw = item.get('gst_rate', None)
                gst_rate = Decimal(str(gst_raw)) if gst_raw is not None and str(gst_raw) != '' else None
                InvoiceItem.objects.create(
                    invoice=invoice,
                    product=product,
                    quantity=int(qty),
                    unit_price=unit_price,
                    discount=discount,
                    gst_rate=gst_rate,
                )

                if hasattr(product, 'stock'):
                    product.stock.quantity = max(0, product.stock.quantity - qty)
                    product.stock.save()
                consume_product_batches(product, qty)

            invoice.calculate_totals(update_status=False)
            total_amount = invoice.total_amount

            # Handle payment status & A/R customer ledger
            if payment_type == 'full_payment' or amount_paid_now >= total_amount:
                invoice.status = 'paid'
                invoice.advance_paid = total_amount
                invoice.outstanding_amount = Decimal('0')
            elif payment_type == 'full_credit' or amount_paid_now <= 0:
                invoice.status = 'credit'
                invoice.advance_paid = Decimal('0')
                invoice.outstanding_amount = total_amount
            else:
                invoice.advance_paid = amount_paid_now
                invoice.outstanding_amount = max(Decimal('0'), total_amount - amount_paid_now)
                invoice.status = 'paid' if invoice.outstanding_amount == Decimal('0') else 'partially_paid'

            invoice.save()

            # Record customer ledger + payment received
            if customer_name:
                cust, _ = Customer.objects.get_or_create(name=customer_name, defaults={'phone': customer_phone})
                if invoice.outstanding_amount > Decimal('0'):
                    cust.outstanding_balance += invoice.outstanding_amount
                    cust.save()
                    CustomerLedgerEntry.objects.create(
                        customer=cust,
                        invoice=invoice,
                        entry_type='invoice',
                        debit=invoice.outstanding_amount,
                        credit=Decimal('0'),
                        balance_after=cust.outstanding_balance,
                        description=f"Invoice #{invoice.invoice_number}"
                    )
                if invoice.advance_paid > Decimal('0'):
                    PaymentReceived.objects.create(
                        customer=cust,
                        invoice=invoice,
                        amount=invoice.advance_paid,
                        payment_method=payment_method,
                        notes=f'Collected at billing ({payment_method.upper()})',
                    )

            return Response({
                'message': 'Invoice created successfully',
                'invoice': InvoiceSerializer(invoice).data
            }, status=201)

    except Exception as e:
        return Response({'error': str(e)}, status=400)

class StockViewSet(viewsets.ModelViewSet):
    queryset = Stock.objects.all()
    serializer_class = StockSerializer
    def get_queryset(self):
        queryset = Stock.objects.all()
        search = self.request.query_params.get('search') or self.request.query_params.get('q')
        if search:
            queryset = queryset.filter(
                Q(product__name__icontains=search) | Q(product__sku__icontains=search)
            )
        return queryset.select_related('product').prefetch_related('product__batches')

    @action(detail=False, methods=['get'])
    def low_stock(self, request):
        low_stock_items = Stock.objects.filter(quantity__lte=models.F('low_stock_threshold'))
        serializer = self.get_serializer(low_stock_items, many=True)
        return Response(serializer.data)

class InvoiceViewSet(viewsets.ModelViewSet):
    queryset = Invoice.objects.prefetch_related('items', 'items__product').all()
    serializer_class = InvoiceSerializer
    def get_queryset(self):
        queryset = Invoice.objects.prefetch_related('items', 'items__product').all()
        customer_name = self.request.query_params.get('customer_name', None)
        search = self.request.query_params.get('search') or self.request.query_params.get('q')
        if customer_name:
            queryset = queryset.filter(customer_name__icontains=customer_name)
        if search:
            queryset = queryset.filter(
                Q(invoice_number__icontains=search) |
                Q(customer_name__icontains=search) |
                Q(customer_phone__icontains=search)
            )
        return queryset

    @action(detail=True, methods=['get'])
    def items(self, request, pk=None):
        invoice = self.get_object()
        items = InvoiceItem.objects.filter(invoice=invoice).select_related('product')
        serializer = InvoiceItemSerializer(items, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def generate_pdf(self, request, pk=None):
        invoice = self.get_object()
        return generate_invoice_pdf(request, invoice.id)

    @action(detail=True, methods=['post'])
    @transaction.atomic
    def cancel(self, request, pk=None):
        invoice = self.get_object()
        if invoice.status == 'cancelled':
            return Response({'message': 'Invoice is already cancelled.'})

        for item in invoice.items.all():
            product = item.product
            if hasattr(product, 'stock') and product.stock:
                prev_qty = product.stock.quantity
                restored_qty = prev_qty + Decimal(str(item.quantity))
                product.stock.quantity = restored_qty
                product.stock.save()

                restore_product_batches(product, Decimal(str(item.quantity)))

                StockMovementLog.objects.create(
                    item_type='finished_product',
                    product=product,
                    movement_type='sale_cancellation',
                    quantity=Decimal(str(item.quantity)),
                    previous_balance=prev_qty,
                    new_balance=restored_qty,
                    reference_id=invoice.invoice_number,
                    reason=f"Restored stock from cancelled invoice #{invoice.invoice_number}"
                )

        if invoice.customer_name and invoice.outstanding_amount > 0:
            cust = Customer.objects.filter(name=invoice.customer_name).first()
            if cust:
                last_entry = cust.ledger_entries.order_by('-id').first()
                curr_bal = last_entry.balance_after if last_entry else cust.outstanding_balance
                new_bal = max(Decimal('0'), curr_bal - invoice.outstanding_amount)
                CustomerLedgerEntry.objects.create(
                    customer=cust,
                    invoice=invoice,
                    entry_type='adjustment',
                    debit=Decimal('0'),
                    credit=invoice.outstanding_amount,
                    balance_after=new_bal,
                    description=f"Cancelled Invoice #{invoice.invoice_number}"
                )
                cust.outstanding_balance = new_bal
                cust.save()

        invoice.status = 'cancelled'
        invoice.outstanding_amount = Decimal('0')
        invoice.save()

        return Response(InvoiceSerializer(invoice).data)

def dashboard(request):
    # Get statistics
    total_products = Product.objects.count()
    low_stock_count = Stock.objects.filter(quantity__lte=F('low_stock_threshold')).count()
    out_of_stock_count = Stock.objects.filter(quantity=0).count()

    # Inventory value = sum(price × quantity) — same idea as stock/products views.
    # Use ExpressionWrapper so DB backends handle Decimal correctly.
    total_expr = ExpressionWrapper(
        F('price') * F('stock__quantity'),
        output_field=DecimalField(max_digits=24, decimal_places=6),
    )
    agg_total = Product.objects.aggregate(total=Sum(total_expr))['total']
    total_value = (
        Decimal(str(agg_total))
        if agg_total is not None
        else Decimal('0')
    )

    # Get recent products
    recent_products = Product.objects.select_related('stock').order_by('-created_at')[:5]

    # Get low stock items (Stock rows; template uses item.product)
    low_stock_items = Stock.objects.select_related('product').filter(
        quantity__lte=F('low_stock_threshold')
    ).order_by('quantity')[:5]

    context = {
        'total_products': total_products,
        'low_stock_count': low_stock_count,
        'out_of_stock_count': out_of_stock_count,
        'total_value': total_value,
        'recent_products': recent_products,
        'low_stock_items': low_stock_items,
    }
    return render(request, 'dashboard.html', context)



def products(request):
    products_list = Product.objects.select_related('stock', 'category').all()
    selected_category = request.GET.get('category')
    if selected_category:
        products_list = products_list.filter(category_id=selected_category)

    stock_filter = request.GET.get('stock') or ''

    # Stats for the full filtered list (not just current page)
    total_products = products_list.count()
    in_stock_count = products_list.filter(stock__quantity__gt=0).count()
    low_stock_count = products_list.filter(stock__quantity__lte=models.F('stock__low_stock_threshold')).count()
    out_of_stock_count = products_list.filter(stock__quantity=0).count()

    # Apply stock-specific filters only for the table (not for the summary cards)
    if stock_filter == 'low':
        products_list = products_list.filter(
            stock__quantity__lte=models.F('stock__low_stock_threshold')
        ).exclude(stock__quantity=0)
    elif stock_filter == 'out':
        products_list = products_list.filter(stock__quantity=0)

    paginator = Paginator(products_list.order_by('-created_at'), 20)
    page_obj = paginator.get_page(request.GET.get('page'))

    categories = ProductCategory.objects.filter(is_active=True).order_by('name')

    context = {
        'products': page_obj,
        'page_obj': page_obj,
        'form': ProductForm(),
        'total_products': total_products,
        'in_stock_count': in_stock_count,
        'low_stock_count': low_stock_count,
        'out_of_stock_count': out_of_stock_count,
        'categories': categories,
        'selected_category': int(selected_category) if selected_category else None,
        'stock_filter': stock_filter or None,
    }
    return render(request, 'products.html', context)


@login_required
def add_category(request):
    if request.method == 'POST':
        name = (request.POST.get('name') or '').strip()
        description = (request.POST.get('description') or '').strip()
        if not name:
            messages.error(request, 'Category name is required.')
            return redirect('billing:products')

        category, created = ProductCategory.objects.get_or_create(
            name=name,
            defaults={'description': description, 'is_active': True},
        )
        if not created:
            # Optionally update description for existing category
            if description and category.description != description:
                category.description = description
                category.save(update_fields=['description', 'updated_at'])
            messages.info(request, 'Category already exists and was reused.')
        else:
            messages.success(request, 'Category added successfully.')

    return redirect('billing:products')


@login_required
def delete_category(request, pk):
    """Delete a product category. Products in this category will have category set to None (SET_NULL)."""
    category = get_object_or_404(ProductCategory, pk=pk)
    name = category.name
    category.delete()
    messages.success(request, f'Category "{name}" has been deleted. Products in that category are now uncategorized.')
    return redirect('billing:products')


@login_required
def add_product(request):
    if request.method == 'POST':
        data = request.POST
        name = (data.get('name') or '').strip()
        sku = (data.get('sku') or '').strip()
        type_ = data.get('type') or 'sale'
        uom = data.get('uom') or 'unit'
        product_id = data.get('product_id') or ''
        category_id = (data.get('category') or '').strip()

        # Basic validation
        if not name or not sku:
            messages.error(request, 'Name and Item code are required.')
        else:
            try:
                cost_price = Decimal(data.get('cost_price') or '0')
                price = Decimal(data.get('price') or '0')
                daily_rate_raw = (data.get('daily_rental_rate') or '').strip()
                daily_rental_rate = Decimal(daily_rate_raw) if daily_rate_raw else None
                initial_stock = Decimal(data.get('initial_stock') or '0')
                low_stock_threshold = Decimal(data.get('low_stock_threshold') or '0')
                category = None
                if category_id:
                    category = ProductCategory.objects.filter(pk=category_id).first()

                # If product_id present, update existing; else create new
                if product_id:
                    product = get_object_or_404(Product, pk=product_id)
                    # Ensure SKU unique for other products
                    if Product.objects.exclude(pk=product.pk).filter(sku=sku).exists():
                        messages.error(request, 'Item code already exists. Please use a different item code.')
                    else:
                        product.name = name
                        product.sku = sku
                        product.type = type_
                        product.uom = uom
                        product.cost_price = cost_price
                        product.price = price
                        product.daily_rental_rate = daily_rental_rate
                        product.description = data.get('description') or ''
                        product.category = category
                        product.save()

                        stock, _ = Stock.objects.get_or_create(product=product)
                        stock.quantity = initial_stock
                        stock.low_stock_threshold = low_stock_threshold
                        stock.save()

                        messages.success(request, 'Product updated successfully!')
                        return redirect('billing:products')
                else:
                    if Product.objects.filter(sku=sku).exists():
                        messages.error(request, 'Item code already exists. Please use a different item code.')
                    else:
                        product = Product.objects.create(
                            name=name,
                            description=data.get('description') or '',
                            uom=uom,
                            cost_price=cost_price,
                            price=price,
                            type=type_,
                            daily_rental_rate=daily_rental_rate,
                            sku=sku,
                            category=category,
                        )
                        Stock.objects.create(
                            product=product,
                            quantity=initial_stock,
                            low_stock_threshold=low_stock_threshold,
                        )
                        messages.success(request, 'Product added successfully!')
                        return redirect('billing:products')
            except (InvalidOperation, ValueError):
                messages.error(request, 'Please enter valid numeric values for prices and stock.')

        # On any validation error, re-render page with current list
        products_list = Product.objects.select_related('stock', 'category').all()
        context = {
            'products': products_list,
            'total_products': products_list.count(),
            'in_stock_count': products_list.filter(stock__quantity__gt=0).count(),
            'low_stock_count': products_list.filter(
                stock__quantity__lte=models.F('stock__low_stock_threshold')
            ).count(),
            'out_of_stock_count': products_list.filter(stock__quantity=0).count(),
            'categories': ProductCategory.objects.filter(is_active=True).order_by('name'),
            'selected_category': None,
        }
        return render(request, 'products.html', context)

    return redirect('billing:products')

@login_required
def stock(request):
    stock_qs = Stock.objects.select_related('product').all()

    # Calculate statistics on the full queryset (not just the current page)
    total_items = stock_qs.count()
    low_stock_count = stock_qs.filter(quantity__lte=F('low_stock_threshold')).exclude(quantity=0).count()
    out_of_stock_count = stock_qs.filter(quantity=0).count()
    total_value = sum(Decimal(str(item.quantity)) * item.product.price for item in stock_qs)

    paginator = Paginator(stock_qs.order_by('product__name'), 20)
    page_obj = paginator.get_page(request.GET.get('page'))

    context = {
        'stock_items': page_obj,
        'page_obj': page_obj,
        'total_items': total_items,
        'low_stock_count': low_stock_count,
        'out_of_stock_count': out_of_stock_count,
        'total_value': total_value,
    }
    
    return render(request, 'billing/stock.html', context)

def reports(request):
    # Reports summary (high level)
    total_products = Product.objects.count()
    low_stock_count = Stock.objects.filter(quantity__lte=F('low_stock_threshold')).count()

    # Inventory valuation based on cost_price (fallback to 0 if not set)
    inventory_value = Product.objects.aggregate(
        total=Sum(F('cost_price') * F('stock__quantity'))
    )['total'] or 0

    # Sales & purchases totals (lifetime for now)
    total_sales = Invoice.objects.exclude(status='cancelled').aggregate(total=Sum('total_amount'))['total'] or 0
    total_purchases = PurchaseOrder.objects.filter(status='received').aggregate(total=Sum('total_amount'))['total'] or 0

    # Top selling products (by quantity sold from invoice items, excluding cancelled invoices)
    top_selling = (
        InvoiceItem.objects.filter(invoice__status__in=('credit', 'partially_paid', 'paid'))
        .values('product_id', 'product__name', 'product__sku')
        .annotate(total_quantity=Sum('quantity'), total_revenue=Sum('total'))
        .order_by('-total_quantity')[:15]
    )
    top_selling_list = [
        {
            'rank': i + 1,
            'name': item['product__name'],
            'sku': item['product__sku'] or '-',
            'quantity': item['total_quantity'],
            'revenue': item['total_revenue'] or 0,
        }
        for i, item in enumerate(top_selling)
    ]

    # Frequently visited customers (by invoice count per customer_name + customer_phone)
    # Exclude cancelled invoices and entries with blank/NULL customer_name
    valid_invoices = Invoice.objects.exclude(status='cancelled').exclude(customer_name__isnull=True).exclude(customer_name__exact='')
    top_customers_raw = (
        valid_invoices.values('customer_name', 'customer_phone')
        .annotate(visit_count=Count('id'), total_amount=Sum('total_amount'))
        .order_by('-visit_count')
    )

    # Only keep customers whose names are real alphabetic names
    top_customers_list = []
    for item in top_customers_raw:
        raw_name = (item['customer_name'] or '').strip()
        # Skip completely blank names
        if not raw_name:
            continue
        # Skip names that are not letters/spaces (e.g. numbers like "123344")
        if not re.fullmatch(r'[A-Za-z\s]+', raw_name):
            continue
        top_customers_list.append({
            'rank': len(top_customers_list) + 1,
            'name': raw_name,
            'phone': item['customer_phone'] or '-',
            'visit_count': item['visit_count'],
            'total_amount': item['total_amount'] or 0,
        })
        if len(top_customers_list) >= 15:
            break

    context = {
        'total_products': total_products,
        'low_stock_count': low_stock_count,
        'inventory_value': "{:,.2f}".format(inventory_value),
        'total_sales': "{:,.2f}".format(total_sales),
        'total_purchases': "{:,.2f}".format(total_purchases),
        'top_selling': top_selling_list,
        'top_customers': top_customers_list,
    }
    return render(request, 'reports.html', context)


@login_required
def reports_export(request):
    """Export key report data (summary, top products, top customers) as a CSV."""
    # Reuse the same calculations as the reports view
    total_products = Product.objects.count()
    low_stock_count = Stock.objects.filter(quantity__lte=F('low_stock_threshold')).count()
    inventory_value = Product.objects.aggregate(
        total=Sum(F('cost_price') * F('stock__quantity'))
    )['total'] or 0
    total_sales = Invoice.objects.exclude(status='cancelled').aggregate(total=Sum('total_amount'))['total'] or 0
    total_purchases = PurchaseOrder.objects.filter(status='received').aggregate(total=Sum('total_amount'))['total'] or 0

    top_selling = (
        InvoiceItem.objects.filter(invoice__status__in=('credit', 'partially_paid', 'paid'))
        .values('product__name', 'product__sku')
        .annotate(total_quantity=Sum('quantity'), total_revenue=Sum('total'))
        .order_by('-total_quantity')[:15]
    )

    valid_invoices = Invoice.objects.exclude(status='cancelled').exclude(customer_name__isnull=True).exclude(customer_name__exact='')
    top_customers_raw = (
        valid_invoices.values('customer_name', 'customer_phone')
        .annotate(visit_count=Count('id'), total_amount=Sum('total_amount'))
        .order_by('-visit_count')
    )

    top_customers = []
    for item in top_customers_raw:
        raw_name = (item['customer_name'] or '').strip()
        if not raw_name or not re.fullmatch(r'[A-Za-z\s]+', raw_name):
            continue
        top_customers.append({
            'name': raw_name,
            'phone': item['customer_phone'] or '-',
            'visit_count': item['visit_count'],
            'total_amount': item['total_amount'] or 0,
        })
        if len(top_customers) >= 15:
            break

    # Build CSV
    import csv
    from io import StringIO

    buffer = StringIO()
    writer = csv.writer(buffer)

    # Summary section
    writer.writerow(['Summary'])
    writer.writerow(['Metric', 'Value'])
    writer.writerow(['Total Products', total_products])
    writer.writerow(['Inventory Value (Rs)', f"{inventory_value:,.2f}"])
    writer.writerow(['Low Stock Items', low_stock_count])
    writer.writerow(['Total Sales (Rs)', f"{total_sales:,.2f}"])
    writer.writerow(['Total Purchases (Received) (Rs)', f"{total_purchases:,.2f}"])
    writer.writerow([])

    # Top selling products
    writer.writerow(['Top Selling Products'])
    writer.writerow(['#', 'Product', 'SKU', 'Qty Sold', 'Revenue (Rs)'])
    for i, item in enumerate(top_selling, start=1):
        writer.writerow([
            i,
            item['product__name'],
            item['product__sku'] or '-',
            item['total_quantity'],
            f"{(item['total_revenue'] or 0):.2f}",
        ])
    writer.writerow([])

    # Frequently visited customers
    writer.writerow(['Frequently Visited Customers'])
    writer.writerow(['#', 'Customer', 'Phone', 'Visits', 'Total (Rs)'])
    for i, c in enumerate(top_customers, start=1):
        writer.writerow([
            i,
            c['name'],
            c['phone'],
            c['visit_count'],
            f"{c['total_amount']:.2f}",
        ])

    csv_data = buffer.getvalue()
    buffer.close()

    response = HttpResponse(csv_data, content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="reports_export.csv"'
    return response


@login_required
def purchase_orders(request):
    orders = PurchaseOrder.objects.all().order_by('-created_at')
    return render(request, 'purchase_orders.html', {'orders': orders})


def _generate_po_number():
    """Generate a unique PO number: POYYYYMMDD-XXXX"""
    today = timezone.localdate()
    date_str = today.strftime('%Y%m%d')
    prefix = f"PO{date_str}-"
    last_po = PurchaseOrder.objects.filter(order_number__startswith=prefix).order_by('-order_number').first()
    if last_po and last_po.order_number:
        try:
            last_seq = int(last_po.order_number.split('-')[-1])
        except Exception:
            last_seq = 0
        seq = last_seq + 1
    else:
        seq = 1
    return f"{prefix}{seq:04d}"


@login_required
def create_purchase_order(request):
    if request.method == 'POST':
        supplier_name = (request.POST.get('supplier_name') or '').strip()
        supplier_phone = (request.POST.get('supplier_phone') or '').strip()
        supplier_address = (request.POST.get('supplier_address') or '').strip()
        supplier_gstin = (request.POST.get('supplier_gstin') or '').strip()
        order_date = request.POST.get('order_date') or timezone.localdate().isoformat()
        notes = request.POST.get('notes') or ''

        product_ids = request.POST.getlist('product[]')
        quantities = request.POST.getlist('quantity[]')
        unit_costs = request.POST.getlist('unit_cost[]')

        errors = []

        if not supplier_name:
            errors.append('Supplier name is required.')
        else:
            if not re.fullmatch(r'[A-Za-z\s]+', supplier_name):
                errors.append('Supplier name must contain only letters and spaces (no numbers or symbols).')

        # Strict phone check: optional, but if given must be 10 digits
        if supplier_phone:
            if not supplier_phone.isdigit() or len(supplier_phone) != 10:
                errors.append('Supplier phone must be a 10-digit number.')

        # Strict GSTIN check: optional, but if given must match standard GSTIN format
        gstin_regex = re.compile(r'^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z][1-9A-Z]Z[0-9A-Z]$')
        if supplier_gstin:
            gstin = supplier_gstin.upper()
            if not gstin_regex.fullmatch(gstin):
                errors.append('Supplier GSTIN is invalid. Please enter a valid 15-character GSTIN (e.g. 27ABCDE1234F1Z5).')
            else:
                supplier_gstin = gstin

        # Validate and parse lines
        parsed_lines = []
        for idx, (pid, qty, cost) in enumerate(zip(product_ids, quantities, unit_costs), start=1):
            if not pid and not qty and not cost:
                continue
            if not pid:
                errors.append(f'Line {idx}: Please select a product.')
                continue
            try:
                qty_d = Decimal(str(qty or '0'))
                cost_d = Decimal(str(cost or '0'))
            except (InvalidOperation, ValueError):
                errors.append(f'Line {idx}: Please enter valid numeric quantity and unit cost.')
                continue
            if qty_d <= 0:
                errors.append(f'Line {idx}: Quantity must be greater than 0.')
            if cost_d < 0:
                errors.append(f'Line {idx}: Unit cost cannot be negative.')
            parsed_lines.append((pid, qty_d, cost_d))

        if not parsed_lines:
            errors.append('Please add at least one product line with quantity and unit cost.')

        if errors:
            for msg in errors:
                messages.error(request, msg)
            return redirect('billing:create_purchase_order')

        try:
            with transaction.atomic():
                po = PurchaseOrder.objects.create(
                    order_number=_generate_po_number(),
                    supplier_name=supplier_name,
                    supplier_phone=supplier_phone,
                    supplier_address=supplier_address,
                    supplier_gstin=supplier_gstin,
                    order_date=order_date,
                    status='ordered',
                    notes=notes,
                )

                for pid, qty_d, unit_cost in parsed_lines:
                    product = get_object_or_404(Product, id=int(pid))
                    PurchaseOrderItem.objects.create(
                        purchase_order=po,
                        product=product,
                        uom=product.uom,
                        quantity=qty_d,
                        unit_cost=unit_cost,
                    )

                po.calculate_totals()

                # Optional immediate receive
                if request.POST.get('action') == 'receive':
                    _receive_purchase_order(po)
                    messages.success(request, f'Purchase Order {po.order_number} received and stock updated.')
                else:
                    messages.success(request, f'Purchase Order {po.order_number} created.')

            return redirect('billing:purchase_order_detail', pk=po.id)
        except Exception as e:
            messages.error(request, f'Error creating purchase order: {str(e)}')
            return redirect('billing:create_purchase_order')

    products = Product.objects.select_related('stock').all()
    return render(request, 'create_purchase_order.html', {'products': products})


def _receive_purchase_order(po: PurchaseOrder):
    """Mark PO as received and update stock + cost_price (weighted average)."""
    if po.status == 'received':
        return

    for item in po.items.select_related('product').all():
        product = item.product
        if not product:
            continue
        stock, _ = Stock.objects.get_or_create(product=product, defaults={'quantity': 0, 'low_stock_threshold': 10})

        current_qty = Decimal(str(stock.quantity or 0))
        incoming_qty = Decimal(str(item.quantity))
        new_qty = current_qty + incoming_qty

        # Weighted average cost update
        if new_qty > 0:
            current_cost = product.cost_price or Decimal('0')
            incoming_cost = item.unit_cost
            weighted_cost = ((current_cost * current_qty) + (incoming_cost * incoming_qty)) / new_qty
            product.cost_price = weighted_cost.quantize(Decimal('0.01'))
            product.save(update_fields=['cost_price', 'updated_at'])

        stock.quantity = new_qty
        stock.save(update_fields=['quantity', 'updated_at'])

    po.status = 'received'
    po.received_date = timezone.localdate()
    po.save(update_fields=['status', 'received_date', 'updated_at'])


@login_required
def purchase_order_detail(request, pk):
    po = get_object_or_404(PurchaseOrder, pk=pk)
    return render(request, 'purchase_order_detail.html', {'po': po})


@login_required
def purchase_order_print(request, pk):
    """Print-friendly view for a single purchase order."""
    po = get_object_or_404(PurchaseOrder.objects.prefetch_related('items__product'), pk=pk)
    return render(request, 'purchase_order_print.html', {'po': po})


@login_required
def receive_purchase_order(request, pk):
    po = get_object_or_404(PurchaseOrder, pk=pk)
    if request.method == 'POST':
        try:
            with transaction.atomic():
                _receive_purchase_order(po)
            messages.success(request, f'Purchase Order {po.order_number} received and stock updated.')
        except Exception as e:
            messages.error(request, f'Failed to receive purchase order: {str(e)}')
    return redirect('billing:purchase_order_detail', pk=po.id)


@login_required
def balance_sheet(request):
    from .financial_reports import compute_balance_sheet
    data = compute_balance_sheet()
    context = {
        'as_of': data['as_of'],
        'company_name': data['company_name'],
        'total_sales': Decimal(data['pl_summary']['total_sales']),
        'total_purchases': Decimal(data['pl_summary']['total_purchases_received']),
        'inventory_value': Decimal(data['assets']['items'][0]['amount']) + Decimal(data['assets']['items'][1]['amount']),
        'gross_margin': Decimal(data['pl_summary']['gross_profit']),
        'balance_data': data,
    }
    return render(request, 'balance_sheet.html', context)

def edit_product(request, pk):
    product = get_object_or_404(Product, pk=pk)
    if request.method == 'POST':
        form = ProductForm(request.POST, instance=product)
        if form.is_valid():
            form.save()
            messages.success(request, 'Product updated successfully!')
            return redirect('billing:products')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = ProductForm(instance=product)
    
    context = {
        'form': form,
        'product': product,
        'is_edit': True
    }
    return render(request, 'billing/products.html', context)

@login_required
def update_stock(request, product_id):
    if request.method == 'POST':
        product = get_object_or_404(Product, id=product_id)
        stock = Stock.objects.get(product=product)
        try:
            quantity = Decimal(str(request.POST.get('quantity', '0')))
        except Exception:
            quantity = Decimal('0')
        
        if quantity > 0:
            stock.quantity = Decimal(str(stock.quantity)) + quantity
            stock.save()
            messages.success(request, f'Successfully added {quantity} {product.get_uom_display()} to {product.name}')
        else:
            messages.error(request, 'Please enter a valid quantity')
            
    return redirect('billing:stock')

@login_required
def update_threshold(request, product_id):
    if request.method == 'POST':
        product = get_object_or_404(Product, id=product_id)
        stock = Stock.objects.get(product=product)
        try:
            threshold = Decimal(str(request.POST.get('low_stock_threshold', '0')))
        except Exception:
            threshold = Decimal('0')
        
        if threshold >= 0:
            stock.low_stock_threshold = threshold
            stock.save()
            messages.success(request, f'Successfully updated low stock threshold for {product.name}')
        else:
            messages.error(request, 'Please enter a valid threshold value')
            
    return redirect('billing:stock')

def delete_product(request, pk):
    product = get_object_or_404(Product, pk=pk)
    if request.method == 'POST':
        try:
            product.delete()
            messages.success(request, 'Product deleted successfully!')
        except ProtectedError:
            messages.error(
                request,
                'This product cannot be deleted because it is used in purchase orders or invoices. '
                'You can set its stock to 0 and optionally rename it instead of deleting.'
            )
    return redirect('billing:products')

def invoices(request):
    # Hide draft invoices (token-only orders not yet finalized) from the main gallery
    invoices_list = Invoice.objects.exclude(status='draft').order_by('-created_at')
    context = {
        'invoices': invoices_list
    }
    return render(request, 'invoices.html', context)

def _get_or_create_customer(name, phone='', email='', address=''):
    """Get or create customer by name+phone."""
    phone = (phone or '').strip()
    customer, _ = Customer.objects.get_or_create(
        name=name.strip(),
        phone=phone,
        defaults={'email': email or '', 'address': address or ''}
    )
    return customer


def _add_ledger_entry(customer, invoice, entry_type, debit, credit, description=''):
    """Add ledger entry and update customer balance."""
    prev = customer.ledger_entries.order_by('-id').first()
    balance_before = prev.balance_after if prev else Decimal('0')
    balance_after = balance_before + debit - credit
    CustomerLedgerEntry.objects.create(
        customer=customer,
        invoice=invoice,
        entry_type=entry_type,
        debit=debit,
        credit=credit,
        balance_after=balance_after,
        entry_date=timezone.localdate(),
        description=description
    )
    customer.outstanding_balance = balance_after
    customer.save(update_fields=['outstanding_balance', 'updated_at'])


def _create_invoice_page_context(form):
    """Shared context for GET / POST error render of create_invoice."""
    products = Product.objects.all()
    company_settings = CompanySettings.objects.first()
    gst_percentage = company_settings.gst_percentage if company_settings else Decimal('18.00')
    half_gst_rate = gst_percentage / 2
    return {
        'form': form,
        'products': products,
        'gst_percentage': gst_percentage,
        'half_gst_rate': half_gst_rate,
        'company_settings': company_settings,
    }


def _redeem_external_coupon_if_needed(request, token_only):
    """
    When finalizing a real invoice (not token-only kitchen draft), redeem an
    external coupon on the coupon server so it is marked as used.
    Manual discounts entered as e.g. '10%' in the coupon box are skipped.
    Returns None on success, or an error string for the user.
    """
    import requests

    if token_only:
        return None
    coupon_type = (request.POST.get('applied_coupon_type') or '').strip()
    if not coupon_type:
        return None
    code = (request.POST.get('applied_coupon_code') or '').strip().upper()
    if not code or re.match(r'^\d+(\.\d+)?%$', code, re.I):
        return None
    if 'coupon_session_cookie' not in request.session:
        return 'Coupon login required in Settings to use a coupon code.'
    cookie_header = request.session.get('coupon_session_cookie')
    try:
        resp = requests.post(
            coupon_api.redeem_coupon_url,
            json={'code': code},
            headers={
                'Cookie': cookie_header,
                'Accept': 'application/json',
            },
            timeout=15,
            verify=coupon_api.verify_ssl,
        )
    except Exception as e:
        return f'Unable to reach coupon server: {e}'
    data = _parse_coupon_server_response(resp, endpoint_hint=coupon_api.redeem_coupon_path)
    if not resp.ok:
        if isinstance(data, dict):
            return data.get('error') or data.get('message') or f'Coupon server error ({resp.status_code}).'
        return f'Coupon server error ({resp.status_code}).'
    if isinstance(data, dict) and not data.get('success', False):
        return data.get('error') or data.get('message') or 'Coupon could not be redeemed.'
    return None


@login_required
def create_invoice(request):
    if request.method == 'POST':
        token_only = bool(request.POST.get('print_token'))
        form = InvoiceForm(request.POST)
        if form.is_valid():
            payment_type = form.cleaned_data.get('payment_type', 'full_payment')
            amount_paid_now = form.cleaned_data.get('amount_paid_now') or Decimal('0')

            # Decide invoice and token numbers based on either assigned values from the UI
            # (first item selection) or, if missing/duplicated, from the last saved values in DB.
            company_settings = CompanySettings.objects.first()
            token_enabled = bool(company_settings and getattr(company_settings, 'enable_token_system', False))

            assigned_invoice_number = (request.POST.get('assigned_invoice_number') or '').strip()
            assigned_token_number = (request.POST.get('assigned_token_number') or '').strip()

            # If user is printing token only and a token with this number for today
            # already exists, treat this as a re-print: do NOT create a new invoice.
            if token_only and token_enabled:
                invoice_date_candidate = form.cleaned_data.get('invoice_date') or timezone.localdate()
                desired_token = None
                if assigned_token_number:
                    try:
                        desired_token = int(assigned_token_number)
                    except (ValueError, TypeError):
                        desired_token = None
                if desired_token is not None:
                    existing_token_invoice = (
                        Invoice.objects
                        .filter(invoice_date=invoice_date_candidate, token_number=desired_token)
                        .order_by('id')
                        .first()
                    )
                    if existing_token_invoice:
                        from urllib.parse import urlencode
                        params = {'token_only': '1', 'auto_print': '1'}
                        print_url = reverse('billing:invoice_print', args=[existing_token_invoice.pk])
                        print_url += '?' + urlencode(params)
                        return redirect(print_url)

            # Mark external coupon as used only when creating a real invoice (not token-only draft).
            redeem_err = _redeem_external_coupon_if_needed(request, token_only)
            if redeem_err:
                messages.error(request, redeem_err)
                return render(request, 'billing/create_invoice.html', _create_invoice_page_context(form))

            # Update existing reserved draft when user submits form with assigned number (from reserve-on-first-item)
            existing_draft = None
            if not token_only and assigned_invoice_number:
                existing_draft = Invoice.objects.filter(
                    invoice_number=assigned_invoice_number, status='draft'
                ).first()

            if existing_draft:
                invoice = existing_draft
                invoice.customer_name = form.cleaned_data['customer_name']
                invoice.customer_phone = form.cleaned_data.get('customer_phone') or ''
                invoice.customer_address = form.cleaned_data.get('customer_address') or ''
                invoice.customer_gstin = form.cleaned_data.get('customer_gstin') or ''
                invoice.invoice_date = form.cleaned_data['invoice_date']
                invoice.due_date = form.cleaned_data['due_date']
                invoice.advance_paid = amount_paid_now
                invoice.save(update_fields=[
                    'customer_name', 'customer_phone', 'customer_address', 'customer_gstin',
                    'invoice_date', 'due_date', 'advance_paid', 'updated_at',
                ])
                invoice.items.all().delete()
                products = request.POST.getlist('product[]')
                quantities = request.POST.getlist('quantity[]')
                unit_prices = request.POST.getlist('unit_price[]')
                for i, (product_id, quantity) in enumerate(zip(products, quantities)):
                    if product_id and quantity:
                        product = Product.objects.get(id=product_id)
                        unit_price = product.price
                        if i < len(unit_prices) and (unit_prices[i] or '').strip():
                            try:
                                unit_price = Decimal((unit_prices[i] or '').strip())
                                if unit_price < 0:
                                    unit_price = product.price
                            except (InvalidOperation, TypeError, ValueError):
                                pass
                        InvoiceItem.objects.create(
                            invoice=invoice,
                            product=product,
                            quantity=int(quantity),
                            unit_price=unit_price
                        )
                invoice.calculate_totals()

                # If a coupon was applied (validated on Apply; redeemed on submit), compute discount locally
                # and reduce TOTAL (after GST) before ledger/token/payment logic.
                coupon_type = (request.POST.get('applied_coupon_type') or '').strip()
                coupon_percentage_raw = (request.POST.get('applied_coupon_percentage') or '').strip()
                coupon_flat_raw = (request.POST.get('applied_coupon_flat') or '').strip()
                if coupon_type:
                    discount_amount = Decimal('0')
                    try:
                        if coupon_type == 'percentage':
                            pct = Decimal(coupon_percentage_raw or '0')
                            discount_amount = (invoice.total_amount * pct / Decimal('100'))
                        elif coupon_type == 'flat':
                            flat = Decimal(coupon_flat_raw or '0')
                            discount_amount = min(flat, invoice.total_amount)
                    except (InvalidOperation, TypeError, ValueError):
                        discount_amount = Decimal('0')

                    discount_amount = max(discount_amount, Decimal('0'))
                    discount_amount = discount_amount.quantize(Decimal('0.01'))
                    invoice.total_amount = max(invoice.total_amount - discount_amount, Decimal('0'))
                    invoice.outstanding_amount = invoice.total_amount - invoice.advance_paid

                    # Keep status consistent with the updated totals
                    if invoice.outstanding_amount <= 0:
                        invoice.status = 'paid'
                    elif invoice.advance_paid == 0:
                        invoice.status = 'credit'
                    else:
                        invoice.status = 'partially_paid'
                    invoice.save(update_fields=['total_amount', 'outstanding_amount', 'status'])

                # Reduce stock for each item on this finalized draft invoice
                for item in invoice.items.select_related('product'):
                    try:
                        stock = Stock.objects.get(product=item.product)
                        # Prevent negative stock; clamp at 0
                        if item.quantity >= stock.quantity:
                            stock.quantity = 0
                        else:
                            stock.quantity = Decimal(str(stock.quantity)) - Decimal(str(item.quantity))
                        stock.save(update_fields=['quantity', 'updated_at'])
                    except Stock.DoesNotExist:
                        # If no stock record exists for this product, skip
                        continue

                # If token printing is enabled and token system is on, allocate kitchen
                # tokens sequentially per *current* day (new calendar day → start again from 1),
                # independent of the invoice's accounting date.
                if token_enabled and getattr(company_settings, 'print_token_enabled', False):
                    if getattr(invoice, 'token_number', None) is None:
                        today = timezone.localdate()
                        last_token = (
                            Invoice.objects
                            .filter(
                                invoice_date=today,
                                token_number__isnull=False,
                            )
                            .aggregate(max_token=Max('token_number'))
                            .get('max_token') or 0
                        )
                        invoice.token_number = last_token + 1
                    invoice.token_status = 'pending'
                    invoice.save(update_fields=['token_number', 'token_status'])

                if payment_type == 'full_payment':
                    invoice.advance_paid = invoice.total_amount
                    invoice.outstanding_amount = Decimal('0')
                    invoice.status = 'paid'
                    invoice.save(update_fields=['advance_paid', 'outstanding_amount', 'status'])
                if payment_type in ('full_credit', 'partial_credit') and invoice.outstanding_amount > 0:
                    customer = _get_or_create_customer(
                        invoice.customer_name,
                        invoice.customer_phone,
                        address=invoice.customer_address
                    )
                    _add_ledger_entry(
                        customer,
                        invoice,
                        'invoice',
                        debit=invoice.outstanding_amount,
                        credit=Decimal('0'),
                        description=f'Invoice {invoice.invoice_number} - Outstanding'
                    )
                customer = _get_or_create_customer(
                    invoice.customer_name,
                    invoice.customer_phone,
                    address=invoice.customer_address
                )
                if invoice.customer_address and customer.address != invoice.customer_address:
                    customer.address = invoice.customer_address
                    customer.save(update_fields=['address', 'updated_at'])
                if request.POST.get('print_token') and getattr(invoice, 'token_number', None) is not None:
                    from urllib.parse import urlencode
                    params = {'token_only': '1', 'auto_print': '1'}
                    print_url = reverse('billing:invoice_print', args=[invoice.pk])
                    print_url += '?' + urlencode(params)
                    return redirect(print_url)
                messages.success(request, 'Invoice created successfully!')
                return redirect('billing:view_invoice', pk=invoice.pk)

            invoice = form.save(commit=False)

            # 1) Invoice number & 2) Token number
            invoice_date = invoice.invoice_date or timezone.localdate()
            invoice.invoice_date = invoice_date

            if token_only:
                # Token-only flow: do NOT allocate a real invoice number in the INV00001 series.
                # We only generate a kitchen token and keep this record as a draft
                # with an internal TOK* invoice_number so DB constraints are satisfied.
                if token_enabled:
                    if assigned_token_number:
                        try:
                            tok_int = int(assigned_token_number)
                        except (ValueError, TypeError):
                            tok_int = None
                        if tok_int is not None:
                            invoice.token_number = tok_int
                            invoice.token_status = 'pending'
                    if getattr(invoice, 'token_number', None) is None:
                        last_token = (
                            Invoice.objects
                            .filter(invoice_date=invoice_date, token_number__isnull=False)
                            .aggregate(max_token=Max('token_number'))
                            .get('max_token') or 0
                        )
                        invoice.token_number = last_token + 1
                        invoice.token_status = 'pending'
                else:
                    invoice.token_number = None
                # Internal draft identifier: prefix with TOK so it is ignored by
                # normal invoice numbering logic (which looks at INV* invoices).
                import uuid
                invoice.invoice_number = f"TOK{invoice_date.strftime('%Y%m%d')}{uuid.uuid4().hex[:12]}"
            else:
                # Normal invoice: allocate next invoice number and also allocate a kitchen token
                if assigned_invoice_number and not Invoice.objects.filter(invoice_number=assigned_invoice_number).exists():
                    invoice.invoice_number = assigned_invoice_number
                else:
                    # Only consider real INV* invoices for next number (ignore TOK drafts)
                    last_invoice = (
                        Invoice.objects
                        .filter(invoice_number__isnull=False)
                        .exclude(invoice_number__startswith='TOK')
                        .order_by('-id')
                        .first()
                    )
                    if last_invoice and last_invoice.invoice_number:
                        try:
                            last_number = int(last_invoice.invoice_number.replace('INV', '').replace('inv', ''))
                        except (ValueError, AttributeError):
                            last_number = 0
                        invoice.invoice_number = f'INV{str(last_number + 1).zfill(5)}'
                    else:
                        invoice.invoice_number = 'INV00001'

                # For normal invoices, allocate token numbers sequentially per *current* day
                # (new calendar day → token 1 again, then 2, 3, ...), independent of invoice number
                # and independent of invoice_date value.
                if token_enabled and getattr(company_settings, 'print_token_enabled', False):
                    if getattr(invoice, 'token_number', None) is None:
                        today = timezone.localdate()
                        last_token = (
                            Invoice.objects
                            .filter(invoice_date=today, token_number__isnull=False)
                            .aggregate(max_token=Max('token_number'))
                            .get('max_token') or 0
                        )
                        invoice.token_number = last_token + 1
                    invoice.token_status = 'pending'
                else:
                    invoice.token_number = None

            # Set advance_paid based on payment type
            if token_only:
                # Draft token: treat as not paid yet
                payment_type = 'full_credit'
                amount_paid_now = Decimal('0')
            else:
                if payment_type == 'full_payment':
                    pass  # Will set after calculate_totals
                elif payment_type == 'full_credit':
                    amount_paid_now = Decimal('0')
                elif payment_type == 'partial_credit':
                    pass  # Use amount_paid_now as entered

            invoice.advance_paid = amount_paid_now
            invoice.save()

            # Process products (unit_price[] optional; default to product.price)
            products = request.POST.getlist('product[]')
            quantities = request.POST.getlist('quantity[]')
            unit_prices = request.POST.getlist('unit_price[]')

            for i, (product_id, quantity) in enumerate(zip(products, quantities)):
                if product_id and quantity:
                    product = Product.objects.get(id=product_id)
                    unit_price = product.price
                    if i < len(unit_prices) and (unit_prices[i] or '').strip():
                        try:
                            unit_price = Decimal((unit_prices[i] or '').strip())
                            if unit_price < 0:
                                unit_price = product.price
                        except (InvalidOperation, TypeError, ValueError):
                            pass
                    InvoiceItem.objects.create(
                        invoice=invoice,
                        product=product,
                        quantity=int(quantity),
                        unit_price=unit_price
                    )

            if token_only:
                # Draft token: compute amounts but keep status as Draft, no ledger impact
                invoice.calculate_totals(update_status=False)
                # Apply coupon discount (external codes redeemed only on full invoice submit) so draft amounts stay consistent.
                coupon_type = (request.POST.get('applied_coupon_type') or '').strip()
                coupon_percentage_raw = (request.POST.get('applied_coupon_percentage') or '').strip()
                coupon_flat_raw = (request.POST.get('applied_coupon_flat') or '').strip()
                if coupon_type:
                    discount_amount = Decimal('0')
                    try:
                        if coupon_type == 'percentage':
                            pct = Decimal(coupon_percentage_raw or '0')
                            discount_amount = (invoice.total_amount * pct / Decimal('100'))
                        elif coupon_type == 'flat':
                            flat = Decimal(coupon_flat_raw or '0')
                            discount_amount = min(flat, invoice.total_amount)
                    except (InvalidOperation, TypeError, ValueError):
                        discount_amount = Decimal('0')
                    discount_amount = max(discount_amount, Decimal('0')).quantize(Decimal('0.01'))
                    invoice.total_amount = max(invoice.total_amount - discount_amount, Decimal('0'))
                    invoice.outstanding_amount = invoice.total_amount - invoice.advance_paid

                invoice.status = 'draft'
                invoice.save(update_fields=[
                    'subtotal',
                    'cgst_amount',
                    'sgst_amount',
                    'igst_amount',
                    'total_amount',
                    'advance_paid',
                    'outstanding_amount',
                    'status',
                ])
            else:
                invoice.calculate_totals()

                # Apply coupon discount to finalized invoice totals (reduce TOTAL after GST)
                coupon_type = (request.POST.get('applied_coupon_type') or '').strip()
                coupon_percentage_raw = (request.POST.get('applied_coupon_percentage') or '').strip()
                coupon_flat_raw = (request.POST.get('applied_coupon_flat') or '').strip()
                if coupon_type:
                    discount_amount = Decimal('0')
                    try:
                        if coupon_type == 'percentage':
                            pct = Decimal(coupon_percentage_raw or '0')
                            discount_amount = (invoice.total_amount * pct / Decimal('100'))
                        elif coupon_type == 'flat':
                            flat = Decimal(coupon_flat_raw or '0')
                            discount_amount = min(flat, invoice.total_amount)
                    except (InvalidOperation, TypeError, ValueError):
                        discount_amount = Decimal('0')

                    discount_amount = max(discount_amount, Decimal('0')).quantize(Decimal('0.01'))
                    invoice.total_amount = max(invoice.total_amount - discount_amount, Decimal('0'))
                    invoice.outstanding_amount = invoice.total_amount - invoice.advance_paid

                    # Update status consistent with adjusted outstanding
                    if invoice.outstanding_amount <= 0:
                        invoice.status = 'paid'
                    elif invoice.advance_paid == 0:
                        invoice.status = 'credit'
                    else:
                        invoice.status = 'partially_paid'
                    invoice.save(update_fields=['total_amount', 'outstanding_amount', 'status'])

                # Reduce stock for each item on a finalized invoice
                for item in invoice.items.select_related('product'):
                    try:
                        stock = Stock.objects.get(product=item.product)
                        # Prevent negative stock; clamp at 0
                        if item.quantity >= stock.quantity:
                            stock.quantity = 0
                        else:
                            stock.quantity = Decimal(str(stock.quantity)) - Decimal(str(item.quantity))
                        stock.save(update_fields=['quantity', 'updated_at'])
                    except Stock.DoesNotExist:
                        # If no stock record exists for this product, skip
                        continue

                # For full payment, set advance_paid = total_amount
                if payment_type == 'full_payment':
                    invoice.advance_paid = invoice.total_amount
                    invoice.outstanding_amount = Decimal('0')
                    invoice.status = 'paid'
                    invoice.save(update_fields=['advance_paid', 'outstanding_amount', 'status'])

                # Update A/R ledger for credit or partial credit
                if payment_type in ('full_credit', 'partial_credit') and invoice.outstanding_amount > 0:
                    customer = _get_or_create_customer(
                        invoice.customer_name,
                        invoice.customer_phone,
                        address=invoice.customer_address
                    )
                    _add_ledger_entry(
                        customer,
                        invoice,
                        'invoice',
                        debit=invoice.outstanding_amount,
                        credit=Decimal('0'),
                        description=f'Invoice {invoice.invoice_number} - Outstanding'
                    )

            # Always ensure a Customer record exists/updated for this invoice
            customer = _get_or_create_customer(
                invoice.customer_name,
                invoice.customer_phone,
                address=invoice.customer_address
            )
            if invoice.customer_address and customer.address != invoice.customer_address:
                customer.address = invoice.customer_address
                customer.save(update_fields=['address', 'updated_at'])

            # If user clicked "Print Token", redirect this (new-tab) request to token-only print page
            if request.POST.get('print_token') and getattr(invoice, 'token_number', None) is not None:
                from urllib.parse import urlencode
                params = {'token_only': '1', 'auto_print': '1'}
                print_url = reverse('billing:invoice_print', args=[invoice.pk])
                print_url += '?' + urlencode(params)
                return redirect(print_url)

            messages.success(request, 'Invoice created successfully!')
            return redirect('billing:view_invoice', pk=invoice.pk)
    else:
        form = InvoiceForm()

    return render(request, 'billing/create_invoice.html', _create_invoice_page_context(form))


@login_required
def api_search_customers(request):
    """API: Search existing customers by name for create invoice autocomplete."""
    q = (request.GET.get('q') or '').strip()
    if len(q) < 1:
        return JsonResponse({'customers': []})
    seen = set()
    customers = []
    # From Invoices - most recent first, use latest address/gstin per (name,phone)
    for inv in Invoice.objects.filter(customer_name__icontains=q).order_by('-id')[:30]:
        key = (inv.customer_name, inv.customer_phone or '')
        if key not in seen:
            seen.add(key)
            customers.append({
                'name': inv.customer_name,
                'phone': inv.customer_phone or '',
                'address': inv.customer_address or '',
                'gstin': inv.customer_gstin or '',
            })
            if len(customers) >= 15:
                break
    # Also from Customer model (A/R customers)
    for c in Customer.objects.filter(name__icontains=q)[:10]:
        key = (c.name, c.phone or '')
        if key not in seen:
            seen.add(key)
            customers.append({
                'name': c.name,
                'phone': c.phone or '',
                'address': c.address or '',
                'gstin': '',
            })
            if len(customers) >= 15:
                break
    return JsonResponse({'customers': customers[:15]})


@login_required
def api_next_invoice_token(request):
    """
    Return the next invoice number and today's next token number,
    based purely on the last saved records in the database.
    Used by the Create Invoice page to replace 'Auto' labels once
    the user starts filling customer/items.
    """
    company_settings = CompanySettings.objects.first()
    # Next invoice number (global sequence) – ignore draft token-only records (TOK*)
    last_invoice = (
        Invoice.objects
        .filter(invoice_number__isnull=False)
        .exclude(invoice_number__startswith='TOK')
        .order_by('-id')
        .first()
    )
    if last_invoice and last_invoice.invoice_number:
        try:
            last_number = int(last_invoice.invoice_number.replace('INV', '').replace('inv', ''))
        except (ValueError, AttributeError):
            last_number = 0
        next_invoice_number = f'INV{str(last_number + 1).zfill(5)}'
    else:
        next_invoice_number = 'INV00001'

    # Token number: sequential per *current* day
    next_token_number = None
    if company_settings and getattr(company_settings, 'enable_token_system', False):
        today = timezone.localdate()
        last_token = (
            Invoice.objects
            .filter(invoice_date=today, token_number__isnull=False)
            .aggregate(max_token=Max('token_number'))
            .get('max_token') or 0
        )
        next_token_number = last_token + 1

    return JsonResponse({
        'invoice_number': next_invoice_number,
        'token_number': next_token_number,
    })


@login_required
def api_reserve_invoice_token(request):
    """
    Reserve the next invoice number (and token) by creating a minimal draft invoice.
    Called when the user adds their first item on the create-invoice page so that
    another open tab gets the next number when its user adds an item.
    Accepts POST with optional: invoice_date, due_date, customer_name.
    Returns { invoice_number, token_number }.
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)
    company_settings = CompanySettings.objects.first()
    token_enabled = bool(company_settings and getattr(company_settings, 'enable_token_system', False))
    # Parse optional body
    try:
        data = json.loads(request.body) if request.body else {}
    except json.JSONDecodeError:
        data = {}
    today = timezone.localdate()
    invoice_date = today
    due_date = invoice_date
    if data.get('invoice_date'):
        try:
            from datetime import datetime as dt
            invoice_date = dt.strptime(data['invoice_date'], '%Y-%m-%d').date()
        except (ValueError, TypeError):
            pass
    if data.get('due_date'):
        try:
            from datetime import datetime as dt
            due_date = dt.strptime(data['due_date'], '%Y-%m-%d').date()
        except (ValueError, TypeError):
            pass
    from datetime import timedelta
    dues_days = int(getattr(company_settings, 'dues_days', 7) or 7)
    if not data.get('due_date'):
        due_date = invoice_date + timedelta(days=dues_days)
    customer_name = (data.get('customer_name') or '').strip() or '—'
    # Next invoice number (same logic as create_invoice: last INV* + 1)
    last_invoice = (
        Invoice.objects
        .filter(invoice_number__isnull=False)
        .exclude(invoice_number__startswith='TOK')
        .order_by('-id')
        .first()
    )
    if last_invoice and last_invoice.invoice_number:
        try:
            last_number = int(last_invoice.invoice_number.replace('INV', '').replace('inv', ''))
        except (ValueError, AttributeError):
            last_number = 0
        next_invoice_number = f'INV{str(last_number + 1).zfill(5)}'
    else:
        next_invoice_number = 'INV00001'
    # Next token: reserve sequential per *current* day so each open tab
    # immediately sees a unique token preview.
    base_token = None
    if token_enabled:
        last_token = (
            Invoice.objects
            .filter(invoice_date=today, token_number__isnull=False)
            .aggregate(max_token=Max('token_number'))
            .get('max_token') or 0
        )
        base_token = last_token + 1

    # Create minimal draft so this number (invoice + token) is reserved; save items if provided.
    draft_kwargs = dict(
        invoice_number=next_invoice_number,
        customer_name=customer_name[:200],
        invoice_date=invoice_date,
        due_date=due_date,
        status='draft',
        advance_paid=Decimal('0'),
        outstanding_amount=Decimal('0'),
    )
    if token_enabled and base_token is not None:
        draft_kwargs.update(
            token_number=base_token,
            token_status='pending',
        )
    draft = Invoice(**draft_kwargs)
    draft.save()
    # Save items on draft (list of { product_id, quantity })
    items_data = data.get('items') or []
    for entry in items_data:
        try:
            pid = entry.get('product_id') or entry.get('product')
            qty = entry.get('quantity')
            if pid and qty:
                product = Product.objects.get(pk=int(pid))
                qty_int = int(qty)
                if qty_int > 0:
                    InvoiceItem.objects.create(
                        invoice=draft,
                        product=product,
                        quantity=qty_int,
                        unit_price=product.price,
                    )
        except (Product.DoesNotExist, (ValueError, TypeError)):
            continue
    if draft.items.exists():
        draft.calculate_totals(update_status=False)
        draft.save(update_fields=[
            'subtotal', 'cgst_amount', 'sgst_amount', 'igst_amount',
            'total_amount', 'outstanding_amount', 'updated_at',
        ])
    return JsonResponse({
        'invoice_number': next_invoice_number,
        'token_number': base_token,
    })


@login_required
def api_update_draft_items(request):
    """
    Update items on an existing draft invoice (reserved from create-invoice page).
    POST JSON: { invoice_number: "INV00012", items: [ { product_id, quantity }, ... ] }.
    Keeps draft in sync so invoice gallery shows current line items.
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)
    try:
        data = json.loads(request.body) if request.body else {}
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    invoice_number = (data.get('invoice_number') or '').strip()
    if not invoice_number:
        return JsonResponse({'error': 'invoice_number required'}, status=400)
    draft = Invoice.objects.filter(
        invoice_number=invoice_number,
        status='draft',
    ).first()
    if not draft:
        return JsonResponse({'error': 'Draft not found', 'ok': False}, status=404)
    items_data = data.get('items') or []
    draft.items.all().delete()
    for entry in items_data:
        try:
            pid = entry.get('product_id') or entry.get('product')
            qty = entry.get('quantity')
            if pid and qty:
                product = Product.objects.get(pk=int(pid))
                qty_int = int(qty)
                if qty_int > 0:
                    unit_price = product.price
                    if entry.get('unit_price') is not None:
                        try:
                            unit_price = Decimal(str(entry.get('unit_price')))
                            if unit_price < 0:
                                unit_price = product.price
                        except (InvalidOperation, TypeError, ValueError):
                            pass
                    InvoiceItem.objects.create(
                        invoice=draft,
                        product=product,
                        quantity=qty_int,
                        unit_price=unit_price,
                    )
        except (Product.DoesNotExist, (ValueError, TypeError)):
            continue
    if draft.items.exists():
        draft.calculate_totals(update_status=False)
        draft.save(update_fields=[
            'subtotal', 'cgst_amount', 'sgst_amount', 'igst_amount',
            'total_amount', 'outstanding_amount', 'updated_at',
        ])
    return JsonResponse({'ok': True})


@login_required
def edit_invoice(request, pk):
    """Update items and bill for an existing invoice (e.g. customer orders more after serving)."""
    invoice = get_object_or_404(Invoice, pk=pk)
    if request.method == 'POST':
        form = InvoiceForm(request.POST, instance=invoice)
        if form.is_valid():
            invoice = form.save(commit=False)
            invoice.save()
            # Replace items with posted product[], quantity[], unit_price[] (same names as create form)
            invoice.items.all().delete()
            product_ids = request.POST.getlist('product[]')
            quantities = request.POST.getlist('quantity[]')
            unit_prices = request.POST.getlist('unit_price[]') or []
            for i, (product_id, quantity) in enumerate(zip(product_ids or [], quantities or [])):
                if product_id and quantity:
                    try:
                        product = Product.objects.get(id=product_id)
                        qty = int(quantity)
                        if qty > 0:
                            unit_price = product.price
                            if i < len(unit_prices) and (unit_prices[i] or '').strip():
                                try:
                                    unit_price = Decimal((unit_prices[i] or '').strip())
                                    if unit_price < 0:
                                        unit_price = product.price
                                except (InvalidOperation, TypeError, ValueError):
                                    pass
                            InvoiceItem.objects.create(
                                invoice=invoice,
                                product=product,
                                quantity=qty,
                                unit_price=unit_price
                            )
                    except (Product.DoesNotExist, ValueError):
                        pass
            invoice.calculate_totals()
            # Keep customer master in sync when editing invoice customer details
            customer = _get_or_create_customer(
                invoice.customer_name,
                invoice.customer_phone,
                address=invoice.customer_address
            )
            if invoice.customer_address and customer.address != invoice.customer_address:
                customer.address = invoice.customer_address
                customer.save(update_fields=['address', 'updated_at'])
            messages.success(request, 'Invoice updated successfully. Totals recalculated.')
            return redirect('billing:view_invoice', pk=invoice.pk)
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = InvoiceForm(instance=invoice)
    company_settings = CompanySettings.objects.first()
    gst_percentage = company_settings.gst_percentage if company_settings else Decimal('18.00')
    half_gst_rate = gst_percentage / 2
    products = Product.objects.all()
    context = {
        'form': form,
        'invoice': invoice,
        'products': products,
        'is_edit': True,
        'company_settings': company_settings,
        'gst_percentage': gst_percentage,
        'half_gst_rate': half_gst_rate,
        'next_invoice_number': invoice.invoice_number,
        'next_token_number': getattr(invoice, 'token_number', None),
    }
    return render(request, 'billing/create_invoice.html', context)

@login_required
def delete_invoice(request, pk):
    """Delete a single invoice."""
    try:
        invoice = get_object_or_404(Invoice, pk=pk)
        invoice.delete()
        messages.success(request, f'Invoice #{invoice.invoice_number} deleted successfully.')
    except Exception as e:
        messages.error(request, f'Error deleting invoice: {str(e)}')
    return redirect('billing:invoice_gallery')

@login_required
def delete_all_invoices(request):
    """Delete all invoices."""
    try:
        count = Invoice.objects.count()
        Invoice.objects.all().delete()
        messages.success(request, f'Successfully deleted {count} invoices.')
    except Exception as e:
        messages.error(request, f'Error deleting invoices: {str(e)}')
    return redirect('billing:invoice_gallery')

def view_invoice(request, pk):
    invoice = get_object_or_404(Invoice, pk=pk)
    company_settings = CompanySettings.objects.first()
    payments = PaymentReceived.objects.filter(invoice=invoice).order_by('-payment_date')
    # Derive a display token number: prefer stored token_number; fallback to number from invoice_no (INV00022 → 22)
    display_token_number = invoice.token_number
    if display_token_number is None and invoice.invoice_number:
        inv = str(invoice.invoice_number)
        if inv.upper().startswith('INV'):
            try:
                display_token_number = int(inv[3:])
            except (ValueError, TypeError):
                display_token_number = None
    # Use direct print when printer is selected (prints directly, no popup)
    printer_name = getattr(company_settings, 'printer_name', '') or '' if company_settings else ''
    use_direct_print = bool(printer_name) or getattr(company_settings, 'use_direct_print', False) if company_settings else False
    context = {
        'invoice': invoice,
        'company_settings': company_settings,
        'payments': payments,
        'use_direct_print': use_direct_print,
        'print_service_url': (getattr(company_settings, 'print_service_url', '') or 'http://localhost:8765').rstrip('/') if company_settings else 'http://localhost:8765',
        'display_token_number': display_token_number,
    }
    return render(request, 'billing/invoice_detail.html', context)


@csrf_exempt
@require_http_methods(["POST"])
def api_print_invoice(request, pk):
    """Print invoice - pure code first (no external apps), then fallbacks."""
    from .print_utils import (
        print_pdf_via_gdi,
        print_pdf_silent_no_dialog,
        print_to_printer,
        print_raw_text_to_printer,
        generate_raw_invoice_text,
        generate_token_only_text,
    )
    invoice = get_object_or_404(Invoice, pk=pk)
    company_settings = CompanySettings.objects.first()
    if not company_settings:
        return JsonResponse({'success': False, 'message': 'Company settings not found'}, status=500)
    print_bill = getattr(company_settings, 'print_bill_enabled', True)
    print_token = getattr(company_settings, 'print_token_enabled', True)
    if not print_bill and not print_token:
        return JsonResponse({
            'success': False,
            'message': 'Printing is disabled. Enable "Print bill" or "Print token" in Company Settings.'
        }, status=400)
    printer_name = getattr(company_settings, 'printer_name', '') or ''
    try:
        data = json.loads(request.body) if request.body else {}
        if data.get('printer_name'):
            printer_name = data['printer_name']
    except (json.JSONDecodeError, TypeError):
        pass
    try:
        if not invoice.total_amount:
            invoice.calculate_totals()
        if os.name != 'nt':
            return JsonResponse({
                'success': False,
                'message': 'Direct print is for Windows. Open print page and use Ctrl+P.'
            }, status=500)
        # Token-only print
        if print_token and not print_bill:
            if getattr(invoice, 'token_number', None) is None:
                return JsonResponse({'success': False, 'message': 'This invoice has no token.'}, status=400)
            text = generate_token_only_text(invoice)
            ok, msg = print_raw_text_to_printer(text, printer_name or None)
            if ok:
                return JsonResponse({'success': True, 'message': 'Token sent to printer'})
            return JsonResponse({'success': False, 'message': msg or 'Print failed.'}, status=500)
        last_error = None
        pdf_path = None
        include_token_in_bill = print_token and getattr(company_settings, 'enable_token_system', False) and getattr(invoice, 'token_number', None) is not None
        # Method 1: PDF + ShellExecute (works without OpenPrinter - avoids "Unable to open printer")
        try:
            pdf_buffer = create_invoice_pdf(invoice)
            with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as f:
                f.write(pdf_buffer.getvalue())
                pdf_path = f.name
            ok, msg = print_to_printer(pdf_path, printer_name or None)
            if ok:
                if print_token and getattr(invoice, 'token_number', None) is not None:
                    token_text = generate_token_only_text(invoice)
                    print_raw_text_to_printer(token_text, printer_name or None)
                import threading
                def _cleanup(p):
                    import time
                    time.sleep(15)
                    try:
                        if os.path.exists(p):
                            os.unlink(p)
                    except Exception:
                        pass
                threading.Thread(target=_cleanup, args=(pdf_path,), daemon=True).start()
                return JsonResponse({'success': True, 'message': 'Bill and token sent to printer' if (print_token and getattr(invoice, 'token_number', None) is not None) else 'Sent to printer'})
            last_error = msg
        except Exception as e:
            last_error = str(e)
        if pdf_path and os.path.exists(pdf_path):
            try:
                os.unlink(pdf_path)
            except Exception:
                pass
        # Method 2: Raw text via win32print (NO DIALOG)
        try:
            text = generate_raw_invoice_text(invoice, company_settings, include_token=include_token_in_bill)
            ok, msg = print_raw_text_to_printer(text, printer_name or None)
            if ok:
                if print_token and getattr(invoice, 'token_number', None) is not None:
                    token_text = generate_token_only_text(invoice)
                    print_raw_text_to_printer(token_text, printer_name or None)
                return JsonResponse({'success': True, 'message': 'Bill and token sent to printer' if (print_token and getattr(invoice, 'token_number', None) is not None) else msg})
            last_error = msg
        except Exception as e:
            last_error = str(e)
        # Method 3: SumatraPDF if installed (NO DIALOG)
        try:
            pdf_buffer = create_invoice_pdf(invoice)
            with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as f:
                f.write(pdf_buffer.getvalue())
                pdf_path = f.name
            ok, msg = print_pdf_silent_no_dialog(pdf_path, printer_name or None)
            if ok:
                if print_token and getattr(invoice, 'token_number', None) is not None:
                    token_text = generate_token_only_text(invoice)
                    print_raw_text_to_printer(token_text, printer_name or None)
                import threading
                def _cleanup(p):
                    import time
                    time.sleep(15)
                    try:
                        if os.path.exists(p):
                            os.unlink(p)
                    except Exception:
                        pass
                threading.Thread(target=_cleanup, args=(pdf_path,), daemon=True).start()
                return JsonResponse({'success': True, 'message': 'Bill and token sent to printer' if (print_token and getattr(invoice, 'token_number', None) is not None) else msg})
            last_error = msg
        except Exception as e:
            last_error = str(e)
        if pdf_path and os.path.exists(pdf_path):
            try:
                os.unlink(pdf_path)
            except Exception:
                pass
        # Method 4: pypdfium2 + win32ui (NO DIALOG)
        try:
            pdf_buffer = create_invoice_pdf(invoice)
            pdf_bytes = pdf_buffer.getvalue()
            ok, msg = print_pdf_via_gdi(pdf_bytes, printer_name or None)
            if ok:
                if print_token and getattr(invoice, 'token_number', None) is not None:
                    token_text = generate_token_only_text(invoice)
                    print_raw_text_to_printer(token_text, printer_name or None)
                return JsonResponse({'success': True, 'message': 'Bill and token sent to printer' if (print_token and getattr(invoice, 'token_number', None) is not None) else msg})
            last_error = msg
        except Exception as e:
            last_error = str(e)
        return JsonResponse({
            'success': False,
            'message': last_error or 'Print failed. Ensure a printer is selected in Settings.'
        }, status=500)
    except Invoice.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Invoice not found'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=500)


def invoice_print(request, pk):
    """Render a print-optimized invoice page. Opens print dialog or user can Ctrl+P. Respects Print bill / Print token settings."""
    invoice = get_object_or_404(Invoice, pk=pk)
    company_settings = CompanySettings.objects.first()
    if not company_settings:
        return HttpResponse("Company settings not found. Please configure company settings first.", status=500)

    # Token-only print (e.g. from "Print token" on create invoice): show token slip only, never the bill
    if request.GET.get('token_only') in ('1', 'true', 'yes') and getattr(invoice, 'token_number', None) is not None:
        auto_print = request.GET.get('auto_print') in ('1', 'true') or getattr(company_settings, 'auto_print_dialog', True)
        response = render(request, 'billing/token_print.html', {
            'invoice': invoice,
            'auto_print': auto_print,
        })
        response['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
        response['Pragma'] = 'no-cache'
        return response

    print_bill = getattr(company_settings, 'print_bill_enabled', True)
    print_token = getattr(company_settings, 'print_token_enabled', True)
    if not print_bill and not print_token:
        return HttpResponse(
            "<!DOCTYPE html><html><head><title>Print disabled</title></head><body style='font-family:sans-serif;padding:2rem;'>"
            "<h2>Printing is disabled</h2><p>Enable <strong>Print bill</strong> or <strong>Print token</strong> in "
            "<a href='" + reverse('billing:company_settings') + "'>Company Settings</a> to print.</p></body></html>",
            content_type='text/html'
        )

    # Token-only print: minimal page with just the token number
    if print_token and not print_bill:
        if getattr(invoice, 'token_number', None) is None:
            return HttpResponse("This invoice has no token.", status=400)
        auto_print = request.GET.get('auto_print') == '1' or getattr(company_settings, 'auto_print_dialog', True)
        return render(request, 'billing/token_print.html', {
            'invoice': invoice,
            'auto_print': auto_print,
        })

    payments = PaymentReceived.objects.filter(invoice=invoice).order_by('-payment_date')
    if not invoice.total_amount:
        invoice.calculate_totals()

    # Amount in words
    try:
        amount_in_words = num2words(float(invoice.total_amount), to='currency', lang='en_IN').replace(
            'euro', 'Rupees'
        ).replace('cents', 'paise').title() + " Only"
    except Exception:
        amount_in_words = "Not Provided"

    # Use printer settings: thermal layout for thermal types
    printer_type = getattr(company_settings, 'printer_type', 'thermal_80mm')
    thermal = printer_type in ('thermal_80mm', 'thermal_58mm')
    # ?auto_print=1 from Print button forces browser print dialog
    auto_print = request.GET.get('auto_print') == '1' or getattr(company_settings, 'auto_print_dialog', True)
    # Compute display token number for printing: stored token or derive from invoice number (INV00022 → 22)
    display_token_number = getattr(invoice, 'token_number', None)
    if display_token_number is None and invoice.invoice_number:
        inv = str(invoice.invoice_number)
        if inv.upper().startswith('INV'):
            try:
                display_token_number = int(inv[3:])
            except (ValueError, TypeError):
                display_token_number = None

    # Decide whether to include a separate token slip page:
    # only when "Print token" is enabled AND there is a token number.
    show_token_page = (
        print_token
        and getattr(company_settings, 'enable_token_system', False)
        and display_token_number is not None
    )

    context = {
        'invoice': invoice,
        'company_settings': company_settings,
        'payments': payments,
        'amount_in_words': amount_in_words,
        'thermal': thermal,
        'printer_type': printer_type,
        'auto_print': auto_print,
        'printer_name': getattr(company_settings, 'printer_name', '') or None,
        'display_token_number': display_token_number,
        'show_token_page': show_token_page,
    }
    return render(request, 'billing/invoice_print.html', context)


@login_required
def kitchen_display(request):
    """Kitchen screen: show today's tokens that are pending or preparing."""
    company_settings = CompanySettings.objects.first()
    if not (company_settings and getattr(company_settings, 'enable_token_system', False)):
        messages.error(request, 'Token system is disabled. Enable it in Company Settings to use the kitchen view.')
        return redirect('billing:dashboard')

    today = timezone.localdate()
    invoices = (
        Invoice.objects
        .prefetch_related('items__product')
        .filter(
            invoice_date=today,
            token_number__isnull=False,
            token_status__in=['pending', 'preparing'],
        )
        .order_by('token_number')
    )

    context = {
        'invoices': invoices,
        'today': today,
        'company_settings': company_settings,
    }
    return render(request, 'billing/kitchen_display.html', context)


@login_required
@require_http_methods(["POST"])
def mark_token_ready(request, pk):
    """Mark a token as Ready from the kitchen screen."""
    company_settings = CompanySettings.objects.first()
    if not (company_settings and getattr(company_settings, 'enable_token_system', False)):
        messages.error(request, 'Token system is disabled.')
        return redirect('billing:dashboard')

    invoice = get_object_or_404(Invoice, pk=pk)
    if invoice.token_number is not None:
        invoice.token_status = 'ready'
        invoice.token_ready_at = timezone.now()
        invoice.save(update_fields=['token_status', 'token_ready_at'])
        messages.success(request, f'Token {invoice.token_number} marked as Ready.')
    else:
        messages.error(request, 'This invoice does not have a token.')

    return redirect('billing:kitchen_display')


@login_required
@require_http_methods(["POST"])
def mark_token_ready_by_number(request):
    """API: mark today's invoice with given token_number as ready (for drag-drop in Manage Tokens modal)."""
    company_settings = CompanySettings.objects.first()
    if not (company_settings and getattr(company_settings, 'enable_token_system', False)):
        return JsonResponse({'success': False, 'error': 'Token system is disabled'}, status=404)
    try:
        data = json.loads(request.body) if request.body else {}
        token_number = data.get('token_number')
        if token_number is None:
            return JsonResponse({'success': False, 'error': 'token_number required'}, status=400)
        token_number = int(token_number)
    except (ValueError, TypeError, json.JSONDecodeError):
        return JsonResponse({'success': False, 'error': 'Invalid token_number'}, status=400)
    today = timezone.localdate()
    invoice = (
        Invoice.objects
        .filter(
            invoice_date=today,
            token_number=token_number,
            token_status__in=['pending', 'preparing'],
        )
        .first()
    )
    if not invoice:
        return JsonResponse({'success': False, 'error': f'No preparing order with token {token_number}'}, status=404)
    invoice.token_status = 'ready'
    invoice.token_ready_at = timezone.now()
    invoice.save(update_fields=['token_status', 'token_ready_at'])
    return JsonResponse({'success': True, 'token_number': token_number})


@login_required
@require_http_methods(["POST"])
def clear_ready_tokens(request):
    """
    Clear all today's ready tokens from the display by marking them as delivered.
    Returns JSON when called via AJAX (e.g. from Manage Tokens modal).
    """
    company_settings = CompanySettings.objects.first()
    if not (company_settings and getattr(company_settings, 'enable_token_system', False)):
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'error': 'Token system is disabled.'}, status=400)
        messages.error(request, 'Token system is disabled.')
        return redirect('billing:dashboard')

    today = timezone.localdate()
    updated = (
        Invoice.objects
        .filter(
            invoice_date=today,
            token_number__isnull=False,
            token_status='ready',
        )
        .update(token_status='delivered')
    )
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            'success': True,
            'cleared': updated,
            'message': f'Cleared {updated} ready token(s).' if updated else 'No ready tokens to clear.',
        })
    if updated:
        messages.success(request, f'Cleared {updated} ready token(s) from display.')
    else:
        messages.info(request, 'No ready tokens to clear.')
    return redirect('billing:kitchen_display')

@require_http_methods(["GET"])
def token_display(request):
    """
    TV screen: show today's tokens by status.
    Left: Pending/Preparing, Right: Ready.
    Intended for full-screen display; no login required.
    """
    company_settings = CompanySettings.objects.first()
    if not (company_settings and getattr(company_settings, 'enable_token_system', False)):
        return HttpResponse("Token system is disabled.", status=404)

    today = timezone.localdate()
    now = timezone.now()
    cutoff = now - timedelta(minutes=5)

    pending_tokens = list(
        Invoice.objects
        .filter(
            invoice_date=today,
            token_number__isnull=False,
            token_status__in=['pending', 'preparing'],
        )
        .order_by('token_number')
        .values_list('token_number', flat=True)
    )

    ready_tokens = list(
        Invoice.objects
        .filter(
            invoice_date=today,
            token_number__isnull=False,
            token_status='ready',
        )
        .filter(
            models.Q(token_ready_at__isnull=True) | models.Q(token_ready_at__gte=cutoff)
        )
        .order_by('token_number')
        .values_list('token_number', flat=True)
    )

    ready_sound = getattr(company_settings, 'tv_ready_sound', 'beep')
    tv_voice = (getattr(company_settings, 'tv_announce_voice', None) or '').strip()
    custom_sound_url = ''
    if getattr(company_settings, 'tv_ready_sound_file', None) and company_settings.tv_ready_sound_file:
        custom_sound_url = request.build_absolute_uri(company_settings.tv_ready_sound_file.url)
    context = {
        'pending_tokens': pending_tokens,
        'ready_tokens': ready_tokens,
        'today': today,
        'tv_ready_sound': ready_sound,
        'tv_announce_voice': tv_voice,
        'tv_custom_sound_url': custom_sound_url,
    }
    return render(request, 'billing/token_display.html', context)


@login_required
@require_http_methods(["GET"])
def token_summary_json(request):
    """API: return today's pending and ready token numbers and item details for the Manage Tokens modal."""
    company_settings = CompanySettings.objects.first()
    if not (company_settings and getattr(company_settings, 'enable_token_system', False)):
        return JsonResponse({'error': 'Token system is disabled'}, status=404)
    today = timezone.localdate()
    now = timezone.now()
    cutoff = now - timedelta(minutes=5)
    pending_qs = (
        Invoice.objects
        .filter(
            invoice_date=today,
            token_number__isnull=False,
            token_status__in=['pending', 'preparing'],
        )
        .order_by('token_number')
        .prefetch_related('items__product')
    )
    ready_qs = (
        Invoice.objects
        .filter(
            invoice_date=today,
            token_number__isnull=False,
            token_status='ready',
        )
        .filter(
            models.Q(token_ready_at__isnull=True) | models.Q(token_ready_at__gte=cutoff)
        )
        .order_by('token_number')
        .prefetch_related('items__product')
    )
    def build_token_details(queryset):
        details = {}
        for inv in queryset:
            items = [
                {'name': item.product.name, 'quantity': item.quantity}
                for item in inv.items.all()
            ]
            details[inv.token_number] = items
        return details
    pending_tokens = [inv.token_number for inv in pending_qs]
    ready_tokens = [inv.token_number for inv in ready_qs]
    token_details = {}
    token_details.update(build_token_details(pending_qs))
    token_details.update(build_token_details(ready_qs))
    return JsonResponse({
        'pending_tokens': pending_tokens,
        'ready_tokens': ready_tokens,
        'token_details': token_details,
        'today': today.isoformat(),
    })


@login_required
def payment_received(request):
    """Record payment received from a customer (party)."""
    if request.method == 'POST':
        party_name = request.POST.get('party_name', '').strip()
        party_phone = (request.POST.get('party_phone') or '').strip()
        amount = request.POST.get('amount')
        invoice_id = request.POST.get('invoice')
        payment_method = request.POST.get('payment_method', 'cash')
        payment_date = request.POST.get('payment_date')
        notes = request.POST.get('notes', '').strip()

        if not party_name:
            messages.error(request, 'Party name is required.')
            return redirect('billing:payment_received')
        try:
            amount = Decimal(amount)
            if amount <= 0:
                raise ValueError('Amount must be positive')
        except (TypeError, ValueError):
            messages.error(request, 'Please enter a valid amount.')
            return redirect('billing:payment_received')

        # Find customer: try exact match first, then by name only (with outstanding balance)
        customer = None
        party_phone = (party_phone or '').strip()
        candidates = Customer.objects.filter(
            name__iexact=party_name.strip(),
            outstanding_balance__gt=0
        ).order_by('-outstanding_balance')
        if party_phone:
            customer = candidates.filter(phone=party_phone).first()
        if not customer:
            customer = candidates.filter(phone='').first()
        if not customer:
            customer = candidates.first()
        if not customer:
            messages.error(request, f'Customer "{party_name}" not found with outstanding balance. Create a credit invoice first.')
            return redirect('billing:payment_received')

        if customer.outstanding_balance <= 0:
            messages.warning(request, f'{customer.name} has no outstanding balance.')
            return redirect('billing:payment_received')

        if amount > customer.outstanding_balance:
            messages.warning(request, f'Amount (Rs{amount}) exceeds outstanding (Rs{customer.outstanding_balance}). Recording Rs{customer.outstanding_balance}.')
            amount = customer.outstanding_balance

        invoice = None
        if invoice_id:
            try:
                invoice = Invoice.objects.get(pk=invoice_id)
                if invoice.outstanding_amount <= 0:
                    invoice = None
                elif amount > invoice.outstanding_amount:
                    amount = invoice.outstanding_amount
            except Invoice.DoesNotExist:
                pass

        with transaction.atomic():
            payment = PaymentReceived.objects.create(
                customer=customer,
                invoice=invoice,
                amount=amount,
                payment_method=payment_method,
                payment_date=payment_date or timezone.localdate(),
                notes=notes,
            )
            _add_ledger_entry(
                customer,
                invoice,
                'payment',
                debit=Decimal('0'),
                credit=amount,
                description=f'Payment received: Rs{amount} via {payment.get_payment_method_display()}' + (f' (Ref: {notes})' if notes else '')
            )

            # If a specific invoice was selected, update just that invoice
            if invoice:
                invoice.advance_paid += amount
                invoice.outstanding_amount = invoice.total_amount - invoice.advance_paid
                if invoice.outstanding_amount <= 0:
                    invoice.status = 'paid'
                else:
                    invoice.status = 'partially_paid'
                invoice.save(update_fields=['advance_paid', 'outstanding_amount', 'status'])
            else:
                # No invoice selected: automatically apply payment to this customer's
                # outstanding invoices (oldest first), so gallery and invoice views stay in sync.
                remaining = amount
                outstanding_invoices = Invoice.objects.filter(
                    customer_name__iexact=customer.name,
                    customer_phone=customer.phone,
                    outstanding_amount__gt=0,
                ).order_by('invoice_date', 'id')

                for inv in outstanding_invoices:
                    if remaining <= 0:
                        break
                    apply_amount = min(remaining, inv.outstanding_amount)
                    if apply_amount <= 0:
                        continue
                    inv.advance_paid += apply_amount
                    inv.outstanding_amount = inv.total_amount - inv.advance_paid
                    if inv.outstanding_amount <= 0:
                        inv.status = 'paid'
                    else:
                        inv.status = 'partially_paid'
                    inv.save(update_fields=['advance_paid', 'outstanding_amount', 'status'])
                    remaining -= apply_amount

        messages.success(request, f'Payment of Rs{amount} recorded successfully for {customer.name}.')
        if invoice:
            return redirect('billing:view_invoice', pk=invoice.pk)
        return redirect('billing:customer_ledger', customer_id=customer.pk)

    form = PaymentReceivedForm()
    customers_with_balance = Customer.objects.filter(outstanding_balance__gt=0).order_by('name')
    # Preselect invoice when coming from invoice detail (via ?invoice=ID)
    selected_invoice_id = None
    try:
        if request.method == 'GET' and request.GET.get('invoice'):
            selected_invoice_id = int(request.GET.get('invoice'))
    except (TypeError, ValueError):
        selected_invoice_id = None
    context = {
        'form': form,
        'customers_with_balance': customers_with_balance,
        'today': timezone.localdate().isoformat(),
        'selected_invoice_id': selected_invoice_id,
    }
    return render(request, 'billing/payment_received.html', context)


@login_required
def customer_ledger(request, customer_id):
    """View customer ledger with all debits, credits, and balance."""
    customer = get_object_or_404(Customer, pk=customer_id)
    entries = customer.ledger_entries.select_related('invoice').order_by('-entry_date', '-id')
    payments = customer.payments_received.select_related('invoice').order_by('-payment_date')
    context = {
        'customer': customer,
        'entries': entries,
        'payments': payments,
    }
    return render(request, 'billing/customer_ledger.html', context)


@login_required
def dues_summary(request):
    """List customers with outstanding dues (for Payment Received flow)."""
    customers = Customer.objects.filter(outstanding_balance__gt=0).order_by('-outstanding_balance')
    total_outstanding = sum(c.outstanding_balance for c in customers)
    context = {
        'customers': customers,
        'total_outstanding': total_outstanding,
    }
    return render(request, 'billing/dues_summary.html', context)

def mark_invoice_paid(request, pk):
    invoice = get_object_or_404(Invoice, pk=pk)
    if request.method == 'POST':
        invoice.advance_paid = invoice.total_amount
        invoice.outstanding_amount = Decimal('0')
        invoice.status = 'paid'
        invoice.save(update_fields=['advance_paid', 'outstanding_amount', 'status'])
        messages.success(request, 'Invoice marked as paid successfully!')
    return redirect('billing:invoices')

@login_required
def company_settings(request):
    # Get or create company settings
    settings, created = CompanySettings.objects.get_or_create()
    
    if request.method == 'POST':
        # Update settings
        settings.company_name = request.POST.get('company_name')
        settings.address_line1 = request.POST.get('address_line1')
        settings.address_line2 = request.POST.get('address_line2')
        settings.city = request.POST.get('city')
        settings.state = request.POST.get('state')
        settings.postal_code = request.POST.get('postal_code')
        settings.phone = request.POST.get('phone')
        settings.email = request.POST.get('email')
        settings.website = request.POST.get('website')
        settings.gstin = request.POST.get('gstin')
        settings.gst_percentage = Decimal(request.POST.get('gst_percentage', '18.00'))
        settings.pan_number = request.POST.get('pan_number')
        settings.bank_name = request.POST.get('bank_name')
        settings.bank_account_number = request.POST.get('bank_account_number', request.POST.get('bank_account', ''))
        settings.bank_ifsc = request.POST.get('bank_ifsc')
        settings.invoice_footer_text = request.POST.get('invoice_footer_text', request.POST.get('invoice_footer', ''))
        dues_days = request.POST.get('dues_days', '7')
        try:
            settings.dues_days = max(1, int(dues_days))
        except (ValueError, TypeError):
            settings.dues_days = 7
        # Printer settings
        settings.printer_type = request.POST.get('printer_type', 'thermal_80mm')
        settings.printer_name = (request.POST.get('printer_name') or '').strip()
        settings.auto_print_dialog = request.POST.get('auto_print_dialog') == '1'
        settings.use_direct_print = request.POST.get('use_direct_print') == '1'
        settings.print_service_url = (request.POST.get('print_service_url') or 'http://localhost:8765').strip()
        # Print options: bill and token toggles
        settings.print_bill_enabled = request.POST.get('print_bill_enabled') == 'on'
        settings.print_token_enabled = request.POST.get('print_token_enabled') == 'on'
        # TV display: order ready sound
        tv_sound = request.POST.get('tv_ready_sound', 'beep')
        if tv_sound in dict(CompanySettings.READY_SOUND_CHOICES):
            settings.tv_ready_sound = tv_sound
        # TV display: announcement voice (system voice name)
        settings.tv_announce_voice = (request.POST.get('tv_announce_voice') or '').strip()[:200]
        # TV display: custom sound file (user upload)
        if request.POST.get('clear_sound_file') == '1':
            if settings.tv_ready_sound_file:
                settings.tv_ready_sound_file.delete(save=False)
            settings.tv_ready_sound_file = None
        else:
            f = request.FILES.get('tv_ready_sound_file')
            if f:
                if settings.tv_ready_sound_file:
                    settings.tv_ready_sound_file.delete(save=False)
                settings.tv_ready_sound_file = f
        settings.save()

        messages.success(request, 'Company settings updated successfully!')
        return redirect('billing:company_settings')
    
    # Get printer list for dropdown (Windows)
    printers_list = _get_windows_printers()
    custom_sound_url = None
    if settings.tv_ready_sound_file:
        custom_sound_url = request.build_absolute_uri(settings.tv_ready_sound_file.url)
    coupon_logged_in = bool(request.session.get('coupon_session_cookie'))
    coupon_login_email = request.session.get('coupon_login_email') or settings.email or ''
    context = {
        'settings': settings,
        'printers_list': printers_list,
        'api_printers_url': reverse('billing:api_printers'),
        'custom_sound_preview_url': custom_sound_url,
        'coupon_logged_in': coupon_logged_in,
        'coupon_login_email': coupon_login_email,
    }
    return render(request, 'billing/company_settings.html', context)

def generate_invoice_pdf(request, invoice_id):
    try:
        invoice = Invoice.objects.get(id=invoice_id)
        company_settings = CompanySettings.objects.first()

        if not company_settings:
            return HttpResponse("Company settings not found. Please configure company settings first.", status=500)

        if not invoice.total_amount:
            invoice.calculate_totals()

        payments = PaymentReceived.objects.filter(invoice=invoice).order_by('-payment_date')
        try:
            amount_in_words = num2words(float(invoice.total_amount), to='currency', lang='en_IN').replace(
                'euro', 'Rupees'
            ).replace('cents', 'paise').title() + " Only"
        except Exception:
            amount_in_words = "Not Provided"

        context = {
            'invoice': invoice,
            'company_settings': company_settings,
            'payments': payments,
            'amount_in_words': amount_in_words,
            'thermal': False,
            'printer_type': 'a4',
            'auto_print': False,
            'printer_name': None,
            'display_token_number': None,
            'show_token_page': False,
            'for_pdf': True,
        }

        pdf_bytes = None
        try:
            import pdfkit
            html_string = render_to_string('billing/invoice_print.html', context, request=request)
            config = get_wkhtmltopdf_config()
            if config:
                opts = get_pdf_options('a4')
                opts['enable-local-file-access'] = None
                pdf_bytes = pdfkit.from_string(html_string, False, configuration=config, options=opts)
        except Exception:
            pdf_bytes = None

        if pdf_bytes is None:
            pdf_bytes = create_invoice_pdf(invoice).getvalue()

        response = HttpResponse(pdf_bytes, content_type='application/pdf')
        response['Content-Disposition'] = f'inline; filename="Invoice_{invoice.invoice_number}.pdf"'
        return response

    except Invoice.DoesNotExist:
        return HttpResponse("Invoice not found", status=404)
    except Exception as e:
        print(f"Error generating PDF: {str(e)}")
        return HttpResponse(f"Error generating PDF: {str(e)}", status=500)

@login_required
def invoice_gallery(request):
    """Display a gallery of generated invoice PDFs with search functionality."""
    # Get search parameters
    customer_name = request.GET.get('customer_name', '')
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    
    # Start with all invoices and prefetch related data
    invoices = Invoice.objects.prefetch_related(
        'items',
        'items__product'
    ).all()
    
    # Apply filters
    if customer_name:
        invoices = invoices.filter(customer_name__icontains=customer_name)
    
    if date_from:
        invoices = invoices.filter(invoice_date__gte=date_from)
    
    if date_to:
        invoices = invoices.filter(invoice_date__lte=date_to)
    
    # Order by creation date
    invoices = invoices.order_by('-created_at')
    
    # Paginate results: 4 columns × 5 rows = 20 invoices per page
    paginator = Paginator(invoices, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    company_settings = CompanySettings.objects.first()
    printer_name = getattr(company_settings, 'printer_name', '') or '' if company_settings else ''
    use_direct_print = bool(printer_name) or getattr(company_settings, 'use_direct_print', False) if company_settings else False
    context = {
        'invoices': page_obj,
        'page_obj': page_obj,
        'search_params': {
            'customer_name': customer_name,
            'date_from': date_from,
            'date_to': date_to,
        },
        'use_direct_print': use_direct_print,
        'print_service_url': (getattr(company_settings, 'print_service_url', '') or 'http://localhost:8765').rstrip('/') if company_settings else 'http://localhost:8765',
        'company_settings': company_settings,
    }
    return render(request, 'billing/invoice_gallery.html', context)

@login_required
def return_rented_item(request, pk):
    rented_item = get_object_or_404(RentedItem, pk=pk)
    
    if request.method == 'POST':
        try:
            return_quantity = int(request.POST.get('return_quantity', 0))
            
            if return_quantity <= 0:
                messages.error(request, 'Please enter a valid return quantity')
                return redirect('billing:return_rented_item', pk=pk)
            
            if return_quantity > rented_item.remaining_quantity:
                messages.error(request, f'Return quantity cannot exceed remaining quantity ({rented_item.remaining_quantity})')
                return redirect('billing:return_rented_item', pk=pk)
            
            # Use transaction to ensure both return and stock update succeed or fail together
            with transaction.atomic():
                # Add return record
                return_record = rented_item.add_return(
                    return_date=timezone.now().date(),
                    returned_qty=return_quantity
                )
                
                # Update stock
                stock = Stock.objects.get(product=rented_item.product)
                stock.quantity += return_quantity
                stock.save()

                # Create notification for item return
                Notification.create(
                    type='return',
                    title=f'Item Returned: {rented_item.product.name}',
                    message=f'{rented_item.customer_name} has returned {return_quantity} units of {rented_item.product.name}. Amount: Rs{return_record.amount}',
                    related_object=rented_item
                )
            
            messages.success(request, f'{return_quantity} items returned successfully')
            return redirect('billing:rent_items')
            
        except ValueError as e:
            messages.error(request, str(e))
            return redirect('billing:return_rented_item', pk=pk)
        except Exception as e:
            messages.error(request, f'Error processing return: {str(e)}')
            return redirect('billing:return_rented_item', pk=pk)
    
    return render(request, 'billing/return_rented_item.html', {'rental': rented_item})

@login_required
def add_advance_payment(request, rental_id):
    """Add an advance payment for a rental item."""
    if request.method == 'POST':
        try:
            rental = get_object_or_404(RentedItem, pk=rental_id)
            amount = request.POST.get('amount', '0')
            notes = request.POST.get('notes', '')

            try:
                amount = Decimal(amount)
            except (ValueError, InvalidOperation):
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({
                        'status': 'error',
                        'message': 'Please enter a valid amount'
                    })
                messages.error(request, 'Please enter a valid amount')
                return redirect('billing:rent_items')

            if amount <= 0:
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({
                        'status': 'error',
                        'message': 'Amount must be greater than 0'
                    })
                messages.error(request, 'Amount must be greater than 0')
                return redirect('billing:rent_items')

            # Create advance payment
            advance_payment = AdvancePayment.objects.create(
                rental_item=rental,
                amount=amount,
                notes=notes
            )

            # If this is an AJAX request, return JSON response
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'status': 'success',
                    'total_advance': float(rental.total_advance_paid),
                    'message': f'Advance payment of Rs{amount} added successfully'
                })

            messages.success(request, f'Advance payment of Rs{amount} added successfully')

        except Exception as e:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'status': 'error',
                    'message': f'Error adding advance payment: {str(e)}'
                })
            messages.error(request, f'Error adding advance payment: {str(e)}')

    return redirect('billing:rent_items')

@api_view(['GET', 'POST'])
def rent_items(request):
    """View for managing rented items."""
    if request.method == 'POST':
        try:
            # Get customer information
            customer_name = request.data.get('customer_name')
            phone = request.data.get('phone')
            email = request.data.get('email')
            expected_return_date = request.data.get('expected_return_date')
            notes = request.data.get('notes')

            # Basic validation
            if not customer_name or not phone or not expected_return_date:
                return Response(
                    {'error': 'Please fill in all required fields (Customer Name, Phone, Expected Return Date)'},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Clean and validate customer name (letters and spaces only)
            customer_name = (customer_name or '').strip()
            if not re.fullmatch(r'[A-Za-z\s]+', customer_name):
                msg = 'Customer name must contain only letters and spaces (no numbers or symbols).'
                if request.content_type == 'application/json':
                    return Response({'error': msg}, status=status.HTTP_400_BAD_REQUEST)
                messages.error(request, msg)
                return redirect('billing:rent_items')

            # Clean and validate phone (10 digits)
            phone = (phone or '').strip()
            if not phone.isdigit() or len(phone) != 10:
                msg = 'Phone number must be a 10-digit number.'
                if request.content_type == 'application/json':
                    return Response({'error': msg}, status=status.HTTP_400_BAD_REQUEST)
                messages.error(request, msg)
                return redirect('billing:rent_items')

            # Get product information
            product_ids = request.data.getlist('product[]')
            quantities = request.data.getlist('quantity[]')

            # Validate that we have at least one product
            if not product_ids or not quantities:
                return Response({'error': 'Please add at least one product'}, 
                              status=status.HTTP_400_BAD_REQUEST)

            # Use transaction to ensure all operations succeed or fail together
            with transaction.atomic():
                # Create rented items
                rented_items = []
                for product_id, quantity in zip(product_ids, quantities):
                    if product_id and quantity:
                        try:
                            product = Product.objects.get(id=product_id)
                            if product.type != 'rent':
                                raise ValueError(f'{product.name} is not available for rent')
                                
                            stock = Stock.objects.get(product=product)
                            
                            # Convert and validate quantity
                            try:
                                quantity = int(quantity)
                                if quantity <= 0:
                                    raise ValueError(f'Please enter a valid quantity for {product.name}')
                            except ValueError as e:
                                raise ValueError(str(e))

                            # Validate stock
                            if quantity > stock.quantity:
                                raise ValueError(f'Only {stock.quantity} units available for {product.name}')

                            # Create rented item using product's daily rental rate
                            rented_item = RentedItem.objects.create(
                                product=product,
                                customer_name=customer_name,
                                phone=phone,
                                email=email,
                                rent_date=timezone.now().date(),
                                expected_return_date=expected_return_date,
                                daily_rental_rate=product.daily_rental_rate,
                                quantity=quantity,
                                notes=notes
                            )
                            
                            # Update stock
                            stock.quantity -= quantity
                            stock.save()

                            # Create notification for new rental
                            Notification.create(
                                type='rent',
                                title=f'New Rental: {product.name}',
                                message=f'{customer_name} has rented {quantity} units of {product.name} at Rs{product.daily_rental_rate} per day. Expected return: {expected_return_date}',
                                related_object=rented_item
                            )
                            
                            rented_items.append(rented_item)

                        except Product.DoesNotExist:
                            raise ValueError('Product not found')
                        except Stock.DoesNotExist:
                            raise ValueError(f'Stock not found for {product.name}')
                        except Exception as e:
                            raise ValueError(str(e))

            # Return success response for API
            if request.content_type == 'application/json':
                return Response({
                    'success': True,
                    'message': 'Items rented successfully!',
                    'rented_items': RentedItemSerializer(rented_items, many=True).data
                })
            
            # Redirect for web interface
            messages.success(request, 'Items rented successfully!')
            return redirect('billing:rent_items')

        except ValueError as e:
            if request.content_type == 'application/json':
                return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
            messages.error(request, str(e))
            return redirect('billing:rent_items')
        except Exception as e:
            if request.content_type == 'application/json':
                return Response({'error': f'Error processing request: {str(e)}'}, 
                              status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            messages.error(request, f'Error processing request: {str(e)}')
            return redirect('billing:rent_items')

    # Get only rental products with their stock information
    products = Product.objects.filter(type='rent').select_related('stock').all()
    
    # Get all rentals and calculate totals
    all_rentals = RentedItem.objects.prefetch_related('advance_payments').all().order_by('-rent_date')
    
    # Filter active and closed rentals based on bill generation status
    active_rentals = all_rentals.filter(is_final_bill_generated=False)
    closed_rentals = all_rentals.filter(is_final_bill_generated=True)
    
    customer_totals = {}
    customer_advances = {}
    customer_bill_status = {}
    
    # Calculate totals for active (unbilled) rentals only
    for rental in active_rentals:
        customer_name = rental.customer_name
        if customer_name not in customer_totals:
            customer_totals[customer_name] = Decimal('0')
            customer_advances[customer_name] = Decimal('0')
            customer_bill_status[customer_name] = {
                'all_returned': True,
                'bill_generated': False
            }
        
        # Only add to totals if not billed
        if not rental.is_final_bill_generated:
            customer_totals[customer_name] += rental.calculate_total()
            customer_advances[customer_name] += rental.total_advance_paid
        
        # Check if all items are returned and if bill is generated
        if not rental.is_fully_returned():
            customer_bill_status[customer_name]['all_returned'] = False
        if rental.is_final_bill_generated:
            customer_bill_status[customer_name]['bill_generated'] = True

    rental_customers = RentedItem.objects.values_list('customer_name', flat=True)
    sales_customers = Invoice.objects.values_list('customer_name', flat=True)
    customer_names = set(f"{c['customer_name']} | {c['phone']}" for c in RentedItem.objects.values('customer_name', 'phone').distinct())
    # Get all unique customers with name, phone, and email
    customers = RentedItem.objects.values('customer_name', 'phone', 'email').distinct()
    
    context = {
        'products': products,
        'active_rentals': active_rentals,
        'closed_rentals': closed_rentals,
        'customer_totals': customer_totals,
        'customer_advances': customer_advances,
        'customer_bill_status': customer_bill_status,
        'bill_generated': request.GET.get('bill_generated') == 'true',
        'customer_names': sorted(customer_names),
        'customers': customers,
    }
    
    # Return JSON response for API
    if request.content_type == 'application/json':
        return Response({
            'products': ProductSerializer(products, many=True).data,
            'active_rentals': RentedItemSerializer(active_rentals, many=True).data,
            'closed_rentals': RentedItemSerializer(closed_rentals, many=True).data,
            'customer_totals': customer_totals,
            'customer_advances': customer_advances,
            'customer_bill_status': customer_bill_status,
            'customers': customers
        })
    
    # Return HTML response for web interface
    return render(request, 'billing/rent_items.html', context)


@login_required
def rent_items_export(request):
    """Export rental items to CSV (active and closed)."""
    rentals = RentedItem.objects.select_related('product').all().order_by('-rent_date')

    import csv
    from io import StringIO

    buffer = StringIO()
    writer = csv.writer(buffer)

    writer.writerow(['Rent Items'])
    writer.writerow([])
    writer.writerow([
        'Customer',
        'Phone',
        'Email',
        'Product',
        'Quantity',
        'Daily Rate (Rs)',
        'Rent Date',
        'Expected Return',
        'Is Returned',
        'Notes',
    ])

    for item in rentals:
        writer.writerow([
            item.customer_name,
            item.phone,
            item.email or '',
            item.product.name if item.product_id else '',
            item.quantity,
            item.daily_rental_rate,
            item.rent_date,
            item.expected_return_date,
            'Yes' if item.is_returned else 'No',
            (item.notes or '').replace('\r\n', ' ').replace('\n', ' '),
        ])

    csv_data = buffer.getvalue()
    buffer.close()

    response = HttpResponse(csv_data, content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="rent_items_export.csv"'
    return response

@login_required
def return_customer_rentals(request, customer_name):
    """Generate final bill for all returned rentals of a customer."""
    try:
        # Get all rentals for the customer
        rentals = RentedItem.objects.filter(
            customer_name=customer_name,
            is_final_bill_generated=False  # Only get unbilled rentals
        ).prefetch_related('advance_payments')

        # Check if all items are returned
        if not rentals.exists():
            messages.error(request, 'No rentals found for this customer')
            return redirect('billing:rent_items')

        # Check if all items are returned
        if not all(rental.is_fully_returned() for rental in rentals):
            messages.error(request, 'Cannot generate final bill until all items are returned')
            return redirect('billing:rent_items')

        # Calculate total advance payments
        total_advance = sum(rental.total_advance_paid for rental in rentals)

        # Get company settings for invoice
        company_settings = CompanySettings.objects.first()
        if not company_settings:
            messages.error(request, 'Please configure company settings first')
            return redirect('billing:rent_items')

        # Generate unique invoice number
        timestamp = timezone.now().strftime("%Y%m%d%H%M%S")
        base_invoice_number = f'RENT-{timestamp}'
        invoice_number = base_invoice_number
        counter = 1
        
        # Keep trying until we find a unique invoice number
        while Invoice.objects.filter(invoice_number=invoice_number).exists():
            invoice_number = f'{base_invoice_number}-{counter}'
            counter += 1

        # Calculate total amount
        total_amount = sum(rental.calculate_total() for rental in rentals)

        # Determine status based on advance vs total
        outstanding = total_amount - total_advance
        inv_status = 'paid' if outstanding <= 0 else ('partially_paid' if total_advance > 0 else 'credit')

        # Token system: assign daily token when enabled
        company_settings = CompanySettings.objects.first()
        token_enabled = bool(company_settings and getattr(company_settings, 'enable_token_system', False))
        invoice_date = timezone.localdate()
        token_kwargs = {}
        if token_enabled:
            last_token = (
                Invoice.objects
                .filter(invoice_date=invoice_date, token_number__isnull=False)
                .aggregate(max_token=Max('token_number'))
                .get('max_token') or 0
            )
            token_kwargs['token_number'] = last_token + 1
            token_kwargs['token_status'] = 'pending'

        # Create invoice
        invoice = Invoice.objects.create(
            invoice_number=invoice_number,
            customer_name=customer_name,
            customer_phone=rentals.first().phone or '',
            customer_address=f"Phone: {rentals.first().phone}\nEmail: {rentals.first().email}",
            invoice_date=invoice_date,
            due_date=invoice_date,
            status=inv_status,
            subtotal=total_amount,
            total_amount=total_amount,
            advance_paid=total_advance,
            outstanding_amount=max(outstanding, Decimal('0')),
            notes=f'Final bill for {customer_name}\n\nRental Details:\n',
            **token_kwargs,
        )

        # Add rental details to notes
        for rental in rentals:
            return_record = rental.return_history.first()
            days_rented = max((return_record.return_date - rental.rent_date).days, 1)
            invoice.notes += f"\nProduct: {rental.product.name}"
            invoice.notes += f"\nQuantity: {rental.quantity}"
            invoice.notes += f"\nDays: {days_rented}"
            invoice.notes += f"\nAmount: Rs{return_record.amount}"
            
            # Create invoice item
            InvoiceItem.objects.create(
                invoice=invoice,
                product=rental.product,
                quantity=rental.quantity,
                unit_price=rental.daily_rental_rate * days_rented,
                total=return_record.amount
            )

        invoice.notes += f'\n\nTotal Amount: Rs{total_amount}\nAdvance Paid: Rs{total_advance}\nFinal Amount: Rs{total_amount - total_advance}'
        invoice.save()

        # Update A/R ledger for credit/partial rental bills
        if outstanding > 0:
            customer = _get_or_create_customer(
                customer_name,
                rentals.first().phone or '',
                email=rentals.first().email or '',
                address=f"Phone: {rentals.first().phone}\nEmail: {rentals.first().email}"
            )
            _add_ledger_entry(
                customer,
                invoice,
                'invoice',
                debit=outstanding,
                credit=Decimal('0'),
                description=f'Rental Invoice {invoice.invoice_number} - Outstanding'
            )

        # Mark rentals as billed
        for rental in rentals:
            rental.is_final_bill_generated = True
            rental.save()

        # Create notification for bill generation
        Notification.create(
            type='bill',
            title=f'Bill Generated: {invoice.invoice_number}',
            message=f'Final bill generated for {customer_name}. Total Amount: Rs{total_amount}, Advance Paid: Rs{total_advance}, Final Amount: Rs{total_amount - total_advance}',
            related_object=invoice
        )

        messages.success(request, f'Final bill generated successfully. Invoice number: {invoice.invoice_number}')
        return redirect(f'/api/invoices/{invoice.id}/')

    except Exception as e:
        messages.error(request, f'Error generating final bill: {str(e)}')
        return redirect('billing:rent_items')

def base_context(request):
    """Context processor to add common data to all templates."""
    company_settings = CompanySettings.objects.first()
    return {
        'company_settings': company_settings,
    }


def _get_windows_printers():
    """Get list of printers on Windows. Tries pywin32 first, then PowerShell, then wmic."""
    import subprocess
    printers = []
    # 1. Try pywin32 (best)
    try:
        import win32print
        raw = win32print.EnumPrinters(
            win32print.PRINTER_ENUM_LOCAL | win32print.PRINTER_ENUM_CONNECTIONS
        )
        for item in raw:
            name = item[2] if len(item) > 2 else str(item)
            if name and name not in printers:
                printers.append(name)
    except Exception:
        pass
    # 2. Fallback: PowerShell (no pywin32 needed)
    if not printers:
        try:
            result = subprocess.run(
                ['powershell', '-Command', 'Get-Printer | Select-Object -ExpandProperty Name'],
                capture_output=True, text=True, timeout=10, creationflags=0x08000000 if os.name == 'nt' else 0
            )
            if result.returncode == 0 and result.stdout:
                for line in result.stdout.strip().splitlines():
                    name = line.strip()
                    if name and name not in printers:
                        printers.append(name)
        except Exception:
            pass
    # 3. Fallback: wmic
    if not printers:
        try:
            result = subprocess.run(
                ['wmic', 'printer', 'get', 'name'],
                capture_output=True, text=True, timeout=10, creationflags=0x08000000 if os.name == 'nt' else 0
            )
            if result.returncode == 0 and result.stdout:
                lines = result.stdout.strip().splitlines()[1:]  # skip header
                for line in lines:
                    name = line.strip()
                    if name and name not in printers and name.lower() != 'name':
                        printers.append(name)
        except Exception:
            pass
    printers.sort()
    return printers


def get_removable_drives():
    """Get list of removable drives on Windows"""
    drives = []
    try:
        # Use wmic to get removable drives with more detailed information
        output = os.popen("wmic logicaldisk where drivetype=2 get deviceid,volumename,size,freespace").read()
        
        # Process each line of output
        for line in output.split('\n'):
            if line.strip():
                parts = line.strip().split()
                if len(parts) >= 1:
                    drive = parts[0]
                    # Get volume name if available, otherwise use drive letter
                    name = parts[1] if len(parts) > 1 else f"Drive {drive[0]}"
                    
                    # Verify drive exists and is accessible
                    if os.path.exists(drive):
                        try:
                            # Try to access the drive to ensure it's mounted
                            os.listdir(drive)
                            drives.append({
                                'path': drive,
                                'name': name,
                                'size': parts[2] if len(parts) > 2 else 'Unknown',
                                'free_space': parts[3] if len(parts) > 3 else 'Unknown'
                            })
                        except Exception as e:
                            print(f"Error accessing drive {drive}: {e}")
                            continue
    except Exception as e:
        print(f"Error getting removable drives: {e}")
        # Fallback method using direct drive letter check
        for letter in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ':
            drive = f"{letter}:\\"
            if os.path.exists(drive):
                try:
                    # Check if it's a removable drive by trying to access it
                    os.listdir(drive)
                    drives.append({
                        'path': drive,
                        'name': f"Drive {letter}",
                        'size': 'Unknown',
                        'free_space': 'Unknown'
                    })
                except Exception:
                    continue
    
    return drives

@login_required
@require_http_methods(["GET"])
def api_get_printers(request):
    """Return list of printers connected to this computer (Windows)."""
    printers = _get_windows_printers()
    return JsonResponse({'printers': printers, 'error': None})


@require_http_methods(["GET"])
def check_pendrive(request):
    """Check if a pendrive is connected"""
    try:
        drives = get_removable_drives()
        if drives:
            # Get the first removable drive
            drive = drives[0]
            return JsonResponse({
                'drive_detected': True,
                'drive_name': drive['name'],
                'drive_path': drive['path'],
                'drive_size': drive['size'],
                'free_space': drive['free_space']
            })
        return JsonResponse({
            'drive_detected': False,
            'drive_name': '',
            'drive_path': '',
            'drive_size': '',
            'free_space': ''
        })
    except Exception as e:
        print(f"Error in check_pendrive: {e}")
        return JsonResponse({
            'drive_detected': False,
            'drive_name': '',
            'drive_path': '',
            'drive_size': '',
            'free_space': '',
            'error': str(e)
        })

@require_http_methods(["POST"])
def start_backup(request):
    """Start the backup process"""
    try:
        # Get backup parameters
        include_images = request.POST.get('include_images', 'false') == 'true'
        compress_backup = request.POST.get('compress_backup', 'false') == 'true'
        drive_path = request.POST.get('drive_path')
        
        if not drive_path:
            return JsonResponse({
                'status': 'error',
                'message': 'No drive path provided'
            })
        
        # Create backup directory
        backup_dir = os.path.join(drive_path, 'invoice_backup')
        os.makedirs(backup_dir, exist_ok=True)
        
        # Get all invoices
        invoices = Invoice.objects.all()
        
        # Prepare backup data
        backup_data = {
            'invoices': [],
            'timestamp': datetime.now().isoformat(),
            'version': '1.0'
        }
        
        # Process each invoice
        total_invoices = invoices.count()
        for index, invoice in enumerate(invoices):
            # Update progress
            progress = int((index + 1) / total_invoices * 100)
            
            # Create invoice data
            invoice_data = {
                'invoice_number': invoice.invoice_number,
                'customer_name': invoice.customer_name,
                'invoice_date': invoice.invoice_date.isoformat(),
                'total_amount': str(invoice.total_amount),
                'advance_paid': str(invoice.advance_paid),
                'status': invoice.status,
                'notes': invoice.notes,
                'created_at': invoice.created_at.isoformat(),
                'updated_at': invoice.updated_at.isoformat(),
                'items': []
            }
            
            # Add invoice items
            for item in invoice.items.all():
                item_data = {
                    'product_name': item.product.name,
                    'quantity': item.quantity,
                    'unit_price': str(item.unit_price),
                    'total': str(item.total)
                }
                invoice_data['items'].append(item_data)
            
            backup_data['invoices'].append(invoice_data)
        
        # Save backup data
        backup_file = os.path.join(backup_dir, 'backup.json')
        with open(backup_file, 'w', encoding='utf-8') as f:
            json.dump(backup_data, f, indent=2, ensure_ascii=False)
        
        # Compress backup if requested
        if compress_backup:
            try:
                zip_file = os.path.join(drive_path, 'invoice_backup.zip')
                with zipfile.ZipFile(zip_file, 'w', zipfile.ZIP_DEFLATED) as zipf:
                    for root, dirs, files in os.walk(backup_dir):
                        for file in files:
                            file_path = os.path.join(root, file)
                            arcname = os.path.relpath(file_path, backup_dir)
                            zipf.write(file_path, arcname)
                
                # Remove uncompressed backup directory
                shutil.rmtree(backup_dir)
                final_path = zip_file
            except Exception as e:
                print(f"Error compressing backup: {e}")
                final_path = backup_file
        else:
            final_path = backup_file
        
        # Create backup history record with correct field names
        BackupHistory.objects.create(
            type='backup',  # Changed from backup_type to type
            location=final_path,  # Changed from file_path to location
            size=f"{os.path.getsize(final_path) / 1024:.2f} KB",
            status='success',
            details=f"Backed up {total_invoices} invoices to {drive_path}"
        )
        
        return JsonResponse({
            'status': 'success',
            'message': 'Backup completed successfully',
            'progress': 100
        })
        
    except Exception as e:
        print(f"Error in start_backup: {e}")
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        })

@login_required
def start_restore(request):
    if request.method == 'POST':
        try:
            backup_file = request.POST.get('backup_file')
            overwrite_existing = request.POST.get('overwrite_existing', 'false') == 'true'
            restore_images = request.POST.get('restore_images', 'false') == 'true'

            if not backup_file:
                return JsonResponse({
                    'status': 'error',
                    'message': 'Please select a backup file.'
                })

            # Convert relative path to absolute path
            backup_file = os.path.abspath(backup_file)
            print(f"Attempting to restore from: {backup_file}")

            if not os.path.exists(backup_file):
                print(f"Backup file not found at: {backup_file}")
                return JsonResponse({
                    'status': 'error',
                    'message': f'Backup file not found at: {backup_file}'
                })

            # Create a temporary directory for extraction if needed
            temp_dir = None
            try:
                if backup_file.endswith('.zip'):
                    print("Processing ZIP backup file...")
                    temp_dir = tempfile.mkdtemp()
                    print(f"Created temporary directory: {temp_dir}")
                    
                    with zipfile.ZipFile(backup_file, 'r') as zip_ref:
                        zip_ref.extractall(temp_dir)
                        print(f"Extracted files to: {temp_dir}")
                    
                    # Look for backup.json in the extracted files
                    backup_json = os.path.join(temp_dir, 'backup.json')
                    if not os.path.exists(backup_json):
                        print("backup.json not found in ZIP file")
                        return JsonResponse({
                            'status': 'error',
                            'message': 'Invalid backup file: backup.json not found in ZIP archive'
                        })
                    backup_file = backup_json
                    print(f"Found backup.json at: {backup_file}")

                # Read and validate backup data
                print("Reading backup data...")
                with open(backup_file, 'r', encoding='utf-8') as f:
                    backup_data = json.load(f)
                    print(f"Successfully read backup data with {len(backup_data.get('invoices', []))} invoices")

                if 'invoices' not in backup_data:
                    print("No invoices found in backup data")
                    return JsonResponse({
                        'status': 'error',
                        'message': 'Invalid backup file: No invoices found'
                    })

                # Get total number of invoices for progress calculation
                total_invoices = len(backup_data['invoices'])
                print(f"Total invoices to restore: {total_invoices}")

                # Restore invoices
                restored_count = 0
                for invoice_data in backup_data['invoices']:
                    try:
                        invoice_number = invoice_data.get('invoice_number')
                        if not invoice_number:
                            print("Skipping invoice with no invoice number")
                            continue

                        # Check if invoice already exists
                        existing_invoice = Invoice.objects.filter(invoice_number=invoice_number).first()
                        if existing_invoice and not overwrite_existing:
                            print(f"Skipping existing invoice: {invoice_number}")
                            continue

                        # Create or update invoice
                        inv_status = invoice_data.get('status', 'draft')
                        if inv_status == 'pending':
                            inv_status = 'credit'
                        invoice, created = Invoice.objects.update_or_create(
                            invoice_number=invoice_number,
                            defaults={
                                'customer_name': invoice_data.get('customer_name', ''),
                                'customer_address': invoice_data.get('customer_address', ''),
                                'invoice_date': invoice_data.get('invoice_date'),
                                'due_date': invoice_data.get('due_date', invoice_data.get('invoice_date')),
                                'total_amount': Decimal(str(invoice_data.get('total_amount', 0))),
                                'advance_paid': Decimal(str(invoice_data.get('advance_paid', 0))),
                                'notes': invoice_data.get('notes', ''),
                                'status': inv_status
                            }
                        )
                        print(f"{'Created' if created else 'Updated'} invoice: {invoice_number}")

                        # Handle invoice items
                        if 'items' in invoice_data:
                            # Clear existing items if updating
                            if not created:
                                invoice.items.all().delete()
                            
                            for idx, item_data in enumerate(invoice_data['items']):
                                try:
                                    product_name = item_data.get('product_name', '')
                                    if not product_name:
                                        print(f"Skipping item with no product name for invoice {invoice_number}")
                                        continue
                                    sku_base = product_name.replace(' ', '-')[:15] if product_name else 'RESTORE'
                                    sku = f"RESTORE-{sku_base}-{invoice_number}-{idx}"[:50]
                                    product, created = Product.objects.get_or_create(
                                        sku=sku,
                                        defaults={
                                            'name': product_name,
                                            'price': Decimal(str(item_data.get('unit_price', 0))),
                                            'type': 'sale',
                                            'cost_price': Decimal('0')
                                        }
                                    )
                                    if created:
                                        Stock.objects.get_or_create(product=product, defaults={'quantity': 0, 'low_stock_threshold': 10})

                                    # Create invoice item with all details
                                    InvoiceItem.objects.create(
                                        invoice=invoice,
                                        product=product,
                                        quantity=item_data.get('quantity', 0),
                                        unit_price=Decimal(item_data.get('unit_price', 0)),
                                        total=Decimal(item_data.get('total', 0)),
                                        description=item_data.get('description', product_name),
                                        days=item_data.get('days', 1),
                                        amount=Decimal(item_data.get('amount', 0))
                                    )
                                    print(f"Restored item: {product_name} for invoice {invoice_number}")
                                except Exception as e:
                                    print(f"Error restoring item for invoice {invoice_number}: {str(e)}")
                                    continue

                        # Handle invoice image if present (only if Invoice has image field)
                        if restore_images and 'image' in invoice_data and hasattr(invoice, 'image'):
                            image_data = invoice_data['image']
                            if image_data:
                                try:
                                    image_bytes = base64.b64decode(image_data)
                                    image_filename = f'invoice_{invoice_number}.jpg'
                                    image_path = os.path.join(settings.MEDIA_ROOT, 'invoice_images', image_filename)
                                    os.makedirs(os.path.dirname(image_path), exist_ok=True)
                                    with open(image_path, 'wb') as f:
                                        f.write(image_bytes)
                                    invoice.image = f'invoice_images/{image_filename}'
                                    invoice.save()
                                    print(f"Restored image for invoice {invoice_number}")
                                except Exception as e:
                                    print(f"Error restoring image for invoice {invoice_number}: {str(e)}")

                        restored_count += 1
                        progress = int((restored_count / total_invoices) * 100)
                        print(f"Restore progress: {progress}%")

                    except Exception as e:
                        print(f"Error restoring invoice {invoice_number}: {str(e)}")
                        continue

                # Clean up temporary directory if it exists
                if temp_dir and os.path.exists(temp_dir):
                    shutil.rmtree(temp_dir)
                    print("Cleaned up temporary directory")

                print(f"Restore completed. Successfully restored {restored_count} out of {total_invoices} invoices.")
                return JsonResponse({
                    'status': 'success',
                    'message': f'Successfully restored {restored_count} invoices',
                    'progress': 100
                })

            finally:
                # Ensure temporary directory is cleaned up
                if temp_dir and os.path.exists(temp_dir):
                    shutil.rmtree(temp_dir)

        except Exception as e:
            print(f"Restore error: {str(e)}")
            return JsonResponse({
                'status': 'error',
                'message': f'Restore failed: {str(e)}'
            })

    return JsonResponse({
        'status': 'error',
        'message': 'Invalid request method'
    })

@require_http_methods(["GET"])
def get_backup_history(request):
    """Get backup history"""
    history = BackupHistory.objects.all()[:10]  # Get last 10 entries
    history_data = [{
        'id': entry.id,
        'date': entry.date.strftime('%Y-%m-%d %H:%M:%S'),
        'type': entry.type,
        'location': entry.location,
        'size': entry.size,
        'status': entry.status,
        'details': entry.details
    } for entry in history]
    
    return JsonResponse({
        'history': history_data
    })

@login_required
def backup_restore(request):
    """Render backup and restore page"""
    return render(request, 'billing/backup_restore.html')

@login_required
@login_required
def customers(request):
    """
    Customers overview based on Customer master and Invoice data.
    """
    from collections import OrderedDict

    customer_map = OrderedDict()  # (name, phone) -> stats dict

    for cust in Customer.objects.all():
        key = (cust.name or '', cust.phone or '')
        invoices_qs = Invoice.objects.filter(customer_name__iexact=cust.name)
        if cust.phone:
            invoices_qs = invoices_qs.filter(customer_phone__iexact=cust.phone)
            
        inv_totals = invoices_qs.aggregate(total=Sum('total_amount'))
        total_spent = inv_totals['total'] or Decimal('0')
        total_invoices_count = invoices_qs.count()

        customer_map[key] = {
            'id': cust.id,
            'name': cust.name,
            'phone': cust.phone or '',
            'email': cust.email or '',
            'gstin': getattr(cust, 'gstin', ''),
            'total_rentals': total_invoices_count,
            'total_spent': total_spent,
        }

    customer_data = list(customer_map.values())
    total_invoices = sum(c['total_rentals'] for c in customer_data)
    total_revenue = sum(c['total_spent'] for c in customer_data)

    context = {
        'customers': customer_data,
        'total_rentals': total_invoices,
        'total_revenue': total_revenue,
    }
    return render(request, 'billing/customers.html', context)


