# fehrestbaha/admin.py
from django.contrib import admin
from django.contrib.admin import DateFieldListFilter
from django.utils import timezone
from django.utils.safestring import mark_safe
from django.urls import path
from django.shortcuts import render, redirect
from django.http import HttpResponse, FileResponse
from django.contrib import messages
from django.core.files.storage import FileSystemStorage
import os
import jdatetime
from .models import PriceList, PriceListItem

class JalaliDateFilter(DateFieldListFilter):
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

class PriceListItemInline(admin.TabularInline):
    model = PriceListItem
    extra = 1
    fields = ('row_number', 'description', 'price', 'unit', 'is_starred', 'is_active')
    readonly_fields = ('created_at', 'updated_at')
    ordering = ('row_number',)

@admin.register(PriceList)
class PriceListAdmin(admin.ModelAdmin):
    list_display = (
        'discipline_choice_display',
        'discipline',
        'year_display',
        'items_count',
        'is_active',
        'created_at_jalali',
        'updated_at_jalali'
    )
    
    list_filter = (
        'discipline_choice',
        'year',
        'is_active',
        ('created_at', JalaliDateFilter),
    )
    
    search_fields = ('discipline', 'discipline_choice')
    
    readonly_fields = ('created_at', 'updated_at')
    
    inlines = [PriceListItemInline]
    
    fieldsets = (
        ('اطلاعات اصلی فهرست بها', {
            'fields': ('discipline_choice', 'discipline', 'year')
        }),
        ('مدیریت وضعیت', {
            'fields': ('is_active', 'modified_by')
        }),
        ('لاگ‌گیری', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    # اضافه کردن اکشن‌های سفارشی
    actions = ['export_to_excel', 'create_sample_excel']
    
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('<path:object_id>/import-excel/', self.admin_site.admin_view(self.import_excel_view), name='fehrestbaha_pricelist_import_excel'),
            path('download-sample/', self.admin_site.admin_view(self.download_sample_view), name='fehrestbaha_pricelist_download_sample'),
        ]
        return custom_urls + urls
    
    def export_to_excel(self, request, queryset):
        """اکشن برای صادر کردن به اکسل"""
        if queryset.count() != 1:
            self.message_user(request, "لطفاً فقط یک فهرست بها را انتخاب کنید", level=messages.ERROR)
            return
        
        price_list = queryset.first()
        filepath, filename = price_list.export_to_excel()
        
        try:
            response = FileResponse(open(filepath, 'rb'), as_attachment=True, filename=filename)
            self.message_user(request, f"فایل اکسل با موفقیت ایجاد شد: {filename}", level=messages.SUCCESS)
            return response
        except Exception as e:
            self.message_user(request, f"خطا در ایجاد فایل اکسل: {str(e)}", level=messages.ERROR)
    
    export_to_excel.short_description = "صادر کردن آیتم‌ها به اکسل"
    
    def create_sample_excel(self, request, queryset):
        """ایجاد فایل نمونه"""
        filepath, filename = PriceList.create_sample_excel()
        
        try:
            response = FileResponse(open(filepath, 'rb'), as_attachment=True, filename=filename)
            self.message_user(request, f"فایل نمونه با موفقیت ایجاد شد: {filename}", level=messages.SUCCESS)
            return response
        except Exception as e:
            self.message_user(request, f"خطا در ایجاد فایل نمونه: {str(e)}", level=messages.ERROR)
    
    create_sample_excel.short_description = "ایجاد فایل نمونه اکسل"
    
    def import_excel_view(self, request, object_id):
        """ویو برای وارد کردن از اکسل"""
        price_list = self.get_object(request, object_id)
        
        if request.method == 'POST' and request.FILES.get('excel_file'):
            excel_file = request.FILES['excel_file']
            
            # ذخیره موقت فایل
            fs = FileSystemStorage()
            filename = fs.save(f"temp_{excel_file.name}", excel_file)
            filepath = fs.path(filename)
            
            try:
                success, message = PriceList.import_from_excel(filepath, price_list, request.user)
                
                if success:
                    self.message_user(request, message, level=messages.SUCCESS)
                else:
                    self.message_user(request, message, level=messages.ERROR)
                
                # حذف فایل موقت
                if os.path.exists(filepath):
                    os.remove(filepath)
                
                return redirect('admin:fehrestbaha_pricelist_change', object_id)
                
            except Exception as e:
                if os.path.exists(filepath):
                    os.remove(filepath)
                self.message_user(request, f"خطا در پردازش فایل: {str(e)}", level=messages.ERROR)
        
        context = {
            **self.admin_site.each_context(request),
            'title': 'وارد کردن از اکسل',
            'opts': self.model._meta,
            'price_list': price_list,
        }
        
        return render(request, 'admin/fehrestbaha/pricelist/import_excel.html', context)
    
    def download_sample_view(self, request):
        """دانلود فایل نمونه"""
        filepath, filename = PriceList.create_sample_excel()
        
        try:
            response = FileResponse(open(filepath, 'rb'), as_attachment=True, filename=filename)
            return response
        except Exception as e:
            self.message_user(request, f"خطا در ایجاد فایل نمونه: {str(e)}", level=messages.ERROR)
            return redirect('admin:fehrestbaha_pricelist_changelist')
    
    def change_view(self, request, object_id, form_url='', extra_context=None):
        extra_context = extra_context or {}
        extra_context['show_import_button'] = True
        return super().change_view(request, object_id, form_url, extra_context)
    
    def discipline_choice_display(self, obj):
        return obj.get_discipline_choice_display()
    discipline_choice_display.short_description = 'رشته'
    
    def year_display(self, obj):
        return f"{obj.year}" if obj.year else "---"
    year_display.short_description = 'سال'
    
    def items_count(self, obj):
        count = obj.items.filter(is_active=True).count()
        return mark_safe(f'<span style="color: {"green" if count > 0 else "red"}">{count}</span>')
    items_count.short_description = 'تعداد آیتم‌ها'
    
    def created_at_jalali(self, obj):
        try:
            jd = jdatetime.datetime.fromgregorian(datetime=obj.created_at)
            return jd.strftime("%Y/%m/%d")
        except:
            return obj.created_at
    created_at_jalali.short_description = 'تاریخ ایجاد'
    
    def updated_at_jalali(self, obj):
        try:
            jd = jdatetime.datetime.fromgregorian(datetime=obj.updated_at)
            return jd.strftime("%Y/%m/%d")
        except:
            return obj.updated_at
    updated_at_jalali.short_description = 'آخرین ویرایش'
    
    def save_model(self, request, obj, form, change):
        obj.modified_by = request.user
        super().save_model(request, obj, form, change)

@admin.register(PriceListItem)
class PriceListItemAdmin(admin.ModelAdmin):
    list_display = (
        'row_number',
        'description_short',
        'price_list_display',
        'price_display',
        'unit',
        'is_starred_display',
        'is_active',
        'created_at_jalali'
    )
    
    list_filter = (
        'price_list__discipline_choice',
        'price_list',
        'is_starred',
        'is_active',
        ('created_at', JalaliDateFilter),
    )
    
    search_fields = ('row_number', 'description', 'price_list__discipline')
    
    readonly_fields = ('created_at', 'updated_at')
    
    fieldsets = (
        ('اطلاعات اصلی آیتم', {
            'fields': ('price_list', 'row_number', 'description', 'price', 'unit')
        }),
        ('ویژگی‌ها', {
            'fields': ('is_starred',)
        }),
        ('مدیریت وضعیت', {
            'fields': ('is_active', 'modified_by')
        }),
        ('لاگ‌گیری', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    def description_short(self, obj):
        return obj.description[:100] + "..." if len(obj.description) > 100 else obj.description
    description_short.short_description = 'شرح'
    
    def price_list_display(self, obj):
        return f"{obj.price_list.get_discipline_choice_display()} - {obj.price_list.discipline}"
    price_list_display.short_description = 'فهرست بها'
    
    def price_display(self, obj):
        return f"{obj.price:,.0f} ریال"
    price_display.short_description = 'قیمت واحد'
    
    def is_starred_display(self, obj):
        if obj.is_starred:
            return mark_safe('<span style="color: gold;">★</span>')
        return "---"
    is_starred_display.short_description = 'ستاره‌دار'
    
    def created_at_jalali(self, obj):
        try:
            jd = jdatetime.datetime.fromgregorian(datetime=obj.created_at)
            return jd.strftime("%Y/%m/%d")
        except:
            return obj.created_at
    created_at_jalali.short_description = 'تاریخ ایجاد'
    
    def save_model(self, request, obj, form, change):
        obj.modified_by = request.user
        super().save_model(request, obj, form, change)