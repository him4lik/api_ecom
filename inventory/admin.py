from django.contrib import admin
from .models import FeaturedProductLine, Product, Category, FilterSpecs, ProductVariant

admin.site.register(FeaturedProductLine)
admin.site.register(Product)
admin.site.register(Category)
admin.site.register(FilterSpecs)


# from .forms import ProductVariantForm  # Custom form

# class ProductVariantAdmin(admin.ModelAdmin):
#     form = ProductVariantForm
#     list_display = ("product_id", "category_id", "price", "file_path", "current_stock")  # Display fields
#     search_fields = ("product_id", "category_id")
#     list_filter = ("is_active",)

# # Manually register the model in Django admin
# admin.site.register(ProductVariant, ProductVariantAdmin)