from django.conf import settings
import json

from dashboard.models import Category


def storefront(request):
    return {
        "logo_url": "/media/company/kushnath_ayurvedic.png",
        "nav_categories": Category.objects.all().order_by("name"),
        "firebase_config_json": json.dumps(getattr(settings, "FIREBASE_CONFIG", {})),
    }
