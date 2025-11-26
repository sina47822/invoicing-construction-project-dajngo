# forms.py
from django import forms
from .models import MeasurementSession, MeasurementSessionItem
from fehrestbaha.models import PriceListItem, DisciplineChoices, PriceList
from django.db import models

# class MeasurementSessionForm(forms.ModelForm):
#     class Meta:
#         model = MeasurementSession
#         fields = ['session_number', 'session_date', 'discipline_choice', 'description', 'notes', 'status']
#         widgets = {
#             'session_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
#             'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
#             'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
#             'discipline_choice': forms.Select(attrs={'class': 'form-control'}),
#             'status': forms.Select(attrs={'class': 'form-control'}),
#         }

class MeasurementSessionItemForm(forms.ModelForm):
    class Meta:
        model = MeasurementSessionItem
        fields = [
            'pricelist_item',
            'row_description', 
            'length', 
            'width', 
            'height', 
            'weight', 
            'count', 
            'notes'
        ]
        widgets = {
            'pricelist_item': forms.Select(attrs={'class': 'form-select'}),
            'row_description': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'شرح ردیف...'}),
            'length': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'width': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'height': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'weight': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'count': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0.01'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }

    def __init__(self, *args, **kwargs):
        self.session = kwargs.pop('session', None)
        super().__init__(*args, **kwargs)
        
        if self.session and self.session.price_list:
            # فقط آیتم‌های مربوط به فهرست بها این صورت جلسه را نمایش بده
            self.fields['pricelist_item'].queryset = PriceListItem.objects.filter(
                price_list=self.session.price_list,
                is_active=True
            ).order_by('row_number')
        else:
            # اگر session نداریم یا فهرست بها ندارد، همه آیتم‌های فعال را نشان بده
            self.fields['pricelist_item'].queryset = PriceListItem.objects.filter(
                is_active=True
            ).order_by('row_number')

        self.fields['pricelist_item'].required = True
        self.fields['row_description'].required = True
        self.fields['count'].required = True

class MeasurementSessionForm(forms.ModelForm):
    
    discipline_filter = forms.ChoiceField(
        choices=[],  # ابتدا خالی می‌گذاریم
        required=True,
        label='رشته',
        widget=forms.Select(attrs={
            'class': 'form-select',
            'id': 'discipline-filter'
        })
    )

    class Meta:
        model = MeasurementSession
        fields = [
            'session_number',
            'session_date', 
            'price_list', 
            'description', 
            'notes', 
            'status'
        ]

        widgets = {
            'session_date': forms.DateInput(attrs={
                'type': 'date', 
                'class': 'form-control',
                'placeholder': 'انتخاب تاریخ'
            }),
            'session_number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'شماره صورت جلسه'
            }),
            'price_list': forms.Select(attrs={
                'class': 'form-control',
                'id': 'price-list-select'
            }),
            'status': forms.Select(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'توضیحات صورت جلسه'
            }),
            'notes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'placeholder': 'یادداشت‌های داخلی'
            }),
        }
        labels = {
            'session_number': 'شماره صورت جلسه',
            'session_date': 'تاریخ صورت جلسه',
            'price_list': 'فهرست بها مرتبط',
            'description': 'توضیحات',
            'notes': 'یادداشت‌ها',
            'status': 'وضعیت',
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # تنظیم choices برای discipline_filter
        self.fields['discipline_filter'].choices = [('', '-- انتخاب رشته --')] + list(DisciplineChoices.choices)
        
        # اگر داده‌ای از قبل وجود دارد (مثلاً در حالت بازگشت فرم با خطا)، بر اساس آن داده‌ها، queryset را تنظیم کنیم
        if self.data:  # اگر فرم قبلا ارسال شده و اکنون در حالت بازگشت با خطاست
            discipline = self.data.get('discipline_filter')
            print(f"🔍 تنظیم queryset بر اساس داده‌های فرم - رشته: {discipline}")
            if discipline:
                self.fields['price_list'].queryset = PriceList.objects.filter(
                    discipline_choice=discipline,
                    is_active=True
                )
                print(f"✅ تعداد گزینه‌های price_list: {self.fields['price_list'].queryset.count()}")
            else:
                self.fields['price_list'].queryset = PriceList.objects.none()
        elif self.instance and self.instance.pk:  # حالت ویرایش
            # اگر صورت جلسه فهرست بها دارد، رشته مربوطه را تنظیم کنیم
            if self.instance.price_list:
                self.fields['discipline_filter'].initial = self.instance.price_list.discipline_choice
                
                # فیلتر کردن فهرست‌های بها بر اساس رشته
                self.fields['price_list'].queryset = PriceList.objects.filter(
                    discipline_choice=self.instance.price_list.discipline_choice,
                    is_active=True
                )
        else:
            # در حالت ایجاد جدید، فهرست‌های بها را خالی می‌کنیم
            self.fields['price_list'].queryset = PriceList.objects.none()
            print("ℹ️ حالت ایجاد جدید - price_list queryset خالی است")

    def clean_discipline_filter(self):
        """اعتبارسنجی فیلد رشته"""
        discipline = self.cleaned_data.get('discipline_filter')
        if not discipline:
            raise forms.ValidationError("لطفا رشته را انتخاب کنید.")
        
        # بررسی اینکه مقدار در choices معتبر است
        valid_choices = [choice[0] for choice in DisciplineChoices.choices]
        if discipline not in valid_choices:
            raise forms.ValidationError("رشته انتخاب شده معتبر نیست.")
        
        return discipline

    def clean_price_list(self):
        """اعتبارسنجی فیلد فهرست بها"""
        price_list = self.cleaned_data.get('price_list')
        discipline = self.cleaned_data.get('discipline_filter')
        
        print(f"🔍 اعتبارسنجی price_list: {price_list}, رشته: {discipline}")
        
        if not price_list:
            raise forms.ValidationError("لطفا فهرست بها را انتخاب کنید.")
        
        # بررسی وجود فهرست بها در دیتابیس
        try:
            price_list_obj = PriceList.objects.get(pk=price_list.pk, is_active=True)
            print(f"✅ فهرست بها یافت شد: {price_list_obj.discipline}")
        except PriceList.DoesNotExist:
            raise forms.ValidationError("فهرست بها انتخاب شده معتبر نیست.")
        
        # بررسی تطابق با رشته
        if discipline and price_list_obj.discipline_choice != discipline:
            raise forms.ValidationError("فهرست بها انتخاب شده با رشته مطابقت ندارد.")
        
        return price_list

    def clean(self):
        cleaned_data = super().clean()
        discipline_filter = cleaned_data.get('discipline_filter')
        price_list = cleaned_data.get('price_list')
        
        print(f"🔍 clean() - رشته: {discipline_filter}, فهرست بها: {price_list}")
        
        # بررسی تطابق رشته انتخاب شده با فهرست بها
        if discipline_filter and price_list:
            if price_list.discipline_choice != discipline_filter:
                self.add_error('price_list', "فهرست بها انتخاب شده با رشته صورت جلسه مطابقت ندارد.")
        
        return cleaned_data