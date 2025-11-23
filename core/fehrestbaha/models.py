# fehrestbaha/models.py

from django.db import models
from django.utils import timezone
from django.core.validators import MinValueValidator
from django.utils.translation import gettext_lazy as _
from simple_history.models import HistoricalRecords

class DisciplineChoices(models.TextChoices):
    # رشته‌های صورت وضعیت (می‌تونی اضافه کنی)
    ABANIE = 'AB', 'ابنیه'
    MECHANIC = 'ME', 'مکانیک'
    ELECTRIC = 'EL', 'برق'
    OTHER = 'OT', 'سایر'

class PriceList(models.Model):
    discipline_choice = models.CharField(
        max_length=2, 
        choices=DisciplineChoices.choices, 
        verbose_name=_("رشته")
    )
    discipline = models.CharField(
        max_length=100, 
        verbose_name=_("نسخه فهرست بها"),
        help_text=_("مثلاً: ابنیه ۱۴۰۲، مکانیک ۱۴۰۰")
    )    
    year = models.IntegerField(
        verbose_name=_("سال فهرست بها"), 
        null=True, 
        blank=True,
        help_text=_("سال انتشار فهرست بها")
    )

    # logging
    # لاگ‌گیری
    created_at = models.DateTimeField(
        auto_now_add=True, 
        verbose_name=_("زمان ایجاد")
    )
    updated_at = models.DateTimeField(
        auto_now=True, 
        verbose_name=_("زمان آخرین ویرایش")
    )
    is_active = models.BooleanField(
        default=True, 
        verbose_name=_("فعال/غیرفعال")
    )
    modified_by = models.ForeignKey(
        'auth.User', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        verbose_name=_("ویرایش‌کننده")
    )
    history = HistoricalRecords()

    class Meta:
        verbose_name = _("فهرست بها")
        verbose_name_plural = _("فهرست‌های بها")
        ordering = ['-year', 'discipline_choice', 'discipline']
        unique_together = ['discipline_choice', 'discipline', 'year']
        indexes = [
            models.Index(fields=['discipline_choice', 'is_active']),
            models.Index(fields=['year', 'is_active']),
        ]

    def __str__(self):
        year_str = f" - {self.year}" if self.year else ""
        return f"{self.get_discipline_choice_display()} - {self.discipline}{year_str}"
    
    def save(self, *args, **kwargs):
        """ذخیره با مدیریت user"""
        user = kwargs.pop('user', None)
        if user and not self.modified_by:
            self.modified_by = user
        super().save(*args, **kwargs)
    
    @property
    def active_items_count(self):
        """تعداد آیتم‌های فعال"""
        return self.items.filter(is_active=True).count()
    
    @property
    def active_items_count(self):
        return self.items.filter(is_active=True).count()
    
    def export_to_excel(self):
        """صادر کردن آیتم‌های فهرست بها به اکسل"""
        items = self.items.filter(is_active=True).order_by('row_number')
        
        data = []
        for item in items:
            data.append({
                'شماره ردیف': item.row_number,
                'شرح': item.description,
                'قیمت واحد (ریال)': float(item.price),
                'واحد': item.unit,
                'ستاره‌دار': 'بله' if item.is_starred else 'خیر'
            })
        
        df = pd.DataFrame(data)
        
        # ایجاد نام فایل
        filename = f"فهرست_بها_{self.discipline}_{self.year or 'بدون_سال'}.xlsx"
        filepath = os.path.join(settings.MEDIA_ROOT, 'exports', filename)
        
        # اطمینان از وجود پوشه
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        
        # ذخیره فایل اکسل
        with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='فهرست بها', index=False)
            
            # تنظیمات ظاهری
            workbook = writer.book
            worksheet = writer.sheets['فهرست بها']
            
            # تنظیم عرض ستون‌ها
            worksheet.column_dimensions['A'].width = 15
            worksheet.column_dimensions['B'].width = 50
            worksheet.column_dimensions['C'].width = 20
            worksheet.column_dimensions['D'].width = 15
            worksheet.column_dimensions['E'].width = 12
        
        return filepath, filename
    
    @classmethod
    def import_from_excel(cls, file_path, price_list_instance, user):
        """ورود داده از اکسل"""
        try:
            df = pd.read_excel(file_path)
            
            required_columns = ['شماره ردیف', 'شرح', 'قیمت واحد (ریال)', 'واحد']
            missing_columns = [col for col in required_columns if col not in df.columns]
            
            if missing_columns:
                return False, f"ستون‌های ضروری وجود ندارند: {', '.join(missing_columns)}"
            
            success_count = 0
            error_count = 0
            errors = []
            
            with transaction.atomic():
                for index, row in df.iterrows():
                    try:
                        row_number = str(row['شماره ردیف']).strip()
                        description = str(row['شرح']).strip()
                        price = float(row['قیمت واحد (ریال)'])
                        unit = str(row['واحد']).strip()
                        
                        # بررسی وجود ستون ستاره‌دار
                        is_starred = False
                        if 'ستاره‌دار' in df.columns:
                            starred_value = str(row['ستاره‌دار']).strip().lower()
                            is_starred = starred_value in ['بله', 'yes', 'true', '1', '✓']
                        
                        # ایجاد یا به‌روزرسانی آیتم
                        item, created = PriceListItem.objects.get_or_create(
                            price_list=price_list_instance,
                            row_number=row_number,
                            defaults={
                                'description': description,
                                'price': price,
                                'unit': unit,
                                'is_starred': is_starred,
                                'modified_by': user
                            }
                        )
                        
                        if not created:
                            # به‌روزرسانی آیتم موجود
                            item.description = description
                            item.price = price
                            item.unit = unit
                            item.is_starred = is_starred
                            item.modified_by = user
                            item.save()
                        
                        success_count += 1
                        
                    except Exception as e:
                        error_count += 1
                        errors.append(f"خطا در ردیف {index + 2}: {str(e)}")
            
            message = f"عملیات وارد کردن کامل شد. {success_count} آیتم موفق، {error_count} آیتم ناموفق"
            if errors:
                message += f"\nخطاها: {'; '.join(errors[:5])}"  # فقط 5 خطای اول
            
            return True, message
            
        except Exception as e:
            return False, f"خطا در خواندن فایل اکسل: {str(e)}"
                
    @property
    def total_items_price(self):
        """مجموع قیمت آیتم‌ها"""
        from django.db.models import Sum
        result = self.items.filter(is_active=True).aggregate(total=Sum('price'))
        return result['total'] or 0

