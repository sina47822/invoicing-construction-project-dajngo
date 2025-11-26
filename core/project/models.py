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
        ('draft', _('پیش‌نویس')),
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
    # کاربر ایجادکننده (معمولاً پیمانکار اصلی)
    created_by = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='created_projects',
        verbose_name=_('ایجادکننده'),
        help_text=_('کاربری که این پروژه را ایجاد کرده است')
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
    
    # مالیات بر ارزش افزوده
    vat_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=10.00,  # 10% مالیات
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        verbose_name=_("درصد مالیات بر ارزش افزوده"),
        help_text=_("درصد مالیات بر ارزش افزوده (مثال: 10)")
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
        permissions = [
            ("can_assign_roles", "Can assign roles to projects"),
            ("can_manage_all_projects", "Can manage all projects"),
            ("can_view_all_projects", "Can view all projects"),
        ]

    def __str__(self):
        return f"{self.project_name} - {self.project_code}"

        # متدهای دسترسی
    def get_contractor(self):
        """دریافت پیمانکار اصلی پروژه"""
        return self.project_users.filter(
            role='contractor', 
            is_primary=True, 
            is_active=True
        ).first()
    
    def get_employer(self):
        """دریافت کارفرمای پروژه"""
        return self.project_users.filter(
            role='employer', 
            is_primary=True, 
            is_active=True
        ).first()
    
    def get_project_manager(self):
        """دریافت مدیر طرح پروژه"""
        return self.project_users.filter(
            role='project_manager', 
            is_primary=True, 
            is_active=True
        ).first()

    def get_all_users_by_role(self, role):
        """دریافت تمام کاربران با نقش خاص"""
        return self.project_users.filter(role=role, is_active=True)
    
    def get_absolute_url(self):
        from django.urls import reverse
        return reverse('project:project_detail', kwargs={'pk': self.pk})
    
    def has_access(self, user, required_roles=None):
        """
        بررسی دسترسی کاربر به پروژه
        required_roles: لیست نقش‌های مورد نیاز (اختیاری)
        """
        if user.is_superuser:
            return True
            
        if required_roles is None:
            required_roles = ['contractor', 'project_manager', 'employer', 'supervisor']
        
        # بررسی آیا کاربر در این پروژه نقشی دارد
        return self.project_users.filter(
            user=user, 
            role__in=required_roles,
            is_active=True
        ).exists()
    
    def can_edit(self, user):
        """آیا کاربر می‌تواند پروژه را ویرایش کند؟"""
        if user.is_superuser:
            return True
            
        # پیمانکار و مدیر طرح می‌توانند ویرایش کنند
        return self.project_users.filter(
            user=user,
            role__in=['contractor', 'project_manager'],
            is_active=True
        ).exists()    
    
    def can_edit_measurements(self, user):
        """آیا کاربر می‌تواند متره را ویرایش کند؟"""
        if user.is_superuser:
            return True
            
        user_assignment = self.project_users.filter(
            user=user,
            is_active=True
        ).first()
        
        return user_assignment and user_assignment.role.can_edit_measurements
    
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
            super().delete(**kwargs)
        else:
            self.is_active = False
            self.deleted_at = timezone.now()
            self.save()
    @property
    def contract_amount_with_vat(self):
        """محاسبه مبلغ قرارداد با احتساب مالیات"""
        if self.contract_amount:
            vat_amount = (self.contract_amount * self.vat_percentage) / 100
            return self.contract_amount + vat_amount
        return Decimal('0.00')
    
    @property
    def formatted_contract_amount_with_vat(self):
        """فرمت مبلغ قرارداد با مالیات"""
        from sooratvaziat.utils import format_number_int
        return format_number_int(self.contract_amount_with_vat)
        
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

