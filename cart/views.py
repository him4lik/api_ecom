from rest_framework.permissions import AllowAny
from rest_framework.views import APIView
from rest_framework.response import Response
from .models import CartItem
from user.models import UserProfile
from inventory.models import ProductVariant
from rest_framework.status import HTTP_200_OK, HTTP_400_BAD_REQUEST
from rest_framework.permissions import IsAuthenticated
from django.db.models import Q
from django.core.exceptions import ObjectDoesNotExist
from django.contrib.auth.models import User
from django.utils.text import slugify
from lib.common import calculate_shipping

GST_PERC = 0.18

class AddToCartView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        variant_id = request.data.get("variant_id")
        action = request.data.get("action")
        if not user or not variant_id or action not in ["add", "remove"]:
            return Response({"error": "Invalid input data"}, status=HTTP_400_BAD_REQUEST)

        user_profile = UserProfile.objects.get(user=user)
        if not user_profile:
            return Response({"error": "User not found"}, status=HTTP_404_NOT_FOUND)

        variant = ProductVariant.objects.filter(id=variant_id).first() 
        if not variant:
            return Response({"error": "Product variant not found"}, status=HTTP_404_NOT_FOUND)
        existing_item = next((item for item in user_profile.cart_items.all() if item.variant.id == int(variant_id)), None)
        if action == "add":
            if existing_item:
                quantity = existing_item.quantity + 1 if existing_item.is_active else 1
                existing_item.quantity = existing_item.quantity+1 if existing_item.is_active else 1
                existing_item.is_active = True
                existing_item.save()
            else:
                cart_item = CartItem(
                    variant=variant,
                    quantity=1,
                )
                cart_item.save()
                user_profile.cart_items.add(cart_item)
                quantity = 1

        elif action == "remove":
            if existing_item and existing_item.quantity > 1:
                quantity = existing_item.quantity - 1
                existing_item.quantity -= 1
                existing_item.save()
            else:
                user_profile.cart_items.remove(*[item for item in user_profile.cart_items.all() if item.variant.id == int(variant_id)])
                quantity = 0
        if quantity:
            variant = ProductVariant.objects.get(id=variant_id)
            total_amt = quantity*variant.price
        else:
            total_amt = 0

        user_profile.save()

        cart_items = user_profile.cart_items.all()

        product_variants = ProductVariant.objects.filter(id__in=[cart_item.variant_id for cart_item in cart_items])

        subtotal = 0
        for item in cart_items:
            variant = ProductVariant.objects.get(id=item.variant.id)
            subtotal += variant.price * item.quantity

        return Response({"quantity": quantity, "subtotal":subtotal, "total_amt":total_amt, "success":True},status=HTTP_200_OK,)


class UserCartView(APIView):
    permission_classes = [IsAuthenticated] 

    def get(self, request):
        try:
            user = request.user
            user_profile = UserProfile.objects.filter(user_id=user.id).first()

            cart_items = user_profile.cart_items.filter(is_active=True)

            product_variants = ProductVariant.objects.filter(id__in=[cart_item.variant.id for cart_item in cart_items])

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
                        "file_path": f"http://localhost{variant.file_path.url}",
                        "filters": variant.filters,
                        "current_stock": variant.current_stock,
                        "sold_stock": variant.sold_stock,
                        "is_active": variant.is_active,
                        "created_at": variant.created_at,
                        "updated_at": variant.updated_at,
                        "quantity": item.quantity,
                        "total_amt":item.quantity*variant.price
                    })

            shipping = calculate_shipping(user.id)
            gst = round(GST_PERC*subtotal)
            response_data = {
                "username": user.username,
                "subtotal": subtotal,
                "gst":gst,
                "shipping":shipping,
                "total":subtotal+gst+shipping,
                "variants": variants,
            }

            return Response(response_data, status=200)

        except UserProfile.DoesNotExist:
            return Response({"error": "User profile not found"}, status=404)

