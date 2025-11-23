from django import forms
from django.forms import modelform_factory, TextInput, Select, DateInput, Textarea, CheckboxInput, FileInput
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model
from django.utils import timezone
from project.models import Project
import json
from datetime import datetime
from jalali_date.fields import JalaliDateField
from jalali_date.widgets import AdminJalaliDateWidget
from accounts.models import ProjectUser

from jdatetime import datetime
User = get_user_model()

class ProjectCreateForm(forms.ModelForm):
    """
    فرم سفارشی برای ایجاد پروژه با پشتیبانی از تاریخ جلالی
    """
    # سال اجرا (محدوده مناسب برای پروژه‌های عمرانی)
    execution_year = forms.ChoiceField(
        choices=[(year, f"{year} (سال {year})") for year in range(1374, 1405)],
        widget=Select(attrs={
            'class': 'form-select',
            'data-placeholder': 'سال اجرا را انتخاب کنید'
        }),
        required=True,
        label='سال اجرا بر اساس صورت وضعیت'
    )
    
    # اصلاح فیلد تاریخ به شمسی
    contract_date = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'form-control persian-datepicker',
            'placeholder': 'برای انتخاب تاریخ کلیک کنید',
            'autocomplete': 'off',
            'readonly': 'readonly',  # جلوگیری از ورود دستی
        }),
        required=True,
        label='تاریخ قرارداد'
    )
    
    # مبلغ قرارداد با فرمت مناسب
    contract_amount = forms.CharField(
        widget=TextInput(attrs={
            'class': 'form-control',
            'placeholder': '100,000,000',
            'type': 'text',
            'data-inputmask': "'alias': 'numeric', 'groupSeparator': ',', 'radixPoint': '.', 'digits': 0"
        }),
        required=True,
        label='مبلغ قرارداد (ریال)'
    )
    
    # وضعیت پیش‌فرض
    status = forms.ChoiceField(
        choices=Project.STATUS_CHOICES,
        widget=Select(attrs={
            'class': 'form-select'
        }),
        initial='active',
        label='وضعیت پروژه'
    )
    # **جدید: فیلدهای location به صورت ChoiceField**
    country = forms.ChoiceField(
        choices=[
            ('', 'انتخاب کشور'),
            ('ایران', 'ایران'),
            ('افغانستان', 'افغانستان'),
            ('عراق', 'عراق'),
            ('ترکیه', 'ترکیه'),
            ('امارات متحده عربی', 'امارات متحده عربی'),
            ('قطر', 'قطر'),
            ('عمان', 'عمان'),
            ('بحرین', 'بحرین'),
            ('کویت', 'کویت'),
            ('سوریه', 'سوریه'),
            ('لبنان', 'لبنان'),
            ('اردن', 'اردن'),
            ('پاکستان', 'پاکستان'),
            ('ترکمنستان', 'ترکمنستان'),
            ('آذربایجان', 'آذربایجان'),
            ('ارمنستان', 'ارمنستان'),
            ('گرجستان', 'گرجستان'),
        ],
        widget=Select(attrs={
            'class': 'form-select',
            'id': 'id_country',
            'name': 'country'
        }),
        initial='ایران',
        required=True,
        label='کشور'
    )
    
    province = forms.ChoiceField(
        choices=[('', 'انتخاب استان')],  # در __init__ تنظیم می‌شود
        widget=Select(attrs={
            'class': 'form-select',
            'id': 'id_province',
            'name': 'province'
        }),
        required=True,
        label='استان'
    )
    
    city = forms.CharField(
        widget=forms.Select(attrs={
            'class': 'form-select', 
            'id': 'id_city',
            'name': 'city',
            'disabled': True
        }),
        required=True,
        label='شهر'
    )

    # توضیحات
    description = forms.CharField(
        widget=Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'توضیحات مختصر درباره پروژه (اختیاری)'
        }),
        required=False,
        label='توضیحات پروژه'
    )
    # New fields for user assignment
    employer_user = forms.ModelChoiceField(
        queryset=User.objects.none(),
        required=False,
        widget=Select(attrs={'class': 'form-select'}),
        label='کاربر کارفرما'
    )
    
    employer_user = forms.ModelChoiceField(
        queryset=User.objects.filter(is_active=True),
        required=False,
        widget=Select(attrs={
            'class': 'form-select',
            'data-role': 'employer'
        }),
        label='کاربر کارفرما'
    )
    
    project_manager_user = forms.ModelChoiceField(
        queryset=User.objects.filter(is_active=True),
        required=False,
        widget=Select(attrs={
            'class': 'form-select',
            'data-role': 'project_manager'
        }),
        label='کاربر مدیر طرح'
    )
    
    consultant_user = forms.ModelChoiceField(
        queryset=User.objects.filter(is_active=True),
        required=False,
        widget=Select(attrs={
            'class': 'form-select',
            'data-role': 'consultant'
        }),
        label='کاربر مشاور'
    )
    
    supervising_engineer_user = forms.ModelChoiceField(
        queryset=User.objects.filter(is_active=True),
        required=False,
        widget=Select(attrs={
            'class': 'form-select',
            'data-role': 'supervisor'
        }),
        label='کاربر ناظر'
    )
     
    class Meta:
        model = Project
        fields = [
            'project_name',
            'project_code',
            'project_type',
            'contract_number',
            'contract_date',
            'execution_year',
            'contract_amount',
            'status',
            'contract_file',
            'description',
            'country',
            'province',
            'city',    
        ]
        widgets = {
            'project_name': TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'نام کامل پروژه (مثال: پروژه احداث پل فلزی)',
                'maxlength': 255,
                'required': True
            }),
            'project_code': TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'P-1403-001',
                'maxlength': 50,
                'required': True,
                'autocomplete': 'off'
            }),
            'contract_number': TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'شماره قرارداد (مثال: 1403/001)',
                'maxlength': 50,
                'required': True
            }),
            'contract_file': FileInput(attrs={
                'class': 'form-control',
                'accept': '.pdf,.doc,.docx',
                'data-max-size': '5242880'  # 5MB
            }),
            'project_type': Select(attrs={
                'class': 'form-select'
            }),
        }
        labels = {
            'project_name': 'نام پروژه',
            'project_code': 'کد پروژه',
            'contract_number': 'شماره قرارداد',
            'contract_amount': 'مبلغ قرارداد (ریال)',
            'contract_file': 'فایل قرارداد',
            'description': 'توضیحات',
        }
    
    def __init__(self, *args, **kwargs):
        self.current_user = kwargs.pop('current_user', None)
        super().__init__(*args, **kwargs)        
        
        # تنظیم کشور پیش‌فرض
        self.fields['country'].initial = 'ایران'
        
        # تنظیم سال اجرا به امسال
        try:
            current_year = jdatetime.now().year
            self.fields['execution_year'].initial = current_year
        except ImportError:
            current_year = 1404
            self.fields['execution_year'].initial = current_year        
        
        # تنظیم تاریخ امروز برای فرم ایجاد
        if not self.instance.pk and not self.data:
            try:
                today = jdatetime.now()
                self.initial['contract_date'] = today.strftime('%Y/%m/%d')
            except ImportError:
                today = datetime.now()
                self.initial['contract_date'] = today.strftime('%Y/%m/%d')

        # محدود کردن انتخاب سال
        self.fields['execution_year'].choices = [
            (year, f"{year} (سال {year})") 
            for year in range(current_year - 10, current_year + 3)
        ]
        
        # تنظیم گزینه‌های استان و شهر
        self.set_location_choices()
        
        # اگر در حالت ویرایش هستیم و شهر داریم، آن را تنظیم کن
        if self.instance and self.instance.pk and self.instance.city:
            self.set_city_choices_based_on_province()
            # تنظیم مقدار اولیه برای شهر
            self.fields['city'].initial = self.instance.city
        # تنظیم queryset برای فیلدهای کاربر
        active_users = User.objects.filter(is_active=True)
        self.fields['employer_user'].queryset = active_users
        self.fields['project_manager_user'].queryset = active_users
        self.fields['consultant_user'].queryset = active_users
        self.fields['supervising_engineer_user'].queryset = active_users
        
        if self.instance and self.instance.pk:
            self.set_initial_users()
    
    def set_initial_users(self):
        """تنظیم کاربران فعلی برای حالت ویرایش"""
        project_users = ProjectUser.objects.filter(project=self.instance)
        
        for project_user in project_users:
            if project_user.role == 'employer':
                self.fields['employer_user'].initial = project_user.user
            elif project_user.role == 'project_manager':
                self.fields['project_manager_user'].initial = project_user.user
            elif project_user.role == 'consultant':
                self.fields['consultant_user'].initial = project_user.user
            elif project_user.role == 'supervisor':
                self.fields['supervising_engineer_user'].initial = project_user.user            
    
    def set_location_choices(self):
        """تنظیم گزینه‌های استان و شهر"""
        
        # لیست استان‌های ایران
        provinces = [
            ('تهران', 'تهران'),
            ('اصفهان', 'اصفهان'),
            ('خراسان رضوی', 'خراسان رضوی'),
            ('فارس', 'فارس'),
            ('آذربایجان شرقی', 'آذربایجان شرقی'),
            ('خوزستان', 'خوزستان'),
            ('البرز', 'البرز'),
            ('قم', 'قم'),
            ('کرمانشاه', 'کرمانشاه'),
            ('آذربایجان غربی', 'آذربایجان غربی'),
            ('گیلان', 'گیلان'),
            ('زنجان', 'زنجان'),
            ('همدان', 'همدان'),
            ('کرمان', 'کرمان'),
            ('یزد', 'یزد'),
            ('اردبیل', 'اردبیل'),
            ('هرمزگان', 'هرمزگان'),
            ('مرکزی', 'مرکزی'),
            ('بوشهر', 'بوشهر'),
            ('سیستان و بلوچستان', 'سیستان و بلوچستان'),
            ('قزوین', 'قزوین'),
            ('سمنان', 'سمنان'),
            ('مازندران', 'مازندران'),
            ('گلستان', 'گلستان'),
            ('خراسان شمالی', 'خراسان شمالی'),
            ('خراسان جنوبی', 'خراسان جنوبی'),
            ('چهارمحال و بختیاری', 'چهارمحال و بختیاری'),
            ('لرستان', 'لرستان'),
            ('ایلام', 'ایلام'),
            ('کردستان', 'کردستان'),
            ('همدان', 'همدان'),
            ('کهگیلویه و بویراحمد', 'کهگیلویه و بویراحمد'),
        ]

        self.fields['province'].choices = [('', 'انتخاب استان')] + provinces
    
        # شهرهای هر استان (می‌توانید از دیتابیس بخوانید)
        cities_by_province = {
            'تهران': [
                ('تهران', 'تهران'),
                ('ری', 'ری'),
                ('ورامین', 'ورامین'),
                ('ملارد', 'ملارد'),
                ('شهرری', 'شهرری'),
                ('رودهن', 'رودهن'),
                ('بومهن', 'بومهن'),
                ('دماوند', 'دماوند'),
                ('پردیس', 'پردیس'),
                ('شهریار', 'شهریار'),
            ],
            'اصفهان': [
                ('اصفهان', 'اصفهان'),
                ('کاشان', 'کاشان'),
                ('خمینی‌شهر', 'خمینی‌شهر'),
                ('نجف‌آباد', 'نجف‌آباد'),
                ('شاهین‌شهر', 'شاهین‌شهر'),
                ('لنجان', 'لنجان'),
                ('فلاورجان', 'فلاورجان'),
                ('گلپایگان', 'گلپایگان'),
                ('خور و بیابانک', 'خور و بیابانک'),
                ('اردستان', 'اردستان'),
            ],
            'خراسان رضوی': [
                ('مشهد', 'مشهد'),
                ('نیشابور', 'نیشابور'),
                ('سبزوار', 'سبزوار'),
                ('قوچان', 'قوچان'),
                ('تربت حیدریه', 'تربت حیدریه'),
                ('سرخس', 'سرخس'),
                ('کلات', 'کلات'),
                ('تایباد', 'تایباد'),
                ('درگز', 'درگز'),
                ('چناران', 'چناران'),
            ],
            'فارس': [
                ('شیراز', 'شیراز'),
                ('مرودشت', 'مرودشت'),
                ('کازرون', 'کازرون'),
                ('لار', 'لار'),
                ('داراب', 'داراب'),
                ('جهرم', 'جهرم'),
                ('فسا', 'فسا'),
                ('نورآباد ممسنی', 'نورآباد ممسنی'),
                ('اقلید', 'اقلید'),
                ('سروستان', 'سروستان'),
            ],
            'آذربایجان شرقی': [
                ('تبریز', 'تبریز'),
                ('مراغه', 'مراغه'),
                ('مرند', 'مرند'),
                ('میانه', 'میانه'),
                ('اهر', 'اهر'),
                ('عجبشیر', 'عجبشیر'),
                ('بناب', 'بناب'),
                ('ملکان', 'ملکان'),
                ('اسکو', 'اسکو'),
                ('آذرشهر', 'آذرشهر'),
            ],
            'خوزستان': [
                ('اهواز', 'اهواز'),
                ('آبادان', 'آبادان'),
                ('خرمشهر', 'خرمشهر'),
                ('دزفول', 'دزفول'),
                ('شوشتر', 'شوشتر'),
                ('بهبهان', 'بهبهان'),
                ('اندیمشک', 'اندیمشک'),
                ('شوش', 'شوش'),
                ('سریع‌السیر', 'سریع‌السیر'),
                ('ماهشهر', 'ماهشهر'),
            ],
            'البرز': [
                ('کرج', 'کرج'),
                ('فردیس', 'فردیس'),
                ('نظرآباد', 'نظرآباد'),
                ('اشتهارد', 'اشتهارد'),
                ('ساوجبلاغ', 'ساوجبلاغ'),
            ],
            'قم': [
                ('قم', 'قم'),
            ],
            'کرمانشاه': [
                ('کرمانشاه', 'کرمانشاه'),
                ('سرپل ذهاب', 'سرپل ذهاب'),
                ('کنگاور', 'کنگاور'),
                ('صحنه', 'صحنه'),
                ('اسلام‌آباد غرب', 'اسلام‌آباد غرب'),
                ('روانسر', 'روانسر'),
                ('جوانرود', 'جوانرود'),
            ],
            'آذربایجان غربی': [
                ('ارومیه', 'ارومیه'),
                ('خوی', 'خوی'),
                ('مهاباد', 'مهاباد'),
                ('بوکان', 'بوکان'),
                ('میاندوآب', 'میاندوآب'),
                ('سلماس', 'سلماس'),
                ('خسروشهر', 'خسروشهر'),
                ('شاپور', 'شاپور'),
                ('نقده', 'نقده'),
                ('اشنویه', 'اشنویه'),
            ],
            'گیلان': [
                ('رشت', 'رشت'),
                ('انزلی', 'انزلی'),
                ('لاهیجان', 'لاهیجان'),
                ('آستارا', 'آستارا'),
                ('لنگرود', 'لنگرود'),
                ('فومن', 'فومن'),
                ('صومعه‌سرا', 'صومعه‌سرا'),
                ('سیاهکل', 'سیاهکل'),
                ('آستانه اشرفیه', 'آستانه اشرفیه'),
                ('رودسر', 'رودسر'),
            ],
            'زنجان': [
                ('زنجان', 'زنجان'),
                ('ابهر', 'ابهر'),
                ('خرمدره', 'خرمدره'),
                ('طارم', 'طارم'),
            ],
            'همدان': [
                ('همدان', 'همدان'),
                ('ملایر', 'ملایر'),
                ('نهاوند', 'نهاوند'),
                ('تویسرکان', 'تویسرکان'),
                ('اسدآباد', 'اسدآباد'),
                ('کبودرآهنگ', 'کبودرآهنگ'),
                ('رزن', 'رزن'),
                ('فامنین', 'فامنین'),
            ],
            'کرمان': [
                ('کرمان', 'کرمان'),
                ('سیرجان', 'سیرجان'),
                ('بم', 'بم'),
                ('جیرفت', 'جیرفت'),
                ('رفسنجان', 'رفسنجان'),
                ('شهربابک', 'شهربابک'),
                ('بردسیر', 'بردسیر'),
                ('کهنوج', 'کهنوج'),
                ('منوجان', 'منوجان'),
                ('رودبار جنوب', 'رودبار جنوب'),
            ],
            'یزد': [
                ('یزد', 'یزد'),
                ('اردکان', 'اردکان'),
                ('مهریز', 'مهریز'),
                ('تفت', 'تفت'),
                ('اشکذر', 'اشکذر'),
                ('بفض', 'بفض'),
                ('بهاباد', 'بهاباد'),
                ('طبس', 'طبس'),
                ('خاتم', 'خاتم'),
                ('مهر', 'مهر'),
            ],
            'اردبیل': [
                ('اردبیل', 'اردبیل'),
                ('مشگین‌شهر', 'مشگین‌شهر'),
                ('پارس‌آباد', 'پارس‌آباد'),
                ('خلخال', 'خلخال'),
                ('گرمی', 'گرمی'),
                ('نمین', 'نمین'),
                ('کوثر', 'کوثر'),
            ],
            'هرمزگان': [
                ('بندرعباس', 'بندرعباس'),
                ('میناب', 'میناب'),
                ('بندر لنگه', 'بندر لنگه'),
                ('قشم', 'قشم'),
                ('بستک', 'بستک'),
                ('سیریک', 'سیریک'),
                ('جاسک', 'جاسک'),
                ('حاجی‌آباد', 'حاجی‌آباد'),
                ('بندر خمیر', 'بندر خمیر'),
            ],
            'مرکزی': [
                ('اراک', 'اراک'),
                ('ساوه', 'ساوه'),
                ('دلیجان', 'دلیجان'),
                ('خمین', 'خمین'),
                ('شازند', 'شازند'),
                ('محلات', 'محلات'),
                ('خنداب', 'خنداب'),
                ('زرندیه', 'زرندیه'),
                ('آشتیان', 'آشتیان'),
            ],
            'بوشهر': [
                ('بوشهر', 'بوشهر'),
                ('برازجان', 'برازجان'),
                ('کنگان', 'کنگان'),
                ('دیر', 'دیر'),
                ('کنارک', 'کنارک'),
                ('عسلویه', 'عسلویه'),
                ('تنگستان', 'تنگستان'),
                ('جم', 'جم'),
                ('دشتستان', 'دشتستان'),
            ],
            'سیستان و بلوچستان': [
                ('زاهدان', 'زاهدان'),
                ('چابهار', 'چابهار'),
                ('ایرانشهر', 'ایرانشهر'),
                ('سراوان', 'سراوان'),
                ('زابل', 'زابل'),
                ('خاش', 'خاش'),
                ('سربیشه', 'سربیشه'),
                ('نیک‌شهر', 'نیک‌شهر'),
                ('سراوان', 'سراوان'),
                ('کنارک', 'کنارک'),
            ],
            'قزوین': [
                ('قزوین', 'قزوین'),
                ('بوئین‌زهرا', 'بوئین‌زهرا'),
                ('البرز', 'البرز'),
                ('آوج', 'آوج'),
                ('تاكستان', 'تاكستان'),
            ],
            'سمنان': [
                ('سمنان', 'سمنان'),
                ('شاهرود', 'شاهرود'),
                ('دامغان', 'دامغان'),
                ('مهدیشهر', 'مهدیشهر'),
                ('سرخه', 'سرخه'),
                ('ایوانکی', 'ایوانکی'),
                ('گرمسار', 'گرمسار'),
            ],
            'مازندران': [
                ('ساری', 'ساری'),
                ('بابل', 'بابل'),
                ('بابلسر', 'بابلسر'),
                ('بهشهر', 'بهشهر'),
                ('امیرآباد', 'امیرآباد'),
                ('نکا', 'نکا'),
                ('جویبار', 'جویبار'),
                ('قائمشهر', 'قائمشهر'),
                ('سوادکوه', 'سوادکوه'),
                ('بابلکنار', 'بابلکنار'),
            ],
            'گلستان': [
                ('گرگان', 'گرگان'),
                ('گنبد کاووس', 'گنبد کاووس'),
                ('بندر ترکمن', 'بندر ترکمن'),
                ('آق‌قلا', 'آق‌قلا'),
                ('رامیان', 'رامیان'),
                ('کلاله', 'کلاله'),
                ('مراوه تپه', 'مراوه تپه'),
                ('بندر گز', 'بندر گز'),
                ('علی‌آباد', 'علی‌آباد'),
                ('مینودشت', 'مینودشت'),
            ],
            'خراسان شمالی': [
                ('بجنورد', 'بجنورد'),
                ('شیروان', 'شیروان'),
                ('اسفراین', 'اسفراین'),
                ('جاجرم', 'جاجرم'),
                ('مانه و سملقان', 'مانه و سملقان'),
                ('فاروج', 'فاروج'),
                ('گرگان', 'گرگان'),
            ],
            'خراسان جنوبی': [
                ('بیرجند', 'بیرجند'),
                ('قاینات', 'قاینات'),
                ('فردوس', 'فردوس'),
                ('سرایان', 'سرایان'),
                ('نهبندان', 'نهبندان'),
                ('طبس', 'طبس'),
                ('بشرویه', 'بشرویه'),
                ('حاجی‌آباد', 'حاجی‌آباد'),
                ('خوسف', 'خوسف'),
            ],
            'چهارمحال و بختیاری': [
                ('شهرکرد', 'شهرکرد'),
                ('بروجن', 'بروجن'),
                ('لرستان', 'لرستان'),
                ('اردل', 'اردل'),
                ('فارسان', 'فارسان'),
                ('کوهرنگ', 'کوهرنگ'),
                ('لایبرک', 'لایبرک'),
            ],
            'لرستان': [
                ('خرم‌آباد', 'خرم‌آباد'),
                ('دلفان', 'دلفان'),
                ('الیگودرز', 'الیگودرز'),
                ('بروجرد', 'بروجرد'),
                ('دورود', 'دورود'),
                ('ازنا', 'ازنا'),
                ('پلدختر', 'پلدختر'),
                ('سلسله', 'سلسله'),
                ('معروف', 'معروف'),
            ],
            'ایلام': [
                ('ایلام', 'ایلام'),
                ('ایوان', 'ایوان'),
                ('مهران', 'مهران'),
                ('دهلران', 'دهلران'),
                ('دره‌شهر', 'دره‌شهر'),
                ('آبدانان', 'آبدانان'),
                ('بدره', 'بدره'),
                ('سیروان', 'سیروان'),
                ('ملکشاهی', 'ملکشاهی'),
            ],
            'کردستان': [
                ('سنندج', 'سنندج'),
                ('مریوان', 'مریوان'),
                ('سقز', 'سقز'),
                ('بانه', 'بانه'),
                ('کامیاران', 'کامیاران'),
                ('دیواندره', 'دیواندره'),
                ('بیجار', 'بیجار'),
                ('سروآباد', 'سروآباد'),
                ('دولت‌آباد', 'دولت‌آباد'),
            ],
            'کهگیلویه و بویراحمد': [
                ('یاسوج', 'یاسوج'),
                ('دهدشت', 'دهدشت'),
                ('گچساران', 'گچساران'),
                ('بهمئی', 'بهمئی'),
                ('چرام', 'چرام'),
                ('دنا', 'دنا'),
                ('لیگور', 'لیگور'),
                ('دیشموک', 'دیشموک'),
            ],
        }


        # ذخیره برای استفاده در جاوااسکریپت
        self.province_cities_data = cities_by_province

    def set_city_choices_based_on_province(self):
        """تنظیم گزینه‌های شهر بر اساس استان انتخاب شده"""
        if self.instance and self.instance.province:
            province = self.instance.province
            if province in self.province_cities_data:
                cities = self.province_cities_data[province]
                # تبدیل به فرمت مناسب برای فیلد CharField با ویجت Select
                self.fields['city'].widget.choices = [('', 'انتخاب شهر')] + cities
                self.fields['city'].widget.attrs.pop('disabled', None)

    def get_province_cities_json(self):
        """دریافت داده‌های JSON برای جاوااسکریپت"""
        return json.dumps(self.province_cities_data)
    
    def save(self, commit=True):
        """ذخیره فرم با مقادیر location"""
        instance = super().save(commit=False)

        if self.current_user:
            instance.created_by = self.current_user
            instance.modified_by = self.current_user        
        
        if commit:
            instance.save()
            
            # مدیریت کاربر پیمانکار (کاربر جاری)
            ProjectUser.objects.get_or_create(
                project=instance,
                user=self.current_user,
                role='contractor',
                defaults={
                    'is_primary': True,
                    'assigned_by': self.current_user
                }
            )
            # مدیریت سایر کاربران
            self.manage_project_users(instance)

        if self.current_user:
            instance.created_by = self.current_user
            instance.modified_by = self.current_user        
     
        return instance
    
    def manage_project_users(self, project):
        """مدیریت کاربران پروژه"""
        role_user_mapping = {
            'employer_user': 'employer',
            'project_manager_user': 'project_manager', 
            'consultant_user': 'consultant',
            'supervising_engineer_user': 'supervisor',
        }
        
        for form_field, role in role_user_mapping.items():
            user = self.cleaned_data.get(form_field)
            
            # حذف کاربران قبلی با این نقش
            ProjectUser.objects.filter(
                project=project, 
                role=role
            ).exclude(user=user).delete()
            
            # اگر کاربر جدید انتخاب شده، اضافه کن
            if user:
                ProjectUser.objects.update_or_create(
                    project=project,
                    user=user,
                    role=role,
                    defaults={
                        'assigned_by': self.current_user,
                        'is_active': True
                    }
                )

    def clean_project_code(self):
        """بررسی منحصر به فرد بودن کد پروژه"""
        project_code = self.cleaned_data.get('project_code')
        
        if project_code:
            if Project.objects.filter(project_code=project_code, is_active=True).exists():
                raise ValidationError(
                    f'کد پروژه "{project_code}" قبلاً استفاده شده است. '
                    f'لطفاً کد منحصر به فردی انتخاب کنید.',
                    code='duplicate_code'
                )
        
        # اعتبارسنجی فرمت کد پروژه
        if not self._is_valid_project_code_format(project_code):
            raise ValidationError(
                'فرمت کد پروژه صحیح نیست. مثال: P-1403-001',
                code='invalid_format'
            )
        
        return project_code

    def clean_contract_amount(self):
        """پاکسازی و اعتبارسنجی مبلغ قرارداد"""
        amount_str = self.cleaned_data.get('contract_amount', '')
        
        if amount_str:
            # حذف کاما، فضاها و هر کاراکتر غیرعددی
            cleaned_amount = ''.join(filter(lambda x: x.isdigit(), amount_str))
            
            if not cleaned_amount:
                raise ValidationError('مبلغ قرارداد باید عدد صحیح باشد.')
            
            try:
                amount_value = int(cleaned_amount)
                if amount_value < 100000:  # حداقل مبلغ منطقی
                    raise ValidationError('مبلغ قرارداد نمی‌تواند کمتر از 100,000 ریال باشد.')
                
                if amount_value > 100000000000000:  # حداکثر مبلغ منطقی
                    raise ValidationError('مبلغ قرارداد بیش از حد مجاز است.')
                
                return amount_value
            except ValueError:
                raise ValidationError('مبلغ قرارداد باید عدد صحیح باشد.')
        
        raise ValidationError('مبلغ قرارداد الزامی است.')
    
    def clean_execution_year(self):
        """اعتبارسنجی سال اجرا"""
        year = self.cleaned_data.get('execution_year')
        
        if year:
            try:
                year_int = int(year)
                current_year = 1404  # یا از datetime استفاده کنید
                
                if year_int < 1374 or year_int > current_year + 2:
                    raise ValidationError(
                        f'سال اجرا باید بین 1390 تا {current_year + 2} باشد.'
                    )
                
                return year_int
            except (ValueError, TypeError):
                raise ValidationError('سال اجرا باید عدد صحیح باشد.')
        
        raise ValidationError('سال اجرا الزامی است.')
    
        # **اصلاح اصلی: clean_contract_date**
    
    def clean_contract_date(self):
        """تبدیل تاریخ شمسی به میلادی"""
        jalali_date_str = self.cleaned_data.get('contract_date')
        
        if not jalali_date_str:
            raise ValidationError('تاریخ قرارداد الزامی است.')
        
        try:
            # تبدیل تاریخ شمسی به میلادی
            # فرمت: YYYY/MM/DD
            from jdatetime import date as jdate
            import re
            
            # پاکسازی و استخراج اعداد
            numbers = re.findall(r'\d+', jalali_date_str)
            if len(numbers) < 3:
                raise ValidationError('فرمت تاریخ صحیح نیست.')
            
            year, month, day = map(int, numbers[:3])
            
            # ایجاد تاریخ شمسی و تبدیل به میلادی
            jalali_date = jdate(year, month, day)
            gregorian_date = jalali_date.togregorian()
            
            return gregorian_date
            
        except (ValueError, AttributeError, Exception) as e:
            raise ValidationError('تاریخ وارد شده معتبر نیست. لطفاً از تقویم استفاده کنید.')

    def _is_valid_project_code_format(self, code):
        """بررسی فرمت صحیح کد پروژه"""
        if not code:
            return False
        
        # الگوی پیشنهادی: P-YYYY-NNN (حرف-سال-شماره)
        import re
        pattern = r'^[A-Z]{1,3}-\d{4}-\d{3,4}$'
        return bool(re.match(pattern, code.upper()))
    
    def clean(self):
        """اعتبارسنجی کلی فرم"""
        cleaned_data = super().clean()
        
        employer = cleaned_data.get('employer')
        contractor = cleaned_data.get('contractor')
        
        if employer and contractor:
            if employer.lower() == contractor.lower():
                raise ValidationError({
                    'employer': 'کارفرما و پیمانکار نمی‌توانند یکسان باشند.',
                    'contractor': 'کارفرما و پیمانکار نمی‌توانند یکسان باشند.'
                }) 
        return cleaned_data
    
    def save(self, commit=True):
        """ذخیره فرم"""
        instance = super().save(commit=False)
        
        if self.current_user:
            instance.created_by = self.current_user
            instance.modified_by = self.current_user        
        
        if commit:
            instance.save()
            # ایجاد رکورد ProjectUser برای پیمانکار
            ProjectUser.objects.create(
                project=instance,
                user=self.current_user,
                role='contractor',
                is_primary=True,
                assigned_by=self.current_user
            )        
        return instance

