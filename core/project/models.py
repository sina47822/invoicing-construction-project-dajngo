#  project/models.py
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from fehrestbaha.models import DisciplineChoices
from simple_history.models import HistoricalRecords  # اگر django-simple-history نصب کردی
from django.contrib.auth.models import User
from django.utils.translation import gettext_lazy as _

class Project(models.Model):
    # وضعیت‌های پروژه
    STATUS_CHOICES = [
        ('active', _('فعال')),
        ('in_progress', _('در حال اجرا')),
        ('under_review', _('در حال بررسی')),
        ('awaiting_approval', _('منتظر تأیید')),
        ('completed', _('تمام‌شده')),
        ('suspended', _('معلق')),
        ('cancelled', _('لغو شده')),
    ]
    
    # نوع پروژه‌ها (برای گسترش آینده)
    PROJECT_TYPE_CHOICES = [
        ('civil', _('عمرانی')),
        ('building', _('ساختمانی')),
        ('bridge', _('پل‌سازی')),
        ('dam', _('سدسازی')),
        ('road', _('جاده‌سازی')),
        ('electrical', _('برقی')),
        ('mechanical', _('مکانیکی')),
        ('other', _('سایر')),
    ]
    user = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='projects',
        verbose_name=_('کاربر'),
        limit_choices_to={'is_staff': False}  # فقط کاربران عادی
    )
    
    # اطلاعات اصلی پروژه
    project_name = models.CharField(
        max_length=255, 
        verbose_name=_("نام پروژه"),
        help_text=_("نام کامل و دقیق پروژه")
    )

    project_code = models.CharField(
        max_length=50, 
        unique=True, 
        verbose_name=_("کد پروژه"),
        help_text=_("کد منحصر به فرد پروژه - قابل تغییر نیست")
    )

    # طرف‌های قرارداد
    employer = models.CharField(
        max_length=255, 
        verbose_name=_("کارفرما"),
        help_text=_("نام کامل کارفرما یا سازمان کارفرما")
    )

    contractor = models.CharField(
        max_length=255, 
        verbose_name=_("پیمانکار"),
        help_text=_("نام کامل پیمانکار مجری پروژه")
    )

    # نقش‌های مدیریتی (اختیاری)
    consultant = models.CharField(
        max_length=255, 
        blank=True, 
        null=True, 
        verbose_name=_("مدیر طرح یا مشاور"),
        help_text=_("نام مدیر طرح، مشاور یا شرکت مشاور")
    )

    supervising_engineer = models.CharField(
        max_length=255, 
        blank=True, 
        null=True, 
        verbose_name=_("مهندس ناظر"),
        help_text=_("نام مهندس ناظر پروژه")
    )

    # موقعیت جغرافیایی
    city = models.CharField(
        max_length=100, 
        verbose_name=_("شهر پروژه"),
        help_text=_("شهر محل اجرای پروژه")
    )

    province = models.CharField(
        max_length=100, 
        verbose_name=_("استان"),
        help_text=_("استان محل پروژه")
    )

    country = models.CharField(
        max_length=100, 
        default="ایران", 
        verbose_name=_("کشور"),
        help_text=_("کشور محل پروژه")
    )

    # اطلاعات قرارداد
    contract_number = models.CharField(
        max_length=50, 
        verbose_name=_("شماره قرارداد"),
        help_text=_("شماره رسمی قرارداد")
    )

    contract_date = models.DateField(
        verbose_name=_("تاریخ قرارداد"),
        help_text=_("تاریخ انعقاد قرارداد")
    )

    execution_year = models.IntegerField(
        validators=[
            MinValueValidator(1370), 
            MaxValueValidator(1410)
        ], 
        verbose_name=_("سال اجرا بر اساس صورت وضعیت"),
        help_text=_("سال شروع اجرای پروژه یا صدور صورت وضعیت")
    )

    contract_amount = models.DecimalField(
        max_digits=15, 
        decimal_places=0,
        validators=[MinValueValidator(100000)], 
        verbose_name=_("مبلغ قرارداد"),
        help_text=_("مبلغ کل قرارداد به ریال")
    )

    # اطلاعات اضافی
    project_type = models.CharField(
        max_length=20,
        choices=PROJECT_TYPE_CHOICES,
        default='civil',
        verbose_name=_("نوع پروژه"),
        help_text=_("دسته‌بندی نوع پروژه")
    )
    
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='active', 
        verbose_name=_("وضعیت پروژه"),
        help_text=_("وضعیت فعلی پروژه")
    )
    
    contract_file = models.FileField(
        upload_to='contracts/%Y/%m/',
        blank=True, 
        null=True, 
        verbose_name=_("فایل قرارداد"),
        help_text=_("فایل PDF یا Word قرارداد")
    )
    
    amount = models.DecimalField(
        max_digits=21, 
        decimal_places=2, 
        validators=[MinValueValidator(0)], 
        blank=True, 
        null=True, 
        verbose_name=_("مبلغ صورت وضعیت"),
        help_text=_("مبلغ آخرین صورت وضعیت (اختیاری)")
    )
    
    description = models.TextField(
        blank=True, 
        null=True, 
        verbose_name=_("توضیحات"),
        help_text=_("توضیحات اضافی درباره پروژه")
    )
    
    # مدیریت وضعیت و لاگ
    is_active = models.BooleanField(
        default=True, 
        verbose_name=_("فعال/غیرفعال"),
        help_text=_("برای حذف نرم: غیرفعال = مخفی از لیست‌ها")
    )
    
    created_at = models.DateTimeField(
        auto_now_add=True, 
        verbose_name=_("زمان ایجاد")
    )
    
    updated_at = models.DateTimeField(
        auto_now=True, 
        verbose_name=_("زمان آخرین ویرایش")
    )
    
    deleted_at = models.DateTimeField(
        null=True, 
        blank=True, 
        verbose_name=_("زمان حذف")
    )
    
    modified_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='modified_projects',
        verbose_name=_("ویرایش‌کننده"),
        help_text=_("کاربر آخر ویرایش‌کننده")
    )
    
    # تاریخچه تغییرات
    history = HistoricalRecords(
        excluded_fields=['updated_at', 'is_active', 'deleted_at']
    )

    class Meta:
        verbose_name = _("پروژه عمرانی")
        verbose_name_plural = _("پروژه‌های عمرانی")
        ordering = ['-created_at', 'project_name']
        indexes = [
            models.Index(fields=['project_code', 'is_active']),
            models.Index(fields=['status', 'is_active']),
            models.Index(fields=['execution_year', 'is_active']),
            models.Index(fields=['city', 'province', 'is_active']),
        ]

    def __str__(self):
        return f"{self.project_name} - {self.project_code}"
    
    def save(self, *args, **kwargs):
        """Override save برای مدیریت وضعیت"""
        from django.utils import timezone
        
        # **استخراج user از kwargs اگر وجود دارد**
        user = kwargs.pop('user', None)
        
        # تنظیم modified_by
        if not self.pk:  # ایجاد جدید
            self.modified_by = user or self.user
        else:
            # برای آپدیت، از user دریافتی یا مقدار قبلی استفاده کن
            self.modified_by = user or self.modified_by
        
        # مدیریت حذف نرم
        if self.pk:
            try:
                old_instance = Project.objects.get(pk=self.pk)
                if not self.is_active and self.is_active != old_instance.is_active:
                    self.deleted_at = timezone.now()
            except Project.DoesNotExist:
                pass
        
        # پاک کردن deleted_at هنگام فعال‌سازی
        if self.is_active:
            self.deleted_at = None
        
        # **فراخوانی صحیح super().save() بدون user در kwargs**
        super().save(*args, **kwargs)

    
    @property
    def is_soft_deleted(self):
        """بررسی حذف نرم"""
        return not self.is_active and self.deleted_at is not None
    
    @property
    def display_status(self):
        """نمایش وضعیت با توجه به فعال/غیرفعال"""
        if not self.is_active:
            return 'غیرفعال'
        return self.get_status_display()
    
    def get_absolute_url(self):
        from django.urls import reverse
        return reverse('project:project_detail', kwargs={'pk': self.pk})
    
    def delete(self, hard_delete=False, **kwargs):
        """حذف نرم به طور پیش‌فرض"""
        
        from django.utils import timezone
        if hard_delete or not self.is_active:
            # حذف کامل
            from django.utils import timezone
            self.deleted_at = timezone.now()
            super().delete(**kwargs)
        else:
            # حذف نرم
            self.is_active = False
            self.deleted_at = timezone.now()
            self.save(update_fields=['is_active', 'deleted_at'])

