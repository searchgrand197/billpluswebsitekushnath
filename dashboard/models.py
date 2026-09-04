from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError

# Create your models here.

class Category(models.Model):
    name = models.CharField(max_length=100)
    image = models.ImageField(upload_to='categories/', blank=True, null=True)
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.name

class Tag(models.Model):
    name = models.CharField(max_length=50, unique=True)

    def __str__(self):
        return self.name

class Benefit(models.Model):
    name = models.CharField(max_length=255, unique=True)

    def __str__(self):
        return self.name

PERCENT = 'percent'
AMOUNT = 'amount'
DISCOUNT_TYPE_CHOICES = [
    (PERCENT, 'Percent'),
    (AMOUNT, 'Amount'),
]

class Product(models.Model):
    name = models.CharField(max_length=255)
    quantity = models.CharField(max_length=255)
    total_rating = models.FloatField(default=0)
    category = models.ForeignKey(Category, related_name='products', on_delete=models.CASCADE)
    sku = models.CharField(max_length=100, unique=True)
    tags = models.ManyToManyField(Tag, related_name='products', blank=True)
    benefits = models.ManyToManyField(Benefit, related_name='products', blank=True)
    stock = models.PositiveIntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    discount_type = models.CharField(max_length=10, choices=DISCOUNT_TYPE_CHOICES, default=AMOUNT)
    discount = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    description = models.TextField(blank=True, null=True)
    weight = models.DecimalField(max_digits=6, decimal_places=2, blank=True, null=True)
    length = models.DecimalField(max_digits=6, decimal_places=2, blank=True, null=True)
    breadth = models.DecimalField(max_digits=6, decimal_places=2, blank=True, null=True)
    height = models.DecimalField(max_digits=6, decimal_places=2, blank=True, null=True)
    available = models.BooleanField(default=True)

    def clean(self):
        if self.discount_type == PERCENT and not (0 <= self.discount <= 100):
            raise ValidationError('Percent discount must be between 0 and 100.')

    def __str__(self):
        return self.name

class ProductImage(models.Model):
    product = models.ForeignKey(Product, related_name='images', on_delete=models.CASCADE)
    image = models.ImageField(upload_to='products/')

    def __str__(self):
        return f"Image for {self.product.name}"

class Reply(models.Model):
    comment = models.ForeignKey('Comment', related_name='replies', on_delete=models.CASCADE)
    response = models.TextField()
    reply_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Reply by {self.reply_by} on {self.created_at}"

class Comment(models.Model):
    product = models.ForeignKey(Product, related_name='comments', on_delete=models.CASCADE)
    comment = models.TextField()
    rating = models.PositiveSmallIntegerField()
    commented_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Comment by {self.commented_by} on {self.created_at}"

class PickupLocation(models.Model):
    name = models.CharField(max_length=255)
    address = models.TextField()
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    pin = models.CharField(max_length=10)
    phone = models.CharField(max_length=20)
    country = models.CharField(max_length=100, default='India')

    def __str__(self):
        return f"{self.name} ({self.city})"

class ReturnDetails(models.Model):
    name = models.CharField(max_length=255)
    address = models.TextField()
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    pin = models.CharField(max_length=10)
    phone = models.CharField(max_length=20)
    country = models.CharField(max_length=100, default='India')

    def __str__(self):
        return f"{self.name} ({self.city})"

class OrderDashboard(models.Model):
    name = models.CharField(max_length=255)
    status = models.CharField(max_length=100, default='Pending')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Order {self.id} - {self.name} - {self.status}"

class RazorpayOrder(models.Model):
    order_id = models.CharField(max_length=255, unique=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, default='INR')
    receipt = models.CharField(max_length=255, blank=True, null=True)
    status = models.CharField(max_length=50, default='created')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Razorpay Order {self.order_id} - {self.amount} {self.currency}"
