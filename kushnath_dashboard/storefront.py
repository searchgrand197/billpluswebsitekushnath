import json
from decimal import Decimal

from django.conf import settings
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, render
from django.views.decorators.csrf import ensure_csrf_cookie

from advertisement.models import Slideshow
from dashboard.models import Category, Product

CATEGORY_GRADIENTS = {
    "Beauty": "from-rose-100 to-pink-200",
    "Supplements": "from-amber-100 to-orange-200",
    "Ayurvedic Medicines": "from-emerald-100 to-green-200",
    "HAIR TREATMENT": "from-teal-100 to-cyan-200",
    "Digestive Care": "from-lime-100 to-green-200",
    "Immunity Boosters": "from-yellow-100 to-amber-200",
    "Skin Care": "from-fuchsia-100 to-pink-200",
    "Joint & Pain Relief": "from-slate-100 to-gray-200",
    "Energy & Stamina": "from-orange-100 to-red-200",
    "Daily Wellness": "from-green-100 to-emerald-200",
}

# Mapped from Kushnath Product.pdf — products helpful for each health concern.
SHOP_BY_CONCERNS = [
    {
        "slug": "skin-care",
        "title": "Enhance Your Skin Care",
        "description": "Ayurvedic remedies for itching, fungus, rashes, and skin purification.",
        "image": "/media/concerns/skin-care.png",
        "products": ["Free For Itch", "Kushthaghna Ark Mahakashaya"],
    },
    {
        "slug": "digestion",
        "title": "Improve Digestion",
        "description": "Support smooth digestion, ease gas & acidity, and complete gut detox.",
        "image": "/media/concerns/digestion.png",
        "products": ["Kayakalp Churan"],
    },
    {
        "slug": "immunity",
        "title": "Strengthen Immunity",
        "description": "Boost daily defense, fight seasonal infections, and build body resilience.",
        "image": "/media/concerns/immunity.png",
        "products": [
            "Tejasvi Kadha",
            "Tejasvi Ark",
            "Madhurodak Ark / Capsule",
            "Panchbhadra Ark",
            "Snasa Amrit",
        ],
    },
    {
        "slug": "cold-cough-fever",
        "title": "Relief From Cold & Fever",
        "description": "Natural support for cold, cough, high fever, and seasonal infections.",
        "image": "/media/concerns/cold-cough.png",
        "products": ["Tejasvi Kadha", "Tejasvi Ark", "Panchbhadra Ark"],
    },
    {
        "slug": "heart-circulation",
        "title": "Care For Your Heart",
        "description": "Strengthen heart, veins, and circulation for long-term cardiovascular wellness.",
        "image": "/media/concerns/heart.png",
        "products": [
            "Snasa Amrit",
            "Madhurodak Ark / Capsule",
            "Panchbhadra Ark",
            "Tejasvi Ark",
        ],
    },
    {
        "slug": "kidney-urinary",
        "title": "Kidney & Urinary Health",
        "description": "Flush renal toxins, support filtration, and help reduce stone risk.",
        "image": "/media/concerns/kidney.png",
        "products": ["Kidney Kaya Ark", "Kidney Kaya Capsule"],
    },
    {
        "slug": "diabetes",
        "title": "Manage Blood Sugar",
        "description": "Help maintain blood glucose, ease thirst & urination, and support pancreas.",
        "image": "/media/concerns/diabetes.png",
        "products": ["Madhurodak Ark / Capsule"],
    },
    {
        "slug": "joint-pain",
        "title": "Joint & Muscle Pain",
        "description": "Deep relief from joint inflammation, bone pain, back pain, and sprains.",
        "image": "/media/concerns/joint-pain.png",
        "products": ["Dardantak Powder", "Dardantak Spray"],
    },
    {
        "slug": "hair-care",
        "title": "Stronger Hair Growth",
        "description": "Reduce hair fall, strengthen roots, control dandruff, and nourish the scalp.",
        "image": "/media/concerns/hair-care.png",
        "products": [
            "Kesh Vardhan Oil",
            "Kesh Vardhanam Hair Oil",
            "Hair Strong Shampoo",
            "Vedic Shiv Amrit Ark",
        ],
    },
    {
        "slug": "womens-health",
        "title": "Women's Hormonal Care",
        "description": "Support PCOD/PCOS, menstrual health, thyroid balance, and uterine wellness.",
        "image": "/media/concerns/womens-health.png",
        "products": ["Lady Gold Ark", "Lady Gold Capsule", "Vedic Shiv Amrit Syrup"],
    },
    {
        "slug": "mental-wellness",
        "title": "Stress & Mental Calm",
        "description": "Ease stress, anxiety, and sleep issues while improving memory and focus.",
        "image": "/media/concerns/mental-wellness.png",
        "products": ["Manosudha Ark", "Manosudha Syrup"],
    },
    {
        "slug": "male-vitality",
        "title": "Male Vitality & Stamina",
        "description": "Boost strength, stamina, performance, and reproductive vitality naturally.",
        "image": "/media/concerns/male-vitality.png",
        "products": ["Kamaking Capsule", "Ashwashila Malt"],
    },
    {
        "slug": "piles-care",
        "title": "Piles & Anus Care",
        "description": "Reduce pain, swelling, and bleeding while supporting easy bowel movement.",
        "image": "/media/concerns/piles-care.png",
        "products": ["Anus Care 1", "Anus Care 2"],
    },
    {
        "slug": "liver-detox",
        "title": "Liver Detox & Metabolism",
        "description": "Detox body organs, support liver health, and boost natural metabolism.",
        "image": "/media/concerns/liver-detox.png",
        "products": ["Madhurodak Ark / Capsule", "Panchbhadra Ark", "Tejasvi Ark"],
    },
]


