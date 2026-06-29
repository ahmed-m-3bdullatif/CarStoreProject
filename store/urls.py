from rest_framework.routers import DefaultRouter
from .views import *
from django.urls import path, include
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)

# Initialize DRF router
router = DefaultRouter()

# Register ViewSets with URL prefixes
router.register(r'settings', StoreSettingsViewSet, basename='settings')
router.register(r'inventory', CarInventoryViewSet, basename='inventory')
router.register(r'clients', ClientViewSet, basename='clients')
router.register(r'repairs', RepairViewSet, basename='repairs')
router.register(r'sales', SaleViewSet, basename='sales')

# App URL patterns
urlpatterns = [
    path('auth/register/', RegisterView.as_view(), name='auth_register'),      # POST - new user
    path('auth/login/', TokenObtainPairView.as_view(), name='token_obtain_pair'),  # POST - JWT login
    path('auth/refresh/', TokenRefreshView.as_view(), name='token_refresh'),       # POST - refresh JWT
    path('', include(router.urls)),  # All CRUD endpoints from ViewSets
]
