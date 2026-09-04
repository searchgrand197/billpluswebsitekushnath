from django.db import models
from django.conf import settings

# Create your models here.

class Customer(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    email = models.EmailField()

    def __str__(self):
        return self.name

class CustomerMobile(models.Model):
    customer = models.ForeignKey(Customer, related_name='mobiles', on_delete=models.CASCADE)
    mobile = models.CharField(max_length=15)

    def __str__(self):
        return self.mobile

class CustomerAddress(models.Model):
    customer = models.ForeignKey(Customer, related_name='addresses', on_delete=models.CASCADE)
    address = models.TextField()
    pincode = models.CharField(max_length=10)
    city = models.CharField(max_length=255)
    state = models.CharField(max_length=255)
    country = models.CharField(max_length=255)

    def __str__(self):
        return f"{self.address} - {self.pincode}"

class MoreAddress(models.Model):
    customer = models.ForeignKey(Customer, related_name='more_addresses', on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    mobile = models.CharField(max_length=15)
    email = models.EmailField()
    address = models.TextField()
    pincode = models.CharField(max_length=10)
    city = models.CharField(max_length=255)
    state = models.CharField(max_length=255)
    country = models.CharField(max_length=255)

    def __str__(self):
        return f"{self.name} - {self.address} - {self.pincode}"
