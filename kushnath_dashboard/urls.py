"""
URL configuration for Kushnath Live storefront (+ Billvice when this is ROOT_URLCONF).

If the server uses kushnath_dashboard.settings, this file MUST include billing + billvice
or /billing/api/* falls through to serve_frontend → redirect("/") and the POS page
flashes then disappears.
"""

from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import path, include, re_path
from django.conf import settings
from django.conf.urls.static import static
from rest_framework_simplejwt.views import TokenRefreshView

from kushnath_dashboard.views import serve_frontend
from kushnath_dashboard.storefront import home, product_detail, cart_page, checkout_page, order_success
from kushnath.billvice_views import serve_billvice

urlpatterns = [
    path("admin/", admin.site.urls),

    # Billvice API + Django pages (REQUIRED — without this POS disappears after 1s)
    path("billing/", include("billing.urls")),
    path("accounts/login/", auth_views.LoginView.as_view(), name="login"),
    path(
        "accounts/logout/",
        auth_views.LogoutView.as_view(next_page="/billvice/"),
        name="logout",
    ),
    re_path(r"^billvice(?:/(?P<path>.*))?$", serve_billvice, name="billvice_app"),

    # Storefront pages
    path("", home, name="home"),
    path("product/<int:product_id>/", product_detail, name="product_detail"),
    path("cart/", cart_page, name="cart"),
    path("checkout/", checkout_page, name="checkout"),
    path("order-success/", order_success, name="order_success"),

    # Live ecommerce APIs
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

urlpatterns += [re_path(r"^(?P<path>.*)$", serve_frontend)]
