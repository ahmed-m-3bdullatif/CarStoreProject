from django.contrib import admin
from django.urls import path, include
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

# Root URL configuration
urlpatterns = [
    path('admin/', admin.site.urls),                    # Django admin panel
    path('api/', include('store.urls')),                # CarStore API endpoints
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),      # OpenAPI schema
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema')),  # Swagger UI docs
]