class ProjectEditForm(forms.ModelForm):
    """
    فرم سفارشی برای ویرایش پروژه با پشتیبانی از تاریخ جلالی
    """
    # سال اجرا (محدوده مناسب برای پروژه‌های عمرانی)
    execution_year = forms.ChoiceField(
        choices=[(year, f"{year} (سال {year})") for year in range(1374, 1405)],
        widget=Select(attrs={
            'class': 'form-select',
            'data-placeholder': 'سال اجرا را انتخاب کنید'
        }),
        required=True,
        label='سال اجرا بر اساس صورت وضعیت'
    )
    
    # اصلاح فیلد تاریخ به شمسی
    contract_date = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'form-control persian-datepicker',
            'placeholder': 'برای انتخاب تاریخ کلیک کنید',
            'autocomplete': 'off',
            'readonly': 'readonly',  # جلوگیری از ورود دستی
        }),
        required=True,
        label='تاریخ قرارداد'
    )
    
    # مبلغ قرارداد با فرمت مناسب
    contract_amount = forms.CharField(
        widget=TextInput(attrs={
            'class': 'form-control',
            'placeholder': '100,000,000',
            'type': 'text',
            'data-inputmask': "'alias': 'numeric', 'groupSeparator': ',', 'radixPoint': '.', 'digits': 0"
        }),
        required=True,
        label='مبلغ قرارداد (ریال)'
    )
    
    # وضعیت
    status = forms.ChoiceField(
        choices=Project.STATUS_CHOICES,
        widget=Select(attrs={
            'class': 'form-select'
        }),
        label='وضعیت پروژه'
    )
    
    # **فیلدهای location به صورت ChoiceField**
    country = forms.ChoiceField(
        choices=[
            ('', 'انتخاب کشور'),
            ('ایران', 'ایران'),
            ('افغانستان', 'افغانستان'),
            ('عراق', 'عراق'),
            ('ترکیه', 'ترکیه'),
            ('امارات متحده عربی', 'امارات متحده عربی'),
            ('قطر', 'قطر'),
            ('عمان', 'عمان'),
            ('بحرین', 'بحرین'),
            ('کویت', 'کویت'),
            ('سوریه', 'سوریه'),
            ('لبنان', 'لبنان'),
            ('اردن', 'اردن'),
            ('پاکستان', 'پاکستان'),
            ('ترکمنستان', 'ترکمنستان'),
            ('آذربایجان', 'آذربایجان'),
            ('ارمنستان', 'ارمنستان'),
            ('گرجستان', 'گرجستان'),
        ],
        widget=Select(attrs={
            'class': 'form-select',
            'id': 'id_country',
            'name': 'country'
        }),
        required=True,
        label='کشور'
    )
    
    province = forms.ChoiceField(
        choices=[('', 'انتخاب استان')],  # در __init__ تنظیم می‌شود
        widget=Select(attrs={
            'class': 'form-select',
            'id': 'id_province',
            'name': 'province'
        }),
        required=True,
        label='استان'
    )
    
    city = forms.CharField(
        widget=forms.Select(attrs={
            'class': 'form-select', 
            'id': 'id_city',
            'name': 'city',
            'disabled': True
        }),
        required=True,
        label='شهر'
    )
    
    # توضیحات
    description = forms.CharField(
        widget=Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'توضیحات مختصر درباره پروژه (اختیاری)'
        }),
        required=False,
        label='توضیحات پروژه'
    )
    
    # **فیلد آپلود فایل جدید (اختیاری)**
    contract_file_new = forms.FileField(
        widget=FileInput(attrs={
            'class': 'form-control',
            'accept': '.pdf,.doc,.docx',
            'data-max-size': '5242880'  # 5MB
        }),
        required=False,
        label='فایل جدید قرارداد (اختیاری)'
    )


    class Meta:
        model = Project
        fields = [
            'project_name',
            'project_code',
            'project_type',
            'employer',
            'contractor',
            'consultant',
            'supervising_engineer',
            'contract_number',
            'contract_date',
            'execution_year',
            'contract_amount',
            'status',
            'contract_file',  # فایل فعلی (نمایش) - قابل ویرایش نیست
            'description',
            'country',
            'province',
            'city',    
        ]
        widgets = {
            'project_name': TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'نام کامل پروژه (مثال: پروژه احداث پل فلزی)',
                'maxlength': 255,
                'required': True
            }),
            'project_code': TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'P-1403-001',
                'maxlength': 50,
                'required': True,
                'autocomplete': 'off'
            }),
            'employer': TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'نام کامل کارفرما (مثال: شهرداری تهران)',
                'maxlength': 255,
                'required': True
            }),
            'contractor': TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'نام پیمانکار (مثال: شرکت عمران آتی)',
                'maxlength': 255,
                'required': True
            }),
            'consultant': TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'نام مدیر طرح یا مشاور (اختیاری)',
                'maxlength': 255
            }),
            'supervising_engineer': TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'نام مهندس ناظر (اختیاری)',
                'maxlength': 255
            }),
            'contract_number': TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'شماره قرارداد (مثال: 1403/001)',
                'maxlength': 50,
                'required': True
            }),
            # **فایل فعلی فقط برای نمایش - قابل ویرایش نیست**
            'contract_file': forms.FileInput(attrs={
                'class': 'form-control',
                'disabled': True,
                'readonly': True,
                'style': 'display: none;'  # مخفی کردن از رندر
            }),
            'project_type': Select(attrs={
                'class': 'form-select'
            }),
            'contract_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date',
                'autocomplete': 'off',
                'placeholder': '1403-06-15'
            }),
        }
        labels = {
            'project_name': 'نام پروژه',
            'project_code': 'کد پروژه',
            'employer': 'کارفرما',
            'contractor': 'پیمانکار',
            'consultant': 'مدیر طرح/مشاور',
            'supervising_engineer': 'مهندس ناظر',
            'contract_number': 'شماره قرارداد',
            'contract_amount': 'مبلغ قرارداد (ریال)',
            'contract_file': 'فایل قرارداد فعلی',
            'description': 'توضیحات',
        }
    
    def __init__(self, *args, **kwargs):
        # **پشتیبانی از پارامترهای اضافی**
        self.current_user = kwargs.pop('current_user', None)
        self.original_project = kwargs.pop('original_project', None)  # اضافه کردن این خط
    
        # Call parent __init__ first to set up self.fields
        super().__init__(*args, **kwargs)
        
        # **بررسی اینکه instance و original_project یکی باشند**
        if self.original_project and self.instance:
            # Your existing logic here
            pass        
        # **تنظیمات خاص برای ویرایش**
        if self.instance:
            # تنظیم مقادیر location از instance
            self.set_location_from_instance()
            
            # تنظیم تاریخ قرارداد به فرمت شمسی
            self.set_contract_date_display()
            
            # تنظیم مبلغ قرارداد با فرمت مناسب
            self.set_contract_amount_display()
            
            # تنظیم سال اجرا
            self.fields['execution_year'].initial = self.instance.execution_year
        
        # تنظیم کشور پیش‌فرض (اگر خالی باشد)
        if not self.fields['country'].initial:
            self.fields['country'].initial = 'ایران'
        
        # تنظیم گزینه‌های استان و شهر
        self.set_location_choices()
        
        # **مخفی کردن فیلد contract_file در رندر**
        self.fields['contract_file'].widget = forms.HiddenInput()
        self.fields['contract_file'].required = False

    def set_location_from_instance(self):
        """تنظیم مقادیر location از instance موجود"""
        if self.instance:
            # تنظیم مقادیر location
            self.fields['country'].initial = getattr(self.instance, 'country', 'ایران')
            self.fields['province'].initial = getattr(self.instance, 'province', '')
            self.fields['city'].initial = getattr(self.instance, 'city', '')
    
    def set_contract_date_display(self):
        """تنظیم نمایش تاریخ قرارداد به فرمت شمسی"""
        if self.instance and self.instance.contract_date:
            try:
                from jdatetime import date as jdate
                # تبدیل تاریخ میلادی به شمسی
                gregorian_date = self.instance.contract_date
                jalali_date = jdate.fromgregorian(date=gregorian_date)
                self.initial['contract_date'] = jalali_date.strftime('%Y/%m/%d')
                print(f"✅ تاریخ قرارداد تنظیم شد: {jalali_date.strftime('%Y/%m/%d')}")
            except ImportError:
                # در صورت عدم وجود jdatetime، تاریخ میلادی را نمایش می‌دهیم
                self.initial['contract_date'] = self.instance.contract_date.strftime('%Y-%m-%d')
            except Exception as e:
                print(f"❌ خطا در تبدیل تاریخ: {e}")
                self.initial['contract_date'] = str(self.instance.contract_date)
    
    def set_contract_amount_display(self):
        """تنظیم نمایش مبلغ قرارداد با فرمت مناسب"""
        if self.instance and self.instance.contract_amount:
            # فرمت‌دهی عدد با کاما
            formatted_amount = f"{self.instance.contract_amount:,}"
            self.initial['contract_amount'] = formatted_amount
            print(f"✅ مبلغ قرارداد تنظیم شد: {formatted_amount}")
    
    def set_current_file_display(self):
        """تنظیم نمایش اطلاعات فایل فعلی"""
        if self.instance and self.instance.contract_file:
            # اضافه کردن اطلاعات فایل به initial data
            current_file_info = {
                'name': self.instance.contract_file.name,
                'size': self.instance.contract_file.size,
                'url': self.instance.contract_file.url if hasattr(self.instance.contract_file, 'url') else None
            }
            self.initial['current_contract_file'] = current_file_info
            print(f"✅ فایل فعلی: {current_file_info['name']}")
    
    def set_location_choices(self):
        """تنظیم گزینه‌های استان و شهر"""
        
        # لیست استان‌های ایران
        provinces = [
            ('', 'انتخاب استان'),
            ('تهران', 'تهران'),
            ('اصفهان', 'اصفهان'),
            ('خراسان رضوی', 'خراسان رضوی'),
            ('فارس', 'فارس'),
            ('آذربایجان شرقی', 'آذربایجان شرقی'),
            ('خوزستان', 'خوزستان'),
            ('البرز', 'البرز'),
            ('قم', 'قم'),
            ('کرمانشاه', 'کرمانشاه'),
            ('آذربایجان غربی', 'آذربایجان غربی'),
            ('گیلان', 'گیلان'),
            ('زنجان', 'زنجان'),
            ('همدان', 'همدان'),
            ('کرمان', 'کرمان'),
            ('یزد', 'یزد'),
            ('اردبیل', 'اردبیل'),
            ('هرمزگان', 'هرمزگان'),
            ('مرکزی', 'مرکزی'),
            ('بوشهر', 'بوشهر'),
            ('سیستان و بلوچستان', 'سیستان و بلوچستان'),
            ('قزوین', 'قزوین'),
            ('سمنان', 'سمنان'),
            ('مازندران', 'مازندران'),
            ('گلستان', 'گلستان'),
            ('خراسان شمالی', 'خراسان شمالی'),
            ('خراسان جنوبی', 'خراسان جنوبی'),
            ('چهارمحال و بختیاری', 'چهارمحال و بختیاری'),
            ('لرستان', 'لرستان'),
            ('ایلام', 'ایلام'),
            ('کردستان', 'کردستان'),
            ('کهگیلویه و بویراحمد', 'کهگیلویه و بویراحمد'),
        ]

        self.fields['province'].choices = provinces
    
    def get_cities_by_province(self):
        """دریافت داده‌های شهرهای هر استان"""
        return {
            'تهران': [
                ('تهران', 'تهران'),
                ('ری', 'ری'),
                ('ورامین', 'ورامین'),
                ('ملارد', 'ملارد'),
                ('شهرری', 'شهرری'),
                ('رودهن', 'رودهن'),
                ('بومهن', 'بومهن'),
                ('دماوند', 'دماوند'),
                ('پردیس', 'پردیس'),
                ('شهریار', 'شهریار'),
            ],
            'اصفهان': [
                ('اصفهان', 'اصفهان'),
                ('کاشان', 'کاشان'),
                ('خمینی‌شهر', 'خمینی‌شهر'),
                ('نجف‌آباد', 'نجف‌آباد'),
                ('شاهین‌شهر', 'شاهین‌شهر'),
                ('لنجان', 'لنجان'),
                ('فلاورجان', 'فلاورجان'),
                ('گلپایگان', 'گلپایگان'),
                ('خور و بیابانک', 'خور و بیابانک'),
                ('اردستان', 'اردستان'),
            ],
            'خراسان رضوی': [
                ('مشهد', 'مشهد'),
                ('نیشابور', 'نیشابور'),
                ('سبزوار', 'سبزوار'),
                ('قوچان', 'قوچان'),
                ('تربت حیدریه', 'تربت حیدریه'),
                ('سرخس', 'سرخس'),
                ('کلات', 'کلات'),
                ('تایباد', 'تایباد'),
                ('درگز', 'درگز'),
                ('چناران', 'چناران'),
            ],
            'فارس': [
                ('شیراز', 'شیراز'),
                ('مرودشت', 'مرودشت'),
                ('کازرون', 'کازرون'),
                ('لار', 'لار'),
                ('داراب', 'داراب'),
                ('جهرم', 'جهرم'),
                ('فسا', 'فسا'),
                ('نورآباد ممسنی', 'نورآباد ممسنی'),
                ('اقلید', 'اقلید'),
                ('سروستان', 'سروستان'),
            ],
            'آذربایجان شرقی': [
                ('تبریز', 'تبریز'),
                ('مراغه', 'مراغه'),
                ('مرند', 'مرند'),
                ('میانه', 'میانه'),
                ('اهر', 'اهر'),
                ('عجبشیر', 'عجبشیر'),
                ('بناب', 'بناب'),
                ('ملکان', 'ملکان'),
                ('اسکو', 'اسکو'),
                ('آذرشهر', 'آذرشهر'),
            ],
            'خوزستان': [
                ('اهواز', 'اهواز'),
                ('آبادان', 'آبادان'),
                ('خرمشهر', 'خرمشهر'),
                ('دزفول', 'دزفول'),
                ('شوشتر', 'شوشتر'),
                ('بهبهان', 'بهبهان'),
                ('اندیمشک', 'اندیمشک'),
                ('شوش', 'شوش'),
                ('سریع‌السیر', 'سریع‌السیر'),
                ('ماهشهر', 'ماهشهر'),
            ],
            'البرز': [
                ('کرج', 'کرج'),
                ('فردیس', 'فردیس'),
                ('نظرآباد', 'نظرآباد'),
                ('اشتهارد', 'اشتهارد'),
                ('ساوجبلاغ', 'ساوجبلاغ'),
            ],
            'قم': [
                ('قم', 'قم'),
            ],
            'کرمانشاه': [
                ('کرمانشاه', 'کرمانشاه'),
                ('سرپل ذهاب', 'سرپل ذهاب'),
                ('کنگاور', 'کنگاور'),
                ('صحنه', 'صحنه'),
                ('اسلام‌آباد غرب', 'اسلام‌آباد غرب'),
                ('روانسر', 'روانسر'),
                ('جوانرود', 'جوانرود'),
            ],
            'آذربایجان غربی': [
                ('ارومیه', 'ارومیه'),
                ('خوی', 'خوی'),
                ('مهاباد', 'مهاباد'),
                ('بوکان', 'بوکان'),
                ('میاندوآب', 'میاندوآب'),
                ('سلماس', 'سلماس'),
                ('خسروشهر', 'خسروشهر'),
                ('شاپور', 'شاپور'),
                ('نقده', 'نقده'),
                ('اشنویه', 'اشنویه'),
            ],
            'گیلان': [
                ('رشت', 'رشت'),
                ('انزلی', 'انزلی'),
                ('لاهیجان', 'لاهیجان'),
                ('آستارا', 'آستارا'),
                ('لنگرود', 'لنگرود'),
                ('فومن', 'فومن'),
                ('صومعه‌سرا', 'صومعه‌سرا'),
                ('سیاهکل', 'سیاهکل'),
                ('آستانه اشرفیه', 'آستانه اشرفیه'),
                ('رودسر', 'رودسر'),
            ],
            'زنجان': [
                ('زنجان', 'زنجان'),
                ('ابهر', 'ابهر'),
                ('خرمدره', 'خرمدره'),
                ('طارم', 'طارم'),
            ],
            'همدان': [
                ('همدان', 'همدان'),
                ('ملایر', 'ملایر'),
                ('نهاوند', 'نهاوند'),
                ('تویسرکان', 'تویسرکان'),
                ('اسدآباد', 'اسدآباد'),
                ('کبودرآهنگ', 'کبودرآهنگ'),
                ('رزن', 'رزن'),
                ('فامنین', 'فامنین'),
            ],
            'کرمان': [
                ('کرمان', 'کرمان'),
                ('سیرجان', 'سیرجان'),
                ('بم', 'بم'),
                ('جیرفت', 'جیرفت'),
                ('رفسنجان', 'رفسنجان'),
                ('شهربابک', 'شهربابک'),
                ('بردسیر', 'بردسیر'),
                ('کهنوج', 'کهنوج'),
                ('منوجان', 'منوجان'),
                ('رودبار جنوب', 'رودبار جنوب'),
            ],
            'یزد': [
                ('یزد', 'یزد'),
                ('اردکان', 'اردکان'),
                ('مهریز', 'مهریز'),
                ('تفت', 'تفت'),
                ('اشکذر', 'اشکذر'),
                ('بفض', 'بفض'),
                ('بهاباد', 'بهاباد'),
                ('طبس', 'طبس'),
                ('خاتم', 'خاتم'),
                ('مهر', 'مهر'),
            ],
            'اردبیل': [
                ('اردبیل', 'اردبیل'),
                ('مشگین‌شهر', 'مشگین‌شهر'),
                ('پارس‌آباد', 'پارس‌آباد'),
                ('خلخال', 'خلخال'),
                ('گرمی', 'گرمی'),
                ('نمین', 'نمین'),
                ('کوثر', 'کوثر'),
            ],
            'هرمزگان': [
                ('بندرعباس', 'بندرعباس'),
                ('میناب', 'میناب'),
                ('بندر لنگه', 'بندر لنگه'),
                ('قشم', 'قشم'),
                ('بستک', 'بستک'),
                ('سیریک', 'سیریک'),
                ('جاسک', 'جاسک'),
                ('حاجی‌آباد', 'حاجی‌آباد'),
                ('بندر خمیر', 'بندر خمیر'),
            ],
            'مرکزی': [
                ('اراک', 'اراک'),
                ('ساوه', 'ساوه'),
                ('دلیجان', 'دلیجان'),
                ('خمین', 'خمین'),
                ('شازند', 'شازند'),
                ('محلات', 'محلات'),
                ('خنداب', 'خنداب'),
                ('زرندیه', 'زرندیه'),
                ('آشتیان', 'آشتیان'),
            ],
            'بوشهر': [
                ('بوشهر', 'بوشهر'),
                ('برازجان', 'برازجان'),
                ('کنگان', 'کنگان'),
                ('دیر', 'دیر'),
                ('کنارک', 'کنارک'),
                ('عسلویه', 'عسلویه'),
                ('تنگستان', 'تنگستان'),
                ('جم', 'جم'),
                ('دشتستان', 'دشتستان'),
            ],
            'سیستان و بلوچستان': [
                ('زاهدان', 'زاهدان'),
                ('چابهار', 'چابهار'),
                ('ایرانشهر', 'ایرانشهر'),
                ('سراوان', 'سراوان'),
                ('زابل', 'زابل'),
                ('خاش', 'خاش'),
                ('سربیشه', 'سربیشه'),
                ('نیک‌شهر', 'نیک‌شهر'),
                ('کنارک', 'کنارک'),
            ],
            'قزوین': [
                ('قزوین', 'قزوین'),
                ('بوئین‌زهرا', 'بوئین‌زهرا'),
                ('البرز', 'البرز'),
                ('آوج', 'آوج'),
                ('تاكستان', 'تاكستان'),
            ],
            'سمنان': [
                ('سمنان', 'سمنان'),
                ('شاهرود', 'شاهرود'),
                ('دامغان', 'دامغان'),
                ('مهدیشهر', 'مهدیشهر'),
                ('سرخه', 'سرخه'),
                ('ایوانکی', 'ایوانکی'),
                ('گرمسار', 'گرمسار'),
            ],
            'مازندران': [
                ('ساری', 'ساری'),
                ('بابل', 'بابل'),
                ('بابلسر', 'بابلسر'),
                ('بهشهر', 'بهشهر'),
                ('امیرآباد', 'امیرآباد'),
                ('نکا', 'نکا'),
                ('جویبار', 'جویبار'),
                ('قائمشهر', 'قائمشهر'),
                ('سوادکوه', 'سوادکوه'),
                ('بابلکنار', 'بابلکنار'),
            ],
            'گلستان': [
                ('گرگان', 'گرگان'),
                ('گنبد کاووس', 'گنبد کاووس'),
                ('بندر ترکمن', 'بندر ترکمن'),
                ('آق‌قلا', 'آق‌قلا'),
                ('رامیان', 'رامیان'),
                ('کلاله', 'کلاله'),
                ('مراوه تپه', 'مراوه تپه'),
                ('بندر گز', 'بندر گز'),
                ('علی‌آباد', 'علی‌آباد'),
                ('مینودشت', 'مینودشت'),
            ],
            'خراسان شمالی': [
                ('بجنورد', 'بجنورد'),
                ('شیروان', 'شیروان'),
                ('اسفراین', 'اسفراین'),
                ('جاجرم', 'جاجرم'),
                ('مانه و سملقان', 'مانه و سملقان'),
                ('فاروج', 'فاروج'),
            ],
            'خراسان جنوبی': [
                ('بیرجند', 'بیرجند'),
                ('قاینات', 'قاینات'),
                ('فردوس', 'فردوس'),
                ('سرایان', 'سرایان'),
                ('نهبندان', 'نهبندان'),
                ('طبس', 'طبس'),
                ('بشرویه', 'بشرویه'),
                ('حاجی‌آباد', 'حاجی‌آباد'),
                ('خوسف', 'خوسف'),
            ],
            'چهارمحال و بختیاری': [
                ('شهرکرد', 'شهرکرد'),
                ('بروجن', 'بروجن'),
                ('اردل', 'اردل'),
                ('فارسان', 'فارسان'),
                ('کوهرنگ', 'کوهرنگ'),
                ('لایبرک', 'لایبرک'),
            ],
            'لرستان': [
                ('خرم‌آباد', 'خرم‌آباد'),
                ('دلفان', 'دلفان'),
                ('الیگودرز', 'الیگودرز'),
                ('بروجرد', 'بروجرد'),
                ('دورود', 'دورود'),
                ('ازنا', 'ازنا'),
                ('پلدختر', 'پلدختر'),
                ('سلسله', 'سلسله'),
                ('معروف', 'معروف'),
            ],
            'ایلام': [
                ('ایلام', 'ایلام'),
                ('ایوان', 'ایوان'),
                ('مهران', 'مهران'),
                ('دهلران', 'دهلران'),
                ('دره‌شهر', 'دره‌شهر'),
                ('آبدانان', 'آبدانان'),
                ('بدره', 'بدره'),
                ('سیروان', 'سیروان'),
                ('ملکشاهی', 'ملکشاهی'),
            ],
            'کردستان': [
                ('سنندج', 'سنندج'),
                ('مریوان', 'مریوان'),
                ('سقز', 'سقز'),
                ('بانه', 'بانه'),
                ('کامیاران', 'کامیاران'),
                ('دیواندره', 'دیواندره'),
                ('بیجار', 'بیجار'),
                ('سروآباد', 'سروآباد'),
                ('دولت‌آباد', 'دولت‌آباد'),
            ],
            'کهگیلویه و بویراحمد': [
                ('یاسوج', 'یاسوج'),
                ('دهدشت', 'دهدشت'),
                ('گچساران', 'گچساران'),
                ('بهمئی', 'بهمئی'),
                ('چرام', 'چرام'),
                ('دنا', 'دنا'),
                ('لیگور', 'لیگور'),
                ('دیشموک', 'دیشموک'),
            ],
        }
    
    def get_province_cities_json(self):
        """دریافت داده‌های JSON برای جاوااسکریپت"""
        return json.dumps(self.get_cities_by_province())
    
    def save(self, commit=True):
        """ذخیره فرم با مدیریت فایل جدید"""
        instance = super().save(commit=False)
        if self.current_user:
            instance.created_by = self.current_user
            instance.modified_by = self.current_user        
        
        if commit:
            instance.save()
            
            # Assign the current user as contractor
            ProjectUser.objects.create(
                project=instance,
                user=self.current_user,
                role='contractor',
                is_primary=True,
                assigned_by=self.current_user
            )
            
            # Assign employer user if selected
            employer_user = self.cleaned_data.get('employer_user')
            if employer_user:
                ProjectUser.objects.create(
                    project=instance,
                    user=employer_user,
                    role='employer',
                    assigned_by=self.current_user
                )
            
            # Assign project manager user if selected
            project_manager_user = self.cleaned_data.get('project_manager_user')
            if project_manager_user:
                ProjectUser.objects.create(
                    project=instance,
                    user=project_manager_user,
                    role='project_manager',
                    assigned_by=self.current_user
                )

        # **مدیریت فایل جدید قرارداد**
        contract_file_new = self.cleaned_data.get('contract_file_new')
        if contract_file_new:
            # حذف فایل قدیمی اگر وجود داشته باشد
            if instance.contract_file:
                instance.contract_file.delete(save=False)
            # آپلود فایل جدید
            instance.contract_file = contract_file_new
        
        # **ذخیره instance**
        if commit:
            instance.save()
            # ذخیره location fields
            instance.country = self.cleaned_data.get('country', instance.country)
            instance.province = self.cleaned_data.get('province', instance.province)
            instance.city = self.cleaned_data.get('city', instance.city)
            instance.save()
        
        return instance

    def clean_project_code(self):
        """بررسی منحصر به فرد بودن کد پروژه (به جز instance فعلی)"""
        project_code = self.cleaned_data.get('project_code')
        
        if project_code:
            # بررسی منحصر به فرد بودن به جز instance فعلی
            project_filter = {
                'project_code': project_code,
                'is_active': True
            }
            
            # **استفاده از original_project یا instance**
            exclude_id = None
            if self.original_project:
                exclude_id = self.original_project.id
            elif self.instance:
                exclude_id = self.instance.id
            
            if exclude_id:
                project_filter['id__ne'] = exclude_id  # exclude current instance
            
            if Project.objects.filter(**project_filter).exists():
                raise ValidationError(
                    f'کد پروژه "{project_code}" قبلاً استفاده شده است. '
                    f'لطفاً کد منحصر به فردی انتخاب کنید.',
                    code='duplicate_code'
                )
        
        # اعتبارسنجی فرمت کد پروژه
        if not self._is_valid_project_code_format(project_code):
            raise ValidationError(
                'فرمت کد پروژه صحیح نیست. مثال: P-1403-001',
                code='invalid_format'
            )
        
        return project_code

    def clean_contract_amount(self):
        """پاکسازی و اعتبارسنجی مبلغ قرارداد"""
        amount_str = self.cleaned_data.get('contract_amount', '')
        
        if amount_str:
            # حذف کاما، فضاها و هر کاراکتر غیرعددی
            cleaned_amount = ''.join(filter(lambda x: x.isdigit(), amount_str))
            
            if not cleaned_amount:
                raise ValidationError('مبلغ قرارداد باید عدد صحیح باشد.')
            
            try:
                amount_value = int(cleaned_amount)
                if amount_value < 100000:  # حداقل مبلغ منطقی
                    raise ValidationError('مبلغ قرارداد نمی‌تواند کمتر از 100,000 ریال باشد.')
                
                if amount_value > 100000000000000:  # حداکثر مبلغ منطقی
                    raise ValidationError('مبلغ قرارداد بیش از حد مجاز است.')
                
                return amount_value
            except ValueError:
                raise ValidationError('مبلغ قرارداد باید عدد صحیح باشد.')
        
        raise ValidationError('مبلغ قرارداد الزامی است.')
    
    def clean_execution_year(self):
        """اعتبارسنجی سال اجرا"""
        year = self.cleaned_data.get('execution_year')
        
        if year:
            try:
                year_int = int(year)
                try:
                    from jdatetime import datetime as jdatetime
                    current_year = jdatetime.now().year
                except ImportError:
                    current_year = 1404  # مقدار پیش‌فرض
                
                if year_int < 1374 or year_int > current_year + 2:
                    raise ValidationError(
                        f'سال اجرا باید بین 1374 تا {current_year + 2} باشد.'
                    )
                
                return year_int
            except (ValueError, TypeError):
                raise ValidationError('سال اجرا باید عدد صحیح باشد.')
        
        raise ValidationError('سال اجرا الزامی است.')
    
    def clean_contract_date(self):
        """تبدیل تاریخ شمسی به میلادی"""
        jalali_date_str = self.cleaned_data.get('contract_date')
        
        if not jalali_date_str:
            raise ValidationError('تاریخ قرارداد الزامی است.')
        
        try:
            # تبدیل تاریخ شمسی به میلادی
            # فرمت: YYYY/MM/DD
            from jdatetime import date as jdate
            import re
            
            # پاکسازی و استخراج اعداد
            numbers = re.findall(r'\d+', jalali_date_str)
            if len(numbers) < 3:
                raise ValidationError('فرمت تاریخ صحیح نیست.')
            
            year, month, day = map(int, numbers[:3])
            
            # ایجاد تاریخ شمسی و تبدیل به میلادی
            jalali_date = jdate(year, month, day)
            gregorian_date = jalali_date.togregorian()
            
            return gregorian_date
            
        except ImportError:
            raise ValidationError('کتابخانه jdatetime نصب نشده است.')
        except (ValueError, AttributeError, Exception) as e:
            print(f"❌ خطا در تبدیل تاریخ: {e}")
            raise ValidationError('تاریخ وارد شده معتبر نیست. لطفاً از تقویم استفاده کنید.')

    def _is_valid_project_code_format(self, code):
        """بررسی فرمت صحیح کد پروژه"""
        if not code:
            return False
        
        # الگوی پیشنهادی: P-YYYY-NNN (حرف-سال-شماره)
        import re
        pattern = r'^[A-Z]{1,3}-\d{4}-\d{3,4}$'
        return bool(re.match(pattern, code.upper()))
    
    def clean(self):
        """اعتبارسنجی کلی فرم"""
        cleaned_data = super().clean()
        
        employer = cleaned_data.get('employer')
        contractor = cleaned_data.get('contractor')
        
        if employer and contractor:
            if employer.lower() == contractor.lower():
                raise ValidationError({
                    'employer': 'کارفرما و پیمانکار نمی‌توانند یکسان باشند.',
                    'contractor': 'کارفرما و پیمانکار نمی‌توانند یکسان باشند.'
                }) 
        
        # **اعتبارسنجی location**
        country = cleaned_data.get('country')
        province = cleaned_data.get('province')
        city = cleaned_data.get('city')
        
        if country and province and city:
            if country != 'ایران' and province:  # برای کشورهای دیگر، استان معنایی ندارد
                raise ValidationError({
                    'province': 'برای کشورهای غیر از ایران، استان انتخاب نکنید.'
                })
        
        return cleaned_data

    def clean_contract_file_new(self):
        """اعتبارسنجی فایل جدید"""
        file = self.cleaned_data.get('contract_file_new')
        if file:
            # بررسی اندازه فایل
            if file.size > 5 * 1024 * 1024:  # 5MB
                raise ValidationError('حجم فایل نباید بیش از 5 مگابایت باشد.')
            
            # بررسی نوع فایل
            allowed_types = ['.pdf', '.doc', '.docx']
            file_extension = '.' + file.name.split('.')[-1].lower()
            if file_extension not in allowed_types:
                raise ValidationError('فرمت فایل مجاز نیست. فقط PDF، DOC و DOCX مجاز است.')
        
        return file
        """اعتبارسنجی فایل جدید"""
        file = self.cleaned_data.get('contract_file_new')
        if file:
            # بررسی اندازه فایل
            if file.size > 5 * 1024 * 1024:  # 5MB
                raise ValidationError('حجم فایل نباید بیش از 5 مگابایت باشد.')
            
            # بررسی نوع فایل
            allowed_types = ['.pdf', '.doc', '.docx']
            file_extension = '.' + file.name.split('.')[-1].lower()
            if file_extension not in allowed_types:
                raise ValidationError('فرمت فایل مجاز نیست. فقط PDF، DOC و DOCX مجاز است.')
        
        return file
        instance = super().save(commit=False)
        if commit:
            instance.modified_by = self.current_user
            instance.save()
        return instance

