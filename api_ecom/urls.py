
from django.contrib import admin
from django.urls import path, include
from .settings import PATH_PREFIX, DEBUG, MEDIA_URL, MEDIA_ROOT

urlpatterns = [
    path(PATH_PREFIX + 'admin/', admin.site.urls),
    path(PATH_PREFIX + 'inventory/', include('inventory.urls')),
    path(PATH_PREFIX + 'order/', include('order.urls')),
    path(PATH_PREFIX + 'payment/', include('payment.urls')),
    path(PATH_PREFIX + 'user/', include('user.urls')),
    path(PATH_PREFIX + 'cart/', include('cart.urls')),
]

if DEBUG:
    from django.conf.urls.static import static
    urlpatterns += static(MEDIA_URL, document_root=MEDIA_ROOT)