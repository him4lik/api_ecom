from django.db import models
import datetime
from user.models import UserAddress
from lib.base_classes import BaseModel
from inventory.models import ProductVariant
from django.contrib.auth.models import User


class Order(BaseModel):
    rzp_order_id = models.CharField(max_length=100, blank=True, null=True)
    rzp_payment_id = models.CharField(max_length=100, blank=True, null=True)
    rzp_callback_order_id = models.CharField(max_length=100, blank=True, null=True)
    rzp_signature = models.CharField(max_length=255, blank=True, null=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="orders")
    cost = models.IntegerField()
    gst = models.IntegerField()
    shipping = models.IntegerField(default=200)
    shipping_address = models.ForeignKey(UserAddress, on_delete=models.SET_NULL, null=True, related_name="orders")
    status = models.CharField(max_length=50)
    is_active = models.BooleanField(default=True)
    is_paid = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class SoldProduct(BaseModel):
    variant = models.ForeignKey(ProductVariant, on_delete=models.CASCADE, related_name="sold_items")
    individual_cost = models.IntegerField()
    total_cost = models.IntegerField()
    quantity = models.IntegerField()
    order = models.ForeignKey(Order, on_delete=models.CASCADE)
