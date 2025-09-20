from django.urls import path
from . import views

urlpatterns = [
    path('pay/', views.MakePaymentView.as_view(), name='make-payment'),
]