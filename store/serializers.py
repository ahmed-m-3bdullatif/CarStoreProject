from rest_framework import serializers
from django.core.exceptions import ValidationError
from .models import StoreSettings, Client, CarInventory, Repair, Sale
from datetime import date
from django.contrib.auth.models import User


# ==========================================
# 1. Store Settings Serializer
# ==========================================
class StoreSettingsSerializer(serializers.ModelSerializer):
    # Read-only field to display the string label of the enum (Manual/Automatic)
    stock_number_mode_display = serializers.CharField(source='get_stock_number_mode_display', read_only=True)

    class Meta:
        model = StoreSettings
        fields = ['id', 'name', 'address', 'stock_number_mode', 'stock_number_mode_display', 'stock_number_start_value']


# ==========================================
# 2. Repair Serializer
# ==========================================
class RepairSerializer(serializers.ModelSerializer):
    class Meta:
        model = Repair
        fields = ['id', 'car', 'name', 'price', 'date', 'notes']


# ==========================================
# 3. Client Serializer
# ==========================================
class ClientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Client
        fields = '__all__'

    def validate_license_expiration_date(self, value):
        if value and value < date.today():
            raise serializers.ValidationError("The license expiration date cannot be in the past.")
        return value

# ==========================================
# 4. Car Inventory Serializer
# ==========================================
class CarInventorySerializer(serializers.ModelSerializer):
    repairs = RepairSerializer(many=True, read_only=True)

    stock_number = serializers.CharField(required=False, allow_blank=True, allow_null=True)

    class Meta:
        model = CarInventory
        fields = ['id', 'stock_number', 'vin_number', 'year', 'make', 'model', 'in_stock', 'repairs']

    def validate(self, attrs):
        """
        Validates data and gracefully catches Model ValidationError
        to return a 400 Bad Request instead of a 500 Server Error.
        """
        config = StoreSettings.objects.get_or_create(pk=1)[0]
        stock_number = attrs.get('stock_number')

        # API-level check for Manual mode before reaching the Model
        if config.stock_number_mode == StoreSettings.StockNumberMode.MANUAL:
            if not stock_number or stock_number.strip() == "":
                raise serializers.ValidationError(
                    {"stock_number": "This field is required because the system numbering mode is set to Manual."}
                )
        return attrs

    def create(self, validated_data):
        """Catches any validation errors during actual model instantiation."""
        try:
            return super().create(validated_data)
        except ValidationError as e:
            raise serializers.ValidationError(
                e.message_dict if hasattr(e, 'message_dict') else e.messages
            )

    def update(self, instance, validated_data):
        """Catches any validation errors during actual model updates."""
        try:
            return super().update(instance, validated_data)
        except ValidationError as e:
            raise serializers.ValidationError(
                e.message_dict if hasattr(e, 'message_dict') else e.messages
            )


# ==========================================
# 5. Sale Serializer (For POST/PUT Operations)
# ==========================================
class SaleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Sale
        fields = ['id', 'car', 'client', 'price', 'date']

    def validate(self, attrs):
        """
        Triggers the model's clean() method to return business logic errors
        (e.g., expired license or already sold car) as a 400 Bad Request
        to the frontend, instead of causing a 500 Server Error.
        """
        # Create a temporary unsaved instance to run model-level validation
        instance = Sale(**attrs)
        try:
            instance.clean()
        except ValidationError as e:
            raise serializers.ValidationError(
                e.message_dict if hasattr(e, 'message_dict') else e.messages
            )
        return attrs


# ==========================================
# 6. Detailed Sale Serializer (For GET Operations Only)
# ==========================================
class SaleDetailSerializer(serializers.ModelSerializer):
    """Custom serializer to expand car and client details dynamically for invoice views."""
    car = CarInventorySerializer(read_only=True)
    client = ClientSerializer(read_only=True)

    class Meta:
        model = Sale
        fields = ['id', 'car', 'client', 'price', 'date']

# ==========================================
# 7. Register Serializer
# ==========================================
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
