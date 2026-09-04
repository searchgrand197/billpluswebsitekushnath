from django.contrib import admin
from .models import CartDetails, CartItem

# Register your models here.

class CartItemInline(admin.TabularInline):
    model = CartItem
    extra = 1

class CartDetailsAdmin(admin.ModelAdmin):
    inlines = [CartItemInline]

admin.site.register(CartDetails, CartDetailsAdmin)
