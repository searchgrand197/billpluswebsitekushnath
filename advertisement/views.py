from django.shortcuts import render
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from .models import Slideshow
from .serializers import SlideshowSerializer

# Create your views here.

class SlideshowListView(generics.ListCreateAPIView):
    queryset = Slideshow.objects.filter(is_active=True)
    serializer_class = SlideshowSerializer
    
    def get_permissions(self):
        if self.request.method == 'GET':
            return [AllowAny()]
        return [IsAuthenticated()]

class SlideshowDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Slideshow.objects.all()
    serializer_class = SlideshowSerializer
    permission_classes = [IsAuthenticated]

    def perform_destroy(self, instance):
        instance.is_active = False
        instance.save()
