from django.db import models
from mongoengine import (
	Document, 
	StringField, 
	ReferenceField, 
	DateTimeField, 
	FloatField, 
	BooleanField, 
	DictField, 
	DynamicField,
	EmbeddedDocument, 
	ListField, 
	EmbeddedDocumentField,
	IntField
)
import datetime
from cart.models import CartItem

		
class UserAddress(EmbeddedDocument):
	line_1 = StringField(required=True)
	line_2 = StringField()
	city = StringField()
	state = StringField()
	pin = IntField()
	landmark = StringField()

	meta = {
        "collection": "user_addresses",
        "indexes": [],
    }


class UserProfile(Document):
    user_id = IntField(required=True)
    name = StringField()
    email = StringField(required=False)
    is_active = BooleanField(default=True)
    addresses = ListField(EmbeddedDocumentField(UserAddress))
    created_at = DateTimeField(default=datetime.datetime.utcnow)
    updated_at = DateTimeField(default=datetime.datetime.utcnow)
    whitelisted = BooleanField(default=False)
    blacklisted = BooleanField(default=False)
    cart_items = ListField(EmbeddedDocumentField(CartItem))

    extra_data = DynamicField()  

    meta = {
        "collection": "user_profiles",
        "indexes": ["user_id"],
    }

    def save(self, *args, **kwargs):
        self.updated_at = datetime.datetime.utcnow()
        return super().save(*args, **kwargs)
