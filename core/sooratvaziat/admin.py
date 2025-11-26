from django.contrib import admin
from django.contrib.admin import DateFieldListFilter
from django.utils import timezone
from django.utils.safestring import mark_safe
import jdatetime
from .models import (
    MeasurementSession, 
    MeasurementSessionItem, 
    DetailedMeasurement,
    FinancialStatus,
    ProjectFinancialSummary,
    DetailedFinancialReport,
    MeasurementRevision  # Add this import
)


class JalaliDateFilter(DateFieldListFilter):
    """فیلتر تاریخ جلالی برای ادمین"""
    
    def __init__(self, field, request, params, model, model_admin, field_path):
        super().__init__(field, request, params, model, model_admin, field_path)
        
        try:
            today = jdatetime.date.fromgregorian(date=timezone.now().date())
            yesterday = today - jdatetime.timedelta(days=1)
            
            self.links = list(self.links)
            for i, link in enumerate(self.links):
                if hasattr(link, 'display'):
                    if 'today' in link.display.lower():
                        link.display = f"امروز ({today.strftime('%Y/%m/%d')})"
                    elif 'yesterday' in link.display.lower():
                        link.display = f"دیروز ({yesterday.strftime('%Y/%m/%d')})"
        except:
            pass


class MeasurementSessionItemInline(admin.TabularInline):
    """آیتم‌های صورت‌جلسه به صورت Inline"""
    model = MeasurementSessionItem
    extra = 1
    fields = (
        'pricelist_item', 
        'row_description',
        'length', 'width', 'height', 'weight', 'count',
        'quantity', 'unit_price', 'item_total',
        'is_active'
    )
    readonly_fields = ('quantity', 'item_total')
    raw_id_fields = ('pricelist_item',)


class MeasurementRevisionInline(admin.TabularInline):
    """تغییرات متره به صورت Inline"""
    model = MeasurementRevision
    extra = 0
    readonly_fields = ('edited_by', 'user_role', 'created_at')
    can_delete = False
    
    def has_add_permission(self, request, obj):
        return False


