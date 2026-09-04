from django.urls import path
from . import views

urlpatterns = [
    path('customer/profile/', views.get_customer_data, name='get_customer_data'),
    path('customer/profile/update/', views.update_customer_data, name='update_customer_data'),
] 