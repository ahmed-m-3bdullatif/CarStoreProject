from rest_framework import serializers
from django.core.exceptions import ValidationError, ObjectDoesNotExist
from .models import *
from datetime import date
from django.contrib.auth.models import User


# ==================== 1. Store Settings ====================

class StoreSettingsSerializer(serializers.ModelSerializer):
    stock_number_mode_display = serializers.CharField(source='get_stock_number_mode_display', read_only=True)

    class Meta:
        model = StoreSettings
        fields = ['id', 'name', 'address', 'stock_number_mode', 'stock_number_mode_display', 'stock_number_start_value']


# ==================== 2. Repairs ====================

class RepairSerializer(serializers.ModelSerializer):
    class Meta:
        model = Repair
        fields = ['id', 'car', 'name', 'price', 'date', 'notes']


# ==================== 3. Clients ====================

class ClientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Client
        fields = '__all__'

    def validate_license_expiration_date(self, value):
        if value and value < date.today():
            raise serializers.ValidationError("The license expiration date cannot be in the past.")
        return value


# ==================== 4. Car Inventory ====================

class CarInventorySerializer(serializers.ModelSerializer):
    repairs = RepairSerializer(many=True, read_only=True)
    stock_number = serializers.CharField(required=False, allow_blank=True, allow_null=True)

    class Meta:
        model = CarInventory
        fields = ['id', 'stock_number', 'vin_number', 'year', 'make', 'model', 'in_stock', 'repairs']

    def validate(self, attrs):
        config = StoreSettings.objects.get_or_create(pk=1)[0]
        stock_number = attrs.get('stock_number')

        if config.stock_number_mode == StoreSettings.StockNumberMode.MANUAL:
            if not stock_number or stock_number.strip() == "":
                raise serializers.ValidationError(
                    {"stock_number": "This field is required because the system numbering mode is set to Manual."}
                )
        return attrs

    def create(self, validated_data):
        try:
            return super().create(validated_data)
        except ValidationError as e:
            raise serializers.ValidationError(
                e.message_dict if hasattr(e, 'message_dict') else e.messages
            )

    def update(self, instance, validated_data):
        try:
            return super().update(instance, validated_data)
        except ValidationError as e:
            raise serializers.ValidationError(
                e.message_dict if hasattr(e, 'message_dict') else e.messages
            )


# ==================== 5. Sale (Write) ====================

class SaleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Sale
        fields = '__all__'

    def validate(self, attrs):
        car = attrs.get('car')
        if car:
            if not car.in_stock:
                try:
                    if self.instance and self.instance.car == car:
                        return attrs
                except ObjectDoesNotExist:
                    pass
                raise serializers.ValidationError({"car": "This car is already sold."})
        return attrs


# ==================== 6. Sale Detail (Read-Only) ====================

class SaleDetailSerializer(serializers.ModelSerializer):
    """Expands car and client details for invoice views"""
    car = CarInventorySerializer(read_only=True)
    client = ClientSerializer(read_only=True)

    class Meta:
        model = Sale
        fields = ['id', 'car', 'client', 'price', 'date']


# ==================== 7. Auth - Register ====================

class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ('username', 'password', 'email', 'first_name', 'last_name')

    def create(self, validated_data):
        user = User.objects.create_user(
            username=validated_data['username'],
            password=validated_data['password'],
            email=validated_data.get('email', ''),
            first_name=validated_data.get('first_name', ''),
            last_name=validated_data.get('last_name', '')
        )
        return user
