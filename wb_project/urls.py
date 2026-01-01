from django.contrib import admin
from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from core.views import (
    webapp_catalog, 
    create_order_api, 
    get_cart_api, 
    update_cart_api, 
    save_payment_details_api
)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('webapp/', webapp_catalog, name='webapp'),
    
    # API endpoints
    path('api/create-order/', create_order_api, name='create_order'),
    path('api/get-cart/', get_cart_api, name='get_cart'),
    path('api/update-cart/', update_cart_api, name='update_cart'),
    path('api/save-details/', save_payment_details_api, name='save_details'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)