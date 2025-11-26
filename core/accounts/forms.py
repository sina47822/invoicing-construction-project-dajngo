
# accounts/forms.py
from django import forms
from django.forms import modelform_factory, TextInput, Select, DateInput, Textarea, CheckboxInput, FileInput

from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from .models import UserProfile, UserRole, UserInvitation

class UserInvitationForm(forms.ModelForm):
    class Meta:
        model = UserInvitation
        fields = ['email', 'role']
        widgets = {
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'example@email.com'
            }),
            'role': forms.Select(attrs={
                'class': 'form-select'
            })
        }
        labels = {
            'email': 'آدرس ایمیل',
            'role': 'نقش در پروژه'
        }

class ProjectAccessForm(forms.Form):
    """
    فرم برای مدیریت دسترسی‌های پروژه
    """
    def __init__(self, *args, **kwargs):
        self.project = kwargs.pop('project')
        self.current_user = kwargs.pop('current_user')
        super().__init__(*args, **kwargs)
        
        # فیلدهای داینامیک برای کاربران موجود
        project_users = ProjectUser.objects.filter(project=self.project)
        for pu in project_users:
            self.fields[f'user_{pu.id}_role'] = forms.ChoiceField(
                choices=ProjectUser.PROJECT_ROLE_CHOICES,
                initial=pu.role,
                label=f"نقش {pu.user.get_full_name() or pu.user.username}",
                widget=forms.Select(attrs={'class': 'form-select'})
            )
            self.fields[f'user_{pu.id}_remove'] = forms.BooleanField(
                required=False,
                label='حذف کاربر',
                widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
            )

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
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'example@domain.com'
        }),
        label='آدرس ایمیل'
    )
    
    first_name = forms.CharField(
        max_length=30,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'نام'
        }),
        label='نام'
    )
    
    last_name = forms.CharField(
        max_length=30,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'نام خانوادگی'
        }),
        label='نام خانوادگی'
    )

    # نقش‌های ممکن برای ایجاد توسط پیمانکار
    ROLE_CHOICES = [
        ('employer', 'کارفرما'),
        ('project_manager', 'مدیر طرح'),
        ('supervisor', 'ناظر'),
        ('engineer', 'مهندس'),
        ('consultant', 'مشاور'),
    ]
    
    role = forms.ChoiceField(
        choices=ROLE_CHOICES,
        widget=forms.Select(attrs={
            'class': 'form-select'
        }),
        label='نقش کاربر',
        help_text='نقش کاربر در سیستم را انتخاب کنید'
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

    national_id = forms.CharField(
        max_length=10,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '0012345678'
        }),
        label='کد ملی'
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
        fields = ['username', 'email', 'first_name', 'last_name', 'password1', 'password2']
        
        widgets = {
            'username': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'نام کاربری'
            }),
        }
        labels = {
            'username': 'نام کاربری',
            'password1': 'رمز عبور',
            'password2': 'تکرار رمز عبور',
        }
    
    def __init__(self, *args, **kwargs):
        self.creating_user = kwargs.pop('creating_user', None)
        super().__init__(*args, **kwargs)
        
        # تنظیم کمک‌های رمز عبور
        self.fields['password1'].widget.attrs.update({'class': 'form-control'})
        self.fields['password2'].widget.attrs.update({'class': 'form-control'})
        
        self.fields['password1'].help_text = '''
            <small class="form-text text-muted">
                رمز عبور باید حداقل 8 کاراکتر داشته و ترکیبی از حروف و اعداد باشد.
            </small>
        '''
    
    def clean_username(self):
        username = self.cleaned_data.get('username')
        if User.objects.filter(username=username).exists():
            raise forms.ValidationError('این نام کاربری قبلاً ثبت شده است.')
        return username
    
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError('این ایمیل قبلاً ثبت شده است.')
        return email
    
    def clean_national_id(self):
        national_id = self.cleaned_data.get('national_id')
        if national_id and UserProfile.objects.filter(national_id=national_id).exists():
            raise forms.ValidationError('این کد ملی قبلاً ثبت شده است.')
        return national_id
    
    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        user.is_active = True
        
        if commit:
            user.save()
            
            # ایجاد پروفایل کاربر
            profile, created = UserProfile.objects.get_or_create(user=user)
            profile.phone_number = self.cleaned_data.get('phone_number', '')
            profile.national_id = self.cleaned_data.get('national_id', '')
            profile.company_name = self.cleaned_data.get('company_name', '')
            profile.position = self.cleaned_data.get('position', '')
            profile.is_verified = True  # کاربران ایجاد شده توسط پیمانکار تأیید شده هستند
            profile.save()
            
            # ایجاد نقش کاربر
            role = self.cleaned_data.get('role')
            UserRole.objects.create(user=user, role=role)
            
        return user
