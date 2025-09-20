from django.db import models
from datetime import date
from cart.models import CartItem
from django.contrib.auth.models import User
from lib.base_classes import BaseModel
		
class UserProfile(BaseModel):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    name = models.CharField(max_length=100, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    whitelisted = models.BooleanField(default=False)
    blacklisted = models.BooleanField(default=False)
    cart_items = models.ManyToManyField(CartItem, related_name="user_profiles")
    dob = models.DateField(default=date(2000, 1, 1))
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

class UserAddress(BaseModel):
    ADDRESS_TYPES = [
        ("Home", "Home"),
        ("Office", "Office"),
        ("Friend", "Friend"),
        ("Other", "Other"),
    ]
    profile = models.ForeignKey(UserProfile, on_delete=models.CASCADE, blank=True, null=True)
    address_type = models.CharField(max_length=20, choices=ADDRESS_TYPES)
    poc_name = models.CharField(max_length=100)
    phone = models.CharField(max_length=20)
    line_1 = models.CharField(max_length=255)
    line_2 = models.CharField(max_length=255, blank=True, null=True)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    pin = models.IntegerField()
    landmark = models.CharField(max_length=255, blank=True, null=True)

