from lib.base_classes import BaseModel
from django.db import models
from django.contrib.postgres.fields import ArrayField
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
from bson import ObjectId
from django.db.models import Q
from mongoengine.queryset.visitor import Q as MongoQ
from collections import defaultdict
from django.utils.text import slugify


class Category(BaseModel):
	name = models.CharField(max_length=20)

	class Meta:
		verbose_name_plural = "Categories"

	def __str__(self):
		return self.name

class Product(BaseModel):
	name = models.CharField(max_length=100, unique=True)
	description = models.CharField(max_length=255)
	categories = models.ManyToManyField(Category)

	def __str__(self):
		return self.name

class FeaturedProductLine(BaseModel):
	title = models.CharField(max_length=50, unique=True)
	description = models.CharField(max_length=255)
	images = ArrayField(models.FileField(upload_to="product_line/"), blank=True, default=list)
	is_active = models.BooleanField(default=True)
	variants = ArrayField(models.CharField(max_length=24), blank=True, default=list)
	is_primary = models.BooleanField(default=False)

	def __str__(self):
		return self.title

	def get_variants(self):
		object_ids = [ObjectId(variant_id) for variant_id in self.variants]
		return list(ProductVariant.objects.filter(id__in=object_ids))


class FilterSpecs(BaseModel):
	category = models.ForeignKey(Category, on_delete=models.CASCADE)
	product = models.ForeignKey(Product, on_delete=models.CASCADE)
	filter_tags = ArrayField(models.CharField(max_length=30), default=list)

class VariantFilter(EmbeddedDocument):
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

