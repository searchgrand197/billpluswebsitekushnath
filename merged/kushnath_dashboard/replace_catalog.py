"""Replace catalog with official Kushnath products, matching each photo to the right name and price."""

from decimal import Decimal
from pathlib import Path
import shutil

from django.conf import settings
from dashboard.models import Category, Product, ProductImage

ASSETS = Path(r"C:\Users\MITTA\.cursor\projects\d-quick-cart\assets")
MEDIA = Path(settings.MEDIA_ROOT)
DEST = MEDIA / "products" / "official"
DEST.mkdir(parents=True, exist_ok=True)

# Original uploads copied to p01–p21. Identified by the bottle label, not upload order.
PHOTO_FILES = {
    "p01.png": "c__Users_MITTA_AppData_Roaming_Cursor_User_workspaceStorage_0aa527268fea964a7ac5b3e8a3b97b55_images_48669ea2-c990-4333-adc7-6b2c883191f2-57316509-9762-4440-b4fd-6c2625bc7d16.png",
    "p02.png": "c__Users_MITTA_AppData_Roaming_Cursor_User_workspaceStorage_0aa527268fea964a7ac5b3e8a3b97b55_images_e4ae41ca-b2bb-4a53-ad52-7fd31227b953-cb72e6cf-8e9d-4f40-9e90-d6d33e279018.png",
    "p03.png": "c__Users_MITTA_AppData_Roaming_Cursor_User_workspaceStorage_0aa527268fea964a7ac5b3e8a3b97b55_images_c092d0fd-7ce0-47c4-b94d-a59dfe381398-cf55f2b7-05ec-427d-9ba2-045e90b5bde7.png",
    "p04.png": "c__Users_MITTA_AppData_Roaming_Cursor_User_workspaceStorage_0aa527268fea964a7ac5b3e8a3b97b55_images_b55cffb5-d388-42c4-af01-67eb600420b6-15363556-fa14-45d6-bdfb-d09737cadb5e.png",
    "p05.png": "c__Users_MITTA_AppData_Roaming_Cursor_User_workspaceStorage_0aa527268fea964a7ac5b3e8a3b97b55_images_ee983d2c-d349-4265-9223-eebe4e9af63c-47e4d957-a816-48d0-b3e4-6839e0efadaa.png",
    "p06.png": "c__Users_MITTA_AppData_Roaming_Cursor_User_workspaceStorage_0aa527268fea964a7ac5b3e8a3b97b55_images_b88a8b9a-44f9-41f7-ad31-da5cabbef4ef-e0616025-be6e-4423-a14a-4ce2475cb36f.png",
    "p07.png": "c__Users_MITTA_AppData_Roaming_Cursor_User_workspaceStorage_0aa527268fea964a7ac5b3e8a3b97b55_images_9edfdc7f-3566-4547-8485-0fb9607efed3-b38c53f1-b729-4e82-8a11-c3ba20e4ff44.png",
    "p08.png": "c__Users_MITTA_AppData_Roaming_Cursor_User_workspaceStorage_0aa527268fea964a7ac5b3e8a3b97b55_images_5c3789d1-0770-4a28-9246-4afeaced9e1c-0f2a6e23-1bdc-4805-98c6-3c6fa5c50e43.png",
    "p09.png": "c__Users_MITTA_AppData_Roaming_Cursor_User_workspaceStorage_0aa527268fea964a7ac5b3e8a3b97b55_images_df1c00a4-8373-47d0-9450-a2ece2c332f5-b7f59702-fb3e-4cb2-a7f8-97f81ce7d4b0.png",
    "p10.png": "c__Users_MITTA_AppData_Roaming_Cursor_User_workspaceStorage_0aa527268fea964a7ac5b3e8a3b97b55_images_113ff9d5-17f4-4bc1-9d44-4d8fe749f8b6-984d8058-3e76-4178-8ed0-7e0aa0d13ac4.png",
    "p11.png": "c__Users_MITTA_AppData_Roaming_Cursor_User_workspaceStorage_0aa527268fea964a7ac5b3e8a3b97b55_images_cea124b8-f730-40e2-9eeb-7d7d6e5c3bb1-181f0960-39c1-4e8e-9e45-fd968482165b.png",
    "p12.png": "c__Users_MITTA_AppData_Roaming_Cursor_User_workspaceStorage_0aa527268fea964a7ac5b3e8a3b97b55_images_18fcc97f-d695-4372-bff7-508c7044d200-742b6534-ce8f-47b6-b1ae-0e49e3b09946.png",
    "p13.png": "c__Users_MITTA_AppData_Roaming_Cursor_User_workspaceStorage_0aa527268fea964a7ac5b3e8a3b97b55_images_a5b9a372-b111-46b6-9477-e0027cb0bcc7-64116288-2f1f-4c87-a361-a8300b01b9d4.png",
    "p14.png": "c__Users_MITTA_AppData_Roaming_Cursor_User_workspaceStorage_0aa527268fea964a7ac5b3e8a3b97b55_images_058348e8-0536-41d5-8117-7ed5efb56e35-f55347c1-81fb-417f-a3c4-c4143a00a1ff.png",
    "p15.png": "c__Users_MITTA_AppData_Roaming_Cursor_User_workspaceStorage_0aa527268fea964a7ac5b3e8a3b97b55_images_ad434b6b-48a2-43af-96a0-97d5de64343b-3e985d17-db7f-4382-b146-2611489f1193.png",
    "p16.png": "c__Users_MITTA_AppData_Roaming_Cursor_User_workspaceStorage_0aa527268fea964a7ac5b3e8a3b97b55_images_aef34d12-e464-4c9f-a4b3-877a865df735-a9f88485-4df0-4b25-9c27-24bb1e36775c.png",
    "p17.png": "c__Users_MITTA_AppData_Roaming_Cursor_User_workspaceStorage_0aa527268fea964a7ac5b3e8a3b97b55_images_46200ac6-5603-4cdb-9005-a27c73deac2d-15d017db-e90d-4ae6-b092-c50b827930c1.png",
    "p18.png": "c__Users_MITTA_AppData_Roaming_Cursor_User_workspaceStorage_0aa527268fea964a7ac5b3e8a3b97b55_images_0c1bb1cf-f7a6-4665-9748-3eb89abde656-109e4177-0ed2-44db-a2a0-bfdda44f5896.png",
    "p19.png": "c__Users_MITTA_AppData_Roaming_Cursor_User_workspaceStorage_0aa527268fea964a7ac5b3e8a3b97b55_images_557ca9b1-b819-410e-b54c-a70cf9327c6d-79f88f6c-053c-4b0d-82cd-9b4b9019f221.png",
    "p20.png": "c__Users_MITTA_AppData_Roaming_Cursor_User_workspaceStorage_0aa527268fea964a7ac5b3e8a3b97b55_images_eecd63be-4e74-4828-928d-59b892b9e22f-3b6bec9d-1111-4917-aa16-561a72fca94a.png",
    "p21.png": "c__Users_MITTA_AppData_Roaming_Cursor_User_workspaceStorage_0aa527268fea964a7ac5b3e8a3b97b55_images_e21b4c47-9522-4710-9444-9e723da2051c-470aebdd-4b54-4726-885a-28519ca8caca.png",
}

