# sooratvaziat/models.py
from django.db import models
from django.utils import timezone
from fehrestbaha.models import PriceListItem, DisciplineChoices
from django.core.validators import MinValueValidator
from decimal import Decimal
from simple_history.models import HistoricalRecords
from django.contrib.auth.models import User
from project.models import Project  # import Project
from django.db.models import Sum, Count, Q
from collections import OrderedDict
import jdatetime
import logging
from fehrestbaha.models import PriceList , PriceListItem
from accounts.models import ProjectRole
logger = logging.getLogger(__name__)
from django.utils.translation import gettext_lazy as _

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
    """
    مدل صورت‌جلسه متره (Session)
    """
    # اطلاعات اصلی
    project = models.ForeignKey(
        Project, 
        on_delete=models.CASCADE, 
        related_name='measurement_sessions', 
        verbose_name="پروژه مرتبط"
    )
    session_number = models.CharField(
        max_length=50, 
        blank=True, 
        null=True, 
        help_text="شماره صورت‌جلسه (خودکار تولید می‌شود اگر خالی باشد)"
    )
    session_date = models.DateField(
        verbose_name="تاریخ صورت‌جلسه",
        help_text="تاریخ برگزاری صورت‌جلسه",
        null=True, 
        blank=True
    )
    price_list = models.ForeignKey(
        PriceList,
        on_delete=models.PROTECT,
        related_name='measurement_sessions',
        verbose_name="فهرست بها مرتبط",
        help_text="فهرست بهایی که این صورت جلسه بر اساس آن است"
    )
    
    # اطلاعات توصیفی
    description = models.TextField(
        blank=True, 
        null=True, 
        verbose_name="توضیحات",
        help_text="توضیحات اضافی صورت‌جلسه"
    )
    notes = models.TextField(
        blank=True, 
        null=True, 
        verbose_name="یادداشت‌ها",
        help_text="یادداشت‌های داخلی",
        default=''
    )
    
    # آمار پایه (بدون مجموع مالی)
    items_count = models.PositiveIntegerField(
        default=0, 
        verbose_name="تعداد آیتم‌ها",
        help_text="تعداد کل آیتم‌های این صورت‌جلسه"
    )
    # وضعیت و لاگ‌گیری
    status = models.CharField(
        max_length=20, 
        choices=[
            ('draft', 'پیش‌نویس'),
            ('submitted', 'ارسال‌شده'),
            ('approved', 'تایید‌شده'),
            ('rejected', 'رد‌شده'),
        ],
        default='submitted',
        verbose_name="وضعیت"
    )
    is_active = models.BooleanField(
        default=True, 
        verbose_name="فعال/غیرفعال",
        help_text="برای حذف نرم استفاده می‌شود"
    )
    
    # لاگ‌گیری
    created_at = models.DateTimeField(
        auto_now_add=True, 
        verbose_name="زمان ایجاد"
    )
    updated_at = models.DateTimeField(
        auto_now=True, 
        verbose_name="زمان آخرین ویرایش"
    )
    created_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='created_sessions',
        verbose_name="ایجادکننده"
    )
    modified_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='modified_sessions',
        verbose_name="ویرایش‌کننده"
    )
    
    history = HistoricalRecords()

    class Meta:
        verbose_name = "صورت جلسه"
        verbose_name_plural = "صورت جلسات"
        ordering = ['-session_date', '-created_at']

    def __str__(self):
        return f"صورت جلسه شماره {self.session_number} - {self.price_list} برای پروژه {self.project.project_code}"
    
    @property
    def discipline_choice(self):
        """سازگاری با کدهای قدیمی - رشته را از price_list می‌گیرد"""
        return self.price_list.discipline_choice if self.price_list else None

    def save(self, *args, **kwargs):
        """Override save"""
        user = kwargs.pop('user', None)
        
        if not self.created_by:
            self.created_by = user or getattr(self, 'created_by', None)
        self.modified_by = user or getattr(self, 'modified_by', None)
        
        super().save(*args, **kwargs)    

    # ========== METODS FOR REPORTING ==========
    
    def get_items_grouped_by_pricelist(self):
        """
        گروه‌بندی آیتم‌ها بر اساس PriceListItem (برای نمایش در ویوها)
        """
        groups = OrderedDict()
        active_items = self.items.filter(is_active=True).select_related(
            'pricelist_item'
        ).order_by('pricelist_item__row_number', 'id')
        
        for item in active_items:
            pl = item.pricelist_item
            key = getattr(pl, 'row_number', None) or f"_id_{pl.pk}"
            
            if key not in groups:
                groups[key] = {
                    'pricelist_item': pl,
                    'row_number': getattr(pl, 'row_number', ''),
                    'description': getattr(pl, 'row_description', ''),
                    'unit': getattr(pl, 'unit', ''),
                    'unit_price': self._get_unit_price(pl),
                    'sub_rows': OrderedDict(),  # ردیف‌های مختلف (row_description)
                    'total_quantity': Decimal('0.00'),
                    'total_amount': Decimal('0.00'),
                }
            
            # گروه‌بندی بر اساس row_description
            row_key = item.row_description or "عمومی"
            if row_key not in groups[key]['sub_rows']:
                groups[key]['sub_rows'][row_key] = {
                    'description': row_key,
                    'items': [],
                    'sub_total_quantity': Decimal('0.00'),
                    'sub_total_amount': Decimal('0.00'),
                }
            
            item_amount = item.get_total_item_amount()
            item_total = item_amount * self._get_unit_price(pl)
            
            # اضافه کردن به زیرگروه
            groups[key]['sub_rows'][row_key]['items'].append({
                'instance': item,
                'row_description': item.row_description,
                'quantity': item_amount,
                'amount': item_total,
                'length': item.length,
                'width': item.width,
                'height': item.height,
                'weight': item.weight,
                'count': item.count,
            })
            
            groups[key]['sub_rows'][row_key]['sub_total_quantity'] += item_amount
            groups[key]['sub_rows'][row_key]['sub_total_amount'] += item_total
            
            # اضافه کردن به مجموع کل آیتم فهرست بها
            groups[key]['total_quantity'] += item_amount
            groups[key]['total_amount'] += item_total
        
        # تبدیل به لیست و فرمت کردن اعداد
        formatted_groups = []
        for key, group in groups.items():
            # فرمت کردن زیرگروه‌ها
            formatted_sub_rows = []
            for sub_key, sub_group in group['sub_rows'].items():
                formatted_sub_rows.append({
                    'description': sub_key,
                    'items': sub_group['items'],
                    'items_count': len(sub_group['items']),  # اینجا items_count را دارید
                    'sub_total_quantity': sub_group['sub_total_quantity'].quantize(Decimal('0.00')),
                    'sub_total_amount': sub_group['sub_total_amount'].quantize(Decimal('0.00')),
                    'formatted_sub_total_quantity': self._format_number(sub_group['sub_total_quantity']),
                    'formatted_sub_total_amount': self._format_number(sub_group['sub_total_amount']),
                })
            
        
        return formatted_groups
    
    def get_summary_by_pricelist(self):
        """
        خلاصه بر اساس آیتم‌های فهرست بها (بدون تفکیک ردیف)
        """
        from django.db.models import Sum
        
        summary_data = self.items.filter(is_active=True).values(
            'pricelist_item__row_number',
            'pricelist_item__description',
            'pricelist_item__unit'
        ).annotate(
            total_quantity=Sum('quantity'),
            total_amount=Sum('item_total'),
            items_count=Count('id')
        ).order_by('pricelist_item__row_number')
        
        return list(summary_data)
    
    def _get_unit_price(self, pricelist_item):
        """استخراج قیمت واحد از PriceListItem"""
        for field in ['price', 'unit_price', 'rate', 'baha']:
            if hasattr(pricelist_item, field):
                value = getattr(pricelist_item, field)
                if value is not None:
                    try:
                        return Decimal(str(value)).quantize(Decimal('0.00'))
                    except (ValueError, TypeError):
                        continue
        return Decimal('0.00')
    
    @staticmethod
    def _format_number(value):
        """فرمت کردن عدد با جداکننده فارسی"""
        try:
            v = int(value.quantize(Decimal('1')))
            return f"{v:,}".replace(",", "٬")
        except:
            return "۰"
    
    def get_session_stats(self):
        """آمار کلی صورت‌جلسه"""
        active_items = self.items.filter(is_active=True)
        unique_pricelists = active_items.values(
            'pricelist_item__row_number'
        ).distinct().count()
        
        return {
            'total_items': active_items.count(),
            'unique_pricelists': unique_pricelists,
            'disciplines': [self.discipline_choice] if self.discipline_choice else [],
            'project_name': self.project.project_name,
            'session_date_jalali': self.session_date_jalali,
        }
    
    @property
    def session_date_jalali(self):
        """تاریخ جلالی برای نمایش"""
        try:
            from jdatetime import date as jdate
            if self.session_date:
                jd = jdate.fromgregorian(date=self.session_date)
                return jd.strftime("%Y/%m/%d")
        except ImportError:
            return str(self.session_date)
        return None
    
    def delete(self, *args, **kwargs):
        """حذف نرم"""
        self.is_active = False
        self.save()

