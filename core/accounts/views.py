from django.shortcuts import render, redirect
from django.views import View
from django.contrib.auth.forms import UserCreationForm
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction

from .models import UserRole
from .forms import UserCreateForm
# Create your views here.
class RegisterView(View):
    def get(self, request):
        form = UserCreationForm()
        return render(request, 'accounts/registration/register.html', {'form': form})

    def post(self, request):
        form = UserCreationForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'ثبت‌نام موفق! حالا وارد شوید.')
            return redirect('accounts:login')
        return render(request, 'accounts/registration/register.html', {'form': form})

def dashboard(request):
    # این می‌تونه صفحه اصلی بعد از ورود باشه. فعلاً ساده نگه می‌داریم، بعداً می‌تونی محتوا اضافه کنی
    if not request.user.is_authenticated:
        return redirect('accounts:login')
    return render(request, 'accounts/dashboard.html', {})  # template dashboard.html

@login_required
def profile_view(request):
    """
    پروفایل کاربر
    """
    # دریافت پروژه‌های کاربر
    user_projects = Project.objects.filter(
        project_users__user=request.user,
        project_users__is_active=True,
        is_active=True
    ).distinct().select_related('created_by')
    
    context = {
        'title': 'پروفایل کاربری',
        'user_projects': user_projects,
    }
    
    return render(request, 'accounts/profile/profile.html', context)

@login_required
def settings_view(request):
    user = request.user

    if request.method == "POST":
        username = request.POST.get("username")
        email = request.POST.get("email")
        first_name = request.POST.get("first_name")
        last_name = request.POST.get("last_name")

        # تغییر مشخصات پایه کاربر
        user.username = username
        user.email = email
        user.first_name = first_name
        user.last_name = last_name
        user.save()
        messages.success(request, "تنظیمات حساب با موفقیت ذخیره شد.")
        return redirect("settings")

    return render(request, "accounts/profile/settings.html", {"user": user})

@login_required
def user_create(request):
    """
    ایجاد کاربر جدید توسط پیمانکار یا ادمین
    """
    # بررسی مجوز کاربر
    user_roles = UserRole.objects.filter(user=request.user, is_active=True)
    user_role_names = [role.role for role in user_roles]
    
    if 'contractor' not in user_role_names and 'admin' not in user_role_names:
        messages.error(request, 'شما مجوز ایجاد کاربر جدید را ندارید.')
        return redirect('project:project_list')
    
    if request.method == 'POST':
        form = UserCreateForm(request.POST, creating_user=request.user)
        if form.is_valid():
            try:
                with transaction.atomic():
                    user = form.save()
                    
                    # لاگ کردن عمل ایجاد کاربر
                    messages.success(
                        request, 
                        f'کاربر "{user.get_full_name()}" با نقش "{form.cleaned_data["role"]}" با موفقیت ایجاد شد.'
                    )
                    return redirect('accounts:user_list')
                    
            except Exception as e:
                messages.error(request, f'خطا در ایجاد کاربر: {str(e)}')
        else:
            # نمایش خطاهای فرم
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'خطا در {field}: {error}')
    else:
        form = UserCreateForm(creating_user=request.user)
    
    context = {
        'title': 'ایجاد کاربر جدید',
        'form': form,
        'page_title': 'ایجاد کاربر جدید',
        'active_menu': 'users',
    }
    return render(request, 'accounts/user_form.html', context)

@login_required
def user_list(request):
    """
    لیست کاربران ایجاد شده توسط پیمانکار
    """
    # فقط کاربران ایجاد شده توسط این پیمانکار را نشان بده
    # (اگر نیاز به این قابلیت دارید)
    
    users = User.objects.filter(is_active=True).select_related('profile').prefetch_related('roles')
    
    context = {
        'title': 'لیست کاربران',
        'users': users,
        'page_title': 'مدیریت کاربران',
        'active_menu': 'users',
    }
    return render(request, 'accounts/user_list.html', context)
    