# In your app's admin.py file
# Make sure to import all models from models.py

from django.contrib import admin
from .models import (
    PriceList,
    PriceListItem,
)

# Register all models to the admin site
admin.site.register(PriceList)
admin.site.register(PriceListItem)