class MeasurementSessionItem(models.Model):
    """
    مدل آیتم‌های صورت‌جلسه (جزئیات متره) - هر ردیف مستقل
    """
    # روابط
    measurement_session_number = models.ForeignKey(
        MeasurementSession, 
        on_delete=models.CASCADE, 
        related_name='items',
        verbose_name="صورت‌جلسه"
    )
    pricelist_item = models.ForeignKey(
        PriceListItem, 
        on_delete=models.CASCADE, 
        related_name='session_items',
        verbose_name="آیتم فهرست بها"
    )
    
    # اطلاعات توصیفی - هر ردیف منحصر به فرد
    row_description = models.CharField(
        max_length=255, 
        verbose_name="شرح ردیف",
        help_text="توضیح خاص این متره (مثل 'دیوار غربی - طبقه ۱')"
    )
    
    # ابعاد و مقادیر
    length = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        null=True, 
        blank=True, 
        verbose_name="طول (متر)",
        validators=[MinValueValidator(Decimal('0'))],
        help_text="طول در متر"
    )
    width = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        null=True, 
        blank=True, 
        verbose_name="عرض (متر)",
        validators=[MinValueValidator(Decimal('0'))],
        help_text="عرض در متر"
    )
    height = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        null=True, 
        blank=True, 
        verbose_name="ارتفاع (متر)",
        validators=[MinValueValidator(Decimal('0'))],
        help_text="ارتفاع در متر"
    )
    weight = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        null=True, 
        blank=True, 
        verbose_name="وزن (کیلوگرم)",
        validators=[MinValueValidator(Decimal('0'))],
        help_text="وزن کل در کیلوگرم"
    )
    count = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=1,
        verbose_name="تعداد",
        validators=[MinValueValidator(Decimal('0.01'))],
        help_text="تعداد تکرار"
    )
    
    # محاسبات (برای هر ردیف جداگانه)
    quantity = models.DecimalField(
        max_digits=15, 
        decimal_places=2, 
        default=0,
        verbose_name="مقدار کل",
        help_text="مقدار محاسبه‌شده بر اساس واحد"
    )
    unit_price = models.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        default=0,
        verbose_name="قیمت واحد",
        help_text="قیمت واحد از فهرست بها"
    )
    item_total = models.DecimalField(
        max_digits=15, 
        decimal_places=2, 
        default=0,
        verbose_name="مبلغ کل ردیف",
        help_text="مقدار × قیمت واحد"
    )
    
    # یادداشت‌های اضافی
    notes = models.TextField(
        blank=True, 
        null=True, 
        verbose_name="یادداشت ردیف",
        help_text="یادداشت‌های خاص این ردیف"
    )
    
    # وضعیت
    is_active = models.BooleanField(
        default=True, 
        verbose_name="فعال/غیرفعال"
    )
    
    # لاگ‌گیری
    created_at = models.DateTimeField(
        auto_now_add=True, 
        verbose_name="زمان ایجاد"
    )
    updated_at = models.DateTimeField(
        auto_now=True, 
        verbose_name="زمان آخرین ویرایش"
    )
    created_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='created_items',
        verbose_name="ایجادکننده"
    )
    modified_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='modified_items',
        verbose_name="ویرایش‌کننده"
    )
    
    history = HistoricalRecords()
    
    class Meta:
        verbose_name = "آیتم صورت‌جلسه"
        verbose_name_plural = "آیتم‌های صورت‌جلسه"
        ordering = ['pricelist_item__row_number', 'row_description']
        unique_together = ['measurement_session_number', 'pricelist_item', 'row_description']
    
    def __str__(self):
        return f"{self.row_description[:50]}... - {self.pricelist_item.row_number}"
    
    def save(self, *args, **kwargs):
        """Override save برای محاسبات خودکار هر ردیف"""
        user = kwargs.pop('user', None)
        
        if not self.created_by:
            self.created_by = user
        self.modified_by = user
        
        # مقداردهی قیمت واحد از PriceListItem
        if not self.unit_price and self.pricelist_item:
            self.unit_price = self._get_price_from_pricelist()
        
        # محاسبه مقدار و مبلغ کل برای این ردیف
        self.quantity = self.get_total_item_amount()
        self.item_total = self.quantity * self.unit_price
        
        super().save(*args, **kwargs)
        
        # به‌روزرسانی تعداد آیتم‌های صورت‌جلسه
        if self.measurement_session_number:
            self.measurement_session_number.save(user=user)
    
    def _get_price_from_pricelist(self):
        """استخراج قیمت از PriceListItem"""
        pl = self.pricelist_item
        for field in ['price', 'unit_price', 'rate', 'baha']:
            if hasattr(pl, field):
                value = getattr(pl, field)
                if value is not None:
                    try:
                        return Decimal(str(value)).quantize(Decimal('0.00'))
                    except (ValueError, TypeError):
                        continue
        return Decimal('0.00')
    
    def get_total_item_amount(self):
        """
        محاسبه مقدار کل بر اساس واحد فهرست بها
        (سازگار با کدهای قدیمی)
        """
        if not self.pricelist_item:
            return Decimal('0.00')
        
        unit = getattr(self.pricelist_item, 'unit', '').strip().lower()
        
        if 'متر مربع' in unit or 'm²' in unit:
            return self.count * (self.length or 0) * (self.width or 0)
        elif 'متر مکعب' in unit or 'm³' in unit:
            return self.count * (self.length or 0) * (self.width or 0) * (self.height or 0)
        elif 'کیلوگرم' in unit or 'kg' in unit:
            return self.count * (self.weight or 0)
        elif 'متر' in unit or 'm' in unit:
            return self.count * (self.length or 0)
        elif 'عدد' in unit or 'ea' in unit or 'عدد' in unit:
            return self.count
        else:
            # واحد نامشخص - فقط تعداد
            return self.count
    
    @property
    def get_unit_price(self):
        """سازگاری با کدهای قدیمی"""
        return self.unit_price
    
    def delete(self, *args, **kwargs):
        """حذف نرم"""
        self.is_active = False
        self.save()
    
    def get_display_info(self):
        """اطلاعات نمایشی برای template"""
        return {
            'row_number': getattr(self.pricelist_item, 'row_number', ''),
            'description': getattr(self.pricelist_item, 'description', ''),
            'unit': getattr(self.pricelist_item, 'unit', ''),
            'row_description': self.row_description,
            'quantity': self.quantity,
            'unit_price': self.unit_price,
            'item_total': self.item_total,
            'formatted_quantity': self._format_number(self.quantity),
            'formatted_unit_price': self._format_number(self.unit_price),
            'formatted_item_total': self._format_number(self.item_total),
        }
    
    @staticmethod
    def _format_number(value):
        """فرمت کردن عدد با جداکننده فارسی"""
        try:
            v = int(value.quantize(Decimal('1')))
            return f"{v:,}".replace(",", "٬")
        except:
            return "۰"

