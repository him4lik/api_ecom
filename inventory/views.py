from rest_framework.permissions import AllowAny
from rest_framework.views import APIView
from rest_framework.response import Response
from .models import Category, Product, FilterSpecs, ProductVariant, FeaturedProductLine
from rest_framework import status
from django.db.models import Q
from mongoengine.queryset.visitor import Q as MongoQ
from bson import ObjectId
from django.core.exceptions import ObjectDoesNotExist
from django.utils.text import slugify
from user.models import UserProfile
from mongoengine.errors import DoesNotExist, ValidationError


class ProductCategoriesView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        categories = Category.objects.prefetch_related('product_set')
        data = {i.name:[{"id":j.id, "name":j.name, "desc":j.description} for j in i.product_set.all()] for i in categories}
        return Response(data)


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
                object_ids = []
                for variant_id in product.variants:
                    try:
                        object_ids.append(ObjectId(variant_id))
                    except Exception:
                        continue  
                variants = list(ProductVariant.objects.filter(id__in=object_ids).order_by("-sold_stock").limit(limit)) if object_ids else []

                user = request.user
                user_profile = UserProfile.objects(user_id=user.id).first() if user.is_authenticated else None
                

                variant_data = []
                for variant in variants:
                    if not user_profile:
                        quantity = 0
                    else:
                        for item in user_profile.cart_items:
                            if item.variant_id == str(variant.id):
                                quantity = item.quantity
                                break
                        else:
                            quantity = 0
                    variant_data.append(
                        {
                            "id": str(variant.id),
                            "product_id": variant.product_id,
                            "category_id": variant.category_id,
                            "price": variant.price,
                            "name": variant.name,
                            "slug": slugify(variant.name),
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

                data = {
                    "id": product.id,
                    "title": product.title,
                    "description": product.description,
                    "images": product.images,
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
        skip = request.GET.get("skip", 0)
        limit = request.GET.get("limit", 8)
        skip = int(skip) if skip else 0
        limit = int(limit) if limit else 8

        user = request.user
        user_profile = UserProfile.objects(user_id=user.id).first() if user.is_authenticated else None

        result = []

        if category_name and product_id:
            result = ProductVariant.filter_by_category_product(user_profile, category_name, int(product_id), skip, limit)
        elif search_str:
            result = ProductVariant.filter_by_search_str(user_profile, search_str, skip, limit)
        elif featured_prod_id:
            result = ProductVariant.filter_by_featured_prod(user_profile, featured_prod_id, skip, limit)
        else:
            return Response(
                {"error": "No filter parameters provided"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(result, status=status.HTTP_200_OK)

class VariantDetailsView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        variant_slug = request.GET.get("variant_slug", None)
        user = request.user
        user_profile = UserProfile.objects(user_id=user.id).first() if user.is_authenticated else None
        print(variant_slug)
        try:
            if not variant_slug:
                return Response({"error": "Variant slug is required"}, status=status.HTTP_400_BAD_REQUEST)

            variant_name = variant_slug.replace("-", " ")

            variant = ProductVariant.objects.get(name__iexact=variant_name)

            if not user_profile:
                quantity = 0
            else:
                for item in user_profile.cart_items:
                    if item.variant_id == str(variant.id):
                        quantity = item.quantity
                        break
                else:
                    quantity = 0

            variant_data = {
                "id": str(variant.id),
                "product_id": variant.product_id,
                "category_id": variant.category_id,
                "name": variant.name,
                "price": variant.price,
                "file_path": variant.file_path,
                "filters": variant.filters,
                "current_stock": variant.current_stock,
                "sold_stock": variant.sold_stock,
                "is_active": variant.is_active,
                "created_at": variant.created_at.isoformat(),
                "updated_at": variant.updated_at.isoformat(),
                "extra_data": variant.extra_data,
                "quantity": quantity
            }
            return Response(variant_data, status=status.HTTP_200_OK)

        except DoesNotExist:
            return Response({"error": "Product variant not found"}, status=status.HTTP_404_NOT_FOUND)

        except ValidationError:
            return Response({"error": "Invalid ID format"}, status=status.HTTP_400_BAD_REQUEST)
