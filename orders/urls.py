from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import OrderViewSet, OrderStatusHistoryViewSet

router = DefaultRouter()
router.register(r'orders', OrderViewSet, basename='order')
router.register(r'order-status-history', OrderStatusHistoryViewSet, basename='order-status-history')

urlpatterns = [
    path('', include(router.urls)),
] 