# مدل برای ثبت تغییرات متره با خط خوردگی
class MeasurementRevision(models.Model):
    """
    مدل برای ثبت نسخه‌های مختلف آیتم‌های متره
    """
    measurement_item = models.ForeignKey(
        'MeasurementSessionItem',
        on_delete=models.CASCADE,
        related_name='revisions',
        verbose_name=_('آیتم متره')
    )
    
    # کاربر ویرایش‌کننده
    edited_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='measurement_revisions',
        verbose_name=_('ویرایش‌کننده')
    )
    
    # نقش کاربر در زمان ویرایش
    user_role = models.ForeignKey(
        ProjectRole,
        on_delete=models.PROTECT,
        verbose_name=_('نقش ویرایش‌کننده')
    )
    
    # داده‌های قدیمی
    old_length = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True,
        verbose_name=_('طول قبلی')
    )
    old_width = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True,
        verbose_name=_('عرض قبلی')
    )
    old_height = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True,
        verbose_name=_('ارتفاع قبلی')
    )
    old_count = models.DecimalField(
        max_digits=10, decimal_places=2, default=1,
        verbose_name=_('تعداد قبلی')
    )
    old_quantity = models.DecimalField(
        max_digits=15, decimal_places=2, default=0,
        verbose_name=_('مقدار قبلی')
    )
    
    # دلیل ویرایش
    revision_reason = models.TextField(
        blank=True,
        null=True,
        verbose_name=_('دلیل ویرایش')
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = _('نسخه متره')
        verbose_name_plural = _('نسخه‌های متره')
        ordering = ['-created_at']
    
    def __str__(self):
        return f"تغییر توسط {self.edited_by.username} - {self.created_at}"

class DetailedMeasurement(models.Model):
    """
    مدل ریز متره کل - مجموع‌گیری از تمام صورت‌جلسات بر اساس آیتم فهرست بها
    """
    price_list_item = models.OneToOneField(
        PriceListItem, 
        on_delete=models.CASCADE, 
        related_name='detailed_measurement',
        verbose_name="آیتم فهرست بها"
    )
    
    # مجموع‌ها از تمام صورت‌جلسات (بر اساس آیتم فهرست بها)
    total_quantity = models.DecimalField(
        max_digits=15, 
        decimal_places=2, 
        default=0, 
        verbose_name="مجموع مقدار کل",
        help_text="مجموع مقادیر از تمام صورت‌جلسات برای این آیتم"
    )
    total_amount = models.DecimalField(
        max_digits=18, 
        decimal_places=2, 
        default=0, 
        verbose_name="مجموع مبلغ کل",
        help_text="مجموع مبالغ از تمام صورت‌جلسات برای این آیتم"
    )
    
    # آمار تفصیلی
    sessions_count = models.PositiveIntegerField(
        default=0, 
        verbose_name="تعداد صورت‌جلسات",
        help_text="تعداد صورت‌جلساتی که این آیتم در آن استفاده شده"
    )
    items_count = models.PositiveIntegerField(
        default=0, 
        verbose_name="تعداد ردیف‌ها",
        help_text="تعداد کل ردیف‌های مرتبط با این آیتم"
    )
    projects_count = models.PositiveIntegerField(
        default=0, 
        verbose_name="تعداد پروژه‌ها",
        help_text="تعداد پروژه‌های مختلف"
    )
    
    # فیلدهای کمکی
    unit_price = models.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        default=0,
        verbose_name="قیمت واحد",
        help_text="قیمت واحد از فهرست بها"
    )
    last_updated = models.DateTimeField(
        auto_now=True,
        verbose_name="آخرین به‌روزرسانی"
    )
    
    # لاگ‌گیری
    created_at = models.DateTimeField(auto_now_add=True)
    history = HistoricalRecords()
    
    class Meta:
        verbose_name = "ریز متره کل"
        verbose_name_plural = "ریز متره‌های کل"
        ordering = ['price_list_item__row_number']
    
    def __str__(self):
        return f"ریز متره {self.price_list_item.row_number} - {self.total_quantity}"
    
    def update_from_sessions(self, projects=None):
        """
        به‌روزرسانی از sessions - با فیلتر projects
        """
        from .models import MeasurementSessionItem
        
        if not self.price_list_item:
            return
        
        # فیلتر projects اگر مشخص شده
        if projects:
            items = MeasurementSessionItem.objects.filter(
                measurement_session_number__project__in=projects,
                pricelist_item=self.price_list_item,
                is_active=True
            )
        else:
            items = MeasurementSessionItem.objects.filter(
                pricelist_item=self.price_list_item,
                is_active=True
            )
        # محاسبه مجموع‌ها
        total_qty = sum(item.get_total_item_amount() or 0 for item in items)
        
        # آمار اضافی
        sessions_count = items.values('measurement_session_number').distinct().count()
        projects_count = items.values('measurement_session_number__project').distinct().count()
        
        self.total_quantity = total_qty
        self.sessions_count = sessions_count
        self.projects_count = projects_count
        self.last_updated = timezone.now()
        
        self.save(update_fields=[
            'total_quantity', 'sessions_count', 'projects_count', 'last_updated'
        ])
    
    def _get_unit_price(self):
        """استخراج قیمت واحد"""
        pl = self.price_list_item
        for field in ['price', 'unit_price', 'rate', 'baha']:
            if hasattr(pl, field):
                value = getattr(pl, field)
                if value is not None:
                    try:
                        return Decimal(str(value)).quantize(Decimal('0.00'))
                    except (ValueError, TypeError):
                        continue
        return Decimal('0.00')
    
    def get_breakdown_by_session(self):
        """تفکیک بر اساس صورت‌جلسات"""
        from django.db.models import Sum
        
        return MeasurementSessionItem.objects.filter(
            pricelist_item=self.price_list_item,
            is_active=True,
            measurement_session_number__is_active=True
        ).values(
            'measurement_session_number__session_number',
            'measurement_session_number__session_date'
        ).annotate(
            session_qty=Sum('quantity'),
            session_amount=Sum('item_total'),
            row_count=Count('id')
        ).order_by('-measurement_session_number__session_date')
    
    def get_display_info(self):
        """اطلاعات نمایشی"""
        return {
            'row_number': getattr(self.price_list_item, 'row_number', ''),
            'description': getattr(self.price_list_item, 'description', ''),
            'unit': getattr(self.price_list_item, 'unit', ''),
            'total_quantity': self.total_quantity,
            'unit_price': self.unit_price,
            'total_amount': self.total_amount,
            'formatted_total_quantity': self._format_number(self.total_quantity),
            'formatted_unit_price': self._format_number(self.unit_price),
            'formatted_total_amount': self._format_number(self.total_amount),
            'sessions_count': self.sessions_count,
            'items_count': self.items_count,
        }
    
    @staticmethod
    def _format_number(value):
        """فرمت کردن عدد"""
        try:
            v = int(value.quantize(Decimal('1')))
            return f"{v:,}".replace(",", "٬")
        except:
            return "۰"