# name, qty, price, category, sku, description, photo files (first is the matching bottle)
PRODUCTS = [
    ("Panchbhadra Ark", "450 ml", 450, "Ayurvedic Medicines", "KN-PBA-001",
     "Ayurvedic ark for Vata and Pitta fever.", ["p08.png"]),
    ("Kamaking Capsule", "60 capsules", 1499, "Energy & Stamina", "KN-KMC-002",
     "Ayurvedic capsules for stamina and strength.", ["p21.png"]),
    ("Dardantak Spray", "Spray", 599, "Joint & Pain Relief", "KN-DRS-003",
     "Ayurvedic spray for pain relief.", ["p02.png"]),
    ("Kesh Vardhan Oil", "100 ml", 149, "HAIR TREATMENT", "KN-KVO-004",
     "Cool herbal hair oil for hair growth and scalp care.", ["p11.png"]),
    ("Kesh Vardhanam Hair Oil", "180 ml", 499, "HAIR TREATMENT", "KN-KVH-024",
     "Herbal hair oil for stronger, healthier hair.", ["p04.png"]),
    ("Lady Gold Ark", "450 ml", 699, "Beauty", "KN-LGA-005",
     "Ayurvedic ark beneficial for women's health.", ["p09.png"]),
    ("Madhurodak Ark / Capsule", "450 ml / 60 capsules", 699, "Ayurvedic Medicines", "KN-MDA-006",
     "Ayurvedic support beneficial in diabetes / sugar.", ["p20.png", "p05.png"]),
    ("Tejasvi Ark", "450 ml", 699, "Ayurvedic Medicines", "KN-TJA-007",
     "Beneficial for liver and kidney wellness.", ["p13.png"]),
    ("Tejasvi Kadha", "450 ml", 699, "Immunity Boosters", "KN-TJK-008",
     "Kadha formulation for liver, kidney, heart and lungs.", ["p18.png"]),
    ("Kidney Kaya Ark", "450 ml", 699, "Ayurvedic Medicines", "KN-KKA-009",
     "Ayurvedic ark for kidney care.", ["p17.png"]),
    ("Kidney Kaya Capsule", "60 capsules", 699, "Ayurvedic Medicines", "KN-KKC-010",
     "Ayurvedic capsules for kidney care.", ["p01.png"]),
    ("Vedic Shiv Amrit Ark", "450 ml", 699, "Ayurvedic Medicines", "KN-VSA-011",
     "Beneficial for thyroid, obesity, lumps and infections.", ["p12.png"]),
    ("Vedic Shiv Amrit Syrup", "450 ml", 699, "Ayurvedic Medicines", "KN-VSS-012",
     "Syrup for women's wellness, thyroid and hormonal balance.", ["p14.png"]),
    ("Dardantak Powder", "Powder", 699, "Joint & Pain Relief", "KN-DRP-013",
     "Ayurvedic powder for joint and body pain.", ["p02.png"]),
    ("Hair Strong Shampoo", "200 ml", 499, "HAIR TREATMENT", "KN-HSS-014",
     "Herbal shampoo for stronger, healthier hair.", ["p03.png"]),
    ("Kayakalp Churan", "100 g", 299, "Digestive Care", "KN-KYC-015",
     "Ayurvedic churan for digestive health.", ["p10.png"]),
    ("Lady Gold Capsule", "60 capsules", 699, "Beauty", "KN-LGC-016",
     "Ayurvedic capsules for women's health.", ["p09.png"]),
    ("Snasa Amrit", "Jar", 699, "Ayurvedic Medicines", "KN-SNA-017",
     "Ayurvedic formula beneficial in paralysis related care.", ["p19.png"]),
    ("Ashwashila Malt", "400 ml", 1499, "Energy & Stamina", "KN-ASM-018",
     "Premium malt for vitality and stamina.", ["p16.png"]),
    ("Free For Itch", "60 capsules", 699, "Skin Care", "KN-FFI-019",
     "Ayurvedic capsules for itch and skin irritation.", ["p15.png"]),
    ("Anus Care 1", "Capsules", 699, "Ayurvedic Medicines", "KN-AC1-020",
     "Ayurvedic support for piles and rectal care.", ["p07.png"]),
    ("Anus Care 2", "60 capsules", 699, "Ayurvedic Medicines", "KN-AC2-021",
     "Ayurvedic capsules for piles and rectal care.", ["p07.png"]),
    ("Manosudha Ark", "450 ml", 699, "Daily Wellness", "KN-MSA-022",
     "Beneficial for mind restlessness, sleep and memory.", ["p06.png"]),
    ("Manosudha Syrup", "Syrup", 699, "Daily Wellness", "KN-MSS-023",
     "Syrup for mind calmness, sleep and mental wellness.", ["p06.png"]),
    ("Vishaghna Mahakashaya", "450 ml", 599, "Ayurvedic Medicines", "KN-VMA-025",
     "Ayurvedic mahakashaya for toxin and poison-related wellness.", ["ls-vishaghna-mahakashaya.png"]),
    ("Krimighna Mahakashaya", "450 ml", 599, "Ayurvedic Medicines", "KN-KMA-026",
     "Ayurvedic mahakashaya beneficial for intestinal worms and related care.", ["ls-krimighna-mahakashaya.png"]),
    ("Kushthaghna Ark Mahakashaya", "450 ml", 599, "Ayurvedic Medicines", "KN-KAM-027",
     "Ayurvedic ark mahakashaya for skin-related wellness.", ["ls-kushthaghna-ark-mahakashaya.png"]),
]


