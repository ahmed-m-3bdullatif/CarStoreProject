from django.contrib import admin
from .models import *
# Register your models here.
admin.site.register(StoreSettings)
admin.site.register(CarInventory)
admin.site.register(Client)
admin.site.register(Sale)
admin.site.register(Repair)