class StatusReport(models.Model):
    """
    مدل صورت وضعیت - اصلاح شده
    """
    # ارتباط با پروژه
    project = models.ForeignKey(
        Project, 
        on_delete=models.CASCADE, 
        related_name='status_reports', 
        verbose_name=_("پروژه مرتبط")
    )
    
    # رشته تخصصی
    discipline = models.CharField(
        max_length=2, 
        choices=DisciplineChoices.choices, 
        verbose_name=_("رشته"),
        help_text=_("رشته تخصصی صورت وضعیت")
    )
    
    # شماره صورت وضعیت
    report_number = models.PositiveIntegerField(
        verbose_name=_("شماره صورت وضعیت"),
        help_text=_("شماره ترتیبی صورت وضعیت")
    )
    
    # تاریخ صدور
    issue_date = models.DateField(
        verbose_name=_("تاریخ صدور"),
        help_text=_("تاریخ صدور صورت وضعیت")
    )
    
    # مبلغ صورت وضعیت
    amount = models.DecimalField(
        max_digits=15,
        decimal_places=0,
        validators=[MinValueValidator(0)],
        verbose_name=_("مبلغ صورت وضعیت"),
        help_text=_("مبلغ این صورت وضعیت به ریال")
    )
    
    # درصد پیشرفت
    progress_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        verbose_name=_("درصد پیشرفت"),
        help_text=_("درصد پیشرفت فیزیکی تا این صورت وضعیت")
    )
    
    # فایل پیوست
    attachment = models.FileField(
        upload_to='status_reports/%Y/%m/',
        blank=True, 
        null=True, 
        verbose_name=_("فایل پیوست"),
        help_text=_("فایل PDF صورت وضعیت")
    )
    
    description = models.TextField(
        blank=True, 
        null=True, 
        verbose_name=_("توضیحات"),
        help_text=_("توضیحات اضافی درباره صورت وضعیت")
    )

    # وضعیت تأیید
    approval_status = models.CharField(
        max_length=20,
        choices=[
            ('draft', _('پیش‌نویس')),
            ('submitted', _('ارسال شده')),
            ('approved', _('تأیید شده')),
            ('rejected', _('رد شده')),
        ],
        default='draft',
        verbose_name=_("وضعیت تأیید")
    )
    
    # لاگ‌گیری
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("زمان ایجاد"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("زمان آخرین ویرایش"))
    is_active = models.BooleanField(default=True, verbose_name=_("فعال/غیرفعال"))
    modified_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        verbose_name=_("ویرایش‌کننده")
    )
    
    history = HistoricalRecords()

    class Meta:
        verbose_name = _("صورت وضعیت")
        verbose_name_plural = _("صورت وضعیت‌ها")
        ordering = ['-issue_date', 'report_number']
        unique_together = ['project', 'report_number', 'discipline']
        indexes = [
            models.Index(fields=['project', 'discipline', 'is_active']),
            models.Index(fields=['issue_date', 'is_active']),
        ]

    def __str__(self):
        return f"صورت وضعیت {self.report_number} - {self.get_discipline_display()} - {self.project.project_code}"
    
    def save(self, *args, **kwargs):
        """Override save"""
        user = kwargs.pop('user', None)
        if user:
            self.modified_by = user
        
        # به‌روزرسانی مبلغ پروژه
        if self.approval_status == 'approved':
            self.project.amount = self.amount
            self.project.save(update_fields=['amount'])
        
        super().save(*args, **kwargs)
    
    @property
    def year(self):
        """سال صورت وضعیت"""
        return self.issue_date.year if self.issue_date else None
    
    def clean(self):
        """اعتبارسنجی"""
        if self.progress_percentage > 100:
            raise ValidationError('درصد پیشرفت نمی‌تواند بیش از 100 باشد.')
        
        # بررسی شماره تکراری
        if StatusReport.objects.filter(
            project=self.project,
            report_number=self.report_number,
            discipline=self.discipline,
            is_active=True
        ).exclude(pk=self.pk).exists():
            raise ValidationError('این شماره صورت وضعیت قبلاً استفاده شده است.')