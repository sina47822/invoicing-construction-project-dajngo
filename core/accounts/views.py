from django.shortcuts import render, redirect
from django.views import View
from django.contrib.auth.forms import UserCreationForm
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
import json
from django.http import JsonResponse
from django.contrib.auth import logout

from django.contrib.auth.models import User  
from .models import UserRole
from .forms import UserCreateForm
from project.models import Project
# Create your views here.
class RegisterView(View):
    def get(self, request):
        form = UserCreationForm()
        return render(request, 'account/registration/register.html', {'form': form})

    def post(self, request):
        form = UserCreationForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'ثبت‌نام موفق! حالا وارد شوید.')
            return redirect('accounts:login')
        return render(request, 'account/registration/register.html', {'form': form})

def custom_logout(request):
    logout(request)
    return redirect('accounts:login')

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
    ایجاد کاربر جدید توسط ادمین، سوپر یوزر یا پیمانکار
    """
    from .utils import can_create_users, get_user_roles
    # بررسی مجوز کاربر
    user = request.user
    user_roles = get_user_roles(user)
    print(f"🔍 User: {user.username}, Roles: {user_roles}, Is Superuser: {user.is_superuser}")
    
    if not can_create_users(user):
        error_message = "شما مجوز ایجاد کاربر جدید را ندارید. فقط ادمین‌ها، سوپر یوزرها و پیمانکاران می‌توانند کاربر ایجاد کنند."
        print(f"❌ Permission denied: {error_message}")
        
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({
                'success': False, 
                'errors': {'permission': [error_message]}
            }, status=403)
        
        messages.error(request, error_message)
        return redirect('projects:project_list')
    # سوپر یوزرها همیشه دسترسی دارند
    if user.is_superuser:
        print("✅ Superuser access granted")
        has_permission = True
    else:
        # بررسی نقش‌های کاربر
        user_roles = UserRole.objects.filter(user=user, is_active=True)
        user_role_names = [role.role for role in user_roles]
        
        print(f"🔍 User: {user.username}, Roles: {user_role_names}, Is Superuser: {user.is_superuser}")
        
        # نقش‌های مجاز: ادمین یا پیمانکار
        allowed_roles = ['admin', 'contractor']
        has_permission = any(role in user_role_names for role in allowed_roles)
        
        print(f"🔍 Permission check: {has_permission}")

    if not has_permission:
        error_message = "شما مجوز ایجاد کاربر جدید را ندارید. فقط ادمین‌ها، سوپر یوزرها و پیمانکاران می‌توانند کاربر ایجاد کنند."
        print(f"❌ Permission denied: {error_message}")
        
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({
                'success': False, 
                'errors': {'permission': [error_message]}
            }, status=403)
        
        messages.error(request, error_message)
        return redirect('projects:project_list')
    
    # اگر به اینجا رسیدیم، کاربر مجوز دارد
    if request.method == 'POST':
        print("🔍 POST data:", dict(request.POST))
        form = UserCreateForm(request.POST, creating_user=request.user)
        
        if form.is_valid():
            try:
                with transaction.atomic():
                    user = form.save()
                    print("✅ User created successfully:", user.id, user.username)
                    
                    # اگر درخواست AJAX است
                    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                        response_data = {
                            'success': True,
                            'user_id': user.id,
                            'username': user.username,
                            'full_name': f"{user.first_name} {user.last_name}".strip(),
                            'role': form.cleaned_data.get('role', '')
                        }
                        print("📤 Sending success response:", response_data)
                        return JsonResponse(response_data)
                    
                    messages.success(
                        request, 
                        f'کاربر "{user.get_full_name()}" با نقش "{form.cleaned_data["role"]}" با موفقیت ایجاد شد.'
                    )
                    return redirect('accounts:user_list')
                    
            except Exception as e:
                error_msg = f'خطا در ایجاد کاربر: {str(e)}'
                print("❌ Exception in user creation:", str(e))
                import traceback
                traceback.print_exc()
                
                if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                    return JsonResponse({
                        'success': False, 
                        'errors': {'general': [error_msg]}
                    }, status=500)
                
                messages.error(request, error_msg)
        else:
            # جمع‌آوری تمام خطاها
            all_errors = {}
            for field, errors in form.errors.items():
                all_errors[field] = list(errors)
            
            print("❌ Form errors:", all_errors)
            
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': False, 
                    'errors': all_errors
                }, status=400)
            
            # نمایش خطاهای فرم برای درخواست عادی
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
    لیست کاربران سیستم
    """
    # بررسی مجوز کاربر
    user = request.user
    
    # سوپر یوزرها و ادمین‌ها می‌توانند همه کاربران را ببینند
    if user.is_superuser:
        users = User.objects.filter(is_active=True).select_related('profile').prefetch_related('roles')
        print(f"✅ Superuser - Showing all {users.count()} users")
    else:
        # بررسی نقش‌های کاربر
        user_roles = UserRole.objects.filter(user=user, is_active=True)
        user_role_names = [role.role for role in user_roles]
        
        # اگر کاربر ادمین یا پیمانکار است، می‌تواند کاربران را ببیند
        if 'admin' in user_role_names or 'contractor' in user_role_names:
            users = User.objects.filter(is_active=True).select_related('profile').prefetch_related('roles')
            print(f"✅ Admin/Contractor - Showing all {users.count()} users")
        else:
            # کاربران عادی فقط می‌توانند خودشان را ببینند
            users = User.objects.filter(id=user.id, is_active=True).select_related('profile').prefetch_related('roles')
            print(f"⚠️ Regular user - Showing only themselves")
            
            # نمایش پیام اطلاع‌رسانی
            messages.info(request, "شما فقط می‌توانید اطلاعات کاربری خود را مشاهده کنید.")

    context = {
        'title': 'لیست کاربران',
        'users': users,
        'page_title': 'مدیریت کاربران',
        'active_menu': 'users',
    }
    return render(request, 'accounts/user_list.html', context)
    