class FinancialStatus(models.Model):
    """
    مدل صورت وضعیت مالی - خلاصه مالی هر صورت‌جلسه
    """
    measurement_session = models.OneToOneField(
        MeasurementSession, 
        on_delete=models.CASCADE, 
        related_name='financial_status',
        verbose_name="صورت‌جلسه مرتبط"
    )
    
    # مجموع‌های مالی (محاسبه‌شده از آیتم‌ها)
    total_quantity = models.DecimalField(
        max_digits=15, 
        decimal_places=2, 
        default=0,
        verbose_name="مجموع مقدار",
        help_text="مجموع کل مقادیر تمام آیتم‌های صورت‌جلسه"
    )
    total_amount = models.DecimalField(
        max_digits=18, 
        decimal_places=2, 
        default=0,
        verbose_name="مجموع مبلغ",
        help_text="مجموع کل مبالغ تمام آیتم‌های صورت‌جلسه"
    )
    
    # آمار تفصیلی
    active_items_count = models.PositiveIntegerField(
        default=0, 
        verbose_name="تعداد آیتم‌های فعال",
        help_text="تعداد کل آیتم‌های فعال"
    )
    unique_pricelist_items_count = models.PositiveIntegerField(
        default=0, 
        verbose_name="تعداد آیتم‌های منحصر به فرد فهرست بها",
        help_text="تعداد آیتم‌های مختلف فهرست بها"
    )
    
    # تفکیک بر اساس ردیف‌های مختلف (اختیاری - برای صورت‌جلسات خاص)
    row_descriptions_count = models.PositiveIntegerField(
        default=0, 
        verbose_name="تعداد ردیف‌های توصیفی",
        help_text="تعداد توضیحات مختلف (row_description)"
    )
    
    # اطلاعات اضافی
    vat_rate = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        default=9.00,  # 9% مالیات بر ارزش افزوده
        verbose_name="نرخ مالیات",
        help_text="نرخ VAT"
    )
    total_with_vat = models.DecimalField(
        max_digits=18, 
        decimal_places=2, 
        default=0,
        verbose_name="مجموع با مالیات",
        help_text="مجموع مبلغ + مالیات"
    )
    
    # وضعیت
    is_approved = models.BooleanField(
        default=False, 
        verbose_name="تایید شده",
        help_text="وضعیت تایید صورت‌جلسه"
    )
    approval_date = models.DateField(
        null=True, 
        blank=True, 
        verbose_name="تاریخ تایید"
    )
    approved_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='approved_statuses',
        verbose_name="تاییدکننده"
    )
    
    # لاگ‌گیری
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_calculated_at = models.DateTimeField(
        auto_now=True, 
        verbose_name="آخرین محاسبه"
    )
    
    history = HistoricalRecords()
    
    class Meta:
        verbose_name = "صورت وضعیت مالی"
        verbose_name_plural = "صورت‌های وضعیت مالی"
        ordering = ['-measurement_session__created_at']
    
    def __str__(self):
        return f"صورت وضعیت - {self.measurement_session.session_number}"
    
    def calculate_totals(self):
        """محاسبه مجموع‌ها از آیتم‌های مرتبط"""
        from django.db.models import Sum, Count
        
        # محاسبه از MeasurementSessionItem های فعال
        summary = self.measurement_session.items.filter(
            is_active=True
        ).aggregate(
            total_qty=Sum('quantity'),
            total_amt=Sum('item_total'),
            items_count=Count('id'),
            unique_pl_count=Count('pricelist_item', distinct=True),
            unique_row_count=Count('row_description', filter=models.Q(row_description__isnull=False) & models.Q(row_description__neq=''), distinct=True)
        )
        
        # به‌روزرسانی فیلدها
        self.total_quantity = summary['total_qty'] or Decimal('0.00')
        self.total_amount = summary['total_amt'] or Decimal('0.00')
        self.active_items_count = summary['items_count'] or 0
        self.unique_pricelist_items_count = summary['unique_pl_count'] or 0
        self.row_descriptions_count = summary['unique_row_count'] or 0
        
        # محاسبه مالیات
        self.total_with_vat = self.total_amount * (1 + (self.vat_rate / 100))
        
        self.last_calculated_at = timezone.now()
    
    def get_formatted_totals(self):
        """فرمت کردن اعداد برای نمایش"""
        return {
            'total_quantity': self._format_number(self.total_quantity),
            'total_amount': self._format_number(self.total_amount),
            'total_with_vat': self._format_number(self.total_with_vat),
            'vat_amount': self._format_number(self.total_with_vat - self.total_amount),
        }
    
    def get_session_date_jalali(self):
        """تاریخ جلالی"""
        try:
            if self.measurement_session.session_date:
                jd = jdatetime.date.fromgregorian(date=self.measurement_session.session_date)
                return jd.strftime("%Y/%m/%d")
        except:
            pass
        return None
    
    @staticmethod
    def _format_number(value):
        """فرمت عدد فارسی"""
        try:
            v = int(value.quantize(Decimal('1')))
            return f"{v:,}".replace(",", "٬")
        except:
            return "۰"
    
    def save(self, *args, **kwargs):
        """محاسبه خودکار قبل از ذخیره"""
        self.calculate_totals()
        super().save(*args, **kwargs)

    def initialize_from_session(self):
        """ایجاد اولیه از session"""
        if not self.measurement_session:
            return
        
        self.total_quantity = Decimal('0')
        self.total_amount = Decimal('0')
        self.item_count = 0
        
        # محاسبه از آیتم‌ها
        self.recalculate_totals()
        
    def recalculate_totals(self):
        """محاسبه مجدد مجموع‌ها"""
        from .models import MeasurementSessionItem
        
        if not self.measurement_session:
            return
        
        active_items = MeasurementSessionItem.objects.filter(
            measurement_session_number=self.measurement_session,
            is_active=True
        )
        
        self.total_quantity = sum(
            item.get_total_item_amount() or 0 for item in active_items
        )
        self.total_amount = Decimal('0')
        self.item_count = active_items.count()
        
        # محاسبه مبلغ کل
        for item in active_items:
            if item.pricelist_item:
                qty = item.get_total_item_amount() or 0
                unit_price = self._get_unit_price(item.pricelist_item)
                self.total_amount += Decimal(qty) * Decimal(unit_price or 0)
        
        self.updated_at = timezone.now()
        self.save(update_fields=[
            'total_quantity', 'total_amount', 'item_count', 'updated_at'
        ])
    
    def _get_unit_price(self, price_list_item):
        """استخراج قیمت واحد"""
        for field in ['price', 'unit_price', 'rate', 'baha']:
            if hasattr(price_list_item, field):
                value = getattr(price_list_item, field)
                if value is not None:
                    try:
                        return Decimal(str(value))
                    except:
                        continue
        return Decimal('0')

    def recalculate_from_items(self, projects=None):
        """Recalculate totals from session items"""
        self.total_quantity = self.measurement_session.items.filter(
            is_active=True
        ).aggregate(total=models.Sum('quantity'))['total'] or 0
        
        self.total_amount = self.measurement_session.items.filter(
            is_active=True
        ).aggregate(total=models.Sum('amount'))['total'] or 0
        
        self.updated_at = timezone.now()
        self.save(update_fields=['total_quantity', 'total_amount', 'updated_at'])
        
