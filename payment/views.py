from django.shortcuts import render
from django.contrib.auth.models import User
from rest_framework.response import Response
from rest_framework.views import APIView
from user.models import UserProfile
from order.models import Order

class MakePaymentView(APIView):

    def post(self, request):
        user = request.user
        user_profile = UserProfile.objects.filter(user=user).first()
        order_id = request.POST.get('razorpay_order_id')
        payment_id = request.POST.get('razorpay_payment_id')
        signature = request.POST.get('razorpay_signature')
        order = Order.objects.filter(rzp_order_id=order_id).first()
        order.rzp_payment_id = payment_id
        order.rzp_callback_order_id = order_id
        order.rzp_signature = signature
        order.is_paid = True
        order.save()

        return Response({"success":True})