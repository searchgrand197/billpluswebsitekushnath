"""Add 3 new Mahakashaya products and replace product photos with matching lifestyle shots."""

from decimal import Decimal
from pathlib import Path
import shutil

from django.conf import settings
from dashboard.models import Category, Product, ProductImage

from kushnath_dashboard.remove_product_backgrounds import remove_image_background

ASSETS = Path(r"C:\Users\MITTA\.cursor\projects\d-quick-cart\assets")
MEDIA = Path(settings.MEDIA_ROOT)
LIFESTYLE = MEDIA / "products" / "lifestyle"
LIFESTYLE.mkdir(parents=True, exist_ok=True)

# First 3 Gemini images -> new products @ ₹599
NEW_PRODUCTS = [
    (
        "Vishaghna Mahakashaya",
        "450 ml",
        599,
        "Ayurvedic Medicines",
        "KN-VMA-025",
        "Ayurvedic mahakashaya for toxin and poison-related wellness.",
        "c__Users_MITTA_AppData_Roaming_Cursor_User_workspaceStorage_0aa527268fea964a7ac5b3e8a3b97b55_images_Gemini_Generated_Image_vi3h1xvi3h1xvi3h-ffd3fe57-ae40-42cf-a6f2-148d47582cfa.png",
        "ls-vishaghna-mahakashaya.png",
    ),
    (
        "Krimighna Mahakashaya",
        "450 ml",
        599,
        "Ayurvedic Medicines",
        "KN-KMA-026",
        "Ayurvedic mahakashaya beneficial for intestinal worms and related care.",
        "c__Users_MITTA_AppData_Roaming_Cursor_User_workspaceStorage_0aa527268fea964a7ac5b3e8a3b97b55_images_Gemini_Generated_Image_ucg2nducg2nducg2-c8669f78-71a1-46dc-b7c8-ec33bc77380b.png",
        "ls-krimighna-mahakashaya.png",
    ),
    (
        "Kushthaghna Ark Mahakashaya",
        "450 ml",
        599,
        "Ayurvedic Medicines",
        "KN-KAM-027",
        "Ayurvedic ark mahakashaya for skin-related wellness.",
        "c__Users_MITTA_AppData_Roaming_Cursor_User_workspaceStorage_0aa527268fea964a7ac5b3e8a3b97b55_images_Gemini_Generated_Image_a1o5fma1o5fma1o5-39f21c06-2e08-497e-8c9a-db365a2f77a3.png",
        "ls-kushthaghna-ark-mahakashaya.png",
    ),
]

