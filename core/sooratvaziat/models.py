# sooratvaziat/models.py
from django.db import models
from django.utils import timezone
from fehrestbaha.models import PriceListItem
from django.core.validators import MinValueValidator
from decimal import Decimal
from simple_history.models import HistoricalRecords
from django.contrib.auth.models import User
from project.models import Project  # import Project
from fehrestbaha.models import DisciplineChoices

class DetailedMeasurement(models.Model):
    price_list_item = models.OneToOneField(PriceListItem, on_delete=models.CASCADE, related_name='detailed_measurement')
    _total_quantity = models.DecimalField(max_digits=15, decimal_places=2, default=0, validators=[MinValueValidator(Decimal('0'))])
    
    # فیلدهای لاگ‌گیری
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="زمان ایجاد")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="زمان آخرین ویرایش")
    is_active = models.BooleanField(default=True, verbose_name="فعال/غیرفعال (برای حذف نرم)")
    modified_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="ویرایش‌کننده")
    history = HistoricalRecords()

    @property
    def total_quantity(self):
        return self._total_quantity  # read-only property

    def __str__(self):
        return f"ریز متره برای {self.price_list_item.row_number}"

    def update_total(self):
        # محاسبه مجموع quantities از تمام MeasurementSessionItemهای مرتبط
        self._total_quantity = sum(item.get_total_item_amount() for item in self.price_list_item.pricelist_items.all())
        self.save()

# حالا متد update_detailed_measurements در MeasurementSession
class MeasurementSession(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='measurement_sessions', verbose_name="پروژه مرتبط")  # لینک جدید به پروژه
    session_number = models.CharField(max_length=255, null=True, blank=True)
    session_date = models.DateField(null=True, blank=True, verbose_name="تاریخ صورت جلسه")
    created_at = models.DateTimeField(default=timezone.now, verbose_name="زمان ایجاد")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="زمان آخرین ویرایش")
    description = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True, verbose_name="فعال/غیرفعال (برای حذف نرم)")
    modified_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="ویرایش‌کننده")
    history = HistoricalRecords()
    discipline_choice = models.CharField(max_length=2, choices=DisciplineChoices.choices, verbose_name="رشته (ابنیه، مکانیک، etc)",null=True, blank=True)

    def __str__(self):
        return f"صورت جلسه شماره {self.session_number} برای پروژه {self.project.project_code}"
    
    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # بعد از ذخیره، ریز متره‌ها رو به‌روزرسانی کن (برای همه PriceListItemهای مرتبط)
        self.update_detailed_measurements()
    
    def update_detailed_measurements(self):
        from collections import defaultdict
        items_by_pricelist = defaultdict(list)
        for item in self.items.all():
            items_by_pricelist[item.pricelist_item].append(item)

        for pricelist_item, session_items in items_by_pricelist.items():
            detailed, created = DetailedMeasurement.objects.get_or_create(
                price_list_item=pricelist_item
            )
            session_quantity = sum(item.get_total_item_amount() for item in session_items)
            # اضافه کردن session_quantity به total (اگر می‌خواید افزایشی باشه؛ اگر نه، کامنت کنید)
            detailed._total_quantity += session_quantity
            detailed.save()  # ذخیره مستقیم بدون update_total اگر نمی‌خواید مجموع کل محاسبه بشه
            # یا اگر می‌خواید مجموع کل بروز بشه: detailed.update_total()

class MeasurementSessionItem(models.Model):
    pricelist_item = models.ForeignKey(PriceListItem, on_delete=models.CASCADE, related_name='pricelist_items')
    measurement_session_number = models.ForeignKey(MeasurementSession, on_delete=models.CASCADE, related_name='items')
    row_description = models.CharField(max_length=255)  # ردیف/توضیح (مثل 'دیوار یک')
    length = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)  # طول
    width = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)  # عرض
    height = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)  # ارتفاع
    weight = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)  # وزن
    count = models.DecimalField(max_digits=10, decimal_places=2, default=1)  # تعداد
    
    #logging
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="زمان ایجاد")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="زمان آخرین ویرایش")
    is_active = models.BooleanField(default=True, verbose_name="فعال/غیرفعال (برای حذف نرم)")
    modified_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="ویرایش‌کننده")
    history = HistoricalRecords()
    def __str__(self):
        return f"{self.row_description} در {self.measurement_session_number}  و آیتم فهرست {self.pricelist_item.row_number}"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # بعد از ذخیره آیتم، صورت جلسه رو به‌روزرسانی کن
        self.measurement_session_number.save()
    
    def get_total_item_amount(self):
        # محاسبه مقدار این آیتم بر اساس واحد (logic مشابه قبل)
        unit = self.pricelist_item.unit
        if unit == 'متر مربع':
            return self.count * (self.length or 0) * (self.width or 0)
        elif unit == 'متر مکعب':
            return self.count * (self.length or 0) * (self.width or 0) * (self.height or 0)
        elif unit == 'کیلوگرم':
            return self.count * (self.weight or 0)
        else:
            return self.count