def _concern_by_slug(slug):
    if not slug:
        return None
    return next((c for c in SHOP_BY_CONCERNS if c["slug"] == slug), None)


def _products_for_concern(concern):
    names = concern.get("products") or []
    if not names:
        return []
    q = Q()
    for name in names:
        q |= Q(name__iexact=name)
    matched = list(
        Product.objects.filter(available=True)
        .filter(q)
        .select_related("category")
        .prefetch_related("images", "benefits", "tags")
    )
    by_name = {p.name.lower(): p for p in matched}
    ordered = []
    seen = set()
    for name in names:
        product = by_name.get(name.lower())
        if product and product.id not in seen:
            ordered.append(product)
            seen.add(product.id)
    return ordered


def _sale_price(p):
    if p.discount and p.discount > 0:
        if p.discount_type == "percent":
            price = p.price * (1 - p.discount / 100)
        else:
            price = p.price - p.discount
        return max(price, Decimal("0")).quantize(Decimal("0.01"))
    return p.price


def _product_image(p):
    images = list(p.images.values_list("image", flat=True))
    if images:
        return f"/media/{images[0]}"
    if p.category and p.category.image:
        return p.category.image.url
    return "/media/company/kushnath_ayurvedic.png"


def _product_to_dict(p):
    images = list(p.images.values_list("image", flat=True))
    sale = _sale_price(p)
    image = _product_image(p)

    return {
        "id": p.id,
        "name": p.name,
        "quantity_label": p.quantity,
        "price": float(p.price),
        "sale_price": float(sale),
        "discount": float(p.discount),
        "discount_type": p.discount_type,
        "has_discount": p.discount > 0,
        "stock": p.stock,
        "available": p.available and p.stock > 0,
        "rating": p.total_rating or 4.5,
        "category": p.category.name if p.category else "",
        "category_id": p.category_id,
        "description": p.description or "Premium Kushnath Ayurveda product crafted with natural herbs.",
        "image": image,
        "all_images": [f"/media/{img}" for img in images] or [image],
        "benefits": list(p.benefits.values_list("name", flat=True)),
        "tags": list(p.tags.values_list("name", flat=True)),
    }


def _category_to_dict(c):
    count = c.products.filter(available=True).count()
    gradient = CATEGORY_GRADIENTS.get(c.name, "from-brand-100 to-brand-200")
    return {
        "id": c.id,
        "name": c.name,
        "description": c.description or f"Explore {count} natural Kushnath products",
        "image": c.image.url if c.image else "/media/company/kushnath_ayurvedic.png",
        "gradient": gradient,
        "product_count": count,
    }


def _base_context(**extra):
    ctx = {
        "logo_url": "/media/company/kushnath_ayurvedic.png",
        "razorpay_key": settings.RAZORPAY_KEY_ID,
        "show_search": True,
        "home_hero_nav": False,
    }
    ctx.update(extra)
    return ctx


