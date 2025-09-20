from django.urls import path
from . import views

urlpatterns = [
    path('request-otp/', views.RequestOTPView.as_view(), name='request-otp'),
    path('verify-otp/', views.VerifyOTPView.as_view(), name='verify-otp'),
    path('authenticate/', views.AuthenticateView.as_view(), name='authenticate'),
    path('user-profile/', views.UserProfileView.as_view(), name='user-profile'),
]