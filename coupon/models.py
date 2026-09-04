from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError

# Create your models here.

PERCENT = 'percent'
AMOUNT = 'amount'
DISCOUNT_TYPE_CHOICES = [
    (PERCENT, 'Percent'),
    (AMOUNT, 'Amount'),
]

class SpecialCoupon(models.Model):
    code = models.CharField(max_length=50, unique=True)
    discount_type = models.CharField(max_length=10, choices=DISCOUNT_TYPE_CHOICES, default=AMOUNT)
    discount = models.DecimalField(max_digits=5, decimal_places=2)
    description = models.TextField(blank=True, null=True)
    active = models.BooleanField(default=True)
    coupon_for = models.ManyToManyField(settings.AUTH_USER_MODEL, blank=True, related_name='special_coupons')

    def clean(self):
        if self.discount_type == PERCENT and not (0 <= self.discount <= 100):
            raise ValidationError('Percent discount must be between 0 and 100.')

    def __str__(self):
        return self.code

class CouponForAll(models.Model):
    code = models.CharField(max_length=50, unique=True)
    discount_type = models.CharField(max_length=10, choices=DISCOUNT_TYPE_CHOICES, default=AMOUNT)
    discount = models.DecimalField(max_digits=5, decimal_places=2)
    description = models.TextField(blank=True, null=True)
    valid_from = models.DateTimeField()
    valid_to = models.DateTimeField()
    active = models.BooleanField(default=True)

    def clean(self):
        if self.discount_type == PERCENT and not (0 <= self.discount <= 100):
            raise ValidationError('Percent discount must be between 0 and 100.')

    def __str__(self):
        return self.code

class OneTimeCoupon(models.Model):
    code = models.CharField(max_length=50, unique=True)
    discount_type = models.CharField(max_length=10, choices=DISCOUNT_TYPE_CHOICES, default=AMOUNT)
    discount = models.DecimalField(max_digits=5, decimal_places=2)
    description = models.TextField(blank=True, null=True)
    valid_from = models.DateTimeField()
    valid_to = models.DateTimeField()
    active = models.BooleanField(default=True)
    used_by = models.ManyToManyField(settings.AUTH_USER_MODEL, blank=True, related_name='used_coupons')

    def clean(self):
        if self.discount_type == PERCENT and not (0 <= self.discount <= 100):
            raise ValidationError('Percent discount must be between 0 and 100.')

    def __str__(self):
        return self.code
