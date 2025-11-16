#  ProjectLog/models.py

from django.db import models
from django.contrib.auth.models import User
from simple_history.models import HistoricalRecords 

# مدل اختیاری برای لاگ اقدامات (AuditLog) - اگر بخوای لاگ پیشرفته‌تر
class AuditLog(models.Model):
    ACTION_CHOICES = [
        ('CREATE', 'ایجاد'),
        ('UPDATE', 'ویرایش'),
        ('DELETE', 'حذف (نرم)'),
    ]

    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, verbose_name="کاربر")
    action = models.CharField(max_length=10, choices=ACTION_CHOICES, verbose_name="اقدام")
    model_name = models.CharField(max_length=100, verbose_name="نام مدل (مثل CivilProject)")
    object_id = models.PositiveIntegerField(verbose_name="ID شیء")
    changes = models.JSONField(blank=True, null=True, verbose_name="تغییرات (JSON)")  # برای ذخیره جزئیات تغییرات
    timestamp = models.DateTimeField(auto_now_add=True, verbose_name="زمان لاگ")
    history = HistoricalRecords()  
    class Meta:
        verbose_name = "لاگ اقدام"
        verbose_name_plural = "لاگ اقدامات"
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.action} روی {self.model_name} ({self.object_id}) توسط {self.user}"