from decimal import Decimal
from datetime import datetime
import re

from django.db import transaction
from django.db.models import Count, Q, Sum, Value
from django.db.models.functions import Coalesce
from django.utils import timezone
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import (
    CompanySettings,
    PurchaseOrder,
    PurchaseOrderItem,
    PurchaseReceipt,
    PurchaseReceiptItem,
    RawMaterial,
    StockMovementLog,
    Supplier,
)
from .procurement import GSTIN_RE, calc_charge, calc_line, is_interstate, money
from .serializers import (
    PurchaseOrderSerializer,
    PurchaseReceiptSerializer,
    SupplierSerializer,
)


def generate_po_number():
    year = timezone.localdate().year
    prefix = f'PO-{year}-'
    last = PurchaseOrder.objects.filter(order_number__startswith=prefix).order_by('-order_number').first()
    seq = 1
    if last and last.order_number:
        try:
            seq = int(last.order_number.split('-')[-1]) + 1
        except Exception:
            seq = PurchaseOrder.objects.filter(order_number__startswith=prefix).count() + 1
    return f'{prefix}{seq:05d}'


def generate_grn_number():
    today = timezone.localdate().strftime('%Y%m%d')
    prefix = f'GRN-{today}-'
    last = PurchaseReceipt.objects.filter(receipt_number__startswith=prefix).order_by('-id').first()
    seq = 1
    if last:
        try:
            seq = int(last.receipt_number.split('-')[-1]) + 1
        except Exception:
            seq = PurchaseReceipt.objects.filter(receipt_number__startswith=prefix).count() + 1
    return f'{prefix}{seq:04d}'


def company_gstin():
    cs = CompanySettings.objects.first()
    return (cs.gstin or '') if cs else ''


def apply_po_totals(po, items_data, extra_charges, round_off):
    cs = CompanySettings.objects.first()
    interstate = is_interstate(
        po.supplier_gstin,
        company_gstin(),
        getattr(po, 'supplier_state', '') or '',
        (cs.state or '') if cs else '',
    )
    po.is_interstate = interstate
    po.save(update_fields=['is_interstate'])

    po.items.all().delete()
    for item in items_data:
        rm_id = item.get('raw_material')
        if not rm_id:
            continue
        rm = RawMaterial.objects.filter(id=rm_id).first()
        if not rm:
            continue
        qty = Decimal(str(item.get('quantity') or 0))
        rate = Decimal(str(item.get('unit_cost') or item.get('rate') or 0))
        disc = Decimal(str(item.get('discount') or 0))
        raw_gst = item.get('gst_rate')
        if raw_gst in (None, ''):
            from .procurement import company_default_gst
            raw_gst = rm.gst_rate if rm.gst_rate is not None else company_default_gst()
        gst_rate = Decimal(str(raw_gst))
        if qty <= 0:
            continue
        line = calc_line(qty, rate, disc, gst_rate, interstate)
        item = PurchaseOrderItem(
            purchase_order=po,
            raw_material=rm,
            hsn_code=item.get('hsn_code') or rm.hsn_code or '',
            specification=item.get('specification') or '',
            uom=item.get('uom') or rm.unit or 'kg',
            quantity=qty,
            unit_cost=money(rate),
            discount=line['discount'],
            taxable_amount=line['taxable_amount'],
            gst_rate=gst_rate,
            cgst=line['cgst'],
            sgst=line['sgst'],
            igst=line['igst'],
            total=line['total'],
        )
        item.save(recalc_po=False)

    cleaned_charges = []
    for ch in extra_charges or []:
        name = str(ch.get('name') or '').strip()
        if not name:
            continue
        gst_app = bool(ch.get('gst_applicable'))
        gst_rate = Decimal(str(ch.get('gst_rate') or 0))
        calc = calc_charge(ch.get('amount') or 0, gst_app, gst_rate, interstate)
        cleaned_charges.append({
            'name': name,
            'amount': str(calc['amount']),
            'gst_applicable': gst_app,
            'gst_rate': str(gst_rate),
            'cgst': str(calc['cgst']),
            'sgst': str(calc['sgst']),
            'igst': str(calc['igst']),
            'total': str(calc['total']),
        })
    po.extra_charges = cleaned_charges
    po.round_off = money(round_off or 0)
    po.save(update_fields=['extra_charges', 'round_off', 'updated_at'])
    po.calculate_totals()
    return po


