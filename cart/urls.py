from django.urls import path
from . import views

urlpatterns = [
    path('', views.UserCartView.as_view(), name='user-cart'),
    path('add-to-cart/', views.AddToCartView.as_view(), name='add-to-cart'),
]