# SKU -> list of (source asset filename, dest lifestyle filename)
LIFESTYLE_BY_SKU = {
    "KN-PBA-001": [
        (
            "c__Users_MITTA_AppData_Roaming_Cursor_User_workspaceStorage_0aa527268fea964a7ac5b3e8a3b97b55_images_ChatGPT_Image_Aug_20__2026__01_51_35_PM-a247ea45-ff78-4498-940d-60cd03e4c04d.png",
            "ls-panchbhadra-ark.png",
        ),
    ],
    "KN-DRS-003": [
        (
            "c__Users_MITTA_AppData_Roaming_Cursor_User_workspaceStorage_0aa527268fea964a7ac5b3e8a3b97b55_images_image__1_-0e0f391f-4298-48cb-bcc8-1951554d1611.png",
            "ls-dardantak-spray.png",
        ),
    ],
    "KN-KVO-004": [
        (
            "c__Users_MITTA_AppData_Roaming_Cursor_User_workspaceStorage_0aa527268fea964a7ac5b3e8a3b97b55_images_ChatGPT_Image_Aug_20__2026__03_05_44_PM-e11eddfd-e0f7-4b94-8c16-393942903821.png",
            "ls-kesh-vardhan-oil.png",
        ),
    ],
    "KN-KVH-024": [
        (
            "c__Users_MITTA_AppData_Roaming_Cursor_User_workspaceStorage_0aa527268fea964a7ac5b3e8a3b97b55_images_ChatGPT_Image_Aug_20__2026__02_21_57_PM-6a76efef-b1ac-4e42-b8df-390d3449183f.png",
            "ls-kesh-vardhanam-hair-oil.png",
        ),
    ],
    "KN-LGA-005": [
        (
            "c__Users_MITTA_AppData_Roaming_Cursor_User_workspaceStorage_0aa527268fea964a7ac5b3e8a3b97b55_images_ChatGPT_Image_Aug_20__2026__02_25_47_PM-d44281a6-9eb5-473e-8adf-08b379b63cc9.png",
            "ls-lady-gold-ark.png",
        ),
    ],
    "KN-MDA-006": [
        (
            "c__Users_MITTA_AppData_Roaming_Cursor_User_workspaceStorage_0aa527268fea964a7ac5b3e8a3b97b55_images_ChatGPT_Image_Aug_20__2026__03_07_53_PM-c49e6bfa-db84-45d1-9332-e56bb2b73eea.png",
            "ls-madhurodak-ark.png",
        ),
        (
            "c__Users_MITTA_AppData_Roaming_Cursor_User_workspaceStorage_0aa527268fea964a7ac5b3e8a3b97b55_images_ChatGPT_Image_Aug_20__2026__02_32_26_PM-f59d066c-be11-409f-b168-1b064c83a648.png",
            "ls-madhurodak-capsule.png",
        ),
    ],
    "KN-TJK-008": [
        (
            "c__Users_MITTA_AppData_Roaming_Cursor_User_workspaceStorage_0aa527268fea964a7ac5b3e8a3b97b55_images_ChatGPT_Image_Aug_20__2026__02_42_51_PM-1a4118c1-a967-4728-a121-17af411fbc41.png",
            "ls-tejasvi-kadha.png",
        ),
        (
            "c__Users_MITTA_AppData_Roaming_Cursor_User_workspaceStorage_0aa527268fea964a7ac5b3e8a3b97b55_images_imagle-b4a8eb3a-3465-4bee-a26c-47d490e48c04.png",
            "ls-tejasvi-kadha-alt.png",
        ),
    ],
    "KN-KKA-009": [
        (
            "c__Users_MITTA_AppData_Roaming_Cursor_User_workspaceStorage_0aa527268fea964a7ac5b3e8a3b97b55_images_ChatGPT_Image_Aug_20__2026__02_58_18_PM-5d76bab2-d81a-4ec6-b7d9-38d494f68c50.png",
            "ls-kidney-kaya-ark.png",
        ),
    ],
    "KN-KKC-010": [
        (
            "c__Users_MITTA_AppData_Roaming_Cursor_User_workspaceStorage_0aa527268fea964a7ac5b3e8a3b97b55_images_ChatGPT_Image_Aug_20__2026__03_00_11_PM-5d0211e9-a73c-4898-b14c-18636ac0400b.png",
            "ls-kidney-kaya-capsule.png",
        ),
    ],
    "KN-VSA-011": [
        (
            "c__Users_MITTA_AppData_Roaming_Cursor_User_workspaceStorage_0aa527268fea964a7ac5b3e8a3b97b55_images_ChatGPT_Image_Aug_20__2026__02_47_34_PM-5ea8f75d-a8be-4126-8b53-687d8e5bdda3.png",
            "ls-vedic-shiv-amrit-ark.png",
        ),
    ],
    "KN-VSS-012": [
        (
            "c__Users_MITTA_AppData_Roaming_Cursor_User_workspaceStorage_0aa527268fea964a7ac5b3e8a3b97b55_images_ChatGPT_Image_Aug_20__2026__03_02_48_PM-307c9e7b-8650-460d-a19f-d523553834fa.png",
            "ls-vedic-shiv-amrit-syrup.png",
        ),
    ],
    "KN-HSS-014": [
        (
            "c__Users_MITTA_AppData_Roaming_Cursor_User_workspaceStorage_0aa527268fea964a7ac5b3e8a3b97b55_images_ChatGPT_Image_Aug_20__2026__02_19_12_PM-1981dfef-28aa-40c3-918a-88f692039517.png",
            "ls-hair-strong-shampoo.png",
        ),
    ],
    "KN-KYC-015": [
        (
            "c__Users_MITTA_AppData_Roaming_Cursor_User_workspaceStorage_0aa527268fea964a7ac5b3e8a3b97b55_images_ChatGPT_Image_Aug_20__2026__01_47_20_PM-bfa01d84-a421-440d-a672-9eaf803d1203.png",
            "ls-kayakalp-churan.png",
        ),
    ],
    "KN-SNA-017": [
        (
            "c__Users_MITTA_AppData_Roaming_Cursor_User_workspaceStorage_0aa527268fea964a7ac5b3e8a3b97b55_images_ChatGPT_Image_Aug_20__2026__02_49_20_PM-cf71b69a-db08-4293-8917-e379bcbc5431.png",
            "ls-snasa-amrit.png",
        ),
    ],
    "KN-ASM-018": [
        (
            "c__Users_MITTA_AppData_Roaming_Cursor_User_workspaceStorage_0aa527268fea964a7ac5b3e8a3b97b55_images_ChatGPT_Image_Aug_20__2026__02_12_31_PM-cc0cb2ba-4980-4c40-9c3d-acbaf17ab27b.png",
            "ls-ashwashila-malt.png",
        ),
    ],
    "KN-FFI-019": [
        (
            "c__Users_MITTA_AppData_Roaming_Cursor_User_workspaceStorage_0aa527268fea964a7ac5b3e8a3b97b55_images_ChatGPT_Image_Aug_20__2026__02_10_23_PM-53064044-c62b-4d33-8640-4b0caa86130b.png",
            "ls-free-for-itch.png",
        ),
    ],
    "KN-AC2-021": [
        (
            "c__Users_MITTA_AppData_Roaming_Cursor_User_workspaceStorage_0aa527268fea964a7ac5b3e8a3b97b55_images_ChatGPT_Image_Aug_20__2026__02_40_11_PM-d0566e9b-3092-4fe2-99fc-848677163a01.png",
            "ls-anus-care-2.png",
        ),
    ],
    "KN-MSA-022": [
        (
            "c__Users_MITTA_AppData_Roaming_Cursor_User_workspaceStorage_0aa527268fea964a7ac5b3e8a3b97b55_images_ChatGPT_Image_Aug_20__2026__02_17_03_PM-f11a8eb9-2a76-4c9a-a224-9b7d8360c393.png",
            "ls-manosudha-ark.png",
        ),
    ],
    "KN-KMC-002": [
        (
            "c__Users_MITTA_AppData_Roaming_Cursor_User_workspaceStorage_0aa527268fea964a7ac5b3e8a3b97b55_images_ChatGPT_Image_Aug_20__2026__02_29_29_PM-941f19f8-8539-4665-a1b4-d0c718c67a97.png",
            "ls-kamaking-capsule.png",
        ),
    ],
}


