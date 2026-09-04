from decimal import Decimal

from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from .models import SpecialCoupon, CouponForAll, OneTimeCoupon, PERCENT
from .serializers import (
    SpecialCouponSerializer,
    CouponForAllSerializer,
    OneTimeCouponSerializer,
    CouponValidationSerializer,
)


def _discount_amount(discount_type, discount, cart_total):
    cart_total = Decimal(str(cart_total))
    discount = Decimal(str(discount))
    if discount_type == PERCENT:
        return (cart_total * discount / Decimal("100")).quantize(Decimal("0.01"))
    return min(discount, cart_total)


@api_view(["GET"])
@permission_classes([AllowAny])
def list_coupons(request):
    now = timezone.now()
    special = SpecialCoupon.objects.filter(active=True)
    for_all = CouponForAll.objects.filter(active=True, valid_from__lte=now, valid_to__gte=now)
    one_time = OneTimeCoupon.objects.filter(active=True, valid_from__lte=now, valid_to__gte=now)
    return Response(
        {
            "special": SpecialCouponSerializer(special, many=True).data,
            "for_all": CouponForAllSerializer(for_all, many=True).data,
            "one_time": OneTimeCouponSerializer(one_time, many=True).data,
        }
    )


@api_view(["POST"])
@permission_classes([AllowAny])
def validate_coupon(request):
    serializer = CouponValidationSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    code = serializer.validated_data["code"].strip()
    cart_total = serializer.validated_data["cart_total"]
    user_id = serializer.validated_data.get("user_id")
    now = timezone.now()

    coupon = None
    coupon_kind = None

    special = SpecialCoupon.objects.filter(code__iexact=code, active=True).first()
    if special:
        if user_id and not special.coupon_for.filter(id=user_id).exists():
            return Response(
                {"valid": False, "message": "Coupon not available for this user."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        coupon, coupon_kind = special, "special"

    if coupon is None:
        for_all = CouponForAll.objects.filter(
            code__iexact=code, active=True, valid_from__lte=now, valid_to__gte=now
        ).first()
        if for_all:
            coupon, coupon_kind = for_all, "for_all"

    if coupon is None:
        one_time = OneTimeCoupon.objects.filter(
            code__iexact=code, active=True, valid_from__lte=now, valid_to__gte=now
        ).first()
        if one_time:
            if user_id and one_time.used_by.filter(id=user_id).exists():
                return Response(
                    {"valid": False, "message": "Coupon already used."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            coupon, coupon_kind = one_time, "one_time"

    if coupon is None:
        return Response(
            {"valid": False, "message": "Invalid or expired coupon."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    amount = _discount_amount(coupon.discount_type, coupon.discount, cart_total)
    return Response(
        {
            "valid": True,
            "code": coupon.code,
            "kind": coupon_kind,
            "discount_type": coupon.discount_type,
            "discount": coupon.discount,
            "description": coupon.description or "",
            "discount_amount": amount,
            "message": "Coupon applied successfully.",
        }
    )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def mark_coupon_used(request):
    code = (request.data.get("code") or "").strip()
    if not code:
        return Response({"detail": "code is required"}, status=status.HTTP_400_BAD_REQUEST)

    one_time = OneTimeCoupon.objects.filter(code__iexact=code, active=True).first()
    if not one_time:
        return Response({"detail": "One-time coupon not found"}, status=status.HTTP_404_NOT_FOUND)

    one_time.used_by.add(request.user)
    return Response({"ok": True, "code": one_time.code})
