# forms.py
from django import forms
from .models import MeasurementSession, MeasurementSessionItem
from fehrestbaha.models import PriceListItem, DisciplineChoices, PriceList

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
        
        if self.session:
            # فقط آیتم‌های مربوط به فهرست بها این صورت جلسه را نمایش بده
            self.fields['pricelist_item'].queryset = PriceListItem.objects.filter(
                price_list=self.session.price_list,
                is_active=True
            )

            # اگر session نداریم، همه آیتم‌های فعال را نشان بده
            self.fields['pricelist_item'].queryset = PriceListItem.objects.filter(is_active=True)

        self.fields['pricelist_item'].required = True

class MeasurementSessionForm(forms.ModelForm):
    
    discipline_filter = forms.ChoiceField(
        choices=[('', '--- همه رشته ها ---')] + list(DisciplineChoices.choices),
        required=False,
        label="فیلتر بر اساس رشته",
        widget=forms.Select(attrs={'class': 'form-control', 'id': 'discipline-filter'})
    )

    class Meta:
        model = MeasurementSession
        fields = ['session_number', 'session_date', 'price_list', 'description', 'notes', 'status']

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
        # فقط فهرست‌های بها فعال را نمایش بده
        self.fields['price_list'].queryset = PriceList.objects.filter(is_active=True)
        self.fields['price_list'].required = True