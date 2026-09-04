from django.contrib import admin
from django import forms
from .models import Product, ProductImage, Category, Tag, Benefit, Comment, Reply, PERCENT, PickupLocation, ReturnDetails, OrderDashboard, RazorpayOrder

class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = '__all__'
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.discount_type == PERCENT:
            self.fields['discount'].widget = forms.NumberInput(attrs={'min': 0, 'max': 100})

class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1

class CommentInline(admin.TabularInline):
    model = Comment
    extra = 0

class ReplyInline(admin.TabularInline):
    model = Reply
    extra = 1

class ProductAdmin(admin.ModelAdmin):
    form = ProductForm
    inlines = [ProductImageInline, CommentInline]
    filter_horizontal = ('tags', 'benefits')

class TagAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)

class BenefitAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)

class CommentAdmin(admin.ModelAdmin):
    inlines = [ReplyInline]

@admin.register(RazorpayOrder)
class RazorpayOrderAdmin(admin.ModelAdmin):
    list_display = ('order_id', 'amount', 'currency', 'status', 'created_at')
    list_filter = ('status', 'currency', 'created_at')
    search_fields = ('order_id', 'receipt')
    readonly_fields = ('order_id', 'created_at', 'updated_at')

# Register your models here.
admin.site.register(Product, ProductAdmin)
admin.site.register(ProductImage)
admin.site.register(Category)
admin.site.register(Tag, TagAdmin)
admin.site.register(Benefit, BenefitAdmin)
admin.site.register(Comment, CommentAdmin)
admin.site.register(Reply)

# Register new models
admin.site.register(PickupLocation)
admin.site.register(ReturnDetails)
admin.site.register(OrderDashboard)
