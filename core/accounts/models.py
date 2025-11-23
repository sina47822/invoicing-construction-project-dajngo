# accounts/models.py
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

from simple_history.models import HistoricalRecords
from django.utils.translation import gettext_lazy as _
from project.models import Project

class UserRole(models.Model):
    """
    مدل نقش‌های کاربران در سیستم
    """
    ROLE_CHOICES = [
        ('contractor', _('پیمانکار')),
        ('project_manager', _('مدیر طرح')),
        ('employer', _('کارفرما')),
        ('admin', _('ادمین')),
        ('supervisor', _('ناظر')),
        ('engineer', _('مهندس')),
    ]
    
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='roles',
        verbose_name=_('کاربر')
    )
    
    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        verbose_name=_('نقش')
    )
    
    is_active = models.BooleanField(
        default=True, 
        verbose_name=_('فعال')
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = _('نقش کاربر')
        verbose_name_plural = _('نقش‌های کاربران')
        unique_together = ['user', 'role']
    
    def __str__(self):
        return f"{self.user.username} - {self.get_role_display()}"

class UserProfile(models.Model):
    """
    پروفایل کاربر برای اطلاعات تکمیلی
    """
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='profile',
        verbose_name=_('کاربر')
    )
    
    # اطلاعات تماس
    phone_number = models.CharField(
        max_length=15,
        blank=True,
        null=True,
        verbose_name=_('شماره تلفن')
    )
    
    national_id = models.CharField(
        max_length=10,
        blank=True,
        null=True,
        verbose_name=_('کد ملی')
    )
    
    company_name = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        verbose_name=_('نام شرکت/سازمان')
    )
    
    position = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name=_('سمت')
    )
    
    address = models.TextField(
        blank=True,
        null=True,
        verbose_name=_('آدرس')
    )
    
    is_verified = models.BooleanField(
        default=False,
        verbose_name=_('تأیید شده')
    )
    
    avatar = models.ImageField(
        upload_to="avatars/", 
        default="avatars/default.png", 
        verbose_name=_('آواتار')
    )
    
    bio = models.TextField(
        blank=True,
        null=True,
        verbose_name=_('بیوگرافی')
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _('پروفایل کاربر')
        verbose_name_plural = _('پروفایل‌های کاربران')
    
    def __str__(self):
        return f"{self.user.username} - {self.company_name or 'بدون شرکت'}"


    def __str__(self):
        return f"{self.user.username} - {self.company_name or 'بدون شرکت'}"

class ProjectRole(models.Model):
    """
    مدل نقش‌های پروژه
    """
    ROLE_CHOICES = [
        ('contractor', _('پیمانکار')),
        ('project_manager', _('مدیر طرح')),
        ('employer', _('کارفرما')),
        ('admin', _('ادمین')),
        ('supervisor', _('ناظر')),
        ('engineer', _('مهندس')),
    ]
    
    name = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        unique=True,
        verbose_name=_('نام نقش')
    )
    
    description = models.TextField(
        blank=True,
        null=True,
        verbose_name=_('توضیحات نقش')
    )
    
    can_edit_measurements = models.BooleanField(
        default=False,
        verbose_name=_('می‌تواند متره را ویرایش کند')
    )
    
    can_approve = models.BooleanField(
        default=False,
        verbose_name=_('می‌تواند تأیید کند')
    )
    
    can_view_financial = models.BooleanField(
        default=False,
        verbose_name=_('می‌تواند اطلاعات مالی را ببیند')
    )

    is_active = models.BooleanField(default=True, verbose_name=_('فعال'))
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _('نقش کاربر')
        verbose_name_plural = _('نقش‌های کاربران')
    
    def __str__(self):
        return f"{self.user.username} - {self.get_role_display()}"

class ProjectUser(models.Model):
    """
    مدل واسط برای ارتباط کاربران با پروژه‌ها و نقش‌های خاص در هر پروژه
    """
    PROJECT_ROLE_CHOICES = [
        ('contractor', _('پیمانکار')),
        ('project_manager', _('مدیر طرح')),
        ('employer', _('کارفرما')),
        ('supervisor', _('ناظر')),
        ('consultant', _('مشاور')),
    ]
    
    project = models.ForeignKey(
        'project.Project',
        on_delete=models.CASCADE,
        related_name='project_users',
        verbose_name=_('پروژه')
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='project_assignments',
        verbose_name=_('کاربر')
    )
    role = models.CharField(
        max_length=20,
        choices=PROJECT_ROLE_CHOICES,
        verbose_name=_('نقش در پروژه')
    )
    # تاریخ‌های شروع و پایان مسئولیت
    start_date = models.DateField(
        default=timezone.now,
        verbose_name=_('تاریخ شروع مسئولیت')
    )
    
    end_date = models.DateField(
        blank=True,
        null=True,
        verbose_name=_('تاریخ پایان مسئولیت')
    )
    is_active = models.BooleanField(default=True, verbose_name=_('فعال'))
    
    # لاگ‌گیری
    assigned_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='assigned_project_users',
        verbose_name=_('اختصاص‌دهنده')
    )
    
    assigned_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_primary = models.BooleanField(default=False)  # Add this field

    
    class Meta:
        verbose_name = _('کاربر پروژه')
        verbose_name_plural = _('کاربران پروژه')
        unique_together = ['project', 'user', 'role']
        ordering = ['-is_primary', 'role']
    
    def __str__(self):
        return f"{self.user.username} - {self.get_name_display()} - {self.project.project_name}"

    def save(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        if user and not self.assigned_by:
            self.assigned_by = user
        super().save(*args, **kwargs)
    
    @property
    def is_current(self):
        """آیا مسئولیت کاربر فعلی است؟"""
        if self.end_date and self.end_date < timezone.now().date():
            return False
        return self.is_active

class UserInvitation(models.Model):
    """
    مدل برای دعوت کاربران جدید به سیستم
    """
    INVITATION_STATUS = [
        ('pending', 'در انتظار'),
        ('accepted', 'پذیرفته شده'),
        ('expired', 'منقضی شده'),
    ]
    
    email = models.EmailField(verbose_name='ایمیل')
    role = models.CharField(max_length=20, choices=UserRole.ROLE_CHOICES, verbose_name='نقش')
    project = models.ForeignKey('project.Project', on_delete=models.CASCADE, verbose_name='پروژه')
    invited_by = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='دعوت‌کننده')
    token = models.CharField(max_length=100, unique=True, verbose_name='توکن')
    status = models.CharField(max_length=10, choices=INVITATION_STATUS, default='pending')
    expires_at = models.DateTimeField(verbose_name='تاریخ انقضا')
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'دعوت‌نامه کاربر'
        verbose_name_plural = 'دعوت‌نامه‌های کاربران'
    
    def __str__(self):
        return f"{self.email} - {self.get_role_display()} - {self.project.project_name}"

    def is_expired(self):
        return timezone.now() > self.expires_at