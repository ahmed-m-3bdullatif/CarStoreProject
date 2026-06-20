from rest_framework.routers import DefaultRouter
from .views import *
from django.urls import path, include
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)
# Initialize the DRF router
router = DefaultRouter()

# Register the ViewSets with their respective URL prefixes
router.register(r'settings', StoreSettingsViewSet, basename='settings')
router.register(r'inventory', CarInventoryViewSet, basename='inventory')
router.register(r'clients', ClientViewSet, basename='clients')
router.register(r'repairs', RepairViewSet, basename='repairs')
router.register(r'sales', SaleViewSet, basename='sales')

# URL Patterns for the app
urlpatterns = [
    path('auth/register/', RegisterView.as_view(), name='auth_register'),
    path('auth/login/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('auth/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('', include(router.urls)),
]