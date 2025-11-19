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
            'contract_file': FileInput(attrs={
                'class': 'form-control',
                'accept': '.pdf,.doc,.docx',
                'data-max-size': '5242880'  # 5MB
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
            'contract_file': 'فایل قرارداد',
            'description': 'توضیحات',
        }
    
    def __init__(self, *args, **kwargs):
        self.current_user = kwargs.pop('current_user', None)
        super().__init__(*args, **kwargs)
        
        # تنظیم کشور پیش‌فرض
        self.fields['country'].initial = 'ایران'
        self.fields['province'].initial = ''
        self.fields['city'].initial = ''
        # تنظیم تاریخ امروز به شمسی
        # تنظیم سال اجرا به امسال
        try:
            from jdatetime import datetime as jdatetime
            current_year = jdatetime.now().year
            self.fields['execution_year'].initial = current_year
            print(f"✅ سال اجرا تنظیم شد: {current_year}")
        except ImportError:
            current_year = 1404  # مقدار پیش‌فرض
            self.fields['execution_year'].initial = current_year
        
        # تنظیم تاریخ امروز
        if not self.instance.pk and not self.data:
            try:
                from jdatetime import datetime as jdatetime
                today = jdatetime.now()
                self.initial['contract_date'] = today.strftime('%Y/%m/%d')
                print(f"✅ تاریخ امروز تنظیم شد: {today.strftime('%Y/%m/%d')}")
            except ImportError:
                from datetime import datetime
                today = datetime.now()
                self.initial['contract_date'] = today.strftime('%Y/%m/%d')
        
        # محدود کردن انتخاب سال
        self.fields['execution_year'].choices = [
            (year, f"{year} (سال {year})") 
            for year in range(current_year - 10, current_year + 3)
        ]
        
        # تنظیم گزینه‌های استان و شهر
        self.set_location_choices()
    
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

        self.fields['province'].choices = provinces
        self.fields['province'].initial = ''
    
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
    
    def get_province_cities_json(self):
        """دریافت داده‌های JSON برای جاوااسکریپت"""
        return json.dumps(self.province_cities_data)
    
    def save(self, commit=True):
        """ذخیره فرم با مقادیر location"""
        instance = super().save(commit=False)
        
        if commit:
            instance.save()
        
        return instance

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

class ProjectEditForm(forms.ModelForm):
    """
    فرم سفارشی برای ویرایش پروژه با ردیابی تغییرات و اعتبارسنجی پیشرفته
    """
    # فیلدهای سفارشی برای ردیابی تغییرات
    _original_data = None
    
    # سال اجرا
    execution_year = forms.ChoiceField(
        choices=[(year, f"{year} (سال {year})") for year in range(1374, 1405)],
        widget=Select(attrs={
            'class': 'form-select'
        }),
        required=True,
        label='سال اجرا بر اساس صورت وضعیت'
    )
    
    # تاریخ قرارداد
    contract_date = JalaliDateField(
        widget=AdminJalaliDateWidget(
            attrs={
                'class': 'form-control',
                'autocomplete': 'off',
                'placeholder': '1403/06/15'
            }
        ),
        required=True,
        label='تاریخ قرارداد'
    )
    
    # مبلغ قرارداد
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
    
    # وضعیت پروژه
    status = forms.ChoiceField(
        choices=Project.STATUS_CHOICES,
        widget=Select(attrs={
            'class': 'form-select'
        }),
        label='وضعیت پروژه'
    )
    
    # تأیید تغییرات
    confirm_changes = forms.BooleanField(
        required=True,
        initial=True,
        widget=forms.HiddenInput(),
        label=''
    )
    
    # غیرفعال‌سازی (برای حذف نرم)
    is_active_toggle = forms.BooleanField(
        required=False,
        widget=CheckboxInput(attrs={
            'class': 'form-check-input'
        }),
        label='پروژه فعال باشد'
    )
    
    class Meta:
        model = Project
        fields = [
            'project_name',
            'project_code',
            'employer',
            'contractor',
            'consultant',
            'supervising_engineer',
            'city',
            'province',
            'country',
            'contract_number',
            'contract_date',
            'execution_year',
            'contract_amount',
            'status',
            'contract_file',
            'description',
            'is_active',
        ]
        widgets = {
            'project_name': TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'نام کامل پروژه',
                'maxlength': 255,
                'data-original-value': ''
            }),
            'project_code': TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'P-1403-001',
                'maxlength': 50,
                'autocomplete': 'off',
                'data-original-value': '',
                'readonly': True  # کد پروژه قابل تغییر نباشد
            }),
            'employer': TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'نام کارفرما',
                'maxlength': 255,
                'data-original-value': ''
            }),
            'contractor': TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'نام پیمانکار',
                'maxlength': 255,
                'data-original-value': ''
            }),
            'consultant': TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'مدیر طرح/مشاور (اختیاری)',
                'maxlength': 255,
                'data-original-value': ''
            }),
            'supervising_engineer': TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'مهندس ناظر (اختیاری)',
                'maxlength': 255,
                'data-original-value': ''
            }),
            'city': Select(attrs={
                'class': 'form-select',
                'required': True,
                'data-dependent-field': 'province',
                'data-original-value': '',
                'id': 'id_city_edit'
            }),
            'province': Select(attrs={
                'class': 'form-select',
                'required': True,
                'data-controls-field': 'city',
                'data-original-value': '',
                'id': 'id_province_edit'
            }),
            'country': Select(attrs={
                'class': 'form-select',
                'data-original-value': ''
            }),
            'contract_number': TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'شماره قرارداد',
                'maxlength': 50,
                'data-original-value': ''
            }),
            'contract_file': FileInput(attrs={
                'class': 'form-control',
                'accept': '.pdf,.doc,.docx'
            }),
            'description': Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'توضیحات پروژه...',
                'data-original-value': ''
            }),
            'is_active': CheckboxInput(attrs={
                'class': 'form-check-input',
                'data-original-value': True
            }),
        }
        labels = {
            'project_name': 'نام پروژه',
            'project_code': 'کد پروژه',
            'employer': 'کارفرما',
            'contractor': 'پیمانکار',
            'consultant': 'مدیر طرح/مشاور',
            'supervising_engineer': 'مهندس ناظر',
            'city': 'شهر پروژه',
            'province': 'استان',
            'country': 'کشور',
            'contract_number': 'شماره قرارداد',
            'contract_amount': 'مبلغ قرارداد (ریال)',
            'contract_file': 'فایل قرارداد (جایگزینی)',
            'description': 'توضیحات',
            'is_active': 'پروژه فعال باشد',
        }
        help_texts = {
            'contract_file': 'فایل جدید جایگزین فایل قبلی خواهد شد',
            'is_active': 'غیرفعال کردن = حذف نرم (داده‌ها حفظ می‌شود)',
        }
    
    def __init__(self, *args, **kwargs):
        self.original_project = kwargs.pop('original_project', None)
        super().__init__(*args, **kwargs)
        
        # ذخیره داده‌های اصلی برای ردیابی تغییرات
        if self.original_project:
            self._original_data = self._get_original_data()
            self._set_original_values()
            self._setup_change_tracking()
        
        # غیرفعال کردن کد پروژه
        self.fields['project_code'].widget.attrs['readonly'] = True
        self.fields['project_code'].disabled = True
        
        # تنظیم مقادیر پیش‌فرض
        self.fields['is_active_toggle'].initial = self.instance.is_active if self.instance else True
        
        # تنظیم گزینه‌های استان و شهر
        self.set_province_city_choices()
    
    def set_province_city_choices(self):
        """تنظیم گزینه‌های استان و شهر برای ویرایش"""
        
        # لیست کامل استان‌های ایران
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
        
        # تنظیم choices برای استان
        self.fields['province'].choices = provinces
        
        # شهرهای هر استان (همان داده‌های ProjectCreateForm)
        cities_by_province = {
            # ... همان cities_by_province از ProjectCreateForm ...
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
            # ... بقیه استان‌ها مشابه ProjectCreateForm ...
        }
        
        # تنظیم choices اولیه برای شهر
        all_cities = [('', 'انتخاب شهر')]
        for province_cities in cities_by_province.values():
            all_cities.extend(province_cities)
        
        self.fields['city'].choices = all_cities
        
        # ذخیره برای استفاده در جاوااسکریپت
        self.province_cities_data = cities_by_province
    
    def get_province_cities_json(self):
        """دریافت داده‌های JSON برای جاوااسکریپت"""
        return json.dumps(self.province_cities_data)
    
    def _get_original_data(self):
        """دریافت داده‌های اصلی پروژه"""
        if not self.original_project:
            return {}
        
        return {
            'project_name': self.original_project.project_name,
            'employer': self.original_project.employer,
            'contractor': self.original_project.contractor,
            'consultant': self.original_project.consultant or '',
            'supervising_engineer': self.original_project.supervising_engineer or '',
            'city': self.original_project.city,
            'province': self.original_project.province,
            'country': self.original_project.country,
            'contract_number': self.original_project.contract_number,
            'contract_amount': str(self.original_project.contract_amount),
            'status': self.original_project.status,
            'description': self.original_project.description or '',
            'is_active': self.original_project.is_active,
            'execution_year': self.original_project.execution_year,
            'contract_date': self.original_project.contract_date
        }
    
    def _set_original_values(self):
        """تنظیم مقادیر اصلی در widget ها"""
        if not self._original_data:
            return
        
        field_mapping = {
            'project_name': 'project_name',
            'employer': 'employer',
            'contractor': 'contractor',
            'city': 'city',
            'province': 'province',
            'contract_number': 'contract_number',
            'description': 'description',
            'execution_year': 'execution_year',
            'contract_amount': 'contract_amount',
        }
        
        for form_field, original_field in field_mapping.items():
            if form_field in self.fields and original_field in self._original_data:
                self.fields[form_field].widget.attrs['data-original-value'] = \
                    self._original_data[original_field]
    
    def _setup_change_tracking(self):
        """تنظیم ردیابی تغییرات"""
        if not self.original_project:
            return
        
        # اضافه کردن کلاس‌های CSS برای فیلدهای تغییر یافته
        self._mark_changed_fields()
    
    def _mark_changed_fields(self):
        """علامت‌گذاری فیلدهای تغییر یافته"""
        if not self._original_data or not self.is_bound:
            return
        
        changed_fields = self._get_changed_fields()
        
        for field_name in changed_fields:
            if field_name in self.fields:
                current_class = self.fields[field_name].widget.attrs.get('class', '')
                self.fields[field_name].widget.attrs['class'] = f"{current_class} is-changed"
                self.fields[field_name].widget.attrs['data-changed'] = 'true'
    
    def _get_changed_fields(self):
        """دریافت لیست فیلدهای تغییر یافته"""
        changed = []
        cleaned_data = self.cleaned_data if self.is_bound else {}
        
        for field_name in self._original_data:
            original_value = self._original_data[field_name]
            current_value = cleaned_data.get(field_name)
            
            # مقایسه مقادیر
            if self._values_changed(original_value, current_value):
                changed.append(field_name)
        
        return changed
    
    def _values_changed(self, original, current):
        """بررسی تغییر مقدار"""
        if original is None and current == '':
            return False
        if current is None and original == '':
            return False
        
        # تبدیل تاریخ جلالی
        if isinstance(original, str) and len(original) == 10:  # فرمت جلالی
            try:
                from jdatetime import datetime as jdatetime
                original = jdatetime.strptime(original, '%Y/%m/%d').togregorian().date()
            except:
                pass
        
        if isinstance(current, str) and len(current) == 10:
            try:
                from jdatetime import datetime as jdatetime
                current = jdatetime.strptime(current, '%Y/%m/%d').togregorian().date()
            except:
                pass
        
        return str(original).strip().lower() != str(current).strip().lower()
    
    def clean_project_code(self):
        """کد پروژه قابل تغییر نیست"""
        project_code = self.cleaned_data.get('project_code')
        if project_code != self.instance.project_code:
            raise ValidationError(
                'کد پروژه قابل تغییر نیست. برای تغییر کد، با مدیر سیستم تماس بگیرید.',
                code='immutable'
            )
        return project_code
    
    def clean_contract_amount(self):
        """اعتبارسنجی مبلغ قرارداد"""
        amount_str = self.cleaned_data.get('contract_amount', '')
        
        if amount_str:
            cleaned_amount = ''.join(filter(lambda x: x.isdigit(), amount_str))
            
            if not cleaned_amount:
                raise ValidationError('مبلغ قرارداد باید عدد صحیح باشد.')
            
            try:
                amount_value = int(cleaned_amount)
                
                # بررسی تغییر بیش از حد
                original_amount = self.instance.contract_amount if self.instance else 0
                change_percent = abs(amount_value - original_amount) / original_amount * 100 if original_amount else 0
                
                if change_percent > 50 and original_amount > 0:
                    raise ValidationError(
                        f'تغییر مبلغ ({change_percent:.1f}%) بیش از 50% است. '
                        f'برای تأیید، با مدیر سیستم تماس بگیرید.'
                    )
                
                if amount_value < 100000:
                    raise ValidationError('مبلغ قرارداد نمی‌تواند کمتر از 100,000 ریال باشد.')
                
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
                current_year = 1404
                
                if year_int < 1390 or year_int > current_year + 5:
                    raise ValidationError(
                        f'سال اجرا باید بین 1390 تا {current_year + 5} باشد.'
                    )
                
                # بررسی تغییر سال اجرا
                original_year = self.instance.execution_year if self.instance else None
                if original_year and abs(year_int - original_year) > 2:
                    raise ValidationError(
                        f'تغییر سال اجرا از {original_year} به {year_int} بیش از 2 سال است. '
                        f'برای تأیید، با مدیر سیستم تماس بگیرید.'
                    )
                
                return year_int
            except (ValueError, TypeError):
                raise ValidationError('سال اجرا باید عدد صحیح باشد.')
        
        raise ValidationError('سال اجرا الزامی است.')
    
    def clean_contract_date(self):
        """اعتبارسنجی تاریخ قرارداد"""
        date = self.cleaned_data.get('contract_date')
        
        if date:
            current_year = 1403
            if date.year > current_year + 1:
                raise ValidationError('تاریخ قرارداد نمی‌تواند در آینده باشد.')
            
            execution_year = self.cleaned_data.get('execution_year')
            if execution_year and date.year < int(execution_year) - 3:
                raise ValidationError(
                    'تاریخ قرارداد نمی‌تواند بیش از 3 سال قبل از سال اجرا باشد.'
                )
        
        return date
    
    def clean_contract_file(self):
        """اعتبارسنجی فایل قرارداد"""
        file = self.cleaned_data.get('contract_file')
        
        if file:
            # بررسی نوع فایل
            allowed_types = ['application/pdf', 'application/msword', 
                           'application/vnd.openxmlformats-officedocument.wordprocessingml.document']
            
            if file.content_type not in allowed_types:
                raise ValidationError(
                    'نوع فایل مجاز نیست. فقط PDF و Word قابل قبول است.'
                )
            
            # بررسی حجم فایل
            if file.size > 5 * 1024 * 1024:  # 5MB
                raise ValidationError('حجم فایل نمی‌تواند بیش از 5 مگابایت باشد.')
        
        return file
    
    def clean(self):
        """اعتبارسنجی کلی فرم ویرایش"""
        cleaned_data = super().clean()
        
        # بررسی کارفرما و پیمانکار
        employer = cleaned_data.get('employer')
        contractor = cleaned_data.get('contractor')
        
        if employer and contractor and employer.lower() == contractor.lower():
            raise ValidationError({
                'employer': 'کارفرما و پیمانکار نمی‌توانند یکسان باشند.',
                'contractor': 'کارفرما و پیمانکار نمی‌توانند یکسان باشند.'
            })
        
        # بررسی تغییرات وضعیت
        if self.instance:
            original_status = self.instance.status
            new_status = cleaned_data.get('status')
            
            if original_status != new_status:
                # لاگ تغییرات وضعیت
                if new_status == 'completed' and self.instance.status == 'active':
                    # بررسی وجود صورت وضعیت‌ها
                    from project.models import StatusReport
                    reports_count = StatusReport.objects.filter(
                        project=self.instance, is_active=True
                    ).count()
                    
                    if reports_count == 0:
                        self.add_error(
                            'status',
                            'نمی‌توان پروژه بدون صورت وضعیت به حالت "تمام‌شده" تغییر داد.'
                        )
        
        # بررسی مطابقت شهر و استان
        city = cleaned_data.get('city')
        province = cleaned_data.get('province')
        
        if city and province:
            # بررسی اینکه شهر در استان انتخابی باشد
            valid_cities_for_province = self.province_cities_data.get(province, [])
            city_names = [city_tuple[0] for city_tuple in valid_cities_for_province]
            
            if city not in city_names:
                self.add_error('city', f'شهر "{city}" در استان "{province}" قرار ندارد.')
        
        return cleaned_data
    
    @property
    def has_changes(self):
        """بررسی وجود تغییرات"""
        if not self._original_data or not self.is_bound:
            return False
        
        return bool(self._get_changed_fields())
    
    @property
    def changed_fields_summary(self):
        """خلاصه فیلدهای تغییر یافته"""
        if not self.has_changes:
            return []
        
        changed = self._get_changed_fields()
        summary = []
        
        field_labels = {
            'project_name': 'نام پروژه',
            'employer': 'کارفرما',
            'contractor': 'پیمانکار',
            'city': 'شهر',
            'province': 'استان',
            'contract_number': 'شماره قرارداد',
            'contract_amount': 'مبلغ قرارداد',
            'status': 'وضعیت',
            'description': 'توضیحات',
            'execution_year': 'سال اجرا',
        }
        
        for field in changed:
            label = field_labels.get(field, field.replace('_', ' ').title())
            original = self._original_data.get(field, '')
            current = self.cleaned_data.get(field, '') if self.is_bound else ''
            
            summary.append({
                'field': field,
                'label': label,
                'original': original,
                'current': current
            })
        
        return summary
    
    def save(self, commit=True, modified_by=None):
        """ذخیره با ردیابی تغییرات"""
        instance = super().save(commit=False)
        
        # تنظیم modified_by
        if modified_by:
            instance.modified_by = modified_by
        
        # تنظیم is_active بر اساس toggle
        if 'is_active_toggle' in self.cleaned_data:
            instance.is_active = self.cleaned_data['is_active_toggle']
        
        if commit:
            instance.save()
            
            # ذخیره فایل
            if self.cleaned_data.get('contract_file'):
                instance.contract_file = self.cleaned_data['contract_file']
                instance.save()
        
        return instance