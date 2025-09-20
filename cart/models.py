from django.db import models
import datetime
from lib.base_classes import BaseModel
from django.contrib.auth.models import User
from inventory.models import ProductVariant

class CartItem(BaseModel):
    variant = models.ForeignKey(ProductVariant, on_delete=models.CASCADE, related_name="cart_items")
    quantity = models.IntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
