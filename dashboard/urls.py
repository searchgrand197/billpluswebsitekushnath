from django.urls import path
from . import views

urlpatterns = [
    # Categories
    path('categories/', views.CategoryListView.as_view(), name='category-list'),
    path('categories/<int:pk>/', views.CategoryDetailView.as_view(), name='category-detail'),
    
    # Tags
    path('tags/', views.TagListView.as_view(), name='tag-list'),
    path('tags/<int:pk>/', views.TagDetailView.as_view(), name='tag-detail'),
    
    # Benefits
    path('benefits/', views.BenefitListView.as_view(), name='benefit-list'),
    path('benefits/<int:pk>/', views.BenefitDetailView.as_view(), name='benefit-detail'),
    
    # Products
    path('products/', views.ProductListView.as_view(), name='product-list'),
    path('products/<int:pk>/', views.ProductDetailView.as_view(), name='product-detail'),
    
    # Product Images
    path('product-images/', views.ProductImageListView.as_view(), name='product-image-list'),
    path('product-images/<int:pk>/', views.ProductImageDetailView.as_view(), name='product-image-detail'),
    path('createshipment/', views.createshipment, name='create-shipment'),
    path('delivery/check-pincode/', views.check_delivery_pincode, name='check-delivery-pincode'),
    path('delivery/track/', views.track_delivery, name='track-delivery'),
    
    # Razorpay endpoints
    path('rz/orderid/', views.create_razorpay_order, name='create-razorpay-order'),
    path('rz/orderid/<str:order_id>/', views.get_razorpay_order, name='get-razorpay-order'),
    path('rz/verify-payment/', views.verify_razorpay_payment, name='verify-razorpay-payment'),
    path('rz/config/', views.razorpay_config, name='razorpay-config'),
] 