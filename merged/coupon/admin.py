from django.contrib import admin
from django import forms
from .models import SpecialCoupon, CouponForAll, OneTimeCoupon, PERCENT

# Register your models here.
class SpecialCouponForm(forms.ModelForm):
    class Meta:
        model = SpecialCoupon
        fields = '__all__'
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.discount_type == PERCENT:
            self.fields['discount'].widget = forms.NumberInput(attrs={'min': 0, 'max': 100})

class CouponForAllForm(forms.ModelForm):
    class Meta:
        model = CouponForAll
        fields = '__all__'
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.discount_type == PERCENT:
            self.fields['discount'].widget = forms.NumberInput(attrs={'min': 0, 'max': 100})

class OneTimeCouponForm(forms.ModelForm):
    class Meta:
        model = OneTimeCoupon
        fields = '__all__'
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.discount_type == PERCENT:
            self.fields['discount'].widget = forms.NumberInput(attrs={'min': 0, 'max': 100})

class SpecialCouponAdmin(admin.ModelAdmin):
    form = SpecialCouponForm

class CouponForAllAdmin(admin.ModelAdmin):
    form = CouponForAllForm

class OneTimeCouponAdmin(admin.ModelAdmin):
    form = OneTimeCouponForm

admin.site.register(SpecialCoupon, SpecialCouponAdmin)
admin.site.register(CouponForAll, CouponForAllAdmin)
admin.site.register(OneTimeCoupon, OneTimeCouponAdmin)
