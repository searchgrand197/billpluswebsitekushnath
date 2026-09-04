from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from coupon.models import CouponForAll, SpecialCoupon, OneTimeCoupon

class Command(BaseCommand):
    help = 'Create test coupon data for development'

    def handle(self, *args, **options):
        # Clear existing test coupons
        CouponForAll.objects.filter(code__startswith='TEST').delete()
        SpecialCoupon.objects.filter(code__startswith='TEST').delete()
        OneTimeCoupon.objects.filter(code__startswith='TEST').delete()
        
        current_time = timezone.now()
        
        # Create CouponForAll (available to everyone)
        CouponForAll.objects.create(
            code='TEST10OFF',
            discount_type='percent',
            discount=10.00,
            description='10% off on all orders',
            valid_from=current_time - timedelta(days=1),
            valid_to=current_time + timedelta(days=30),
            active=True
        )
        
        CouponForAll.objects.create(
            code='TEST50RS',
            discount_type='amount',
            discount=50.00,
            description='₹50 off on orders above ₹500',
            valid_from=current_time - timedelta(days=1),
            valid_to=current_time + timedelta(days=30),
            active=True
        )
        
        # Create SpecialCoupon (for specific users)
        SpecialCoupon.objects.create(
            code='TESTVIP20',
            discount_type='percent',
            discount=20.00,
            description='VIP customer special - 20% off',
            active=True
        )
        
        # Create OneTimeCoupon (one-time use per user)
        OneTimeCoupon.objects.create(
            code='TESTFIRST',
            discount_type='amount',
            discount=100.00,
            description='First order discount - ₹100 off',
            valid_from=current_time - timedelta(days=1),
            valid_to=current_time + timedelta(days=60),
            active=True
        )
        
        self.stdout.write(
            self.style.SUCCESS('Successfully created test coupons:\n')
        )
        self.stdout.write('• TEST10OFF - 10% off for everyone\n')
        self.stdout.write('• TEST50RS - ₹50 off for everyone\n')
        self.stdout.write('• TESTVIP20 - 20% off for VIP customers\n')
        self.stdout.write('• TESTFIRST - ₹100 off first order (one-time use)\n')