class ProjectUserAssignmentForm(forms.ModelForm):
    """
    فرم اختصاص کاربر به پروژه
    """
    class Meta:
        model = ProjectUser
        fields = ['user', 'role', 'is_primary', 'start_date', 'end_date']
        widgets = {
            'user': Select(attrs={'class': 'form-select'}),
            'role': Select(attrs={'class': 'form-select'}),
            'is_primary': CheckboxInput(attrs={'class': 'form-check-input'}),
            'start_date': forms.TextInput(attrs={
                'class': 'form-control persian-datepicker',
                'placeholder': 'تاریخ شروع',
                'autocomplete': 'off',
                'readonly': 'readonly',
            }),
            'end_date': forms.TextInput(attrs={
                'class': 'form-control persian-datepicker',
                'placeholder': 'تاریخ پایان (اختیاری)',
                'autocomplete': 'off',
                'readonly': 'readonly',
            }),
        }
    
    def __init__(self, *args, **kwargs):
        self.project = kwargs.pop('project', None)
        self.current_user = kwargs.pop('current_user', None)
        super().__init__(*args, **kwargs)
        
        # فیلتر نقش‌های قابل اختصاص
        self.fields['role'].queryset = ProjectRole.objects.filter(is_active=True)
        
        # فیلتر کاربران (به جز کاربر جاری)
        self.fields['user'].queryset = User.objects.filter(
            is_active=True
        ).exclude(
            pk=self.current_user.pk if self.current_user else None
        )
        
        # تنظیم تاریخ شروع به امروز
        if not self.instance.pk:
            try:
                from jdatetime import datetime as jdatetime
                today = jdatetime.now()
                self.initial['start_date'] = today.strftime('%Y/%m/%d')
            except ImportError:
                self.initial['start_date'] = timezone.now().date()
    
    def clean(self):
        cleaned_data = super().clean()
        user = cleaned_data.get('user')
        role = cleaned_data.get('role')
        is_primary = cleaned_data.get('is_primary')
        
        if user and role and self.project:
            # بررسی تکراری نبودن
            existing = ProjectUser.objects.filter(
                project=self.project,
                user=user,
                role=role,
                is_active=True
            ).exclude(pk=self.instance.pk if self.instance else None)
            
            if existing.exists():
                raise ValidationError('این کاربر با این نقش قبلاً به پروژه اضافه شده است.')
            
            # اگر نقش اصلی است، بررسی کن که فقط یک نقش اصلی از این نوع وجود داشته باشد
            if is_primary:
                primary_exists = ProjectUser.objects.filter(
                    project=self.project,
                    role=role,
                    is_primary=True,
                    is_active=True
                ).exclude(pk=self.instance.pk if self.instance else None)
                
                if primary_exists.exists():
                    raise ValidationError(f'یک {role.get_name_display()} اصلی دیگر برای این پروژه وجود دارد.')
        
        return cleaned_data
    
    def clean_start_date(self):
        """تبدیل تاریخ شمسی به میلادی"""
        jalali_date_str = self.cleaned_data.get('start_date')
        return self._convert_jalali_to_gregorian(jalali_date_str)
    
    def clean_end_date(self):
        """تبدیل تاریخ شمسی به میلادی"""
        jalali_date_str = self.cleaned_data.get('end_date')
        if jalali_date_str:
            return self._convert_jalali_to_gregorian(jalali_date_str)
        return None
    
    def _convert_jalali_to_gregorian(self, jalali_date_str):
        """تبدیل تاریخ شمسی به میلادی"""
        if not jalali_date_str:
            return None
        
        try:
            from jdatetime import date as jdate
            import re
            
            numbers = re.findall(r'\d+', jalali_date_str)
            if len(numbers) < 3:
                raise ValidationError('فرمت تاریخ صحیح نیست.')
            
            year, month, day = map(int, numbers[:3])
            jalali_date = jdate(year, month, day)
            return jalali_date.togregorian()
            
        except (ValueError, AttributeError, Exception) as e:
            raise ValidationError('تاریخ وارد شده معتبر نیست.')
    
    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.project = self.project
        
        if self.current_user and not instance.assigned_by:
            instance.assigned_by = self.current_user
        
        if commit:
            instance.save()
        
        return instance