def _copy_photos():
    DEST.mkdir(parents=True, exist_ok=True)
    for dest_name, src_name in PHOTO_FILES.items():
        src = ASSETS / src_name
        dest = DEST / dest_name
        if src.exists():
            shutil.copyfile(src, dest)
        elif not dest.exists():
            raise FileNotFoundError(f"Missing product photo: {dest_name}")


def replace_catalog():
    _copy_photos()
    from cart.models import CartItem
    from orders.models import OrderItem

    CartItem.objects.all().delete()
    OrderItem.objects.all().delete()
    ProductImage.objects.all().delete()
    Product.objects.all().delete()

    cats = {c.name: c for c in Category.objects.all()}
    default_cat = cats.get("Ayurvedic Medicines") or Category.objects.first()

    created = 0
    for name, qty, price, cat_name, sku, desc, photos in PRODUCTS:
        cat = cats.get(cat_name, default_cat)
        product = Product.objects.create(
            name=name,
            quantity=qty,
            total_rating=4.7,
            category=cat,
            sku=sku,
            stock=100,
            price=Decimal(str(price)),
            discount_type="amount",
            discount=Decimal("0"),
            description=desc,
            available=True,
        )
        for photo in photos:
            rel = f"products/official/{photo}"
            if (MEDIA / rel).exists():
                ProductImage.objects.create(product=product, image=rel)
        created += 1

    return {"created": created, "total": Product.objects.count()}
