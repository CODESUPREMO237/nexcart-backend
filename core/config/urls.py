# Location: core\config\urls.py
"""
NexCart URL Configuration
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from .views import api_health

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # Health check
    path('api/health/', api_health, name='api-health'),
    
    # API endpoints
    path('api/users/', include('apps.users.urls')),
    path('api/', include('apps.products.urls')),
    path('api/', include('apps.orders.urls')),
    path('api/', include('apps.payments.urls')),
   # The free tier (512MB RAM) is insufficient for sklearn/scipy. You need:
   # path('api/', include('apps.recommendations.urls')),

    # New feature apps
    path('api/', include('apps.vendors.urls')),
    path('api/', include('apps.chat.urls')),
    path('api/', include('apps.delivery.urls')),
    path('api/', include('apps.coupons.urls')),
    path('api/', include('apps.analytics.urls')),
]

# Serve static files in development
# Media files are served by Cloudinary, not locally
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    
    # Django Debug Toolbar URLs
    try:
        import debug_toolbar
        urlpatterns = [
            path('__debug__/', include('debug_toolbar.urls')),
        ] + urlpatterns
    except ImportError:
        pass