def refresh_po_receive_status(po):
    items = list(PurchaseOrderItem.objects.filter(purchase_order=po))
    if not items:
        return
    remaining = sum((i.remaining_quantity for i in items), Decimal('0'))
    received = sum((Decimal(str(i.received_quantity or 0)) for i in items), Decimal('0'))
    if received <= 0:
        return
    if remaining <= 0:
        po.status = 'received'
        po.received_date = timezone.localdate()
    else:
        po.status = 'partially_received'
    po.save(update_fields=['status', 'received_date', 'updated_at'])


class SupplierViewSet(viewsets.ModelViewSet):
    queryset = Supplier.objects.all()
    serializer_class = SupplierSerializer
    def get_queryset(self):
        qs = Supplier.objects.all()
        search = self.request.query_params.get('search') or self.request.query_params.get('q')
        if search:
            qs = qs.filter(
                Q(name__icontains=search) | Q(gstin__icontains=search) | Q(phone__icontains=search)
            )
        return qs


class PurchaseOrderViewSet(viewsets.ModelViewSet):
    queryset = PurchaseOrder.objects.prefetch_related('items__raw_material', 'receipts').all().order_by('-created_at')
    serializer_class = PurchaseOrderSerializer
    def get_queryset(self):
        qs = PurchaseOrder.objects.prefetch_related('items__raw_material', 'receipts__items').order_by('-created_at')
        search = self.request.query_params.get('search') or self.request.query_params.get('q')
        status_f = self.request.query_params.get('status')
        date_from = self.request.query_params.get('date_from')
        date_to = self.request.query_params.get('date_to')
        if search:
            qs = qs.filter(
                Q(order_number__icontains=search)
                | Q(supplier_name__icontains=search)
                | Q(supplier_gstin__icontains=search)
            )
        if status_f:
            qs = qs.filter(status=status_f)
        if date_from:
            qs = qs.filter(order_date__gte=date_from)
        if date_to:
            qs = qs.filter(order_date__lte=date_to)
        return qs

    def _payload_from_request(self, data, po=None):
        supplier_id = data.get('supplier')
        supplier = None
        if supplier_id:
            supplier = Supplier.objects.filter(id=supplier_id).first()
        name = (data.get('supplier_name') or (supplier.name if supplier else '')).strip()
        gstin = (data.get('supplier_gstin') or (supplier.gstin if supplier else '')).strip().upper()
        if gstin and not re.fullmatch(GSTIN_RE, gstin):
            return None, 'Invalid supplier GSTIN format.'
        if not name:
            return None, 'Please select a supplier.'
        items = data.get('items') or []
        if not items:
            return None, 'Please add at least one raw material line.'
        fields = {
            'supplier': supplier,
            'supplier_name': name,
            'supplier_phone': data.get('supplier_phone') or (supplier.phone if supplier else ''),
            'supplier_address': data.get('supplier_address') or (supplier.address if supplier else ''),
            'supplier_gstin': gstin,
            'order_date': data.get('order_date') or timezone.localdate(),
            'expected_delivery_date': data.get('expected_delivery_date') or None,
            'warehouse': data.get('warehouse') or '',
            'payment_terms': data.get('payment_terms') or '30',
            'payment_due_date': data.get('payment_due_date') or None,
            'payment_notes': data.get('payment_notes') or '',
            'reference_number': data.get('reference_number') or '',
            'delivery_address': data.get('delivery_address') or '',
            'transporter': data.get('transporter') or '',
            'vehicle_number': data.get('vehicle_number') or '',
            'lr_number': data.get('lr_number') or '',
            'delivery_instructions': data.get('delivery_instructions') or '',
            'notes': data.get('notes') or '',
            'terms': data.get('terms') or '',
        }
        return fields, None

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        fields, err = self._payload_from_request(request.data)
        if err:
            return Response({'error': err}, status=400)
        po = PurchaseOrder.objects.create(order_number=generate_po_number(), status='draft', **fields)
        apply_po_totals(po, request.data.get('items'), request.data.get('extra_charges'), request.data.get('round_off'))
        if request.data.get('place_order'):
            po.status = 'ordered'
            po.save(update_fields=['status', 'updated_at'])
        return Response(PurchaseOrderSerializer(po).data, status=201)

    @transaction.atomic
    def update(self, request, *args, **kwargs):
        po = self.get_object()
        if po.status in ('received', 'cancelled', 'closed'):
            return Response({'error': 'This purchase order can no longer be edited.'}, status=400)
        if po.status == 'partially_received':
            return Response({'error': 'Partially received POs cannot change commercial lines. Use Receive for remaining qty.'}, status=400)
        fields, err = self._payload_from_request(request.data, po)
        if err:
            return Response({'error': err}, status=400)
        for k, v in fields.items():
            setattr(po, k, v)
        po.save()
        apply_po_totals(po, request.data.get('items'), request.data.get('extra_charges'), request.data.get('round_off'))
        return Response(PurchaseOrderSerializer(po).data)

    @action(detail=False, methods=['get'])
    def stats(self, request):
        qs = PurchaseOrder.objects.exclude(status='cancelled')
        def cnt(st):
            return PurchaseOrder.objects.filter(status=st).count()
        total_value = qs.aggregate(t=Coalesce(Sum('total_amount'), Value(Decimal('0'))))['t']
        return Response({
            'total': PurchaseOrder.objects.count(),
            'draft': cnt('draft'),
            'pending_approval': 0,
            'ordered': cnt('ordered'),
            'partially_received': cnt('partially_received'),
            'received': cnt('received'),
            'cancelled': cnt('cancelled'),
            'closed': cnt('closed'),
            'total_value': total_value,
            'pending_receipts': PurchaseOrder.objects.filter(status__in=['ordered', 'partially_received']).count(),
        })

    @action(detail=True, methods=['post'])
    def place_order(self, request, pk=None):
        po = self.get_object()
        if po.status != 'draft':
            return Response({'error': 'Only draft POs can be marked Ordered.'}, status=400)
        if not po.items.exists():
            return Response({'error': 'Add at least one item before placing the order.'}, status=400)
        po.status = 'ordered'
        po.save(update_fields=['status', 'updated_at'])
        return Response(PurchaseOrderSerializer(po).data)

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        po = self.get_object()
        if po.status in ('cancelled', 'received', 'closed'):
            return Response({'error': 'This purchase order cannot be cancelled.'}, status=400)
        reason = str(request.data.get('reason') or '').strip()
        if not reason:
            return Response({'error': 'Cancellation reason is required.'}, status=400)
        po.status = 'cancelled'
        po.cancelled_reason = reason
        po.cancelled_at = timezone.now()
        po.save(update_fields=['status', 'cancelled_reason', 'cancelled_at', 'updated_at'])
        return Response(PurchaseOrderSerializer(po).data)

    @action(detail=True, methods=['post'])
    def duplicate(self, request, pk=None):
        src = self.get_object()
        po = PurchaseOrder.objects.create(
            order_number=generate_po_number(),
            status='draft',
            supplier=src.supplier,
            supplier_name=src.supplier_name,
            supplier_phone=src.supplier_phone,
            supplier_address=src.supplier_address,
            supplier_gstin=src.supplier_gstin,
            order_date=timezone.localdate(),
            expected_delivery_date=src.expected_delivery_date,
            warehouse=src.warehouse,
            payment_terms=src.payment_terms,
            notes=src.notes,
            terms=src.terms,
            extra_charges=src.extra_charges or [],
            round_off=src.round_off,
        )
        items = []
        for it in src.items.all():
            items.append({
                'raw_material': it.raw_material_id,
                'hsn_code': it.hsn_code,
                'specification': it.specification,
                'quantity': it.quantity,
                'uom': it.uom,
                'unit_cost': it.unit_cost,
                'discount': it.discount,
                'gst_rate': it.gst_rate,
            })
        apply_po_totals(po, items, po.extra_charges, po.round_off)
        return Response(PurchaseOrderSerializer(po).data, status=201)

    @action(detail=True, methods=['post'])
    @transaction.atomic
    def receive(self, request, pk=None):
        po = self.get_object()
        if po.status in ('cancelled', 'draft', 'closed'):
            return Response({'error': 'This PO cannot be received in its current status. Place the order first.'}, status=400)
        if po.status == 'received':
            return Response({'error': 'This purchase order is already fully received.'}, status=400)

        lines = request.data.get('items') or []
        if not lines:
            return Response({'error': 'Add at least one received quantity.'}, status=400)

        receipt = PurchaseReceipt.objects.create(
            receipt_number=generate_grn_number(),
            purchase_order=po,
            supplier=po.supplier,
            receipt_date=request.data.get('receipt_date') or timezone.localdate(),
            warehouse=request.data.get('warehouse') or po.warehouse,
            received_by=request.data.get('received_by') or '',
            notes=request.data.get('notes') or '',
        )

        any_qty = False
        for line in lines:
            po_item = po.items.filter(id=line.get('po_item')).select_related('raw_material').first()
            if not po_item:
                continue
            qty = Decimal(str(line.get('quantity') or 0))
            if qty <= 0:
                continue
            remaining = po_item.remaining_quantity
            if qty > remaining:
                transaction.set_rollback(True)
                return Response(
                    {'error': f'Received quantity cannot exceed remaining quantity for this line ({remaining}).'},
                    status=400,
                )
            mfg = line.get('mfg_date') or None
            exp = line.get('expiry_date') or None
            if mfg and exp and str(exp) <= str(mfg):
                transaction.set_rollback(True)
                return Response({'error': 'Expiry date must be after manufacturing date.'}, status=400)

            rm = po_item.raw_material
            PurchaseReceiptItem.objects.create(
                receipt=receipt,
                po_item=po_item,
                raw_material=rm,
                quantity=qty,
                unit_cost=po_item.unit_cost,
                batch_number=line.get('batch_number') or '',
                supplier_batch_number=line.get('supplier_batch_number') or '',
                mfg_date=mfg or None,
                expiry_date=exp or None,
                location=line.get('location') or '',
            )
            po_item.received_quantity = Decimal(str(po_item.received_quantity or 0)) + qty
            po_item.save(update_fields=['received_quantity'])

            if rm:
                prev = rm.current_stock
                new_stk = prev + qty
                # weighted average purchase price
                if new_stk > 0:
                    rm.purchase_price = money(
                        ((rm.purchase_price or 0) * prev + po_item.unit_cost * qty) / new_stk
                    )
                rm.current_stock = new_stk
                if line.get('batch_number'):
                    rm.batch_number = line.get('batch_number')
                if exp:
                    rm.expiry_date = exp
                if line.get('location'):
                    rm.location = line.get('location')
                rm.save()
                StockMovementLog.objects.create(
                    item_type='raw_material',
                    raw_material=rm,
                    movement_type='purchase',
                    quantity=qty,
                    previous_balance=prev,
                    new_balance=new_stk,
                    unit_cost=po_item.unit_cost,
                    amount=money(qty * po_item.unit_cost),
                    reference_id=receipt.receipt_number,
                    reason=f'GRN {receipt.receipt_number} for {po.order_number}',
                )
            any_qty = True

        if not any_qty:
            transaction.set_rollback(True)
            return Response({'error': 'Enter a received quantity greater than 0.'}, status=400)

        refresh_po_receive_status(po)
        po.refresh_from_db()
        return Response(PurchaseOrderSerializer(po).data)

    @action(detail=False, methods=['get'])
    def pending_receipts(self, request):
        qs = self.get_queryset().filter(status__in=['ordered', 'partially_received'])
        return Response(PurchaseOrderSerializer(qs, many=True).data)

    @action(detail=False, methods=['get'])
    def gst_report(self, request):
        qs = PurchaseOrder.objects.exclude(status='cancelled')
        date_from = request.query_params.get('date_from')
        date_to = request.query_params.get('date_to')
        supplier_id = request.query_params.get('supplier')
        tax_type = request.query_params.get('tax_type')
        if date_from:
            qs = qs.filter(order_date__gte=date_from)
        if date_to:
            qs = qs.filter(order_date__lte=date_to)
        if supplier_id:
            qs = qs.filter(supplier_id=supplier_id)
        if tax_type == 'igst':
            qs = qs.filter(is_interstate=True)
        elif tax_type in ('cgst', 'sgst', 'intra'):
            qs = qs.filter(is_interstate=False)
        agg = qs.aggregate(
            taxable=Coalesce(Sum('taxable_amount'), Value(Decimal('0'))),
            cgst=Coalesce(Sum('cgst_amount'), Value(Decimal('0'))),
            sgst=Coalesce(Sum('sgst_amount'), Value(Decimal('0'))),
            igst=Coalesce(Sum('igst_amount'), Value(Decimal('0'))),
            total=Coalesce(Sum('total_amount'), Value(Decimal('0'))),
        )
        return Response({
            **agg,
            'total_gst': (agg['cgst'] or 0) + (agg['sgst'] or 0) + (agg['igst'] or 0),
            'orders': PurchaseOrderSerializer(qs.order_by('-order_date')[:200], many=True).data,
        })
