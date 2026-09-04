from rest_framework import serializers
from .models import SpecialCoupon, CouponForAll, OneTimeCoupon

class SpecialCouponSerializer(serializers.ModelSerializer):
    class Meta:
        model = SpecialCoupon
        fields = ['id', 'code', 'discount_type', 'discount', 'description', 'active']

class CouponForAllSerializer(serializers.ModelSerializer):
    class Meta:
        model = CouponForAll
        fields = ['id', 'code', 'discount_type', 'discount', 'description', 'valid_from', 'valid_to', 'active']

class OneTimeCouponSerializer(serializers.ModelSerializer):
    class Meta:
        model = OneTimeCoupon
        fields = ['id', 'code', 'discount_type', 'discount', 'description', 'valid_from', 'valid_to', 'active']

class CouponValidationSerializer(serializers.Serializer):
    code = serializers.CharField(max_length=50)
    cart_total = serializers.DecimalField(max_digits=10, decimal_places=2)
    user_id = serializers.IntegerField(required=False, allow_null=True)

class CouponResponseSerializer(serializers.Serializer):
    valid = serializers.BooleanField()
    code = serializers.CharField()
    discount_type = serializers.CharField()
    discount = serializers.DecimalField(max_digits=5, decimal_places=2)
    description = serializers.CharField()
    discount_amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    message = serializers.CharField()

