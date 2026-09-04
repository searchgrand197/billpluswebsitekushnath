from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIClient

from billing.models import CompanySettings, Product, RawMaterial, Stock, Supplier
from billing.procurement import calc_line, is_interstate, money


class ProcurementGstTests(TestCase):
    def test_same_state_splits_cgst_sgst(self):
        line = calc_line(1, 10000, 0, 18, interstate=False)
        self.assertEqual(line['taxable_amount'], Decimal('10000.00'))
        self.assertEqual(line['cgst'], Decimal('900.00'))
        self.assertEqual(line['sgst'], Decimal('900.00'))
        self.assertEqual(line['igst'], Decimal('0.00'))
        self.assertEqual(line['total'], Decimal('11800.00'))

    def test_interstate_uses_igst(self):
        line = calc_line(1, 10000, 0, 18, interstate=True)
        self.assertEqual(line['igst'], Decimal('1800.00'))
        self.assertEqual(line['cgst'], Decimal('0.00'))
        self.assertEqual(line['sgst'], Decimal('0.00'))
        self.assertEqual(line['total'], Decimal('11800.00'))

    def test_discount_reduces_taxable(self):
        line = calc_line(2, 100, 20, 5, interstate=False)
        self.assertEqual(line['taxable_amount'], Decimal('180.00'))
        self.assertEqual(line['cgst'] + line['sgst'], Decimal('9.00'))

    def test_gstin_state_compare(self):
        self.assertFalse(is_interstate('29ABCDE1234F1Z5', '29AAAAA0000A1Z5'))
        self.assertTrue(is_interstate('27ABCDE1234F1Z5', '29AAAAA0000A1Z5'))

    def test_haryana_intra_vs_interstate_by_state_name(self):
        self.assertFalse(is_interstate('', '', 'Haryana', 'Haryana'))
        self.assertTrue(is_interstate('', '', 'Punjab', 'Haryana'))
        self.assertTrue(is_interstate('', '06AAAAA0000A1Z5', 'Maharashtra', 'Haryana'))
        self.assertFalse(is_interstate('', '06AAAAA0000A1Z5', 'Haryana', 'Haryana'))

    def test_walk_in_without_state_is_intrastate(self):
        self.assertFalse(is_interstate('', '06AAAAA0000A1Z5', '', 'Haryana'))

    def test_twelve_percent_split(self):
        intra = calc_line(1, 100, 0, 12, interstate=False)
        self.assertEqual(intra['cgst'], Decimal('6.00'))
        self.assertEqual(intra['sgst'], Decimal('6.00'))
        self.assertEqual(intra['igst'], Decimal('0.00'))
        inter = calc_line(1, 100, 0, 12, interstate=True)
        self.assertEqual(inter['igst'], Decimal('12.00'))
        self.assertEqual(inter['cgst'], Decimal('0.00'))
        self.assertEqual(inter['sgst'], Decimal('0.00'))

    def test_money_rounds_half_up(self):
        self.assertEqual(money('10.005'), Decimal('10.01'))


class PurchaseOrderApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        user = User.objects.create_user('tester', password='pass12345')
        self.client.force_authenticate(user=user)
        CompanySettings.objects.create(
            company_name='Billvice',
            address_line1='Factory',
            city='Mysuru',
            state='Karnataka',
            postal_code='570001',
            phone='9999999999',
            email='a@b.com',
            gstin='29AAAAA0000A1Z5',
        )
        self.rm = RawMaterial.objects.create(
            material_code='ASH-01',
            name='Ashwagandha Powder',
            unit='kg',
            current_stock=Decimal('10.000'),
            purchase_price=Decimal('100.00'),
            gst_rate=Decimal('18'),
            hsn_code='1211',
        )
        self.supplier = Supplier.objects.create(
            name='Herb Traders',
            gstin='29ABCDE1234F1Z5',
            phone='8888888888',
            address='Mysuru',
        )

    def _create_po(self, qty='100', place=True, gstin=None):
        payload = {
            'supplier': self.supplier.id,
            'supplier_name': self.supplier.name,
            'supplier_gstin': gstin or self.supplier.gstin,
            'order_date': '2026-08-14',
            'items': [{
                'raw_material': self.rm.id,
                'quantity': qty,
                'unit_cost': '100',
                'discount': '0',
                'gst_rate': '18',
                'uom': 'kg',
            }],
            'round_off': '0',
            'place_order': place,
        }
        return self.client.post('/billing/api/purchase-orders/', payload, format='json')

    def test_create_po_does_not_increase_stock(self):
        res = self._create_po(place=False)
        self.assertEqual(res.status_code, 201)
        self.rm.refresh_from_db()
        self.assertEqual(self.rm.current_stock, Decimal('10.000'))
        self.assertEqual(res.data['status'], 'draft')
        self.assertEqual(Decimal(str(res.data['cgst_amount'])), Decimal('900.00'))
        self.assertEqual(Decimal(str(res.data['sgst_amount'])), Decimal('900.00'))
        self.assertEqual(Decimal(str(res.data['igst_amount'])), Decimal('0.00'))

    def test_interstate_igst_on_create(self):
        res = self._create_po(gstin='27ABCDE1234F1Z5', place=False)
        self.assertEqual(res.status_code, 201)
        self.assertTrue(res.data['is_interstate'])
        self.assertEqual(Decimal(str(res.data['igst_amount'])), Decimal('1800.00'))
        self.assertEqual(Decimal(str(res.data['cgst_amount'])), Decimal('0.00'))

    def test_partial_then_full_receive_updates_stock_once(self):
        res = self._create_po(qty='100', place=True)
        self.assertEqual(res.status_code, 201)
        po_id = res.data['id']
        item_id = res.data['items'][0]['id']

        first = self.client.post(
            f'/billing/api/purchase-orders/{po_id}/receive/',
            {'items': [{'po_item': item_id, 'quantity': '60', 'batch_number': 'B1'}]},
            format='json',
        )
        self.assertEqual(first.status_code, 200)
        self.assertEqual(first.data['status'], 'partially_received')
        self.rm.refresh_from_db()
        self.assertEqual(self.rm.current_stock, Decimal('70.000'))

        over = self.client.post(
            f'/billing/api/purchase-orders/{po_id}/receive/',
            {'items': [{'po_item': item_id, 'quantity': '50'}]},
            format='json',
        )
        self.assertEqual(over.status_code, 400)
        self.rm.refresh_from_db()
        self.assertEqual(self.rm.current_stock, Decimal('70.000'))

        second = self.client.post(
            f'/billing/api/purchase-orders/{po_id}/receive/',
            {'items': [{'po_item': item_id, 'quantity': '40'}]},
            format='json',
        )
        self.assertEqual(second.status_code, 200)
        self.assertEqual(second.data['status'], 'received')
        self.rm.refresh_from_db()
        self.assertEqual(self.rm.current_stock, Decimal('110.000'))

    def test_cancel_requires_reason_and_does_not_touch_stock(self):
        res = self._create_po(place=False)
        po_id = res.data['id']
        bad = self.client.post(f'/billing/api/purchase-orders/{po_id}/cancel/', {}, format='json')
        self.assertEqual(bad.status_code, 400)
        ok = self.client.post(
            f'/billing/api/purchase-orders/{po_id}/cancel/',
            {'reason': 'Supplier delayed'},
            format='json',
        )
        self.assertEqual(ok.status_code, 200)
        self.assertEqual(ok.data['status'], 'cancelled')
        self.rm.refresh_from_db()
        self.assertEqual(self.rm.current_stock, Decimal('10.000'))

    def test_duplicate_creates_new_draft(self):
        res = self._create_po(place=True)
        dup = self.client.post(f'/billing/api/purchase-orders/{res.data["id"]}/duplicate/', format='json')
        self.assertEqual(dup.status_code, 201)
        self.assertEqual(dup.data['status'], 'draft')
        self.assertNotEqual(dup.data['order_number'], res.data['order_number'])
        self.assertEqual(Decimal(str(dup.data['items'][0]['received_quantity'])), Decimal('0'))


class InvoiceGstTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        user = User.objects.create_user('tester', password='pass12345')
        self.client.force_authenticate(user=user)
        CompanySettings.objects.create(
            company_name='Billvice',
            address_line1='Factory',
            city='Mysuru',
            state='Karnataka',
            postal_code='570001',
            phone='9999999999',
            email='a@b.com',
            gstin='29AAAAA0000A1Z5',
            gst_percentage=Decimal('5'),
        )
        self.product = Product.objects.create(
            name='Churna',
            sku='CH-1',
            price=Decimal('1000.00'),
            cost_price=Decimal('400.00'),
            gst_rate=Decimal('5'),
        )
        Stock.objects.create(product=self.product, quantity=100)

    def test_walkin_invoice_uses_cgst_sgst_not_igst(self):
        res = self.client.post('/billing/api/pos/create-invoice/', {
            'customer_name': 'Walk-in Customer',
            'payment_type': 'full_payment',
            'amount_paid_now': '1050',
            'items': [{'product_id': self.product.id, 'quantity': 1, 'unit_price': '1000'}],
        }, format='json')
        self.assertEqual(res.status_code, 201, res.data)
        inv = res.data['invoice']
        self.assertEqual(Decimal(str(inv['subtotal'])), Decimal('1000.00'))
        self.assertEqual(Decimal(str(inv['cgst_amount'])), Decimal('25.00'))
        self.assertEqual(Decimal(str(inv['sgst_amount'])), Decimal('25.00'))
        self.assertEqual(Decimal(str(inv['igst_amount'])), Decimal('0.00'))
        self.assertEqual(Decimal(str(inv['total_amount'])), Decimal('1050.00'))

    def test_interstate_customer_uses_igst(self):
        res = self.client.post('/billing/api/pos/create-invoice/', {
            'customer_name': 'MH Buyer',
            'customer_gstin': '27ABCDE1234F1Z5',
            'payment_type': 'full_payment',
            'amount_paid_now': '1050',
            'items': [{'product_id': self.product.id, 'quantity': 1, 'unit_price': '1000'}],
        }, format='json')
        self.assertEqual(res.status_code, 201, res.data)
        inv = res.data['invoice']
        self.assertEqual(Decimal(str(inv['igst_amount'])), Decimal('50.00'))
        self.assertEqual(Decimal(str(inv['cgst_amount'])), Decimal('0.00'))
        self.assertEqual(Decimal(str(inv['total_amount'])), Decimal('1050.00'))

    def test_zero_gst_product_does_not_add_tax(self):
        self.product.gst_rate = Decimal('0')
        self.product.save()
        res = self.client.post('/billing/api/pos/create-invoice/', {
            'customer_name': 'Walk-in Customer',
            'payment_type': 'full_payment',
            'amount_paid_now': '1000',
            'items': [{'product_id': self.product.id, 'quantity': 1, 'unit_price': '1000'}],
        }, format='json')
        self.assertEqual(res.status_code, 201, res.data)
        inv = res.data['invoice']
        self.assertEqual(Decimal(str(inv['total_amount'])), Decimal('1000.00'))
        self.assertEqual(Decimal(str(inv['cgst_amount'])) + Decimal(str(inv['sgst_amount'])) + Decimal(str(inv['igst_amount'])), Decimal('0.00'))

    def test_product_gst_used_not_company_default(self):
        self.product.gst_rate = Decimal('18')
        self.product.save()
        res = self.client.post('/billing/api/pos/create-invoice/', {
            'customer_name': 'Walk-in Customer',
            'payment_type': 'full_payment',
            'amount_paid_now': '1180',
            'items': [{'product_id': self.product.id, 'quantity': 1, 'unit_price': '1000'}],
        }, format='json')
        self.assertEqual(res.status_code, 201, res.data)
        inv = res.data['invoice']
        self.assertEqual(Decimal(str(inv['cgst_amount'])), Decimal('90.00'))
        self.assertEqual(Decimal(str(inv['sgst_amount'])), Decimal('90.00'))
        self.assertEqual(Decimal(str(inv['total_amount'])), Decimal('1180.00'))