class ProjectFinancialSummary(models.Model):
    """
    مدل خلاصه مالی پروژه - مجموع‌گیری از تمام صورت‌جلسات پروژه
    """
    project = models.OneToOneField(
        Project, 
        on_delete=models.CASCADE, 
        related_name='financial_summary',
        verbose_name="پروژه مرتبط"
    )
    
    # مجموع‌های کل پروژه
    total_quantity = models.DecimalField(
        max_digits=15, 
        decimal_places=2, 
        default=0,
        verbose_name="مجموع کل مقدار",
        help_text="مجموع کل مقادیر تمام صورت‌جلسات"
    )
    total_amount = models.DecimalField(
        max_digits=18, 
        decimal_places=2, 
        default=0,
        verbose_name="مجموع کل مبلغ",
        help_text="مجموع کل مبالغ تمام صورت‌جلسات"
    )
    total_with_vat = models.DecimalField(
        max_digits=18, 
        decimal_places=2, 
        default=0,
        verbose_name="مجموع کل با مالیات",
        help_text="مجموع کل + مالیات"
    )
    
    # تفکیک بر اساس رشته‌ها
    total_quantity_abnieh = models.DecimalField(max_digits=15, decimal_places=2, default=0, verbose_name="مجموع ابنیه")
    total_amount_abnieh = models.DecimalField(max_digits=18, decimal_places=2, default=0, verbose_name="مبلغ ابنیه")
    
    total_quantity_mekanik = models.DecimalField(max_digits=15, decimal_places=2, default=0, verbose_name="مجموع مکانیک")
    total_amount_mekanik = models.DecimalField(max_digits=18, decimal_places=2, default=0, verbose_name="مبلغ مکانیک")
    
    total_quantity_bargh = models.DecimalField(max_digits=15, decimal_places=2, default=0, verbose_name="مجموع برق")
    total_amount_bargh = models.DecimalField(max_digits=18, decimal_places=2, default=0, verbose_name="مبلغ برق")
    
    # آمار کلی
    sessions_count = models.PositiveIntegerField(
        default=0, 
        verbose_name="تعداد صورت‌جلسات"
    )
    approved_sessions_count = models.PositiveIntegerField(
        default=0, 
        verbose_name="تعداد صورت‌جلسات تایید شده"
    )
    total_items_count = models.PositiveIntegerField(
        default=0, 
        verbose_name="تعداد کل آیتم‌ها"
    )
    unique_pricelist_items_count = models.PositiveIntegerField(
        default=0, 
        verbose_name="تعداد آیتم‌های منحصر به فرد فهرست بها"
    )
    
    # پیشرفت پروژه
    progress_percentage = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        default=0,
        verbose_name="درصد پیشرفت",
        help_text="بر اساس نسبت مبلغ متره به مبلغ قرارداد"
    )
    
    # اطلاعات اضافی
    vat_rate = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        default=9.00,
        verbose_name="نرخ مالیات"
    )
    
    # وضعیت
    last_updated = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    history = HistoricalRecords()
    
    class Meta:
        verbose_name = "خلاصه مالی پروژه"
        verbose_name_plural = "خلاصه‌های مالی پروژه‌ها"
        ordering = ['-last_updated']
    
    def __str__(self):
        return f"خلاصه مالی - {self.project.project_name}"
    
    def calculate_project_totals(self):
        """محاسبه مجموع‌های پروژه از تمام صورت‌جلسات"""
        # مجموع کل
        total_summary = FinancialStatus.objects.filter(
            measurement_session__project=self.project,
            measurement_session__is_active=True
        ).aggregate(
            total_qty=Sum('total_quantity'),
            total_amt=Sum('total_amount'),
            total_vat=Sum('total_with_vat'),
            sessions_count=Count('id'),
            approved_count=Count('id', filter=models.Q(is_approved=True)),
            items_count=Sum('active_items_count'),
            unique_items=Count('measurement_session__items__pricelist_item', distinct=True, filter=models.Q(measurement_session__items__is_active=True))
        )
        
        self.total_quantity = total_summary['total_qty'] or Decimal('0.00')
        self.total_amount = total_summary['total_amt'] or Decimal('0.00')
        self.total_with_vat = total_summary['total_vat'] or Decimal('0.00')
        self.sessions_count = total_summary['sessions_count'] or 0
        self.approved_sessions_count = total_summary['approved_count'] or 0
        self.total_items_count = total_summary['items_count'] or 0
        self.unique_pricelist_items_count = total_summary['unique_items'] or 0
        
        # تفکیک بر اساس رشته‌ها
        disciplines_summary = FinancialStatus.objects.filter(
            measurement_session__project=self.project,
            measurement_session__is_active=True
        ).values('measurement_session__discipline_choice').annotate(
            total_qty=Sum('total_quantity'),
            total_amt=Sum('total_amount')
        )
        
        for disc in disciplines_summary:
            discipline = disc['measurement_session__discipline_choice']
            qty = disc['total_qty'] or Decimal('0.00')
            amt = disc['total_amt'] or Decimal('0.00')
            
            if discipline == 'ab':
                self.total_quantity_abnieh = qty
                self.total_amount_abnieh = amt
            elif discipline == 'mk':
                self.total_quantity_mekanik = qty
                self.total_amount_mekanik = amt
            elif discipline == 'br':
                self.total_quantity_bargh = qty
                self.total_amount_bargh = amt
        
        # محاسبه درصد پیشرفت (نسبت به مبلغ قرارداد)
        contract_amount = self.project.total_contract_amount or Decimal('0.00')
        if contract_amount > 0:
            self.progress_percentage = (self.total_amount / contract_amount) * 100
        else:
            self.progress_percentage = Decimal('0.00')
        
        self.vat_rate = Decimal('9.00')  # ثابت یا از تنظیمات
    
    def get_discipline_breakdown(self):
        """تفکیک رشته‌ها برای نمایش"""
        return {
            'abnieh': {
                'quantity': self.total_quantity_abnieh,
                'amount': self.total_amount_abnieh,
                'formatted_quantity': self._format_number(self.total_quantity_abnieh),
                'formatted_amount': self._format_number(self.total_amount_abnieh),
                'label': 'ابنیه'
            },
            'mekanik': {
                'quantity': self.total_quantity_mekanik,
                'amount': self.total_amount_mekanik,
                'formatted_quantity': self._format_number(self.total_quantity_mekanik),
                'formatted_amount': self._format_number(self.total_amount_mekanik),
                'label': 'مکانیک'
            },
            'bargh': {
                'quantity': self.total_quantity_bargh,
                'amount': self.total_amount_bargh,
                'formatted_quantity': self._format_number(self.total_quantity_bargh),
                'formatted_amount': self._format_number(self.total_amount_bargh),
                'label': 'برق'
            }
        }
    
    def get_progress_info(self):
        """اطلاعات پیشرفت"""
        contract_amount = self.project.total_contract_amount or Decimal('0.00')
        remaining_amount = contract_amount - self.total_amount
        
        return {
            'current_amount': self.total_amount,
            'contract_amount': contract_amount,
            'remaining_amount': remaining_amount,
            'progress_percentage': min(self.progress_percentage, 100),
            'formatted_current': self._format_number(self.total_amount),
            'formatted_contract': self._format_number(contract_amount),
            'formatted_remaining': self._format_number(remaining_amount),
        }
    
    @staticmethod
    def _format_number(value):
        """فرمت عدد"""
        try:
            v = int(value.quantize(Decimal('1')))
            return f"{v:,}".replace(",", "٬")
        except:
            return "۰"
    
    def save(self, *args, **kwargs):
        """محاسبه خودکار قبل از ذخیره"""
        self.calculate_project_totals()
        super().save(*args, **kwargs)

    def initialize_from_project(self):
        """ایجاد اولیه از پروژه"""
        self.total_contract_amount = self.project.total_contract_amount or Decimal('0')
        self.total_quantity = Decimal('0')
        self.total_amount = Decimal('0')
        self.progress_percentage = Decimal('0')
        self.updated_at = timezone.now()
        self.save(update_fields=[
            'total_contract_amount', 'total_quantity', 'total_amount', 
            'progress_percentage', 'updated_at'
        ])

    def recalculate_from_sessions(self):
        """محاسبه مجدد از تمام sessions"""
        
        sessions = self.project.measurementsession_set.filter(is_active=True)
        total_qty = Decimal('0')
        total_amt = Decimal('0')
        session_count = 0
        
        for session in sessions:
            status = session.financial_status
            if status:
                total_qty += status.total_quantity or Decimal('0')
                total_amt += status.total_amount or Decimal('0')
                session_count += 1
        
        self.total_quantity = total_qty
        self.total_amount = total_amt
        self.session_count = session_count
        
        # محاسبه پیشرفت
        contract_amount = self.project.total_contract_amount or Decimal('1')
        self.progress_percentage = (
            (total_amt / contract_amount * Decimal('100')).quantize(Decimal('0.01'))
        ) if contract_amount > 0 else Decimal('0')
        
        # ← این خط اصلاح شد - هم‌تراز با خط‌های قبلی
        self.last_updated = timezone.now()
        
        self.save(update_fields=[
            'total_quantity', 'total_amount', 'session_count', 
            'progress_percentage', 'last_updated'
        ])

    def update_from_status(self, financial_statuses):
        """به‌روزرسانی از لیست status ها"""
        if not financial_statuses:
            return
        
        total_qty = sum(fs.total_quantity or Decimal('0') for fs in financial_statuses)
        total_amt = sum(fs.total_amount or Decimal('0') for fs in financial_statuses)
        
        self.total_quantity = total_qty
        self.total_amount = total_amt
        self.last_updated = timezone.now()
        self.save(update_fields=['total_quantity', 'total_amount', 'last_updated'])

    def calculate_project_totals(self):
        """محاسبه آمار اضافی"""
        # تعداد آیتم‌ها
        self.item_count = self.project.measurementsessionitem_set.filter(
            is_active=True
        ).count()
        
        # به‌روزرسانی زمان
        if not self.last_updated:
            self.last_updated = timezone.now()
    
    @property
    def formatted_total_amount(self):
        """نمایش فرمت‌شده مبلغ کل"""
        return self._format_number(self.total_amount)
    
    @property
    def formatted_progress(self):
        """نمایش فرمت‌شده پیشرفت"""
        return f"{self.progress_percentage:.1f}%"

