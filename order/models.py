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


class SoldProduct(EmbeddedDocument):
	variant_id = IntField(required=True)
	individual_cost = IntField()
	total_cost = IntField()
	quantity = IntField()

	meta = {
        "collection": "sold_products",
        "indexes": ["variant_id"],
    }


class Order(Document):
    sold_products = ListField(EmbeddedDocumentField(SoldProduct))
    user_id = IntField()
    cost = IntField()
    gst = IntField(required=True)
    status = StringField()
    is_active = BooleanField(default=True)
    created_at = DateTimeField(default=datetime.datetime.utcnow)
    updated_at = DateTimeField(default=datetime.datetime.utcnow)

    meta = {
        "collection": "orders",
        "indexes": ["user_id"],
    }

    def save(self, *args, **kwargs):
        self.updated_at = datetime.datetime.utcnow()
        return super().save(*args, **kwargs)