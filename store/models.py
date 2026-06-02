from django.db import models
from django.core.exceptions import ValidationError
import datetime



# Validators & Normalizers


def validate_not_future_date(value):
    """Ensures the date is not in the future."""
    if value > datetime.date.today():
        raise ValidationError("The date cannot be in the future!")


def validate_client_age(value):
    """Ensures the client is at least 18 years old."""
    today = datetime.date.today()
    age = today.year - value.year - ((today.month, today.day) < (value.month, value.day))
    if age < 18:
        raise ValidationError("The client must be at least 18 years old.")


def validate_vin(value):
    """Validates the standard 17-character VIN."""
    vin_clean = value.upper().strip()
    if len(vin_clean) != 17:
        raise ValidationError("The VIN number must be exactly 17 characters long.")
    if any(char in vin_clean for char in ['I', 'O', 'Q']):
        raise ValidationError("The VIN number cannot contain the characters I, O, or Q to avoid confusion.")


def validate_car_year(value):
    """Validates that the car's manufacturing year makes sense."""
    current_year = datetime.date.today().year
    if value > current_year + 1:
        raise ValidationError(f"Invalid manufacturing year! It cannot exceed the year {current_year + 1}.")
    if value < 1886:
        raise ValidationError("The manufacturing year cannot be before the invention of the first car (1886)!")


def validate_positive_price(value):
    """Ensures that the price entered is Positive."""
    if value <= 0:
        raise ValidationError("The price must be greater than zero!")


# Database Models


# noinspection PyTypeChecker
class StoreSettings(models.Model):
    """Store Profile and System Configuration """

    class StockNumberMode(models.IntegerChoices):
        MANUAL = 1, 'Manual'
        AUTO = 2, 'Automatic'

    name = models.CharField(max_length=255, default="My Car Showroom")
    address = models.TextField(blank=True, null=True)

    stock_number_mode = models.IntegerField(
        choices=StockNumberMode.choices,
        default=StockNumberMode.MANUAL
    )
    stock_number_start_value = models.PositiveIntegerField(default=1000)

    def save(self, *args, **kwargs):
        if self.stock_number_start_value < 1:
            raise ValidationError("The starting value for stock number must be 1 or greater.")
        self.pk = 1  # Enforces that only one row can exist in the database for settings
        super(StoreSettings, self).save(*args, **kwargs)

    def __str__(self):
        return self.name


class Client(models.Model):
    """Client Profile Records"""
    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50)
    license_number = models.CharField(max_length=30, unique=True)
    license_expiration_date = models.DateField()
    date_of_birth = models.DateField(validators=[validate_client_age])

    def clean(self):
        """Checks if the driving license is valid upon registration."""
        if self.license_expiration_date and self.license_expiration_date < datetime.date.today():
            raise ValidationError(
                {"license_expiration_date": "Cannot register a client with an expired driving license!"})

    def save(self, *args, **kwargs):
        self.full_clean()  # Forces full model validation before saving
        super(Client, self).save(*args, **kwargs)

    def __str__(self):
        return f"{self.first_name} {self.last_name}"


class CarInventory(models.Model):
    """Car Showroom Stock and Inventory"""
    stock_number = models.CharField(max_length=50, unique=True, blank=True, null=True)
    vin_number = models.CharField(max_length=17, unique=True, validators=[validate_vin])
    year = models.PositiveIntegerField(validators=[validate_car_year])
    make = models.CharField(max_length=50)
    model = models.CharField(max_length=50)
    in_stock = models.BooleanField(default=True)

    def save(self, *args, **kwargs):
        self.vin_number = self.vin_number.upper().strip()

        config, created = StoreSettings.objects.get_or_create(pk=1)

        if config.stock_number_mode == StoreSettings.StockNumberMode.AUTO:
            if not self.pk:
                all_stocks = CarInventory.objects.exclude(stock_number__isnull=True).exclude(stock_number="")

                db_highest_stock = 0
                for car in all_stocks:
                    if car.stock_number.isdigit():
                        db_highest_stock = max(db_highest_stock, int(car.stock_number))

                start_value = config.stock_number_start_value

                if db_highest_stock == 0:
                    self.stock_number = str(start_value + 1)
                else:
                    next_stock_value = max(db_highest_stock, start_value)
                    self.stock_number = str(next_stock_value + 1)
        else:
            if not self.stock_number or self.stock_number.strip() == "":
                raise ValidationError(
                    {"stock_number": "The stock number field is required when numbering mode is set to Manual."})

        self.full_clean()
        super(CarInventory, self).save(*args, **kwargs)

    def __str__(self):
        return f"{self.make} {self.model} ({self.year}) - Stock: {self.stock_number}"


class Repair(models.Model):
    """Car Repairs and Service Logs"""
    car = models.ForeignKey(CarInventory, on_delete=models.CASCADE, related_name='repairs')
    name = models.CharField(max_length=255)
    price = models.DecimalField(max_digits=10, decimal_places=2, validators=[validate_positive_price])
    date = models.DateField(validators=[validate_not_future_date])
    notes = models.TextField(blank=True, null=True)

    def save(self, *args, **kwargs):
        self.full_clean()
        super(Repair, self).save(*args, **kwargs)

    def __str__(self):
        return f"Repair: {self.name} for Car Stock: {self.car.stock_number}"


class Sale(models.Model):
    """Sales Transactions and Invoices"""
    car = models.OneToOneField(CarInventory, on_delete=models.PROTECT, related_name='sale_record')
    client = models.ForeignKey(Client, on_delete=models.PROTECT, related_name='purchases')
    price = models.DecimalField(max_digits=12, decimal_places=2, validators=[validate_positive_price])
    date = models.DateTimeField(auto_now_add=True)

    def clean(self):
        # 1. Ensure the car is available for sale (Only on creation)
        if not self.pk and not self.car.in_stock:
            raise ValidationError("This car is already sold and no longer available!")

        # 2. Ensure the client's driving license is valid at the time of purchase
        if self.client.license_expiration_date < datetime.date.today():
            raise ValidationError("Transaction denied! The client's driving license has expired.")

    def save(self, *args, **kwargs):
        self.clean()  

        if not self.pk:
            # Automate status change: flip in_stock to False immediately upon a successful sale
            self.car.in_stock = False
            self.car.save()

        super(Sale, self).save(*args, **kwargs)

    def __str__(self):
        return f"Invoice for Car: {self.car.stock_number} sold to {self.client}"