class DetailedFinancialReport(models.Model):
    """
    مدل ریز مالی - جزئیات کامل هر آیتم فهرست بها در تمام صورت‌جلسات
    """
    price_list_item = models.ForeignKey(
        PriceListItem, 
        on_delete=models.CASCADE, 
        related_name='financial_report',
        verbose_name="آیتم فهرست بها"
    )
    project = models.ForeignKey(
        Project, 
        on_delete=models.CASCADE, 
        related_name='detailed_financial_reports',
        verbose_name="پروژه"
    )
    
    # مجموع‌های مالی برای این آیتم در این پروژه
    total_quantity = models.DecimalField(
        max_digits=15, 
        decimal_places=2, 
        default=0,
        verbose_name="مجموع مقدار"
    )
    total_amount = models.DecimalField(
        max_digits=18, 
        decimal_places=2, 
        default=0,
        verbose_name="مجموع مبلغ"
    )
    total_with_vat = models.DecimalField(
        max_digits=18, 
        decimal_places=2, 
        default=0,
        verbose_name="مجموع با مالیات"
    )
    
    # تفکیک بر اساس صورت‌جلسات
    sessions_count = models.PositiveIntegerField(
        default=0, 
        verbose_name="تعداد صورت‌جلسات"
    )
    approved_sessions_count = models.PositiveIntegerField(
        default=0, 
        verbose_name="تعداد صورت‌جلسات تایید شده"
    )
    items_count = models.PositiveIntegerField(
        default=0, 
        verbose_name="تعداد ردیف‌ها"
    )
    
    # اطلاعات واحد
    unit_price = models.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        default=0,
        verbose_name="قیمت واحد"
    )
    unit = models.CharField(
        max_length=20, 
        verbose_name="واحد"
    )
    row_description = models.CharField(
        max_length=255, 
        verbose_name="شرح ردیف",
        help_text="توضیح کلی (اگر یکسان برای همه)"
    )
    
    # آمار زمانی
    first_used_at = models.DateField(
        null=True, 
        blank=True, 
        verbose_name="اولین استفاده"
    )
    last_used_at = models.DateField(
        null=True, 
        blank=True, 
        verbose_name="آخرین استفاده"
    )
    
    # لاگ‌گیری
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_calculated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "ریز مالی"
        verbose_name_plural = "ریزهای مالی"
        unique_together = ['price_list_item', 'project']
        ordering = ['price_list_item__row_number']
    
    def __str__(self):
        return f"ریز مالی {self.price_list_item.row_number} - {self.project.project_name}"
    
    def calculate_item_financials(self):
        """محاسبه جزئیات مالی برای این آیتم"""
        from django.db.models import Sum, Count, Min, Max
        
        # محاسبه از MeasurementSessionItem ها
        items_summary = MeasurementSessionItem.objects.filter(
            pricelist_item=self.price_list_item,
            measurement_session_number__project=self.project,
            is_active=True,
            measurement_session_number__is_active=True
        ).aggregate(
            total_qty=Sum('quantity'),
            total_amt=Sum('item_total'),
            item_count=Count('id'),
            session_count=Count('measurement_session_number', distinct=True),
            approved_session_count=Count('measurement_session_number', filter=models.Q(measurement_session_number__financial_status__is_approved=True), distinct=True),
            first_date=Min('measurement_session_number__session_date'),
            last_date=Max('measurement_session_number__session_date')
        )
        
        # اطلاعات واحد
        self.unit_price = self._get_unit_price()
        self.unit = getattr(self.price_list_item, 'unit', '')
        self.row_description = getattr(self.price_list_item, 'row_description', '')
        
        # مجموع‌ها
        self.total_quantity = items_summary['total_qty'] or Decimal('0.00')
        self.total_amount = items_summary['total_amt'] or Decimal('0.00')
        self.total_with_vat = self.total_amount * 1.09  # 9% VAT
        
        # آمار
        self.items_count = items_summary['item_count'] or 0
        self.sessions_count = items_summary['session_count'] or 0
        self.approved_sessions_count = items_summary['approved_session_count'] or 0
        
        # تاریخ‌ها
        self.first_used_at = items_summary['first_date']
        self.last_used_at = items_summary['last_date']
    
    def _get_unit_price(self):
        """استخراج قیمت واحد"""
        pl = self.price_list_item
        for field in ['price', 'unit_price', 'rate', 'baha']:
            if hasattr(pl, field):
                value = getattr(pl, field)
                if value is not None:
                    try:
                        return Decimal(str(value)).quantize(Decimal('0.00'))
                    except:
                        continue
        return Decimal('0.00')
    
    def get_session_breakdown(self):
        """تفکیک بر اساس صورت‌جلسات"""
        return MeasurementSessionItem.objects.filter(
            pricelist_item=self.price_list_item,
            measurement_session_number__project=self.project,
            is_active=True,
            measurement_session_number__is_active=True
        ).select_related(
            'measurement_session_number',
            'measurement_session_number__financial_status'
        ).values(
            'measurement_session_number__session_number',
            'measurement_session_number__session_date',
            'measurement_session_number__financial_status__is_approved'
        ).annotate(
            session_qty=Sum('quantity'),
            session_amount=Sum('item_total'),
            row_count=Count('id')
        ).order_by('-measurement_session_number__session_date')
    
    def get_formatted_values(self):
        """فرمت کردن برای نمایش"""
        return {
            'total_quantity': self._format_number(self.total_quantity),
            'total_amount': self._format_number(self.total_amount),
            'total_with_vat': self._format_number(self.total_with_vat),
            'unit_price': self._format_number(self.unit_price),
        }
    
    @staticmethod
    def _format_number(value):
        """فرمت عدد"""
        try:
            v = int(value.quantize(Decimal('1')))
            return f"{v:,}".replace(",", "٬")
        except:
            return "۰"
    
    def save(self, *args, **kwargs):
        """محاسبه خودکار"""
        self.calculate_item_financials()
        super().save(*args, **kwargs)

