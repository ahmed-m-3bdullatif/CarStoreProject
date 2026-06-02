from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import StoreSettings, Client, CarInventory, Repair, Sale
from .serializers import (
    StoreSettingsSerializer,
    ClientSerializer,
    CarInventorySerializer,
    RepairSerializer,
    SaleSerializer,
    SaleDetailSerializer
)

# ==========================================
# 1. Store Settings ViewZone (Updated)
# ==========================================
class StoreSettingsViewSet(viewsets.GenericViewSet):
    """
    Endpoints for System Settings & Configuration
    """
    queryset = StoreSettings.objects.filter(pk=1)
    serializer_class = StoreSettingsSerializer

    def get_object(self):
        obj, created = StoreSettings.objects.get_or_create(pk=1)
        return obj

    # 1. Endpoint: Get stock_number_type -> GET /api/settings/get_stock_mode/
    @action(detail=False, methods=['get'], url_path='get_stock_mode')
    def get_stock_mode(self, request):
        config = self.get_object()
        return Response({
            "stock_number_mode": config.stock_number_mode,
            "stock_number_mode_display": config.get_stock_number_mode_display()
        }, status=status.HTTP_200_OK)

    # 2. Endpoint: Update ALL Settings columns -> PUT /api/settings/update_settings/
    @action(detail=False, methods=['put'], url_path='update_settings')
    def update_settings(self, request):
        config = self.get_object()
        # هنا السيريالايزر هياخد القيم الجديدة لكل الأعمدة ويعدلها في الـ Database
        serializer = self.get_serializer(config, data=request.data, partial=False)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# ==========================================
# 2. Car Inventory ViewZone
# ==========================================
class CarInventoryViewSet(viewsets.ModelViewSet):
    """
    Endpoints for Cars:
    - CRUD Operations: GET (List/Retrieve), POST (Add), PUT (Update), DELETE (Delete)
    - Custom Features: Get last stock number, Get all available cars
    """
    queryset = CarInventory.objects.all().order_by('-id')
    serializer_class = CarInventorySerializer

    # 3. Endpoint: Get last stock_number -> GET /api/inventory/get_last_stock/
    @action(detail=False, methods=['get'], url_path='get_last_stock')
    def get_last_stock(self, request):
        last_car = CarInventory.objects.exclude(stock_number__isnull=True).exclude(stock_number="").order_by('-id').first()
        if last_car:
            return Response({"last_stock_number": last_car.stock_number}, status=status.HTTP_200_OK)
        return Response({"last_stock_number": None, "message": "No cars found in inventory yet."}, status=status.HTTP_200_OK)

    # 4. Endpoint: Get all available cars for sale -> GET /api/inventory/get_available/
    @action(detail=False, methods=['get'], url_path='get_available')
    def get_available(self, request):
        available_cars = CarInventory.objects.filter(in_stock=True).order_by('-id')
        serializer = self.get_serializer(available_cars, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


# ==========================================
# 3. Client (User) ViewZone
# ==========================================
class ClientViewSet(viewsets.ModelViewSet):
    """
    Endpoints for Clients (Users):
    - CRUD Operations: GET (List/Retrieve), POST (Add), PUT (Update), DELETE (Delete)
    """
    queryset = Client.objects.all().order_by('-id')
    serializer_class = ClientSerializer


# ==========================================
# 4. Repair ViewZone (Updated with Car Filtering)
# ==========================================
class RepairViewSet(viewsets.ModelViewSet):
    """
    Endpoints for Car Repairs:
    - CRUD Operations: GET (List/Retrieve), POST (Add), PUT (Update), DELETE (Delete)
    - Filtering: GET /api/repairs/?car_id=<id> (Get repairs for a specific car)
    """
    queryset = Repair.objects.all().order_by('-date')
    serializer_class = RepairSerializer

    def get_queryset(self):
        """
        Dynamically filters repairs if 'car_id' is provided in the query parameters.
        """
        queryset = super().get_queryset()
        car_id = self.request.query_params.get('car_id', None)

        if car_id is not None:
            queryset = queryset.filter(car_id=car_id)

        return queryset


# ==========================================
# 5. Sale ViewZone
# ==========================================
class SaleViewSet(viewsets.ModelViewSet):
    """
    Endpoints for Sales Transactions:
    - CRUD Operations: GET (List/Retrieve), POST (Add), PUT (Update), DELETE (Delete)
    """
    queryset = Sale.objects.all().order_by('-date')

    def get_serializer_class(self):
        """Dynamically switches serializers between write (POST/PUT) and read (GET) actions."""
        if self.action in ['list', 'retrieve']:
            return SaleDetailSerializer
        return SaleSerializer