@login_required
def manage_user_roles(request, user_id):
    """
    مدیریت نقش‌های کاربر
    """
    if not request.user.is_superuser:
        messages.error(request, "فقط سوپر یوزرها می‌توانند نقش‌ها را مدیریت کنند.")
        return redirect('projects:project_list')
    
    target_user = get_object_or_404(User, id=user_id)
    user_roles = UserRole.objects.filter(user=target_user)
    
    context = {
        'target_user': target_user,
        'user_roles': user_roles,
    }
    return render(request, 'accounts/manage_roles.html', context)

@login_required
def add_role(request, user_id):
    """
    افزودن نقش به کاربر
    """
    if not request.user.is_superuser:
        messages.error(request, "فقط سوپر یوزرها می‌توانند نقش اضافه کنند.")
        return redirect('projects:project_list')
    
    target_user = get_object_or_404(User, id=user_id)
    
    if request.method == 'POST':
        role = request.POST.get('role')
        is_active = request.POST.get('is_active') == 'on'
        
        if role:
            # بررسی وجود نقش تکراری
            existing_role = UserRole.objects.filter(user=target_user, role=role).first()
            if existing_role:
                messages.warning(request, f"نقش '{existing_role.get_role_display()}' قبلاً برای این کاربر وجود دارد.")
            else:
                UserRole.objects.create(
                    user=target_user,
                    role=role,
                    is_active=is_active
                )
                messages.success(request, f"نقش '{dict(UserRole.ROLE_CHOICES).get(role)}' با موفقیت اضافه شد.")
        else:
            messages.error(request, "لطفاً یک نقش انتخاب کنید.")
    
    return redirect('accounts:manage_roles', user_id=user_id)

@login_required
def activate_role(request, user_id, role_id):
    """
    فعال کردن نقش
    """
    if not request.user.is_superuser:
        messages.error(request, "فقط سوپر یوزرها می‌توانند نقش‌ها را فعال کنند.")
        return redirect('projects:project_list')
    
    user_role = get_object_or_404(UserRole, id=role_id, user_id=user_id)
    user_role.is_active = True
    user_role.save()
    
    messages.success(request, f"نقش '{user_role.get_role_display()}' فعال شد.")
    return redirect('accounts:manage_roles', user_id=user_id)

@login_required
def deactivate_role(request, user_id, role_id):
    """
    غیرفعال کردن نقش
    """
    if not request.user.is_superuser:
        messages.error(request, "فقط سوپر یوزرها می‌توانند نقش‌ها را غیرفعال کنند.")
        return redirect('projects:project_list')
    
    user_role = get_object_or_404(UserRole, id=role_id, user_id=user_id)
    user_role.is_active = False
    user_role.save()
    
    messages.success(request, f"نقش '{user_role.get_role_display()}' غیرفعال شد.")
    return redirect('accounts:manage_roles', user_id=user_id)

@login_required
def delete_role(request, user_id, role_id):
    """
    حذف نقش
    """
    if not request.user.is_superuser:
        messages.error(request, "فقط سوپر یوزرها می‌توانند نقش‌ها را حذف کنند.")
        return redirect('projects:project_list')
    
    user_role = get_object_or_404(UserRole, id=role_id, user_id=user_id)
    role_name = user_role.get_role_display()
    user_role.delete()
    
    messages.success(request, f"نقش '{role_name}' حذف شد.")
    return redirect('accounts:manage_roles', user_id=user_id)

