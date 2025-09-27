from django.contrib.auth.models import User
from django.core.cache import cache
from django.utils.decorators import method_decorator
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken, AccessToken
from django_ratelimit.decorators import ratelimit

import random
from datetime import datetime

from .models import UserProfile, UserAddress


def get_or_create_user(username):
    user, _ = User.objects.get_or_create(username=username)
    UserProfile.objects.get_or_create(user=user)
    return user


class RequestOTPView(APIView):
    """
    Handles OTP request. Generates a random OTP, stores it in cache,
    and (TODO) should be sent to the user via SMS.
    """
    permission_classes = [AllowAny]

    @method_decorator(ratelimit(key='ip', rate='3/m', method='POST'))
    def post(self, request):
        username = request.data.get('username')
        if not username:
            return Response({"error": "Username is required"}, status=400)

        otp = str(random.randint(100000, 999999))
        cache.set(f"otp_{username}", otp, timeout=300)  # expires in 5 minutes

        # TODO: integrate with SMS/email service provider
        print(f"Generated OTP for {username}: {otp}")

        return Response({"message": "OTP sent successfully"})


class VerifyOTPView(APIView):
    """
    Verifies the OTP. If valid, generates and returns JWT tokens.
    """
    permission_classes = [AllowAny]

    def post(self, request):
        username = request.data.get('username')
        otp = request.data.get('otp')

        stored_otp = cache.get(f"otp_{username}")
        if not stored_otp or stored_otp != otp:
            return Response({"error": "Invalid or expired OTP"}, status=400)

        user = get_or_create_user(username)

        refresh = RefreshToken.for_user(user)
        cache.delete(f"otp_{username}")  # cleanup

        return Response({
            "access": str(refresh.access_token),
            "refresh": str(refresh),
        })

class AuthenticateView(APIView):
    """
    Validates JWT access tokens or refreshes them when expired.
    """
    permission_classes = [AllowAny]

    def post(self, request):
        access_token = request.headers.get("Authorization", "").replace("Bearer ", "").strip()
        refresh_token = request.data.get("refresh_token")

        if access_token:
            user_info = self.validate_access_token(access_token)
            if user_info:
                return Response({"user": user_info}, status=200)

        if refresh_token:
            refreshed = self.refresh_access_token(refresh_token)
            if refreshed:
                return Response({"user": refreshed, "access_token": refreshed["access_token"]}, status=200)

        return Response({"error": "Invalid or expired tokens. Please log in again."}, status=401)

    def validate_access_token(self, token: str):
        try:
            token_obj = AccessToken(token)
            user = User.objects.get(id=token_obj["user_id"])
            return self.get_user_info(user)
        except Exception:
            return None

    def refresh_access_token(self, refresh_token: str):
        try:
            refresh = RefreshToken(refresh_token)
            user = User.objects.get(id=refresh["user_id"])
            new_access_token = str(refresh.access_token)

            user_info = self.get_user_info(user)
            user_info["access_token"] = new_access_token
            return user_info
        except Exception:
            return None

    def get_user_info(self, user: User) -> dict:
        return {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "is_authenticated": True,
        }

class UserProfileView(APIView):
    """
    Handles fetching and updating user profile details,
    along with adding, updating, and deleting addresses.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        user_profile = UserProfile.objects.get(user=user)

        profile_data = {
            "user_id": user_profile.user.id,
            "name": user_profile.name,
            "email": user_profile.email,
            "is_active": user_profile.is_active,
            "dob": user_profile.dob.strftime("%Y-%m-%d") if user_profile.dob else None,
            "whitelisted": user_profile.whitelisted,
            "blacklisted": user_profile.blacklisted,
            "created_at": user_profile.created_at.isoformat(),
            "updated_at": user_profile.updated_at.isoformat(),
            "addresses": [
                {
                    "address_type": addr.address_type,
                    "poc_name": addr.poc_name,
                    "phone": addr.phone,
                    "line_1": addr.line_1,
                    "line_2": addr.line_2,
                    "city": addr.city,
                    "state": addr.state,
                    "pin": addr.pin,
                    "landmark": addr.landmark,
                }
                for addr in user_profile.useraddress_set.all()
            ],
        }

        return Response(profile_data, status=200)

    def post(self, request):
        user = request.user
        data = request.data.copy()
        profile = UserProfile.objects.get(user=user)

        if "name" in data:
            profile.name = data["name"]
        if "email" in data:
            profile.email = data["email"]
        if "dob" in data:
            profile.dob = datetime.strptime(data["dob"], "%Y-%m-%d").date()
        profile.save()

        if "address" in data:
            address_data = data["address"]

            existing_address = UserAddress.objects.filter(profile=profile, phone=address_data.get("phone")).first()
            if existing_address:
                for field, value in address_data.items():
                    setattr(existing_address, field, value)
                existing_address.save()
            else:
                UserAddress.objects.create(
                    profile=profile,
                    address_type=address_data.get('type', ''),
                    poc_name=address_data.get('name', ''),
                    phone=address_data.get('phone', ''),
                    line_1=address_data.get('line1', ''),
                    line_2=address_data.get('line2', ''),
                    city=address_data.get('city', ''),
                    state=address_data.get('state', ''),
                    pin=address_data.get('pin', ''),
                    landmark=address_data.get('landmark', '')
                    )

        if data.get("action") == "delete":
            phone = data.get("phone")
            UserAddress.objects.filter(profile=profile, phone=phone).delete()

        return Response({"message": "Profile updated successfully"}, status=200)
