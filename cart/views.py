from django.shortcuts import render
from rest_framework import generics, permissions
from rest_framework.response import Response
from rest_framework import status
from .models import CartDetails, CartItem
from dashboard.models import Product
from django.contrib.auth import get_user_model
from .serializers import CartDetailsSerializer, CartItemSerializer
from rest_framework import mixins
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated

# Create your views here.

class CartView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        cart, created = CartDetails.objects.get_or_create(user=request.user)
        serializer = CartDetailsSerializer(cart)
        return Response(serializer.data)

    def post(self, request):
        cart, created = CartDetails.objects.get_or_create(user=request.user)
        product_id = request.data.get('product')
        quantity = int(request.data.get('quantity', 1))
        if not product_id:
            return Response({'error': 'Product ID is required.'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            product = Product.objects.get(id=product_id)
        except Product.DoesNotExist:
            return Response({'error': 'Product not found.'}, status=status.HTTP_404_NOT_FOUND)
        cart_item, item_created = CartItem.objects.get_or_create(cart=cart, product=product)
        if not item_created:
            cart_item.quantity += quantity
        else:
            cart_item.quantity = quantity
        cart_item.save()
        serializer = CartDetailsSerializer(cart)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

class CartItemUpdateView(generics.UpdateAPIView):
    queryset = CartItem.objects.all()
    serializer_class = CartItemSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return CartItem.objects.filter(cart__user=self.request.user)

    def delete(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
