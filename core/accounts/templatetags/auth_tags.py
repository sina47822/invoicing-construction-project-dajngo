from django import template
from django.contrib.auth.models import User
from accounts.models import UserRole, ProjectUser

register = template.Library()

@register.filter
def has_any_project_role(user):
    """
    بررسی آیا کاربر دارای هرگونه نقش پروژه است یا سوپریوزر/ادمین است
    """
    if user.is_superuser:
        return True
    
    # بررسی نقش ادمین در UserRole
    if UserRole.objects.filter(user=user, role='admin', is_active=True).exists():
        return True
    
    # بررسی وجود نقش در پروژه‌ها
    return ProjectUser.objects.filter(user=user, is_active=True).exists()

@register.filter
def can_access_management(user):
    """
    بررسی آیا کاربر می‌تواند به بخش مدیریت دسترسی داشته باشد
    """
    if user.is_superuser:
        return True
    
    # بررسی نقش ادمین در UserRole
    if UserRole.objects.filter(user=user, role='admin', is_active=True).exists():
        return True
    
    # یا هر شرط دیگری برای دسترسی مدیریتی
    return user.is_staff

@register.filter
def has_project_role(user, project):
    """
    بررسی آیا کاربر در پروژه خاصی نقش دارد
    """
    if user.is_superuser:
        return True
    
    # بررسی نقش ادمین در UserRole
    if UserRole.objects.filter(user=user, role='admin', is_active=True).exists():
        return True
    
    # بررسی نقش در پروژه خاص
    return ProjectUser.objects.filter(
        project=project, 
        user=user, 
        is_active=True
    ).exists()