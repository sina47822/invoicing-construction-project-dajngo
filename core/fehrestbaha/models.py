# fehrestbaha/models.py

from django.db import models
from django.utils import timezone
from django.utils import timezone
from simple_history.models import HistoricalRecords

class DisciplineChoices(models.TextChoices):
    # رشته‌های صورت وضعیت (می‌تونی اضافه کنی)
    ABANIE = 'AB', 'ابنیه'
    MECHANIC = 'ME', 'مکانیک'
    ELECTRIC = 'EL', 'برق'
    OTHER = 'OT', 'سایر'

class PriceList(models.Model):
    discipline_choice = models.CharField(max_length=2, choices=DisciplineChoices.choices, verbose_name="رشته (ابنیه، مکانیک، etc)")
    discipline = models.CharField(max_length=100)  # رشته (مثل 'ابنیه')
    
    # logging
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="زمان ایجاد")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="زمان آخرین ویرایش")
    is_active = models.BooleanField(default=True, verbose_name="فعال/غیرفعال (برای حذف نرم)")
    modified_by = models.ForeignKey('auth.User', on_delete=models.SET_NULL, null=True, blank=True, verbose_name="ویرایش‌کننده")
    history = HistoricalRecords()  # لاگ تاریخچه تغییرات

    def __str__(self):
        return f"{self.discipline} - {self.created_at}"

class PriceListItem(models.Model):
    price_list = models.ForeignKey(PriceList, on_delete=models.CASCADE, related_name='items')
    row_number = models.CharField(max_length=10)  # ردیف (مثل '180203')
    description = models.TextField()  # شرح (مثل 'گچ‌کاری')
    price = models.DecimalField(max_digits=15, decimal_places=2)  # قیمت واحد
    unit = models.CharField(max_length=50)  # واحد (مثل 'متر مربع')
    is_starred = models.BooleanField(default=False)  # ستاره‌دار هست یا نه
    
    # logging
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="زمان ایجاد")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="زمان آخرین ویرایش")
    is_active = models.BooleanField(default=True, verbose_name="فعال/غیرفعال (برای حذف نرم)")
    modified_by = models.ForeignKey('auth.User', on_delete=models.SET_NULL, null=True, blank=True, verbose_name="ویرایش‌کننده")
    history = HistoricalRecords()  # لاگ تاریخچه تغییرات

    def __str__(self):
        return f"{self.row_number} - {self.description}"

