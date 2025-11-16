#  project/models.py
from django.db import models
from django.core.validators import MinValueValidator
from fehrestbaha.models import DisciplineChoices
from simple_history.models import HistoricalRecords  # اگر django-simple-history نصب کردی
from django.contrib.auth.models import User

class Project(models.Model):
    user = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='projects',
        verbose_name='کاربر'
    )
    # نام پروژه
    project_name = models.CharField(max_length=255, verbose_name="نام پروژه")

    # کد پروژه (منحصر به فرد برای جلوگیری از تکرار)
    project_code = models.CharField(max_length=50, unique=True, verbose_name="کد پروژه")

    # کارفرما
    employer = models.CharField(max_length=255, verbose_name="کارفرما")

    # پیمانکار
    contractor = models.CharField(max_length=255, verbose_name="پیمانکار")

    # مدیر طرح یا مشاور (اختیاری)
    consultant = models.CharField(max_length=255, blank=True, null=True, verbose_name="مدیر طرح یا مشاور")

    # مهندس ناظر (اختیاری)
    supervising_engineer = models.CharField(max_length=255, blank=True, null=True, verbose_name="مهندس ناظر")

    # شهر پروژه
    city = models.CharField(max_length=100, verbose_name="شهر پروژه")

    # استان پروژه
    province = models.CharField(max_length=100, verbose_name="استان پروژه")

    # کشور پروژه (پیش‌فرض ایران، چون پروژه عمرانی ایرانی به نظر می‌رسه)
    country = models.CharField(max_length=100, default="ایران", verbose_name="کشور پروژه")

    # شماره قرارداد
    contract_number = models.CharField(max_length=50, verbose_name="شماره قرارداد")

    # تاریخ قرارداد
    contract_date = models.DateField(verbose_name="تاریخ قرارداد")

    # سال اجرا بر اساس صورت وضعیت (مثلاً سالی که پروژه اجرا می‌شه یا صورت وضعیت صادر می‌شه)
    execution_year = models.IntegerField(
        validators=[MinValueValidator(1370)],  # حداقل سال برای اعتبارسنجی
        verbose_name="سال اجرا بر اساس صورت وضعیت"
    )

    # مبلغ قرارداد (با دقت دو رقم اعشار برای پول)
    contract_amount = models.DecimalField(
        max_digits=15,  # حداکثر 15 رقم (برای مبالغ بزرگ)
        decimal_places=0,
        validators=[MinValueValidator(0)],  # مبلغ نمی‌تونه منفی باشه
        verbose_name="مبلغ قرارداد"
    )

    # فیلدهای اضافی پیشنهادی (اگر لازم داری فعال کن)
    status = models.CharField(max_length=50, choices=[('active', 'فعال'), ('completed', 'تمام‌شده')], default='active', verbose_name="وضعیت پروژه")
    contract_file = models.FileField(upload_to='contracts/', blank=True, null=True, verbose_name="فایل قرارداد")
    amount = models.DecimalField(max_digits=21, decimal_places=2, validators=[MinValueValidator(0)], blank=True, null=True, verbose_name="مبلغ صورت وضعیت")
    description = models.TextField(blank=True, null=True, verbose_name="توضیحات")
    
    # logging
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="زمان ایجاد")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="زمان آخرین ویرایش")
    is_active = models.BooleanField(default=True, verbose_name="فعال/غیرفعال (برای حذف نرم)")
    modified_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="ویرایش‌کننده")
    history = HistoricalRecords()

    class Meta:
        verbose_name = "پروژه عمرانی"
        verbose_name_plural = "پروژه‌های عمرانی"
        ordering = ['-contract_date']  # مرتب‌سازی بر اساس تاریخ قرارداد (جدیدترین اول)

    def __str__(self):
        return f"{self.project_name} کد پروژه : ({self.project_code})"

class StatusReport(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='status_reports', verbose_name="پروژه مرتبط")
    discipline = models.CharField(max_length=2, choices=DisciplineChoices.choices, verbose_name="رشته (ابنیه، مکانیک، etc)")
    attachment = models.FileField(upload_to='status_reports/', blank=True, null=True, verbose_name="فایل پیوست (مثل PDF صورت وضعیت)")
    description = models.TextField(blank=True, null=True, verbose_name="توضیحات")

    # فیلدهای لاگ‌گیری
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="زمان ایجاد")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="زمان آخرین ویرایش")
    is_active = models.BooleanField(default=True, verbose_name="فعال/غیرفعال (برای حذف نرم)")
    modified_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="ویرایش‌کننده")
    history = HistoricalRecords()
    # اضافه کردن فیلدهای مفقوده

    class Meta:
        verbose_name = "صورت وضعیت"
        verbose_name_plural = "صورت وضعیت‌ها"
        ordering = ['-created_at', 'discipline']

    def __str__(self):
        return f"صورت وضعیت {self.get_discipline_display()} - سال {self.year} برای پروژه {self.project.project_code}"