import io

from django.db import transaction
from django.http import FileResponse

from num2words import num2words
from pypdf import PdfReader, PdfWriter
from pypdf.generic import NameObject, NumberObject

from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError as DRFValidationError
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
# 1. Store Settings ViewZone
# ==========================================
class StoreSettingsViewSet(viewsets.GenericViewSet):
    """Endpoints for System Settings & Configuration"""
    queryset = StoreSettings.objects.filter(pk=1)
    serializer_class = StoreSettingsSerializer

    def get_object(self):
        obj, created = StoreSettings.objects.get_or_create(pk=1)
        return obj

    @action(detail=False, methods=['get'], url_path='get_stock_mode')
    def get_stock_mode(self, request):
        config = self.get_object()
        return Response({
            "stock_number_mode": config.stock_number_mode,
            "stock_number_mode_display": config.get_stock_number_mode_display()
        }, status=status.HTTP_200_OK)

    @action(detail=False, methods=['put'], url_path='update_settings')
    def update_settings(self, request):
        config = self.get_object()
        serializer = self.get_serializer(config, data=request.data, partial=False)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# ==========================================
# 2. Car Inventory ViewZone (Updated with Search)
# ==========================================
class CarInventoryViewSet(viewsets.ModelViewSet):
    """Endpoints for Cars with Built-in Search functionality"""
    queryset = CarInventory.objects.all().order_by('-id')
    serializer_class = CarInventorySerializer

    filter_backends = [filters.SearchFilter]
    search_fields = ['vin_number', 'make', 'model']

    @action(detail=False, methods=['get'], url_path='get_last_stock')
    def get_last_stock(self, request):
        all_stocks = CarInventory.objects.exclude(stock_number__isnull=True).exclude(stock_number="")
        db_highest_stock = 0
        for car in all_stocks:
            if car.stock_number.isdigit():
                db_highest_stock = max(db_highest_stock, int(car.stock_number))

        if db_highest_stock > 0:
            return Response({"last_stock_number": str(db_highest_stock)}, status=status.HTTP_200_OK)
        return Response({"last_stock_number": None, "message": "No numerical stock cars found."},
                        status=status.HTTP_200_OK)

    @action(detail=False, methods=['get'], url_path='get_available')
    def get_available(self, request):
        available_cars = CarInventory.objects.filter(in_stock=True).order_by('-id')
        serializer = self.get_serializer(available_cars, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


# ==========================================
# 3. Client ViewZone (Updated with Search)
# ==========================================
class ClientViewSet(viewsets.ModelViewSet):
    """Endpoints for Clients with Search functionality"""
    queryset = Client.objects.all().order_by('-id')
    serializer_class = ClientSerializer

    filter_backends = [filters.SearchFilter]
    search_fields = ['first_name', 'last_name', 'license_number']


# ==========================================
# 4. Repair ViewZone
# ==========================================
class RepairViewSet(viewsets.ModelViewSet):
    """Endpoints for Car Repairs with Car Filter"""
    queryset = Repair.objects.all().order_by('-date')
    serializer_class = RepairSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        car_id = self.request.query_params.get('car_id', None)
        if car_id is not None:
            queryset = queryset.filter(car_id=car_id)
        return queryset


# ==========================================
# 5. Sale ViewZone (Updated with Car/Client Filter & Auto-Sold Logic)
# ==========================================
class SaleViewSet(viewsets.ModelViewSet):
    """Endpoints for Sales Transactions with Filters and Auto-stock Update"""
    queryset = Sale.objects.all().order_by('-date')

    def get_queryset(self):
        queryset = super().get_queryset()
        car_id = self.request.query_params.get('car_id', None)
        client_id = self.request.query_params.get('client_id', None)

        if car_id is not None:
            queryset = queryset.filter(car_id=car_id)
        if client_id is not None:
            queryset = queryset.filter(client_id=client_id)

        return queryset

    def get_serializer_class(self):
        if self.action in ['list', 'retrieve']:
            return SaleDetailSerializer
        return SaleSerializer

    def perform_create(self, serializer):
        with transaction.atomic():
            car_id = self.request.data.get('car')
            try:
                car = CarInventory.objects.get(pk=car_id)
                if not car.in_stock:
                    raise DRFValidationError({"car": "This car has already been sold and is no longer available."})
            except CarInventory.DoesNotExist:
                raise DRFValidationError({"car": "Invalid car ID provided."})

            sale = serializer.save()
            car.in_stock = False
            car.save()

    @action(detail=True, methods=['get'], url_path='download_fillable_pdf')
    def download_fillable_pdf(self, request, pk=None):
        try:
            sale = self.get_object()
            settings = StoreSettings.objects.get_or_create(pk=1)[0]
        except Sale.DoesNotExist:
            return Response({"error": "Sale record not found."}, status=status.HTTP_404_NOT_FOUND)

        template_path = "templates/invoice_template.pdf"

        try:
            reader = PdfReader(template_path)
            writer = PdfWriter()
            writer.append(reader)

            price_in_words = num2words(int(sale.price), lang='en').capitalize()

            form_data = {
                'Date': sale.date.strftime('%Y-%m-%d'),
                'I the undersigned seller name': settings.name,
                'undersigned buyer name': f"{sale.client.first_name} {sale.client.last_name}",
                'Make': sale.car.make,
                'Model': sale.car.model,
                'Year': str(sale.car.year),
                'VIN Number': sale.car.vin_number,
                'Mileage': 'N/A',
                'Sellers name print': settings.name,
                'Buyers name print': f"{sale.client.first_name} {sale.client.last_name}",
                'undefined': f"{sale.price:,.2f}",
                'undefined_2': price_in_words,
            }

            writer.update_page_form_field_values(writer.pages[0], form_data)

            for field in writer.get_fields().values():
                if '/Ff' in field:
                    field.update({
                        NameObject("/Ff"): NumberObject(field['/Ff'] | 1)
                    })

            buffer = io.BytesIO()
            writer.write(buffer)
            buffer.seek(0)

            return FileResponse(
                buffer,
                as_attachment=True,
                filename=f"Bill_Of_Sale_{sale.id}.pdf",
                content_type='application/pdf'
            )

        except FileNotFoundError:
            return Response({"error": "PDF Template file not found on server."},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)