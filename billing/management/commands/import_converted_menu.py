import csv
from pathlib import Path

from django.core.management.base import BaseCommand

from billing.models import Product, ProductCategory, Stock


class Command(BaseCommand):
    help = "Import products and categories from converted.csv (Name,Price,Category) with 5% tax-inclusive prices."

    def add_arguments(self, parser):
        parser.add_argument(
            "--csv-path",
            type=str,
            default=str(Path.home() / "Documents" / "converted.csv"),
            help="Path to converted.csv (default: ~/Documents/converted.csv)",
        )

    def handle(self, *args, **options):
        csv_path = Path(options["csv_path"])
        if not csv_path.exists():
            self.stderr.write(self.style.ERROR(f"CSV file not found: {csv_path}"))
            return

        created_categories = 0
        created_products = 0
        updated_products = 0

        with csv_path.open(newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                name = (row.get("Name") or "").strip()
                raw_price = (row.get("Price") or "").strip()
                category_name = (row.get("Category") or "").strip()

                if not name or not raw_price:
                    continue

                try:
                    price = float(raw_price)
                except ValueError:
                    self.stderr.write(
                        self.style.WARNING(f"Skipping row with invalid price: {row}")
                    )
                    continue

                # Create or get category
                category = None
                if category_name:
                    category, created = ProductCategory.objects.get_or_create(
                        name=category_name,
                        defaults={"description": "", "is_active": True},
                    )
                    if created:
                        created_categories += 1

                # Generate a simple SKU based on name + category
                base_sku = (
                    f"{name}-{category_name}" if category_name else name
                ).upper().replace(" ", "-")[:40]
                sku = base_sku
                counter = 1
                while Product.objects.filter(sku=sku).exists():
                    suffix = f"-{counter}"
                    sku = f"{base_sku[: 40 - len(suffix)]}{suffix}"
                    counter += 1

                # Try matching by name+category first to avoid duplicates
                product_qs = Product.objects.filter(name=name)
                if category:
                    product_qs = product_qs.filter(category=category)

                if product_qs.exists():
                    product = product_qs.first()
                    product.price = price
                    product.category = category
                    product.type = "sale"
                    product.uom = "unit"
                    product.save()
                    updated_products += 1
                else:
                    product = Product.objects.create(
                        name=name,
                        description="",
                        cost_price=0,
                        price=price,
                        type="sale",
                        uom="unit",
                        daily_rental_rate=None,
                        sku=sku,
                        category=category,
                    )
                    Stock.objects.get_or_create(
                        product=product,
                        defaults={
                            "quantity": 0,
                            "low_stock_threshold": 10,
                        },
                    )
                    created_products += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Import complete. Categories created: {created_categories}, "
                f"products created: {created_products}, products updated: {updated_products}."
            )
        )

