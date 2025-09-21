from django.contrib.auth.models import User
from django.core.cache import cache
from rest_framework.response import Response
from rest_framework.views import APIView
import random
from rest_framework_simplejwt.tokens import RefreshToken, AccessToken
from django_ratelimit.decorators import ratelimit
from django.utils.decorators import method_decorator
from rest_framework.permissions import AllowAny
from .models import UserProfile, UserAddress
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from datetime import date, datetime
import json

def get_or_create_user(username):
    user, _ = User.objects.get_or_create(username=username)

    profile, _ = UserProfile.objects.get_or_create(user=user)
    return user


class RequestOTPView(APIView):
    permission_classes = [AllowAny]

    @method_decorator(ratelimit(key='ip', rate='3/m', method='POST'))
    def post(self, request):
        username = request.data.get('username')
        otp = str(random.randint(100000, 999999))
        cache.set(f"otp_{username}", otp, timeout=3000)  # Store OTP in cache for 5 minutes
        print(otp)
        
        # TODO - send otp via SMS

        return Response({"message": "OTP sent successfully"})

class VerifyOTPView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        username = request.data.get('username')
        otp = request.data.get('otp')

        stored_otp = cache.get(f"otp_{username}")
        if stored_otp is None or stored_otp != otp:
            return Response({"error": "Invalid or expired OTP"}, status=400)

        user = get_or_create_user(username)

        refresh = RefreshToken.for_user(user)
        cache.delete(f"otp_{username}")

        return Response({
            "access": str(refresh.access_token),
            "refresh": str(refresh)
        })


class AuthenticateView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        access_token = request.headers.get("Authorization")
        refresh_token = request.data.get("refresh_token")

        if access_token:
            access_token = access_token.replace("Bearer ", "").strip()
            user_info = self.validate_access_token(access_token)
            if user_info:
                return Response({"user": user_info}, status=status.HTTP_200_OK)

        if refresh_token:
            new_access_token = self.refresh_access_token(refresh_token).get('access_token', None)
            if not new_access_token:
                return Response({"error": "Invalid refresh token. Please log in again."}, status=status.HTTP_401_UNAUTHORIZED)

            user_info = self.validate_access_token(new_access_token)
            if user_info:
                return Response({"user": user_info, "access_token": new_access_token}, status=status.HTTP_200_OK)

        return Response({"error": "Invalid refresh token. Please log in again."}, status=status.HTTP_401_UNAUTHORIZED)

    def validate_access_token(self, token):
        try:
            token = AccessToken(token)  
            user_id = token["user_id"]
            user = User.objects.get(id=user_id)
            return {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "is_authenticated": True,
            }
        except Exception as e:  
            return None

    def refresh_access_token(self, refresh_token):
        token = RefreshToken(refresh_token)
        user_id = token["user_id"]
        user = User.objects.get(id=user_id)
        new_access_token = str(token.access_token)

        return {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "is_authenticated": True,
            "access_token": new_access_token  
        }

class UserProfileView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):        
        user = request.user
        user_profile = UserProfile.objects.get(user=user)
        profile_data = {
            "user_id": user_profile.user.id,
            "name": user_profile.name,
            "email": user_profile.email,
            "is_active": user_profile.is_active,
            "addresses": [
                {
                    "address_type": address.address_type,
                    "poc_name":address.poc_name,
                    "phone":address.phone,
                    "line_1": address.line_1,
                    "line_2": address.line_2,
                    "city": address.city,
                    "state": address.state,
                    "pin": address.pin,
                    "landmark": address.landmark
                } for address in user_profile.useraddress_set.all()
            ],
            "created_at": user_profile.created_at.isoformat(),
            "updated_at": user_profile.updated_at.isoformat(),
            "whitelisted": user_profile.whitelisted,
            "blacklisted": user_profile.blacklisted,
            "dob":user_profile.dob.strftime("%Y-%m-%d"),
        }
        
        return Response(profile_data, status=status.HTTP_200_OK)
        
    def post(self, request):
        user = request.user
        data = request.data.copy()
        user_profile = UserProfile.objects.get(user=user)
        if data.get('name', ''):
            user_profile.name = data['name']
        if data.get('email', ''):
            user_profile.email = data['email']
        if data.get('dob', ''):
            user_profile.dob = datetime.strptime(data['dob'], "%Y-%m-%d").date()
        user_profile.save()
        if 'address' in data:
            address = data.get('address', {})
            data_dict = {
                "profile":user.profile,
                "address_type": address.get('type', ''),
                "poc_name":address.get('name', ''),
                "phone":address.get('phone', ''),
                "line_1":address.get('line1', ''),
                "line_2":address.get('line2', ''),
                "city":address.get('city', ''),
                "state":address.get('state', ''),
                "pin":address.get('pin', ''),
                "landmark":address.get('landmark', ''),
            }
            profile = UserProfile.objects.filter(user=user, useraddress__phone=data_dict['phone']).first()
            if not profile:
                address = UserAddress(**data_dict)
                profile = UserProfile.objects.filter(user=user).first()
                address.save()
            else:
                profile = UserProfile.objects(user_id=user.id).first()
                for address in profile.addresses:
                    if address.phone == data_dict['phone']:
                        for key, value in data_dict.items():
                            setattr(address, key, value)
                        break
            profile.save()
        if data.get('action', '') == 'delete':
            phone = data.get('phone', '')
            user_profile = UserProfile.objects(user_id=user.id).first()
            
            if user_profile:
                for address in user_profile.addresses:
                    if address.phone == phone:
                        user_profile.addresses.remove(address)
                        user_profile.save()
                        break
            
        return Response({}, status=status.HTTP_200_OK)