def _copy_and_transparent(src_name: str, dest_name: str, *, transparent: bool = True) -> str:
    src = ASSETS / src_name
    dest = LIFESTYLE / dest_name
    if not src.exists():
        raise FileNotFoundError(f"Missing asset: {src_name}")
    shutil.copyfile(src, dest)
    if transparent:
        remove_image_background(dest)
    return f"products/lifestyle/{dest_name}"


def _set_product_images(product: Product, lifestyle_paths: list[str]) -> None:
    old_paths = list(product.images.values_list("image", flat=True))
    product.images.all().delete()
    for rel in lifestyle_paths:
        ProductImage.objects.create(product=product, image=rel)
    for rel in old_paths:
        if rel not in lifestyle_paths and (MEDIA / rel).exists():
            ProductImage.objects.create(product=product, image=rel)


def update_lifestyle_catalog():
    cats = {c.name: c for c in Category.objects.all()}
    default_cat = cats.get("Ayurvedic Medicines") or Category.objects.first()

    added = []
    for name, qty, price, cat_name, sku, desc, src_name, dest_name in NEW_PRODUCTS:
        if Product.objects.filter(sku=sku).exists():
            continue
        rel = _copy_and_transparent(src_name, dest_name, transparent=False)
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
        ProductImage.objects.create(product=product, image=rel)
        added.append(name)

    updated = []
    for sku, photo_specs in LIFESTYLE_BY_SKU.items():
        try:
            product = Product.objects.get(sku=sku)
        except Product.DoesNotExist:
            continue
        lifestyle_paths = [_copy_and_transparent(src, dest) for src, dest in photo_specs]
        _set_product_images(product, lifestyle_paths)
        updated.append(product.name)

    return {
        "added": added,
        "updated": updated,
        "total_products": Product.objects.count(),
    }