# ========== TOOLS HELPER CLASSES ==========
class DetailedFinancialReport(models.Model):
    # ... existing fields ...
    
    def initialize_from_item(self):
        """ایجاد اولیه از آیتم"""
        self.total_quantity = Decimal('0')
        self.total_amount = Decimal('0')
        self.updated_at = timezone.now()
        self.save(update_fields=['total_quantity', 'total_amount', 'updated_at'])
    
    def update_amounts(self):
        """به‌روزرسانی مقادیر از آیتم‌های session"""
        from .models import MeasurementSessionItem
        
        if not self.price_list_item or not self.project:
            return
        
        # جمع‌آوری از تمام sessions پروژه
        items = MeasurementSessionItem.objects.filter(
            measurement_session_number__project=self.project,
            pricelist_item=self.price_list_item,
            is_active=True
        )
        total_qty = sum(item.get_total_item_amount() or 0 for item in items)
        unit_price = self._get_unit_price()
        total_amt = total_qty * unit_price
        
        self.total_quantity = total_qty
        self.total_amount = total_amt
        self.item_count = items.count()
        self.updated_at = timezone.now()
        
        self.save(update_fields=[
            'total_quantity', 'total_amount', 'item_count', 'updated_at'
        ])
    
    def _get_unit_price(self):
        """استخراج قیمت واحد"""
        if not self.price_list_item:
            return Decimal('0')
        
        for field in ['price', 'unit_price', 'rate', 'baha']:
            if hasattr(self.price_list_item, field):
                value = getattr(self.price_list_item, field)
                if value is not None:
                    try:
                        return Decimal(str(value))
                    except:
                        continue
        return Decimal('0')

