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


class CartItem(EmbeddedDocument):
	variant_id = StringField(required=True)
	quantity = IntField(default=1)
	user_id = IntField(required=True)
	created_at = DateTimeField(default=datetime.datetime.utcnow)
	updated_at = DateTimeField(default=datetime.datetime.utcnow)

	meta = {
		"collection": "cart_items",
		"indexes": ["user_id"],
	}

	def save(self, *args, **kwargs):
		self.updated_at = datetime.datetime.utcnow()
		return super().save(*args, **kwargs)