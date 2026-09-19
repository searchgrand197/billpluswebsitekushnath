"""
Reset Billvice catalog data and import all Kushnath storefront products.

Keeps: Django superusers/staff, CompanySettings.
Deletes: Billvice products/stock, raw materials, recipes, manufacturing,
         invoices, customers, suppliers, POs, payments, ledger, batches, etc.
         Also deletes non-staff Django users (storefront OTP accounts).

Usage:
  python manage.py sync_kushnath_to_billvice
  python manage.py sync_kushnath_to_billvice --dry-run
"""

from __future__ import annotations

from decimal import Decimal

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.db import transaction

from billing.models import (
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
from billing.procurement import before_from_inclusive, money
from dashboard.models import Category as KushnathCategory
from dashboard.models import Product as KushnathProduct


DEFAULT_GST_RATE = Decimal("5.00")


def _sale_price(p: KushnathProduct) -> Decimal:
    """Website MRP (GST-inclusive)."""
    price = Decimal(p.price or 0)
    discount = Decimal(p.discount or 0)
    if discount > 0:
        if p.discount_type == "percent":
            price = price * (1 - discount / Decimal("100"))
        else:
            price = price - discount
    return max(price, Decimal("0")).quantize(Decimal("0.01"))


def _unique_sku(base: str, used: set[str]) -> str:
    sku = (base or "SKU").strip().upper()[:50] or "SKU"
    if sku not in used:
        used.add(sku)
        return sku
    i = 2
    while True:
        candidate = f"{sku[:45]}-{i}"[:50]
        if candidate not in used:
            used.add(candidate)
            return candidate
        i += 1


class Command(BaseCommand):
    help = "Clear Billvice products/raw materials/customers (keep staff) and import Kushnath website products."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would happen without writing to the database.",
        )
        parser.add_argument(
            "--keep-users",
            action="store_true",
            help="Do not delete non-staff Django users.",
        )
        parser.add_argument(
            "--include-unavailable",
            action="store_true",
            help="Also import Kushnath products marked unavailable.",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        dry = options["dry_run"]
        keep_users = options["keep_users"]
        include_unavailable = options["include_unavailable"]

        qs = KushnathProduct.objects.select_related("category").all()
        if not include_unavailable:
            qs = qs.filter(available=True)
        source_products = list(qs.order_by("category__name", "name"))

        self.stdout.write(self.style.NOTICE(
            f"Kushnath products to import: {len(source_products)}"
        ))
        self.stdout.write(self.style.WARNING(
            "Will clear Billvice: products, stock, raw materials, recipes, "
            "manufacturing, invoices, customers, suppliers, POs, payments, ledger..."
        ))

        if dry:
            for p in source_products:
                self.stdout.write(
                    f"  + {p.name} | sku={p.sku} | price={_sale_price(p)} | stock={p.stock} | cat={p.category}"
                )
            staff = User.objects.filter(is_superuser=True) | User.objects.filter(is_staff=True)
            self.stdout.write(f"Staff/superusers kept: {staff.distinct().count()}")
            if not keep_users:
                doomed = User.objects.exclude(is_superuser=True).exclude(is_staff=True).count()
                self.stdout.write(f"Non-staff users that would be deleted: {doomed}")
            self.stdout.write(self.style.SUCCESS("Dry run complete — no changes written."))
            return

        # --- Clear Billvice transactional + catalog data (FK-safe order) ---
        deleted = {}

        def wipe(label, model):
            n, _ = model.objects.all().delete()
            deleted[label] = n

        wipe("invoice_items", InvoiceItem)
        wipe("payments", PaymentReceived)
        wipe("ledger", CustomerLedgerEntry)
        wipe("invoices", Invoice)
        wipe("customers", Customer)

        wipe("po_receipt_items", PurchaseReceiptItem)
        wipe("po_receipts", PurchaseReceipt)
        wipe("po_items", PurchaseOrderItem)
        wipe("purchase_orders", PurchaseOrder)
        wipe("suppliers", Supplier)

        wipe("mfg_item_logs", ManufacturingItemLog)
        wipe("mfg_logs", ManufacturingLog)
        wipe("recipe_items", RecipeItem)
        wipe("recipes", Recipe)
        wipe("product_batches", ProductBatch)
        wipe("stock_movements", StockMovementLog)
        wipe("stock", Stock)
        wipe("products", Product)
        wipe("product_categories", ProductCategory)
        wipe("raw_materials", RawMaterial)

        if not keep_users:
            n, _ = (
                User.objects.exclude(is_superuser=True)
                .exclude(is_staff=True)
                .delete()
            )
            deleted["non_staff_users"] = n

        for label, n in deleted.items():
            self.stdout.write(f"  cleared {label}: {n}")

        # --- Import categories + products ---
        used_skus: set[str] = set()
        cat_map: dict[int, ProductCategory] = {}
        created_cats = 0
        created_products = 0

        for kc in KushnathCategory.objects.all().order_by("name"):
            bc, was_created = ProductCategory.objects.get_or_create(
                name=kc.name[:200],
                defaults={"description": (kc.description or "")[:]},
            )
            cat_map[kc.id] = bc
            if was_created:
                created_cats += 1

        for kp in source_products:
            sku = _unique_sku(kp.sku or f"KN-{kp.id}", used_skus)
            mrp_inclusive = _sale_price(kp)
            # Billvice Product.price is tax-EXCLUSIVE; back-calculate from MRP
            taxable, gst_amt, _ = before_from_inclusive(mrp_inclusive, DEFAULT_GST_RATE)
            cost = money(taxable * Decimal("0.70"))
            desc_bits = []
            if kp.quantity:
                desc_bits.append(str(kp.quantity))
            if kp.description:
                desc_bits.append(str(kp.description))
            description = " — ".join(desc_bits)

            bp = Product.objects.create(
                name=kp.name[:200],
                description=description,
                cost_price=cost,
                price=taxable,
                type="sale",
                uom="unit",
                sku=sku,
                hsn_code="",
                gst_rate=DEFAULT_GST_RATE,
                category=cat_map.get(kp.category_id),
            )
            Stock.objects.create(
                product=bp,
                quantity=Decimal(kp.stock or 0),
                low_stock_threshold=Decimal("10"),
            )
            created_products += 1
            self.stdout.write(
                f"  imported {bp.name} ({bp.sku}) "
                f"MRP={mrp_inclusive} -> taxable={taxable} +GST{DEFAULT_GST_RATE}%={gst_amt} qty={kp.stock}"
            )
        self.stdout.write(self.style.SUCCESS(
            f"Done. Categories: {created_cats} new. Products imported: {created_products}."
        ))
        self.stdout.write(
            "Company settings and staff/superuser accounts were preserved."
        )
