from django.urls import path
from . import views

urlpatterns = [
    path('categories/', views.ProductCategoriesView.as_view(), name='categories'),
    path('popular/', views.PopularVariantsView.as_view(), name='popular_products'),
    path('featured/', views.FeaturedProductLineView.as_view(), name='featured'),
    path('filter/', views.FilterVariantsView.as_view(), name='filter'),
    path('details/', views.VariantDetailsView.as_view(), name='detail'),
]