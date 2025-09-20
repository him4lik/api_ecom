from django.contrib import admin
from .models import FeaturedProductLine, Product, Category, FilterSpecs, VariantFilter, ProductVariant
from .models import ProductVariant

# Register Django ORM models with regular admin
admin.site.register(FeaturedProductLine)
admin.site.register(Product)
admin.site.register(Category)
admin.site.register(FilterSpecs)
admin.site.register(VariantFilter)
admin.site.register(ProductVariant)