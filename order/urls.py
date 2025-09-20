from django.urls import path
from . import views

urlpatterns = [
    path('', views.OrdersAPIView.as_view(), name='orders'),
    path('detail/', views.OrderDetailAPIView.as_view(), name='order-detail'),
    path('create-order/', views.CreateOrderView.as_view(), name='create-order')
]