class ProductVariant(Document):
    product_id = IntField(required=True)
    category_id = IntField(required=True)
    name = StringField(unique=True)
    price = IntField()
    file_path = StringField(required=True)
    filters = DictField()
    current_stock = IntField(default=0)
    sold_stock = IntField(default=0)
    is_active = BooleanField(default=True)
    created_at = DateTimeField(default=datetime.datetime.utcnow)
    updated_at = DateTimeField(default=datetime.datetime.utcnow)

    extra_data = DynamicField()  
    
    meta = {
        "collection": "product_variants",
        "indexes": [
            "product_id", 
            "category_id",
            {"fields": ["$name", "$filters"], "default_language": "english"}
        ],
    }

    def save(self, *args, **kwargs):
        self.updated_at = datetime.datetime.utcnow()
        return super().save(*args, **kwargs)

    @classmethod
    def filter_by_search_str(cls, user_profile, query_string, skip, limit):
        if not query_string:
            return {
                "title": "No results found",
                "description": "",
                "variants": [],
            }

        variant_objs = cls.objects.filter(
            MongoQ(__raw__={"$text": {"$search": query_string}})
        ).order_by("-sold_stock").skip(skip).limit(limit)

        variants = []
        for variant in variant_objs:
            quantity = 0
            if user_profile:
                for item in user_profile.cart_items:
                    if item.variant_id == str(variant.id):
                        quantity = item.quantity
                        break

            variants.append(
                {
                    "id": str(variant.id),
                    "product_id": variant.product_id,
                    "category_id": variant.category_id,
                    "name": variant.name,
                    "slug": slugify(variant.name),
                    "price": variant.price,
                    "file_path": variant.file_path,
                    "filters": variant.filters,
                    "current_stock": variant.current_stock,
                    "sold_stock": variant.sold_stock,
                    "is_active": variant.is_active,
                    "created_at": variant.created_at,
                    "updated_at": variant.updated_at,
                    "extra_data": variant.extra_data,
                    "quantity": quantity,
                }
            )

        filters_dict = defaultdict(set)
        for variant in variant_objs:
            if variant.filters:
                for key, value in variant.filters.items():
                    filters_dict[key].add(value)

        filters_dict = {key: list(values) for key, values in filters_dict.items()}

        return {
            "title": f"Results for {query_string}",
            "description": "",
            "filters": filters_dict,
            "variants": variants,
        }

    @classmethod
    def filter_by_category_product(cls, user_profile, category_name, product_id, skip, limit):
        category = Category.objects.filter(name=category_name).first()
        product = Product.objects.filter(id=product_id).first()

        if not category or not product:
            return {
	            "title": "No results found",
	            "description": f"",
	            "variants": [],
	        }

        variant_objs = cls.objects.filter(
            MongoQ(category_id=int(category.id)) & MongoQ(product_id=int(product_id))
        ).order_by("-sold_stock").skip(skip).limit(limit)

        variants = []
        for variant in variant_objs:
            if not user_profile:
                quantity = 0
            else:
                for item in user_profile.cart_items:
                    if item.variant_id == str(variant.id):
                        quantity = item.quantity
                        break
                else:
                    quantity = 0
            variants.append(
                {
                    "id": str(variant.id),
                    "product_id": variant.product_id,
                    "category_id": variant.category_id,
                    "name": variant.name,
                    "slug": slugify(variant.name),
                    "price": variant.price,
                    "file_path": variant.file_path,
                    "filters": variant.filters,
                    "current_stock": variant.current_stock,
                    "sold_stock": variant.sold_stock,
                    "is_active": variant.is_active,
                    "created_at": variant.created_at,
                    "updated_at": variant.updated_at,
                    "extra_data": variant.extra_data,
                    "quantity": quantity
                }
            )

        filters_dict = defaultdict(set)
    
        for variant in variant_objs:
            if variant.filters:
                for key, value in variant.filters.items():
                    filters_dict[key].add(value)
        
        filters_dict = {key: list(values) for key, values in filters_dict.items()}

        result = {
            "title": category_name,
            "description": f"{product.name} ({product.description})",
            "filters": filters_dict,
            "variants": variants,
        }

        return result


    @classmethod
    def filter_by_featured_prod(cls, user_profile, featured_prod_id, skip, limit):
        featured_prod = FeaturedProductLine.objects.filter(id=featured_prod_id).first()

        if not featured_prod:
            return {
	            "title": "No results found",
	            "description": f"",
	            "variants": [],
	        }

        object_ids = []
        for variant_id in featured_prod.variants:
            try:
                object_ids.append(ObjectId(variant_id))
            except Exception:
                continue  

        variant_objs = list(cls.objects.filter(id__in=object_ids).order_by("-sold_stock").skip(skip).limit(limit)) if object_ids else []

        variants = []
        for variant in variant_objs:
            if not user_profile:
                quantity = 0
            else:
                for item in user_profile.cart_items:
                    if item.variant_id == str(variant.id):
                        quantity = item.quantity
                        break
                else:
                    quantity = 0
            variants.append(
                {
                    "id": str(variant.id),
                    "product_id": variant.product_id,
                    "category_id": variant.category_id,
                    "name": variant.name,
                    "slug": slugify(variant.name),
                    "price": variant.price,
                    "file_path": variant.file_path,
                    "filters": variant.filters,
                    "current_stock": variant.current_stock,
                    "sold_stock": variant.sold_stock,
                    "is_active": variant.is_active,
                    "created_at": variant.created_at,
                    "updated_at": variant.updated_at,
                    "extra_data": variant.extra_data,
                    "quantity": quantity
                }
            )

        filters_dict = defaultdict(set)
    
        for variant in variant_objs:
            if variant.filters:
                for key, value in variant.filters.items():
                    filters_dict[key].add(value)
        
        filters_dict = {key: list(values) for key, values in filters_dict.items()}


        result = {
            "title": featured_prod.title,
            "description": f"{featured_prod.description})",
            "filters": filters_dict,
            "variants": variants,
        }

        return result




@classmethod
def filter_by_search_str(cls, user_profile, query_string, skip, limit):
    if not query_string:
        return {
            "title": "No results found",
            "description": "",
            "variants": [],
        }

    variant_objs = cls.objects.filter(
        MongoQ(__raw__={"$text": {"$search": query_string}})
    ).order_by("-sold_stock").skip(skip).limit(limit)

    variants = []
    for variant in variant_objs:
        quantity = 0
        if user_profile:
            for item in user_profile.cart_items:
                if item.variant_id == str(variant.id):
                    quantity = item.quantity
                    break

        variants.append(
            {
                "id": str(variant.id),
                "product_id": variant.product_id,
                "category_id": variant.category_id,
                "name": variant.name,
                "slug": slugify(variant.name),
                "price": variant.price,
                "file_path": variant.file_path,
                "filters": variant.filters,
                "current_stock": variant.current_stock,
                "sold_stock": variant.sold_stock,
                "is_active": variant.is_active,
                "created_at": variant.created_at,
                "updated_at": variant.updated_at,
                "extra_data": variant.extra_data,
                "quantity": quantity,
            }
        )

    filters_dict = defaultdict(set)
    for variant in variant_objs:
        if variant.filters:
            for key, value in variant.filters.items():
                filters_dict[key].add(value)

    filters_dict = {key: list(values) for key, values in filters_dict.items()}

    return {
        "title": f"Results for {query_string}",
        "description": "",
        "filters": filters_dict,
        "variants": variants,
    }