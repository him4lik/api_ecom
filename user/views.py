from django.contrib.auth.models import User
from django.core.cache import cache
from rest_framework.response import Response
from rest_framework.views import APIView
import random
from rest_framework_simplejwt.tokens import RefreshToken, AccessToken
from django_ratelimit.decorators import ratelimit
from django.utils.decorators import method_decorator
from rest_framework.permissions import AllowAny
from .models import UserProfile
from rest_framework.permissions import IsAuthenticated
from rest_framework import status


def get_or_create_user(username):
    user, _ = User.objects.get_or_create(username=username)

    profile = UserProfile(user_id=user.id)
    profile.save()
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

        return Response({"message": "OTP sent successfully", "otp":otp})

class VerifyOTPView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        username = request.data.get('username')
        otp = request.data.get('otp')

        print(username, otp, type(otp))
        stored_otp = cache.get(f"otp_{username}")
        print(stored_otp)
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
        print('////////////')
        access_token = request.headers.get("Authorization")
        refresh_token = request.data.get("refresh_token")
        print(access_token, refresh_token)

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
                "is_authenticated": True
            }
        except Exception as e:  
            return None

    def refresh_access_token(self, refresh_token):
        try:
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
        except Exception as e:  
            return None