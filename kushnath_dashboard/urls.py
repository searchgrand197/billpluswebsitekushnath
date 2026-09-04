"""
URL configuration for kushnath_dashboard project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.contrib import admin
from django.urls import path, include, re_path
from django.conf import settings
from django.conf.urls.static import static
from rest_framework_simplejwt.views import TokenRefreshView

from kushnath_dashboard.views import serve_frontend
from kushnath_dashboard.storefront import home, product_detail, cart_page, checkout_page, order_success

urlpatterns = [
    path("admin/", admin.site.urls),

    # Storefront pages
    path('', home, name='home'),
    path('product/<int:product_id>/', product_detail, name='product_detail'),
    path('cart/', cart_page, name='cart'),
    path('checkout/', checkout_page, name='checkout'),
    path('order-success/', order_success, name='order_success'),

    # APIs
    path('api/', include('cart.urls')),
    path('api/', include('dashboard.urls')),
    path('api/', include('advertisement.urls')),
    path('api/', include('authentication.urls')),
    path('api/', include('customer.urls')),
    path('api/', include('orders.urls')),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# Catch-all for any remaining React routes (assets, etc.)
urlpatterns += [re_path(r'^(?P<path>.*)$', serve_frontend)]
