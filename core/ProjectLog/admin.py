from django.contrib import admin
from .models import AuditLog

@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ('action', 'model_name', 'object_id', 'user', 'timestamp')
    list_filter = ('action', 'model_name', 'user')
    search_fields = ('changes',)
    readonly_fields = ('changes', 'timestamp')
    # اگر بخوای تغییرات JSON رو بهتر نشون بدی، می‌تونی یک متد custom اضافه کنی
    def changes_display(self, obj):
        return obj.changes  # یا فرمت‌شده‌تر
    changes_display.short_description = "تغییرات"