class UserCreateForm(forms.ModelForm):
    """
    فرم ایجاد کاربر جدید توسط پیمانکار
    """
    password1 = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'رمز عبور'
        }),
        label='رمز عبور'
    )
    
    password2 = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'تکرار رمز عبور'
        }),
        label='تکرار رمز عبور'
    )
    
    phone_number = forms.CharField(
        max_length=15,
        required=False,
        widget=TextInput(attrs={
            'class': 'form-control',
            'placeholder': '09xxxxxxxxx'
        }),
        label='شماره تلفن'
    )
    
    company_name = forms.CharField(
        max_length=255,
        required=False,
        widget=TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'نام شرکت یا سازمان'
        }),
        label='نام شرکت/سازمان'
    )
    
    position = forms.CharField(
        max_length=100,
        required=False,
        widget=TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'سمت'
        }),
        label='سمت'
    )
    
    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email']
        widgets = {
            'username': TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'نام کاربری'
            }),
            'first_name': TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'نام'
            }),
            'last_name': TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'نام خانوادگی'
            }),
            'email': TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'ایمیل'
            }),
        }
    
    def clean_password2(self):
        password1 = self.cleaned_data.get("password1")
        password2 = self.cleaned_data.get("password2")
        if password1 and password2 and password1 != password2:
            raise ValidationError("رمزهای عبور مطابقت ندارند")
        return password2
    
    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password1"])
        
        if commit:
            user.save()
            # ایجاد پروفایل کاربر
            UserProfile.objects.create(
                user=user,
                phone_number=self.cleaned_data.get('phone_number'),
                company_name=self.cleaned_data.get('company_name'),
                position=self.cleaned_data.get('position')
            )
        
        return user

