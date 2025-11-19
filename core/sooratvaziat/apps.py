# sooratvaziat/apps.py

from django.apps import AppConfig


class SooratvaziatConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'sooratvaziat'
    
    def ready(self):
        import sooratvaziat.signals  # Import signals