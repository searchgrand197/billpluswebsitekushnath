from rest_framework import serializers
from .models import CartDetails, CartItem
from dashboard.models import Product

class CartItemSerializer(serializers.ModelSerializer):
    product_name = serializers.ReadOnlyField(source='product.name')
    product_image = serializers.SerializerMethodField()
    product_amount = serializers.SerializerMethodField()
    product_price = serializers.DecimalField(source='product.price', max_digits=10, decimal_places=2)
    product_discount = serializers.DecimalField(source='product.discount', max_digits=5, decimal_places=2)
    product_discount_type = serializers.CharField(source='product.discount_type')
    discounted_price = serializers.SerializerMethodField()

    class Meta:
        model = CartItem
        fields = [
            'id', 'cart', 'product', 'product_name', 'quantity', 
            'product_image', 'product_amount', 'product_price',
            'product_discount', 'product_discount_type', 'discounted_price'
        ]

    def get_product_image(self, obj):
        # Get the first image of the product if available
        product_images = obj.product.images.all()
        if product_images.exists():
            return product_images.first().image.url
        return None

    def get_discounted_price(self, obj):
        product = obj.product
        if product.discount_type == 'percent':
            return float(product.price - (product.price * product.discount / 100))
        return float(product.price - product.discount)

    def get_product_amount(self, obj):
        product = obj.product
        if product.discount_type == 'percent':
            discounted_price = product.price - (product.price * product.discount / 100)
        else:
            discounted_price = product.price - product.discount
        return float(discounted_price * obj.quantity)

class CartDetailsSerializer(serializers.ModelSerializer):
    items = CartItemSerializer(many=True, read_only=True)
    class Meta:
        model = CartDetails
        fields = ['id', 'user', 'items']