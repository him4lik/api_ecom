from collections import defaultdict
from django.db import models
from django.utils.text import slugify
from django.contrib.auth.models import User
from django.contrib.postgres.fields import ArrayField
from django.contrib.postgres.search import SearchVector, SearchQuery, SearchRank
from django.db.models import JSONField

from lib.base_classes import BaseModel


class Category(BaseModel):
    """Represents product categories."""
    name = models.CharField(max_length=20)

    class Meta:
        verbose_name_plural = "Categories"

    def __str__(self):
        return self.name


class Product(BaseModel):
    """Represents a product that belongs to one or more categories."""
    name = models.CharField(max_length=100, unique=True)
    description = models.CharField(max_length=255)
    categories = models.ManyToManyField(Category)

    def __str__(self):
        return self.name


class FeaturedProductLine(BaseModel):
    """Represents a line of featured products with variants and images."""
    title = models.CharField(max_length=50, unique=True)
    description = models.CharField(max_length=255)
    images = ArrayField(models.FileField(upload_to="product_line/"), blank=True, default=list)
    is_active = models.BooleanField(default=True)
    variants = ArrayField(models.CharField(max_length=24), blank=True, default=list)
    is_primary = models.BooleanField(default=False)

    def __str__(self):
        return self.title

    def get_variants(self):
        """Return all variants linked to this featured product line."""
        return list(ProductVariant.objects.filter(id__in=self.variants))


class FilterSpecs(BaseModel):
    """Represents filter tags for a product within a category."""
    category = models.ForeignKey(Category, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    filter_tags = ArrayField(models.CharField(max_length=30), default=list)


class VariantFilter(BaseModel):
    """Represents a user's filter choice for a product variant."""
    variant = models.ForeignKey(
        "ProductVariant",
        on_delete=models.CASCADE,
        related_name="variant_filters",
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="variant_filters",
    )
    quantity = models.PositiveIntegerField(default=1)

    def __str__(self):
        return f"{self.user} - {self.variant} (x{self.quantity})"


class ProductVariant(BaseModel):
    """Represents a specific variant of a product (e.g., size, color)."""
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="variants")
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name="variants")
    name = models.CharField(max_length=100, unique=True)
    price = models.IntegerField()
    file_path = models.FileField(upload_to="variants/")
    filters = JSONField(default=dict)
    current_stock = models.IntegerField(default=0)
    sold_stock = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    # ---------------------------
    # Classmethods for Filtering
    # ---------------------------

    @classmethod
    def filter_by_search_str(cls, user_profile, query_string, skip, limit):
        """Search product variants by free text query across multiple fields."""
        if not query_string:
            return {"title": "No results found", "description": "", "variants": []}

        search_vector = (
            SearchVector("name", weight="A")
            + SearchVector("filters", weight="B")
            + SearchVector("product__name", weight="A")
            + SearchVector("product__description", weight="B")
            + SearchVector("category__name", weight="A")
        )
        search_query = SearchQuery(query_string)

        variant_objs = (
            cls.objects.annotate(rank=SearchRank(search_vector, search_query))
            .filter(rank__gte=0.1, is_active=True)
            .order_by("-rank", "-sold_stock")[skip : skip + limit]
        )
        total_count = variant_objs.count()

        variants = variants_data(user_profile, variant_objs)
        filters_dict = filters_data(variant_objs)

        return {
            "title": f"Results for {query_string}",
            "description": "",
            "filters": filters_dict,
            "variants": variants,
            "total_count": total_count,
        }

    @classmethod
    def filter_by_category_product(cls, user_profile, category_name, product_id, skip, limit):
        """Fetch variants belonging to a specific category and product."""
        category = Category.objects.filter(name=category_name).first()
        product = Product.objects.filter(id=product_id).first()

        if not category or not product:
            return {"title": "No results found", "description": "", "variants": []}

        variant_objs = (
            cls.objects.filter(product=product, category=category)
            .order_by("-sold_stock")[skip : skip + limit]
        )
        variants = variants_data(user_profile, variant_objs)
        filters_dict = filters_data(variant_objs)

        return {
            "title": category_name,
            "description": f"{product.name} ({product.description})",
            "filters": filters_dict,
            "variants": variants,
            "total_count": cls.objects.filter(product=product, category=category).count(),
        }

    @classmethod
    def filter_by_featured_prod(cls, user_profile, featured_prod_id, skip, limit):
        """Fetch variants linked to a featured product line."""
        featured_prod = FeaturedProductLine.objects.filter(id=featured_prod_id).first()
        if not featured_prod:
            return {"title": "No results found", "description": "", "variants": []}

        ids = [variant_id for variant_id in featured_prod.variants if variant_id]
        variant_objs = (
            cls.objects.filter(id__in=ids).order_by("-sold_stock")[skip : skip + limit] if ids else []
        )

        variants = variants_data(user_profile, variant_objs)
        filters_dict = filters_data(variant_objs)

        return {
            "title": featured_prod.title,
            "description": featured_prod.description,
            "filters": filters_dict,
            "variants": variants,
            "total_count": cls.objects.filter(id__in=ids).count(),
        }

def variants_data(user_profile, variant_objs):
    """Helper to build consistent variant response payloads."""
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
    return variants

def filters_data(variant_objs):
    """Helper to extract distinct filters from variants."""
    filters_dict = defaultdict(set)
    for variant in variant_objs:
        if variant.filters:
            for key, value in variant.filters.items():
                filters_dict[key].add(value)
    return {key: list(values) for key, values in filters_dict.items()}
