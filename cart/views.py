from rest_framework.permissions import AllowAny
from rest_framework.views import APIView
from rest_framework.response import Response
from .models import CartItem
from user.models import UserProfile
from inventory.models import ProductVariant
from rest_framework.status import HTTP_200_OK, HTTP_400_BAD_REQUEST
from rest_framework.permissions import IsAuthenticated
from django.db.models import Q
from mongoengine.queryset.visitor import Q as MongoQ
from bson import ObjectId
from django.core.exceptions import ObjectDoesNotExist
from django.contrib.auth.models import User
from django.utils.text import slugify


class AddToCartView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user_id = request.user.id
        variant_id = request.data.get("variant_id")
        action = request.data.get("action")

        if not user_id or not variant_id or action not in ["add", "remove"]:
            return Response({"error": "Invalid input data"}, status=HTTP_400_BAD_REQUEST)

        user_profile = UserProfile.objects(user_id=user_id).first()
        if not user_profile:
            return Response({"error": "User not found"}, status=HTTP_404_NOT_FOUND)

        if not ProductVariant.objects(id=ObjectId(variant_id)).first():
            return Response({"error": "Product variant not found"}, status=HTTP_404_NOT_FOUND)

        existing_item = next((item for item in user_profile.cart_items if item.variant_id == variant_id), None)
        if action == "add":
            if existing_item:
                quantity = existing_item.quantity + 1
                existing_item.quantity += 1
            else:
                cart_item = CartItem(
                    variant_id=variant_id,
                    user_id=int(user_id),
                    quantity=1,
                )
                user_profile.cart_items.append(cart_item)
                quantity = 1

        elif action == "remove":
            if existing_item and existing_item.quantity > 1:
                quantity = existing_item.quantity - 1
                existing_item.quantity -= 1
            else:
                user_profile.cart_items = [item for item in user_profile.cart_items if item.variant_id != variant_id]
                quantity = 0

        user_profile.save()

        cart_items = user_profile.cart_items

        product_variants = ProductVariant.objects.filter(id__in=[cart_item.variant_id for cart_item in user_profile.cart_items])

        subtotal = 0
        for item in cart_items:
            variant = ProductVariant.objects.get(id=item.variant_id)
            subtotal += variant.price * item.quantity

        return Response({"quantity": quantity, "subtotal":subtotal, "success":True},status=HTTP_200_OK,)


class UserCartView(APIView):
    permission_classes = [IsAuthenticated] 

    def get(self, request):
        try:
            user = request.user
            user_profile = UserProfile.objects.filter(user_id=user.id).first()

            cart_items = user_profile.cart_items

            product_variants = ProductVariant.objects.filter(id__in=[cart_item.variant_id for cart_item in user_profile.cart_items])

            subtotal = 0
            variants = []
            for item in cart_items:
                variant = ProductVariant.objects.get(id=item.variant_id)
                subtotal += variant.price * item.quantity
                variants.append(
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
                        "quantity": item.quantity
                    })

            response_data = {
                "username": user.username,
                "subtotal": subtotal,
                "variants": variants,
            }

            return Response(response_data, status=200)

        except UserProfile.DoesNotExist:
            return Response({"error": "User profile not found"}, status=404)