class PriceListItem(models.Model):
    price_list = models.ForeignKey(
        PriceList, 
        on_delete=models.CASCADE, 
        related_name='items',
        verbose_name=_("فهرست بها مرتبط")
    )
    row_number = models.CharField(
        max_length=10,
        verbose_name=_("شماره ردیف"),
        help_text=_("شماره ردیف در فهرست بها (مثال: ۱۸۰۲۰۳)")
    )
    description = models.TextField(
        verbose_name=_("شرح آیتم"),
        help_text=_("شرح کامل آیتم فهرست بها")
    )
    price = models.DecimalField(
        max_digits=15, 
        decimal_places=2,
        validators=[MinValueValidator(0)],
        verbose_name=_("قیمت واحد"),
        help_text=_("قیمت واحد به ریال")
    )
    unit = models.CharField(
        max_length=50,
        verbose_name=_("واحد اندازه‌گیری"),
        help_text=_("واحد اندازه‌گیری (مثال: متر مربع، متر مکعب)")
    )
    is_starred = models.BooleanField(
        default=False,
        verbose_name=_("ستاره‌دار"),
        help_text=_("آیتم‌های مهم و پرکاربرد")
    )
    
    # لاگ‌گیری
    created_at = models.DateTimeField(
        auto_now_add=True, 
        verbose_name=_("زمان ایجاد")
    )
    updated_at = models.DateTimeField(
        auto_now=True, 
        verbose_name=_("زمان آخرین ویرایش")
    )
    is_active = models.BooleanField(
        default=True, 
        verbose_name=_("فعال/غیرفعال")
    )
    modified_by = models.ForeignKey(
        'auth.User', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        verbose_name=_("ویرایش‌کننده")
    )
    history = HistoricalRecords()

    class Meta:
        verbose_name = _("آیتم فهرست بها")
        verbose_name_plural = _("آیتم‌های فهرست بها")
        ordering = ['row_number', 'description']
        unique_together = ['price_list', 'row_number']
        indexes = [
            models.Index(fields=['row_number', 'is_active']),
            models.Index(fields=['price_list', 'is_active']),
            models.Index(fields=['is_starred', 'is_active']),
        ]

    def __str__(self):
        return f"{self.row_number} - {self.description[:50]}..."

    @property
    def discipline_choice(self):
        """دسترسی به رشته از طریق فهرست بها"""
        return self.price_list.discipline_choice if self.price_list else None
    
    @property
    def formatted_price(self):
        """قیمت فرمت شده"""
        return f"{self.price:,.0f}"
    
    def get_absolute_url(self):
        from django.urls import reverse
        return reverse('fehrestbaha:pricelistitem_detail', kwargs={'pk': self.pk})