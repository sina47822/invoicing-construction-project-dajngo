# In your app's admin.py file
# Make sure to import all models from models.py

from django.contrib import admin
from .models import (
    MeasurementSession,
    MeasurementSessionItem,
    DetailedMeasurement,
)

admin.site.register(MeasurementSession)
admin.site.register(MeasurementSessionItem)
admin.site.register(DetailedMeasurement)
