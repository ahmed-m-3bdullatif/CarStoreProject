import io

from django.db import transaction
from django.core.exceptions import ObjectDoesNotExist
from django.http import FileResponse
from django.contrib.auth.models import User


from num2words import num2words
from pypdf import PdfReader, PdfWriter
from pypdf.generic import NameObject, NumberObject
from reportlab.pdfgen import canvas as rl_canvas

from rest_framework import viewsets, status, filters, generics
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError as DRFValidationError
from rest_framework.response import Response
from rest_framework.permissions import AllowAny

from .models import StoreSettings, Client, CarInventory, Repair, Sale
from .serializers import (
    StoreSettingsSerializer,
    ClientSerializer,
    CarInventorySerializer,
    RepairSerializer,
    SaleSerializer,
    SaleDetailSerializer,
    RegisterSerializer
)


# ==================== 1. Store Settings ====================
class StoreSettingsViewSet(viewsets.GenericViewSet):
    """Endpoints for System Settings & Configuration"""
    queryset = StoreSettings.objects.filter(pk=1)
    serializer_class = StoreSettingsSerializer

    def get_object(self):
        obj, created = StoreSettings.objects.get_or_create(pk=1)
        return obj

    @action(detail=False, methods=['get'], url_path='get_stock_mode')
    def get_stock_mode(self, request):
        """Get current stock numbering mode (Manual/Automatic)"""
        config = self.get_object()
        return Response({
            "stock_number_mode": config.stock_number_mode,
            "stock_number_mode_display": config.get_stock_number_mode_display()
        }, status=status.HTTP_200_OK)

    @action(detail=False, methods=['put'], url_path='update_settings')
    def update_settings(self, request):
        """Update store name, address, and stock config"""
        config = self.get_object()
        serializer = self.get_serializer(config, data=request.data, partial=False)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# ==================== 2. Car Inventory ====================
class CarInventoryViewSet(viewsets.ModelViewSet):
    """Endpoints for Cars with Built-in Search functionality"""
    queryset = CarInventory.objects.all().order_by('-id')
    serializer_class = CarInventorySerializer

    filter_backends = [filters.SearchFilter]
    search_fields = ['vin_number', 'make', 'model']

    @action(detail=False, methods=['get'], url_path='get_last_stock')
    def get_last_stock(self, request):
        """Get the highest stock number from inventory"""
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
        """Get all cars currently in stock (not sold)"""
        available_cars = CarInventory.objects.filter(in_stock=True).order_by('-id')
        serializer = self.get_serializer(available_cars, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


# ==================== 3. Clients ====================
class ClientViewSet(viewsets.ModelViewSet):
    """Endpoints for Clients with Search functionality"""
    queryset = Client.objects.all().order_by('-id')
    serializer_class = ClientSerializer

    filter_backends = [filters.SearchFilter]
    search_fields = ['first_name', 'last_name', 'license_number']


# ==================== 4. Repairs ====================
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


# ==================== 5. Sales ====================
class SaleViewSet(viewsets.ModelViewSet):
    """Sales with auto stock management"""
    queryset = Sale.objects.all()
    serializer_class = SaleSerializer

    def perform_create(self, serializer):
        with transaction.atomic():
            car_id = self.request.data.get('car')
            try:
                car = CarInventory.objects.get(pk=car_id)
                if not car.in_stock:
                    raise DRFValidationError({"car": "This car has already been sold."})
            except CarInventory.DoesNotExist:
                raise DRFValidationError({"car": "Invalid car ID provided."})

            sale = serializer.save()
            car.in_stock = False
            car.save()

    def perform_update(self, serializer):
        with transaction.atomic():
            instance = serializer.instance

            try:
                old_car = instance.car
            except ObjectDoesNotExist:
                old_car = None

            updated_instance = serializer.save()

            try:
                new_car = updated_instance.car
            except ObjectDoesNotExist:
                new_car = None

            if old_car != new_car:
                if old_car:
                    old_car.in_stock = True
                    old_car.save()

                if new_car:
                    new_car.in_stock = False
                    new_car.save()

    def perform_destroy(self, instance):
        with transaction.atomic():
            car = getattr(instance, 'car', None)
            if car:
                car.in_stock = True
                car.save()

            instance.delete()

    @action(detail=True, methods=['get'], url_path='download_fillable_pdf')
    def download_fillable_pdf(self, request, pk=None):
        """Generate and download a fillable PDF invoice for a sale"""
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

            # Build reportlab overlay with filled values, then remove form fields
            page = writer.pages[0]
            mbox = page.get("/MediaBox")
            page_w = float(mbox[2])
            page_h = float(mbox[3])
            overlay_buf = io.BytesIO()
            c = rl_canvas.Canvas(overlay_buf, pagesize=(page_w, page_h))

            for annot_ref in page.get("/Annots"):
                annot = annot_ref.get_object()
                rect = annot.get("/Rect", [0, 0, 0, 0])
                ft = annot.get("/FT", "")
                value = annot.get("/V", None)
                if ft == "/Sig" or not value or str(value).strip() == "":
                    continue
                llx, lly, _, _ = [float(x) for x in rect]
                c.setFont("Helvetica", 9)
                c.drawString(llx + 2, lly + 4, str(value))

            c.showPage()
            c.save()
            overlay_buf.seek(0)

            reader_overlay = PdfReader(overlay_buf)
            page.merge_page(reader_overlay.pages[0], over=True)

            writer.remove_annotations(subtypes="/Widget")
            if "/AcroForm" in writer.root_object:
                del writer.root_object["/AcroForm"]

            buffer = io.BytesIO()
            writer.write(buffer)
            buffer.seek(0)

            return FileResponse(
                buffer,
                as_attachment=True,
                filename=f"Bill_Of_Sale_{sale.client.first_name}_{sale.client.last_name}.pdf",
                content_type='application/pdf'
            )

        except FileNotFoundError:
            return Response({"error": "PDF Template file not found on server."},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# ==================== 6. Auth - Registration ====================
class RegisterView(generics.CreateAPIView):
    """User registration endpoint (public)"""
    queryset = User.objects.all()
    permission_classes = (AllowAny,)
    serializer_class = RegisterSerializer
