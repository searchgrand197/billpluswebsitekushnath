from django.urls import path
from . import views
 
urlpatterns = [
    path('slideshows/', views.SlideshowListView.as_view(), name='slideshow-list'),
    path('slideshows/<int:pk>/', views.SlideshowDetailView.as_view(), name='slideshow-detail'),
] 