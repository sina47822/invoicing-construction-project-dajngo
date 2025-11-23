from django.contrib import admin
from django.contrib.admin import DateFieldListFilter
from django.utils import timezone
from django.utils.safestring import mark_safe
import jdatetime
from .models import Project, StatusReport

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

class StatusReportInline(admin.TabularInline):
    model = StatusReport
    extra = 0
    fields = ('report_number', 'discipline', 'issue_date', 'amount', 'progress_percentage', 'approval_status')
    readonly_fields = ('created_at', 'updated_at')

@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = (
        'project_code',
        'project_name',
        'employer',
        'contractor',
        'city',
        'execution_year',
        'contract_amount_display',
        'status_display',
        'is_active',
        'created_at_jalali'
    )
    
    list_filter = (
        'status',
        'project_type',
        'is_active',
        'execution_year',
        'province',
        ('created_at', JalaliDateFilter),
    )
    
    search_fields = (
        'project_code',
        'project_name',
        'employer',
        'contractor',
        'city',
        'contract_number'
    )
    
    readonly_fields = (
        'created_at', 
        'updated_at', 
        'deleted_at',
        'contract_amount_display',
        'created_at_jalali_display'
    )
    
    fieldsets = (
        ('اطلاعات اصلی پروژه', {
            'fields': (
                'project_name', 'project_code', 'project_type', 'status',
                'employer', 'contractor', 'consultant', 'supervising_engineer'
            )
        }),
        ('موقعیت جغرافیایی', {
            'fields': ('country', 'province', 'city')
        }),
        ('اطلاعات قرارداد', {
            'fields': (
                'contract_number', 'contract_date', 'execution_year',
                'contract_amount', 'contract_file'
            )
        }),
        ('اطلاعات اضافی', {
            'fields': ('description', 'amount')
        }),
        ('مدیریت وضعیت', {
            'fields': ('is_active', 'created_by', 'modified_by')
        }),
        ('لاگ‌گیری', {
            'fields': ('created_at', 'updated_at', 'deleted_at'),
            'classes': ('collapse',)
        })
    )
    
    inlines = [StatusReportInline]
    
    def contract_amount_display(self, obj):
        if obj.contract_amount:
            return f"{obj.contract_amount:,.0f} ریال"
        return "---"
    contract_amount_display.short_description = 'مبلغ قرارداد'
    
    def status_display(self, obj):
        status_colors = {
            'active': 'green',
            'in_progress': 'blue',
            'under_review': 'orange',
            'awaiting_approval': 'purple',
            'completed': 'gray',
            'suspended': 'red',
            'cancelled': 'darkred',
            'draft': 'lightgray'
        }
        color = status_colors.get(obj.status, 'black')
        return mark_safe(f'<span style="color: {color}; font-weight: bold;">{obj.get_status_display()}</span>')
    status_display.short_description = 'وضعیت'
    
    def created_at_jalali(self, obj):
        try:
            jd = jdatetime.datetime.fromgregorian(datetime=obj.created_at)
            return jd.strftime("%Y/%m/%d")
        except:
            return obj.created_at
    created_at_jalali.short_description = 'تاریخ ایجاد'
    
    def created_at_jalali_display(self, obj):
        return self.created_at_jalali(obj)
    created_at_jalali_display.short_description = 'تاریخ ایجاد (جلالی)'


@admin.register(StatusReport)
class StatusReportAdmin(admin.ModelAdmin):
    list_display = (
        'report_number',
        'project_display',
        'discipline_display',
        'issue_date_jalali',
        'amount_display',
        'progress_percentage_display',
        'approval_status_display',
        'is_active'
    )
    
    list_filter = (
        'discipline',
        'approval_status',
        'is_active',
        ('issue_date', JalaliDateFilter),
    )
    
    search_fields = (
        'project__project_code',
        'project__project_name',
        'report_number'
    )
    
    readonly_fields = ('created_at', 'updated_at', 'issue_date_jalali_display')
    
    def project_display(self, obj):
        return f"{obj.project.project_code} - {obj.project.project_name}"
    project_display.short_description = 'پروژه'
    
    def discipline_display(self, obj):
        return obj.get_discipline_display()
    discipline_display.short_description = 'رشته'
    
    def amount_display(self, obj):
        if obj.amount:
            return f"{obj.amount:,.0f} ریال"
        return "---"
    amount_display.short_description = 'مبلغ'
    
    def progress_percentage_display(self, obj):
        return f"{obj.progress_percentage}%"
    progress_percentage_display.short_description = 'پیشرفت'
    
    def approval_status_display(self, obj):
        status_colors = {
            'draft': 'gray',
            'submitted': 'orange',
            'approved': 'green',
            'rejected': 'red'
        }
        color = status_colors.get(obj.approval_status, 'black')
        return mark_safe(f'<span style="color: {color};">{obj.get_approval_status_display()}</span>')
    approval_status_display.short_description = 'وضعیت تأیید'
    
    def issue_date_jalali(self, obj):
        try:
            jd = jdatetime.date.fromgregorian(date=obj.issue_date)
            return jd.strftime("%Y/%m/%d")
        except:
            return obj.issue_date
    issue_date_jalali.short_description = 'تاریخ صدور'
    
    def issue_date_jalali_display(self, obj):
        return self.issue_date_jalali(obj)
    issue_date_jalali_display.short_description = 'تاریخ صدور (جلالی)'
    
    def save_model(self, request, obj, form, change):
        obj.modified_by = request.user
        super().save_model(request, obj, form, change)