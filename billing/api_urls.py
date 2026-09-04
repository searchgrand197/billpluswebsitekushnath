from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    ProductCategoryViewSet,
    ProductViewSet,
    StockViewSet,
    InvoiceViewSet,
    CustomerViewSet,
    PaymentReceivedViewSet,
    CompanySettingsViewSet,
    RawMaterialViewSet,
    RecipeViewSet,
    ManufacturingViewSet,
    StockMovementLogViewSet,
    api_dashboard_summary,
    api_reports_summary,
    api_balance_sheet,
    api_dues_summary,
    api_create_invoice_pos,
    api_customer_ledger,
    api_global_search,
)
from .po_api import PurchaseOrderViewSet, SupplierViewSet
from .auth_api import api_csrf, api_login, api_logout, api_me

router = DefaultRouter()
router.register(r'categories', ProductCategoryViewSet)
router.register(r'products', ProductViewSet)
router.register(r'stock', StockViewSet)
router.register(r'invoices', InvoiceViewSet)
router.register(r'customers', CustomerViewSet)
router.register(r'payments', PaymentReceivedViewSet)
router.register(r'settings', CompanySettingsViewSet)
router.register(r'purchase-orders', PurchaseOrderViewSet)
router.register(r'suppliers', SupplierViewSet)
router.register(r'raw-materials', RawMaterialViewSet)
router.register(r'recipes', RecipeViewSet)
router.register(r'manufacturing', ManufacturingViewSet)
router.register(r'stock-movements', StockMovementLogViewSet)

urlpatterns = [
    path('auth/csrf/', api_csrf, name='api_csrf'),
    path('auth/login/', api_login, name='api_login'),
    path('auth/logout/', api_logout, name='api_logout'),
    path('auth/me/', api_me, name='api_me'),
    path('search/', api_global_search, name='api_global_search'),
    path('dashboard/', api_dashboard_summary, name='api_dashboard_summary'),
    path('reports/summary/', api_reports_summary, name='api_reports_summary'),
    path('reports/balance-sheet/', api_balance_sheet, name='api_balance_sheet'),
    path('dues/summary/', api_dues_summary, name='api_dues_summary'),
    path('pos/create-invoice/', api_create_invoice_pos, name='api_create_invoice_pos'),
    path('customers/<int:customer_id>/ledger-data/', api_customer_ledger, name='api_customer_ledger'),
    path('', include(router.urls)),
]
