from rest_framework.permissions import AllowAny
from rest_framework.views import APIView
from rest_framework.response import Response
from .models import Category, Product, FilterSpecs, ProductVariant, FeaturedProductLine
from rest_framework import status
from django.db.models import Q
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.utils.text import slugify
from user.models import UserProfile


class ProductCategoriesView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        categories = Category.objects.prefetch_related('product_set')
        data = {i.name:[{"id":j.id, "name":j.name, "desc":j.description} for j in i.product_set.all()] for i in categories}
        return Response(data,  status=200)


class PopularVariantsView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        limit = int(request.GET.get("limit", 8))
        variants = ProductVariant.objects.filter(is_active=True).order_by("-sold_stock")[:limit]

        user = request.user
        user_profile = UserProfile.objects(user_id=user_id).first() if user.is_authenticated else None

        data = [
            {
                "product_id": variant.product_id,
                "category_id": variant.category_id,
                "price": variant.price,
                "file_path": variant.file_path,
                "filters": variant.filters,
                "current_stock": variant.current_stock,
                "sold_stock": variant.sold_stock,
                "is_active": variant.is_active,
                "created_at": variant.created_at,
                "updated_at": variant.updated_at,
                "extra_data": variant.extra_data,
                "quantity": any(item.variant_id == str(variant.id) for item in user_profile.cart_items) if user.is_authenticated and user_profile else 0
            }
            for variant in variants
        ]

        return Response({"top_selling_variants": data}, status=200)



class FeaturedProductLineView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        limit = int(request.GET.get("limit", 10))
        try:
            featured_products = FeaturedProductLine.objects.filter(is_active=True)

            if not featured_products.exists():
                return Response({"featured_products":[]}, status=200)

            primary_products = []
            secondary_products = []
            for product in featured_products:
                variants = list(ProductVariant.objects.filter(id__in=product.variants).order_by("-sold_stock")[:limit])

                user = request.user
                user_profile = UserProfile.objects.get(user=user) if user.is_authenticated else None
                

                variant_data = []
                for variant in variants:
                    if not user_profile:
                        quantity = 0
                    else:
                        for item in user_profile.cart_items.filter(is_active=True):
                            if item.variant == variant:
                                quantity = item.quantity
                                break
                        else:
                            quantity = 0
                    variant_data.append(
                        {
                            "id": variant.id,
                            "product_id": variant.product.id,
                            "category_id": variant.category.id,
                            "price": variant.price,
                            "name": variant.name,
                            "slug": slugify(variant.name),
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
                images_urls = [
                    image for image in product.images
                ]
                data = {
                    "id": product.id,
                    "title": product.title,
                    "description": product.description,
                    "images": images_urls,
                    "is_active": product.is_active,
                    "variants": variant_data
                }

                if product.is_primary:
                    primary_products.append(data)
                else:
                    secondary_products.append(data)

            return Response({"primary_products": primary_products, "secondary_products": secondary_products}, status=200)

        except ObjectDoesNotExist:
            return Response({"error": "Featured products not found."}, status=404)


class FilterVariantsView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        category_name = request.GET.get("category", None)
        product_id = request.GET.get("product_id", None)
        search_str = request.GET.get("search_str", "").strip()
        featured_prod_id = request.GET.get("featured_prod_id", None) 
        skip = int(request.GET.get("skip", 0))
        limit = int(request.GET.get("limit", 8))

        user = request.user
        user_profile = UserProfile.objects.get(user=user) if user.is_authenticated else None

        result = {}

        if category_name and product_id:
            result = ProductVariant.filter_by_category_product(user_profile, category_name, int(product_id), skip, limit)
            result['category'] = category_name
            result['product_id'] = product_id
        elif search_str:
            result = ProductVariant.filter_by_search_str(user_profile, search_str, skip, limit)
            result['search_str'] = search_str
        elif featured_prod_id:
            result = ProductVariant.filter_by_featured_prod(user_profile, featured_prod_id, skip, limit)
            result['featured_prod_id'] = featured_prod_id
        else:
            return Response(
                {"error": "No filter parameters provided"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        result['pagination'] = {
            'total': result['total_count'],
            'limit': limit,
            'skip': skip,
            'has_more': (skip + limit) < result['total_count']
        }

        return Response(result, status=status.HTTP_200_OK)

class VariantDetailsView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        variant_slug = request.GET.get("variant_slug", None)
        user = request.user
        user_profile = UserProfile.objects.filter(user=user).first() if user.is_authenticated else None
        try:
            if not variant_slug:
                return Response({"error": "Variant slug is required"}, status=status.HTTP_400_BAD_REQUEST)

            variant_name = variant_slug.replace("-", " ")

            variant = ProductVariant.objects.get(name__iexact=variant_name)

            if not user_profile:
                quantity = 0
            else:
                for item in user_profile.cart_items.filter(is_active=True):
                    if item.variant.id == variant.id:
                        quantity = item.quantity
                        break
                else:
                    quantity = 0

            variant_data = {
                "id": variant.id,
                "product_id": variant.product.id,
                "category_id": variant.category.id,
                "name": variant.name,
                "price": variant.price,
                "file_path": f"http://localhost:8001{variant.file_path.url}",
                "filters": variant.filters,
                "current_stock": variant.current_stock,
                "sold_stock": variant.sold_stock,
                "is_active": variant.is_active,
                "created_at": variant.created_at.isoformat(),
                "updated_at": variant.updated_at.isoformat(),
                "quantity": quantity
            }
            return Response(variant_data, status=status.HTTP_200_OK)

        except ProductVariant.DoesNotExist:
            return Response({"error": "Product variant not found"}, status=status.HTTP_404_NOT_FOUND)

        except ValidationError:
            return Response({"error": "Invalid ID format"}, status=status.HTTP_400_BAD_REQUEST)
