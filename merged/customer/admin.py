from django.contrib import admin
from .models import Customer, CustomerMobile, CustomerAddress, MoreAddress

# Register your models here.
class CustomerMobileInline(admin.TabularInline):
    model = CustomerMobile
    extra = 1

class CustomerAddressInline(admin.TabularInline):
    model = CustomerAddress
    extra = 1

class MoreAddressInline(admin.TabularInline):
    model = MoreAddress
    extra = 1

class CustomerAdmin(admin.ModelAdmin):
    inlines = [CustomerMobileInline, CustomerAddressInline, MoreAddressInline]

admin.site.register(Customer, CustomerAdmin)
