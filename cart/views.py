from django.utils.text import slugify
from django.core.exceptions import ObjectDoesNotExist
from django.contrib.auth.models import User
from django.db.models import Q

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.status import HTTP_200_OK, HTTP_400_BAD_REQUEST, HTTP_404_NOT_FOUND

from .models import CartItem
from user.models import UserProfile
from inventory.models import ProductVariant
from lib.common import calculate_shipping


GST_PERC = 0.18


class AddToCartView(APIView):
    """Handles add/remove actions for user's cart."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        variant_id = request.data.get("variant_id")
        action = request.data.get("action")

        if not user or not variant_id or action not in ["add", "remove"]:
            return Response({"error": "Invalid input data"}, status=HTTP_400_BAD_REQUEST)

        user_profile = UserProfile.objects.filter(user=user).first()
        if not user_profile:
            return Response({"error": "User not found"}, status=HTTP_404_NOT_FOUND)

        variant = ProductVariant.objects.filter(id=variant_id).first()
        if not variant:
            return Response({"error": "Product variant not found"}, status=HTTP_404_NOT_FOUND)

        existing_item = next(
            (item for item in user_profile.cart_items.all() if item.variant.id == int(variant_id)),
            None,
        )

        if action == "add":
            if existing_item:
                existing_item.quantity = existing_item.quantity + 1 if existing_item.is_active else 1
                existing_item.is_active = True
                existing_item.save()
                quantity = existing_item.quantity
            else:
                cart_item = CartItem.objects.create(variant=variant, quantity=1)
                user_profile.cart_items.add(cart_item)
                quantity = 1

        elif action == "remove":
            if existing_item and existing_item.quantity > 1:
                existing_item.quantity -= 1
                existing_item.save()
                quantity = existing_item.quantity
            else:
                user_profile.cart_items.remove(
                    *[item for item in user_profile.cart_items.all() if item.variant.id == int(variant_id)]
                )
                quantity = 0

        total_amt = quantity * variant.price if quantity else 0
        user_profile.save()

        cart_items = user_profile.cart_items.all()

        subtotal = sum(
            ProductVariant.objects.get(id=item.variant.id).price * item.quantity
            for item in cart_items
        )

        return Response(
            {"quantity": quantity, "subtotal": subtotal, "total_amt": total_amt, "success": True},
            status=HTTP_200_OK,
        )


class UserCartView(APIView):
    """Fetches current user's active cart with pricing details."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        user_profile = UserProfile.objects.filter(user_id=user.id).first()

        if not user_profile:
            return Response({"error": "User profile not found"}, status=HTTP_404_NOT_FOUND)

        cart_items = user_profile.cart_items.filter(is_active=True)
        variants = []
        subtotal = 0

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
                    "file_path": f"http://localhost{variant.file_path.url}",
                    "filters": variant.filters,
                    "current_stock": variant.current_stock,
                    "sold_stock": variant.sold_stock,
                    "is_active": variant.is_active,
                    "created_at": variant.created_at,
                    "updated_at": variant.updated_at,
                    "quantity": item.quantity,
                    "total_amt": item.quantity * variant.price,
                }
            )

        shipping = calculate_shipping(user.id)
        gst = round(GST_PERC * subtotal)

        response_data = {
            "username": user.username,
            "subtotal": subtotal,
            "gst": gst,
            "shipping": shipping,
            "total": subtotal + gst + shipping,
            "variants": variants,
        }

        return Response(response_data, status=HTTP_200_OK)