@admin.register(MeasurementSession)
class MeasurementSessionAdmin(admin.ModelAdmin):
    list_display = (
        'session_number',
        'project_display',
        'session_date_jalali',
        'discipline_choice_display',
        'items_count',
        'status_display',
        'created_at_jalali'
    )
    
    list_filter = (
        'status',
        'price_list__discipline_choice',
        ('session_date', JalaliDateFilter),
        'is_active',
    )
    
    search_fields = (
        'session_number',
        'project__project_name',
        'project__project_code',
    )
    
    readonly_fields = ('created_at', 'updated_at', 'session_date_jalali_display')
    inlines = [MeasurementSessionItemInline]
    
    fieldsets = (
        ('اطلاعات اصلی', {
            'fields': (
                'session_number', 'project', 'session_date', 'price_list', 'status'
            )
        }),
        ('توضیحات', {
            'fields': ('description', 'notes')
        }),
        ('لاگ‌گیری', {
            'fields': ('created_by', 'modified_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
        ('وضعیت', {
            'fields': ('is_active',)
        })
    )
    
    def project_display(self, obj):
        return f"{obj.project.project_code} - {obj.project.project_name}"
    project_display.short_description = 'پروژه'
    
    def discipline_choice_display(self, obj):
        return obj.price_list.get_discipline_choice_display() if obj.price_list else "---"
    discipline_choice_display.short_description = 'رشته'
    
    def status_display(self, obj):
        status_colors = {
            'draft': 'gray',
            'submitted': 'orange',
            'approved': 'green',
            'rejected': 'red'
        }
        color = status_colors.get(obj.status, 'black')
        return mark_safe(f'<span style="color: {color};">{obj.get_status_display()}</span>')
    status_display.short_description = 'وضعیت'
    
    def created_at_jalali(self, obj):
        try:
            jd = jdatetime.datetime.fromgregorian(datetime=obj.created_at)
            return jd.strftime("%Y/%m/%d %H:%M")
        except:
            return obj.created_at
    created_at_jalali.short_description = 'تاریخ ایجاد'
    
    def session_date_jalali_display(self, obj):
        return obj.session_date_jalali or "---"
    session_date_jalali_display.short_description = 'تاریخ صورت‌جلسه (جلالی)'
    
    def save_model(self, request, obj, form, change):
        if not change:  # Creating new object
            obj.created_by = request.user
        obj.modified_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(MeasurementSessionItem)
class MeasurementSessionItemAdmin(admin.ModelAdmin):
    list_display = (
        'pricelist_item_display',
        'row_description_short',
        'measurement_session_display',
        'quantity_display',
        'unit_price_display',
        'item_total_display',
        'is_active'
    )
    
    list_filter = (
        'measurement_session_number__project',
        'is_active',
        ('created_at', JalaliDateFilter),
    )
    
    search_fields = (
        'pricelist_item__row_number',
        'row_description',
        'measurement_session_number__session_number'
    )
    
    readonly_fields = ('quantity', 'item_total', 'created_at', 'updated_at')
    inlines = [MeasurementRevisionInline]
    
    fieldsets = (
        ('اطلاعات اصلی', {
            'fields': (
                'measurement_session_number', 'pricelist_item', 'row_description'
            )
        }),
        ('ابعاد و مقادیر', {
            'fields': (
                'length', 'width', 'height', 'weight', 'count'
            )
        }),
        ('محاسبات', {
            'fields': ('quantity', 'unit_price', 'item_total')
        }),
        ('یادداشت‌ها', {
            'fields': ('notes',)
        }),
        ('لاگ‌گیری', {
            'fields': ('created_by', 'modified_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
        ('وضعیت', {
            'fields': ('is_active',)
        })
    )
    
    def pricelist_item_display(self, obj):
        return f"{obj.pricelist_item.row_number}"
    pricelist_item_display.short_description = 'ردیف فهرست بها'
    
    def row_description_short(self, obj):
        return obj.row_description[:50] + "..." if len(obj.row_description) > 50 else obj.row_description
    row_description_short.short_description = 'شرح ردیف'
    
    def measurement_session_display(self, obj):
        return obj.measurement_session_number.session_number
    measurement_session_display.short_description = 'شماره صورت‌جلسه'
    
    def quantity_display(self, obj):
        return f"{obj.quantity:,.2f}"
    quantity_display.short_description = 'مقدار'
    
    def unit_price_display(self, obj):
        return f"{obj.unit_price:,.0f}"
    unit_price_display.short_description = 'قیمت واحد'
    
    def item_total_display(self, obj):
        return f"{obj.item_total:,.0f}"
    item_total_display.short_description = 'مبلغ کل'
    
    def save_model(self, request, obj, form, change):
        if not change:  # Creating new object
            obj.created_by = request.user
        obj.modified_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(MeasurementRevision)
class MeasurementRevisionAdmin(admin.ModelAdmin):
    list_display = (
        'measurement_item_display',
        'edited_by_display',
        'user_role_display',
        'revision_reason_short',
        'created_at_jalali'
    )
    
    list_filter = (
        'user_role',
        ('created_at', JalaliDateFilter),
    )
    
    search_fields = (
        'measurement_item__row_description',
        'measurement_item__pricelist_item__row_number',
        'edited_by__username',
        'revision_reason'
    )
    
    readonly_fields = (
        'measurement_item', 'edited_by', 'user_role', 
        'old_length', 'old_width', 'old_height', 'old_count', 'old_quantity',
        'created_at'
    )
    
    def measurement_item_display(self, obj):
        return f"{obj.measurement_item.row_description[:50]}..."
    measurement_item_display.short_description = 'آیتم متره'
    
    def edited_by_display(self, obj):
        return obj.edited_by.get_full_name() or obj.edited_by.username
    edited_by_display.short_description = 'ویرایش‌کننده'
    
    def user_role_display(self, obj):
        return obj.user_role.name if obj.user_role else "---"
    user_role_display.short_description = 'نقش'
    
    def revision_reason_short(self, obj):
        if obj.revision_reason:
            return obj.revision_reason[:50] + "..." if len(obj.revision_reason) > 50 else obj.revision_reason
        return "---"
    revision_reason_short.short_description = 'دلیل ویرایش'
    
    def created_at_jalali(self, obj):
        try:
            jd = jdatetime.datetime.fromgregorian(datetime=obj.created_at)
            return jd.strftime("%Y/%m/%d %H:%M")
        except:
            return obj.created_at
    created_at_jalali.short_description = 'تاریخ تغییر'


@admin.register(DetailedMeasurement)
class DetailedMeasurementAdmin(admin.ModelAdmin):
    list_display = (
        'price_list_item_display',
        'total_quantity_display',
        'sessions_count',
        'last_updated_jalali'
    )
    
    list_filter = (
        'price_list_item__price_list__discipline_choice',
    )
    
    search_fields = (
        'price_list_item__row_number',
        'price_list_item__description',
    )
    
    readonly_fields = ('total_quantity', 'created_at', 'last_updated')
    
    def price_list_item_display(self, obj):
        return f"{obj.price_list_item.row_number} - {obj.price_list_item.description[:50]}..."
    price_list_item_display.short_description = 'آیتم فهرست بها'
    
    def total_quantity_display(self, obj):
        return f"{obj.total_quantity:,.2f}"
    total_quantity_display.short_description = 'مجموع مقدار'
    
    def last_updated_jalali(self, obj):
        try:
            jd = jdatetime.datetime.fromgregorian(datetime=obj.last_updated)
            return jd.strftime("%Y/%m/%d %H:%M")
        except:
            return obj.last_updated
    last_updated_jalali.short_description = 'آخرین به‌روزرسانی'


@admin.register(FinancialStatus)
class FinancialStatusAdmin(admin.ModelAdmin):
    list_display = (
        'measurement_session_display',
        'total_amount_display',
        'total_quantity_display',
        'is_approved',
        'last_calculated_jalali'
    )
    
    list_filter = (
        'is_approved',
        'measurement_session__project',
    )
    
    search_fields = (
        'measurement_session__session_number',
        'measurement_session__project__project_name'
    )
    
    readonly_fields = (
        'total_quantity', 'total_amount', 'total_with_vat',
        'active_items_count', 'unique_pricelist_items_count', 'row_descriptions_count',
        'created_at', 'updated_at', 'last_calculated_at'
    )
    
    def measurement_session_display(self, obj):
        return obj.measurement_session.session_number
    measurement_session_display.short_description = 'شماره صورت‌جلسه'
    
    def total_amount_display(self, obj):
        return f"{obj.total_amount:,.0f} ریال"
    total_amount_display.short_description = 'مبلغ کل'
    
    def total_quantity_display(self, obj):
        return f"{obj.total_quantity:,.2f}"
    total_quantity_display.short_description = 'مقدار کل'
    
    def last_calculated_jalali(self, obj):
        try:
            jd = jdatetime.datetime.fromgregorian(datetime=obj.last_calculated_at)
            return jd.strftime("%Y/%m/%d %H:%M")
        except:
            return obj.last_calculated_at
    last_calculated_jalali.short_description = 'آخرین محاسبه'


@admin.register(ProjectFinancialSummary)
class ProjectFinancialSummaryAdmin(admin.ModelAdmin):
    list_display = (
        'project_display',
        'total_amount_display',
        'progress_percentage_display',
        'sessions_count',
        'last_updated_jalali'
    )
    
    list_filter = (
        'project__status',
    )
    
    search_fields = (
        'project__project_name',
        'project__project_code',
    )
    
    readonly_fields = (
        'total_amount', 'total_quantity', 'total_with_vat',
        'total_amount_abnieh', 'total_amount_mekanik', 'total_amount_bargh',
        'progress_percentage', 'sessions_count', 'approved_sessions_count',
        'last_updated', 'created_at'
    )
    
    def project_display(self, obj):
        return f"{obj.project.project_code} - {obj.project.project_name}"
    project_display.short_description = 'پروژه'
    
    def total_amount_display(self, obj):
        return f"{obj.total_amount:,.0f} ریال"
    total_amount_display.short_description = 'مبلغ کل'
    
    def progress_percentage_display(self, obj):
        color = "green" if obj.progress_percentage >= 80 else "orange" if obj.progress_percentage >= 50 else "red"
        return mark_safe(f'<span style="color: {color}; font-weight: bold;">{obj.progress_percentage:.1f}%</span>')
    progress_percentage_display.short_description = 'پیشرفت'
    
    def last_updated_jalali(self, obj):
        try:
            jd = jdatetime.datetime.fromgregorian(datetime=obj.last_updated)
            return jd.strftime("%Y/%m/%d %H:%M")
        except:
            return obj.last_updated
    last_updated_jalali.short_description = 'آخرین به‌روزرسانی'
