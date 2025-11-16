from django.apps import AppConfig


class ProjectlogConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'ProjectLog'
    
    def ready(self):
        import ProjectLog.signals  # لینک سیگنال‌ها