class FinancialReportGenerator:
    """
    کلاس کمکی برای تولید گزارش‌های مالی
    """
    @staticmethod
    def get_project_financial_overview(project_id):
        """دریافت خلاصه مالی پروژه (سریع - بدون محاسبه)"""
        try:
            summary = ProjectFinancialSummary.objects.get(project_id=project_id)
            return {
                'total_quantity': summary.total_quantity,
                'total_amount': summary.total_amount,
                'total_with_vat': summary.total_with_vat,
                'progress_percentage': summary.progress_percentage,
                'sessions_count': summary.sessions_count,
                'approved_sessions_count': summary.approved_sessions_count,
                'discipline_breakdown': summary.get_discipline_breakdown(),
                'progress_info': summary.get_progress_info(),
                'last_updated': summary.last_updated,
            }
        except ProjectFinancialSummary.DoesNotExist:
            return None
    
    @staticmethod
    def get_session_financial_status(session_id):
        """دریافت صورت وضعیت مالی (سریع)"""
        try:
            status = FinancialStatus.objects.get(measurement_session_id=session_id)
            return {
                'total_quantity': status.total_quantity,
                'total_amount': status.total_amount,
                'total_with_vat': status.total_with_vat,
                'active_items_count': status.active_items_count,
                'is_approved': status.is_approved,
                'formatted_totals': status.get_formatted_totals(),
                'session_date_jalali': status.get_session_date_jalali(),
                'last_calculated': status.last_calculated_at,
            }
        except FinancialStatus.DoesNotExist:
            return None
    
    @staticmethod
    def get_detailed_financial_report(project_id, discipline_choice=None):
        """دریافت ریز مالی (فیلتر شده بر اساس رشته)"""
        queryset = DetailedFinancialReport.objects.filter(project_id=project_id)
        
        if discipline_choice:
            # فیلتر بر اساس رشته (از PriceListItem)
            price_list_items = PriceListItem.objects.filter(
                price_list__discipline_choice=discipline_choice
            ).values_list('id', flat=True)
            queryset = queryset.filter(price_list_item__id__in=price_list_items)
        
        reports = []
        for report in queryset.select_related('price_list_item', 'project').order_by('price_list_item__row_number'):
            reports.append({
                'row_number': getattr(report.price_list_item, 'row_number', ''),
                'description': getattr(report.price_list_item, 'description', ''),
                'unit': report.unit,
                'total_quantity': report.total_quantity,
                'unit_price': report.unit_price,
                'total_amount': report.total_amount,
                'sessions_count': report.sessions_count,
                'items_count': report.items_count,
                'formatted_values': report.get_formatted_values(),
                'last_used': report.last_used_at,
            })
        
        return reports