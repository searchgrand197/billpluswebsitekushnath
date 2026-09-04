from rest_framework import serializers
from .models import Category, Tag, Benefit, Product, ProductImage, RazorpayOrder

class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'name', 'image', 'description']

class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = ['id', 'name']

class BenefitSerializer(serializers.ModelSerializer):
    class Meta:
        model = Benefit
        fields = ['id', 'name']

class ProductImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductImage
        fields = ['id', 'image']

class ProductSerializer(serializers.ModelSerializer):
    category = CategorySerializer(read_only=True)
    category_id = serializers.PrimaryKeyRelatedField(
        queryset=Category.objects.all(),
        source='category',
        write_only=True
    )
    tags = TagSerializer(many=True, read_only=True)
    tag_ids = serializers.ListField(
        child=serializers.IntegerField(),
        write_only=True,
        required=False
    )
    benefits = BenefitSerializer(many=True, read_only=True)
    benefit_ids = serializers.ListField(
        child=serializers.IntegerField(),
        write_only=True,
        required=False
    )
    images = ProductImageSerializer(many=True, read_only=True)

    class Meta:
        model = Product
        fields = [
            'id', 'name', 'quantity', 'total_rating', 'category', 'category_id', 'sku',
            'tags', 'tag_ids', 'benefits', 'benefit_ids', 'stock', 'price', 'discount_type',
            'discount', 'description', 'weight', 'length', 'breadth',
            'height', 'available', 'images'
        ]

    def create(self, validated_data):
        tag_ids = validated_data.pop('tag_ids', [])
        benefit_ids = validated_data.pop('benefit_ids', [])
        
        product = Product.objects.create(**validated_data)
        
        if tag_ids:
            tags = Tag.objects.filter(id__in=tag_ids)
            product.tags.set(tags)
        
        if benefit_ids:
            benefits = Benefit.objects.filter(id__in=benefit_ids)
            product.benefits.set(benefits)
            
        return product

    def update(self, instance, validated_data):
        tag_ids = validated_data.pop('tag_ids', None)
        benefit_ids = validated_data.pop('benefit_ids', None)
        
        # Update other fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        
        # Update tags if provided
        if tag_ids is not None:
            tags = Tag.objects.filter(id__in=tag_ids)
            instance.tags.set(tags)
        
        # Update benefits if provided
        if benefit_ids is not None:
            benefits = Benefit.objects.filter(id__in=benefit_ids)
            instance.benefits.set(benefits)
            
        return instance 

class RazorpayOrderSerializer(serializers.ModelSerializer):
    class Meta:
        model = RazorpayOrder
        fields = '__all__' 