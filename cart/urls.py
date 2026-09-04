from django.urls import path
from .views import CartView, CartItemUpdateView
 
urlpatterns = [
    path('cart/', CartView.as_view(), name='cart'),
    path('cart/items/<int:pk>/', CartItemUpdateView.as_view(), name='cartitem-update'),
] 