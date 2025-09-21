from django.contrib.auth.models import User
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken, AccessToken
from rest_framework.permissions import IsAuthenticated
from rest_framework import status

from django.http import JsonResponse
from django.views import View
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET
import json
from .models import Order, SoldProduct
from inventory.models import ProductVariant
from django.utils.text import slugify
from cart.views import GST_PERC
from user.models import UserProfile
from lib.common import calculate_shipping
import razorpay
from api_ecom.settings import RZP_KEY_ID, RZP_SECRET_KEY

def serialize_address(address):
    if not address:
        return {}
    return {
        "address_type": address.address_type,
        "poc_name": address.poc_name,
        "phone": address.phone,
        "line_1": address.line_1,
        "line_2": address.line_2,
        "city": address.city,
        "state": address.state,
        "pin": address.pin,
        "landmark": address.landmark,
    }

class OrdersAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            user = request.user
            order_id = request.GET.get('order_id')
            status = request.GET.get('status')
            limit = int(request.GET.get('limit', 10))
            offset = int(request.GET.get('offset', 0))
            if not limit:
                limit = 10
            if not offset:
                offset = 0
            
            query_filters = {'is_active': True}
            
            if user:
                query_filters['user'] = user
            
            if order_id:
                query_filters['id'] = order_id
            
            if status:
                query_filters['status'] = status
            
            orders = Order.objects.filter(**query_filters).order_by('-created_at')[offset:offset + limit]
            
            orders_data = []
            for order in orders:
                order_data = {
                    'receipt_id': str(order.id),
                    'order_id':order.rzp_order_id,
                    'is_paid': order.is_paid,
                    'user_id': order.user_id,
                    'cost': order.cost,
                    'gst': order.gst,
                    'shipping':order.shipping,
                    'total_cost': order.cost+order.gst+order.shipping,
                    'status': order.status,
                    'created_at': order.created_at.isoformat(),
                    'updated_at': order.updated_at.isoformat(),
                    'total_quantity':sum(sold_product.quantity for sold_product in order.soldproduct_set.all()),
                    'sold_products':[],
                    'address': serialize_address(order.shipping_address)               }
                
                for sold_product in order.soldproduct_set.all():
                    variant = ProductVariant.objects.filter(id=sold_product.variant.id).first()
                    product_data = {
                        'variant_id': sold_product.variant_id,
                        'individual_cost': sold_product.individual_cost,
                        'total_cost': sold_product.total_cost,
                        'quantity': sold_product.quantity,
                        'product_name':variant.name,
                        'file_path':f"http://localhost{variant.file_path.url}",
                        'slug': slugify(variant.name),
                    }
                    order_data['sold_products'].append(product_data)
                
                orders_data.append(order_data)
            
            total_count = Order.objects.filter(**query_filters).count()
            
            response_data = {
                'success': True,
                'orders': orders_data,
                'pagination': {
                    'total': total_count,
                    'limit': limit,
                    'offset': offset,
                    'has_more': (offset + limit) < total_count
                }
            }
            
            return Response(response_data, status=200)
            
        except ValueError:
            return JsonResponse({
                'success': False,
                'error': 'Invalid parameter format'
            }, status=400)
            
class OrderDetailAPIView(APIView):
    
    def get(self, request):
        rzp_order_id = request.GET.get("order_id")
        order = Order.objects.filter(rzp_order_id = rzp_order_id).first()
        
        if not order:
            return JsonResponse({
                'success': False,
                'error': 'Order not found'
            }, status=404)
        user_profile = UserProfile.objects.filter(user=order.user).first()
        user = request.user
        order_data = {
            'order_id': str(order.id),
            'user_id': order.user_id,
            'name': user_profile.name,
            'email':user_profile.email,
            'phone':user.username,
            'cost': order.cost,
            'gst': order.gst,
            'status': order.status,
            'created_at': order.created_at.isoformat(),
            'updated_at': order.updated_at.isoformat(),
            'sold_products': []
        }
        
        for sold_product in order.soldproduct_set.all():
            product_data = {
                'variant_id': sold_product.variant_id,
                'individual_cost': sold_product.individual_cost,
                'total_cost': sold_product.total_cost,
                'quantity': sold_product.quantity
            }
            order_data['sold_products'].append(product_data)
        
        return JsonResponse({
            'success': True,
            'order': order_data
        }, status=200)
            
class CreateOrderView(APIView):

    def post(self, request):
        user = request.user
        user_profile, _ = UserProfile.objects.get_or_create(user=user)
        sold_products = []
        phone = request.POST.get('phone', None)
        if not phone:
            raise Exception('Shipping address not found')
        if not user_profile.cart_items:
            raise Exception('Cart is empty')

        for addr in user_profile.useraddress_set.all():
            if addr.phone == phone:
                shipping_address = addr
                break
        else:
            raise Exception('Shipping address not found')

        total_cost = sum([ item.variant.price*item.quantity for item in user_profile.cart_items.all() ])
        shipping = calculate_shipping(user)
        order = Order(
            user=user,
            cost=total_cost,
            gst=total_cost*GST_PERC,
            shipping=shipping,
            shipping_address=shipping_address,
            status="Processing",
        )

        order.save()

        for item in user_profile.cart_items.all():
            product = ProductVariant.objects.filter(id=item.variant.id).first()
            sold_product = SoldProduct(
                variant=item.variant,
                individual_cost=product.price,
                total_cost=product.price*item.quantity,
                quantity=item.quantity,
                order=order
            )
            sold_product.save()
            item.is_active = False
            item.save()
        
        client = razorpay.Client(auth=(RZP_KEY_ID, RZP_SECRET_KEY))

        resp = client.order.create({
          "amount": int(total_cost+total_cost*GST_PERC+shipping)*100,
          "currency": "INR",
          "receipt": str(order.id),
        })  

        order.rzp_order_id = resp.get('id')
        order.save()

        return Response({"order_id":resp.get('id')})