@ensure_csrf_cookie
def home(request):
    categories_qs = Category.objects.annotate(
        product_count=Count("products", filter=Q(products__available=True))
    ).order_by("name")

    products_qs = (
        Product.objects.filter(available=True)
        .select_related("category")
        .prefetch_related("images", "benefits", "tags")
    )
    slideshows = Slideshow.objects.filter(is_active=True)
    featured_names = [
        "Ashwashila Malt",
        "Kamaking Capsule",
        "Panchbhadra Ark",
        "Kesh Vardhan Oil",
    ]
    best_selling = []
    for name in featured_names:
        match = next((p for p in products_qs if p.name == name), None)
        if match:
            best_selling.append(match)
    if len(best_selling) < 4:
        extras = [p for p in products_qs.order_by("-total_rating", "-stock", "name") if p not in best_selling]
        best_selling.extend(extras[: 4 - len(best_selling)])
    best_selling_qs = best_selling[:4]

    category_filter = request.GET.get("category")
    concern_slug = request.GET.get("concern", "").strip()
    search_q = request.GET.get("q", "").strip()
    active_concern = _concern_by_slug(concern_slug)

    if active_concern:
        concern_products = _products_for_concern(active_concern)
        if search_q:
            concern_products = [p for p in concern_products if search_q.lower() in p.name.lower()]
        product_list = [_product_to_dict(p) for p in concern_products]
    else:
        if category_filter:
            products_qs = products_qs.filter(category__id=category_filter)
        if search_q:
            products_qs = products_qs.filter(name__icontains=search_q)
        product_list = [_product_to_dict(p) for p in products_qs]

    categories = [_category_to_dict(c) for c in categories_qs]
    all_product_list = [_product_to_dict(p) for p in Product.objects.filter(available=True).select_related("category").prefetch_related("images")]
    active_cat = int(category_filter) if category_filter and not active_concern else None
    active_category_name = next((c["name"] for c in categories if c["id"] == active_cat), None)
    products_heading = (
        active_concern["title"]
        if active_concern
        else active_category_name
        if active_category_name
        else (f'Results for "{search_q}"' if search_q else "Our Products")
    )

    shop_by_concern = [
        {
            "title": c["title"],
            "description": c["description"],
            "image": c["image"],
            "slug": c["slug"],
            "url": f"/?concern={c['slug']}#our-products",
            "active": bool(active_concern and active_concern["slug"] == c["slug"]),
        }
        for c in SHOP_BY_CONCERNS
    ]

    return render(
        request,
        "storefront/home.html",
        _base_context(
            categories=categories,
            products=product_list,
            products_json=json.dumps(all_product_list),
            best_selling_products=[_product_to_dict(p) for p in best_selling_qs],
            featured_products=[_product_to_dict(p) for p in Product.objects.filter(available=True).order_by("-total_rating")[:4]],
            slideshows=slideshows,
            search_q=search_q,
            active_category=active_cat,
            active_category_name=active_category_name,
            active_concern=active_concern,
            products_heading=products_heading,
            total_products=Product.objects.filter(available=True).count(),
            shop_by_concern=shop_by_concern,
            show_search=False,
            home_hero_nav=True,
        ),
    )


@ensure_csrf_cookie
def product_detail(request, product_id):
    product = get_object_or_404(
        Product.objects.select_related("category").prefetch_related(
            "images", "benefits", "tags", "comments__replies"
        ),
        id=product_id,
        available=True,
    )
    related = (
        Product.objects.filter(category=product.category, available=True)
        .exclude(id=product.id)
        .prefetch_related("images")[:4]
    )

    all_products = [_product_to_dict(p) for p in Product.objects.filter(available=True).prefetch_related("images")]

    return render(
        request,
        "storefront/product_detail.html",
        _base_context(
            product=_product_to_dict(product),
            comments=product.comments.select_related("commented_by").order_by("-created_at"),
            related_products=[_product_to_dict(p) for p in related],
            products_json=json.dumps(all_products),
        ),
    )


@ensure_csrf_cookie
def cart_page(request):
    all_products = [_product_to_dict(p) for p in Product.objects.filter(available=True).prefetch_related("images")]
    return render(
        request,
        "storefront/cart.html",
        _base_context(products_json=json.dumps(all_products), categories=[]),
    )


@ensure_csrf_cookie
def checkout_page(request):
    all_products = [_product_to_dict(p) for p in Product.objects.filter(available=True).prefetch_related("images")]
    return render(
        request,
        "storefront/checkout.html",
        _base_context(products_json=json.dumps(all_products), categories=[]),
    )


def order_success(request):
    return render(request, "storefront/order_success.html", _base_context())
