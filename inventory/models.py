from lib.base_classes import BaseModel
from django.db import models
from django.contrib.postgres.fields import ArrayField
import datetime
from django.db.models import Q
from collections import defaultdict
from django.utils.text import slugify
from django.contrib.auth.models import User
from django.db.models import JSONField 
from django.contrib.postgres.search import SearchVector, SearchQuery, SearchRank


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
		ids = [variant_id for variant_id in self.variants]
		return list(ProductVariant.objects.filter(id__in=ids))


class FilterSpecs(BaseModel):
	category = models.ForeignKey(Category, on_delete=models.CASCADE)
	product = models.ForeignKey(Product, on_delete=models.CASCADE)
	filter_tags = ArrayField(models.CharField(max_length=30), default=list)

class VariantFilter(BaseModel):  
    variant = models.ForeignKey(
        "ProductVariant",
        on_delete=models.CASCADE,
        related_name="variant_filters"
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="variant_filters"
    )
    quantity = models.PositiveIntegerField(default=1)

    def __str__(self):
        return f"{self.user} - {self.variant} (x{self.quantity})"

class ProductVariant(BaseModel):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="variants")
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name="variants")
    name = models.CharField(max_length=100, unique=True)
    price = models.IntegerField()
    file_path = models.FileField(upload_to="variants/")
    filters = JSONField(default=dict)  # replaces DictField
    current_stock = models.IntegerField(default=0)
    sold_stock = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    @classmethod
    def filter_by_search_str(cls, user_profile, query_string, skip, limit):
        if not query_string:
            return {
                "title": "No results found",
                "description": "",
                "variants": [],
            }

        search_vector = (
            SearchVector("name", weight="A") +
            SearchVector("filters", weight="B") +
            SearchVector("product__name", weight="A") +
            SearchVector("product__description", weight="B") +
            SearchVector("category__name", weight="A")
        )

        search_query = SearchQuery(query_string)

        variant_objs = cls.objects.annotate(rank=SearchRank(search_vector, search_query)).filter(rank__gte=0.1, is_active=True)
        total_count = variant_objs.count()
        variant_objs = variant_objs.order_by("-rank", "-sold_stock")[skip:skip+limit]

        variants = []
        for variant in variant_objs:
            quantity = 0
            if user_profile:
                for item in user_profile.cart_items.all():
                    if item.variant_id == str(variant.id):
                        quantity = item.quantity
                        break

            variants.append(
                {
                    "id": variant.id,
                    "product_id": variant.product.id,
                    "category_id": variant.category.id,
                    "name": variant.name,
                    "slug": slugify(variant.name),
                    "price": variant.price,
                    "file_path": f"http://localhost:8001{variant.file_path.url}",
                    "filters": variant.filters,
                    "current_stock": variant.current_stock,
                    "sold_stock": variant.sold_stock,
                    "is_active": variant.is_active,
                    "created_at": variant.created_at,
                    "updated_at": variant.updated_at,
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
            "total_count":total_count
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

        variant_objs = cls.objects.filter(product=product, category=category).order_by("-sold_stock")[skip:skip+limit]

        variants = []
        for variant in variant_objs:
            if not user_profile:
                quantity = 0
            else:
                for item in user_profile.cart_items.all():
                    if item.variant_id == str(variant.id):
                        quantity = item.quantity
                        break
                else:
                    quantity = 0
            variants.append(
                {
                    "id": variant.id,
                    "product_id": variant.product.id,
                    "category_id": variant.category.id,
                    "name": variant.name,
                    "slug": slugify(variant.name),
                    "price": variant.price,
                    "file_path": f"http://localhost:8001{variant.file_path.url}",
                    "filters": variant.filters,
                    "current_stock": variant.current_stock,
                    "sold_stock": variant.sold_stock,
                    "is_active": variant.is_active,
                    "created_at": variant.created_at,
                    "updated_at": variant.updated_at,
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
            "total_count":cls.objects.filter(product=product, category=category).count()
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

        ids = []
        for variant_id in featured_prod.variants:
            try:
                ids.append(variant_id)
            except Exception:
                continue  

        variant_objs = list(cls.objects.filter(id__in=ids).order_by("-sold_stock")[skip:skip+limit]) if ids else []

        variants = []
        for variant in variant_objs:
            if not user_profile:
                quantity = 0
            else:
                for item in user_profile.cart_items.all():
                    if item.variant_id == str(variant.id):
                        quantity = item.quantity
                        break
                else:
                    quantity = 0
            variants.append(
                {
                    "id": variant.id,
                    "product_id": variant.product.id,
                    "category_id": variant.category.id,
                    "name": variant.name,
                    "slug": slugify(variant.name),
                    "price": variant.price,
                    "file_path": f"http://localhost:8001{variant.file_path.url}",
                    "filters": variant.filters,
                    "current_stock": variant.current_stock,
                    "sold_stock": variant.sold_stock,
                    "is_active": variant.is_active,
                    "created_at": variant.created_at,
                    "updated_at": variant.updated_at,
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
            "total_count":cls.objects.filter(id__in=ids).count(),
        }

        return result



