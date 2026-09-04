from django.urls import path
from . import views

app_name = 'coupon'

urlpatterns = [
    path('list/', views.list_coupons, name='list_coupons'),
    path('validate/', views.validate_coupon, name='validate_coupon'),
    path('mark-used/', views.mark_coupon_used, name='mark_coupon_used'),
]

