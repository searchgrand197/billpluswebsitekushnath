"""Keep official Kushnath catalog. Do not re-seed demo products."""

from dashboard.models import Category, Product


def setup_storefront_data():
    return {
        "products": Product.objects.count(),
        "categories": Category.objects.count(),
        "seeded": 0,
    }
