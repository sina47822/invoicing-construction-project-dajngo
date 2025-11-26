# accounts/utils.py
from .models import UserRole

def user_has_role(user, role_names):
    """
    بررسی می‌کند که کاربر نقش مورد نظر را دارد یا نه
    """
    if not isinstance(role_names, list):
        role_names = [role_names]
    
    # سوپر یوزرها همه دسترسی‌ها را دارند
    if user.is_superuser:
        return True
    
    user_roles = UserRole.objects.filter(user=user, is_active=True)
    user_role_names = [role.role for role in user_roles]
    
    return any(role in user_role_names for role in role_names)

def get_user_roles(user):
    """
    دریافت لیست نقش‌های کاربر
    """
    user_roles = UserRole.objects.filter(user=user, is_active=True)
    return [role.role for role in user_roles]

def can_create_users(user):
    """
    بررسی می‌کند که کاربر می‌تواند کاربر جدید ایجاد کند
    """
    allowed_roles = ['admin', 'contractor']
    return user.is_superuser or user_has_role(user, allowed_roles)