"""
Merged URL configuration: Kushnath Live storefront + Billvice billing/POS.

Routing strategy (avoids /api/ conflicts):
  /api/           -> Kushnath Live ecommerce APIs
  /billing/       -> Billvice Django pages + /billing/api/ REST
  /billvice/      -> Billvice React SPA
  /               -> Live storefront pages + React catch-all
"""

from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import path, include, re_path
from django.conf import settings
from django.conf.urls.static import static
from rest_framework_simplejwt.views import TokenRefreshView

from kushnath_dashboard.views import serve_frontend
from kushnath_dashboard.storefront import (
    home,
    product_detail,
    cart_page,
    checkout_page,
    order_success,
)
from kushnath.billvice_views import serve_billvice

urlpatterns = [
    path("admin/", admin.site.urls),

    # --- Billvice POS / inventory ---
    path("billing/", include("billing.urls")),
    path(
        "accounts/login/",
        auth_views.LoginView.as_view(),
        name="login",
    ),
    path(
        "accounts/logout/",
        auth_views.LogoutView.as_view(next_page="/billvice/"),
        name="logout",
    ),
    # Billvice SPA — ONLY from frontend/dist (never build/index.html / storefront home)
    # Matches /billvice, /billvice/, /billvice/login, /billvice/assets/...
    re_path(r"^billvice(?:/(?P<path>.*))?$", serve_billvice, name="billvice_app"),

    # --- Kushnath Live storefront pages ---
    path("", home, name="home"),
    path("product/<int:product_id>/", product_detail, name="product_detail"),
    path("cart/", cart_page, name="cart"),
    path("checkout/", checkout_page, name="checkout"),
    path("order-success/", order_success, name="order_success"),

    # --- Kushnath Live APIs (keep at /api/) ---
    path("api/", include("cart.urls")),
    path("api/", include("dashboard.urls")),
    path("api/", include("advertisement.urls")),
    path("api/", include("authentication.urls")),
    path("api/", include("customer.urls")),
    path("api/", include("orders.urls")),
    path("api/coupons/", include("coupon.urls")),
    path("api/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# Catch-all for remaining Live React routes (assets, SPA paths)
urlpatterns += [re_path(r"^(?P<path>.*)$", serve_frontend)]
