# project/context_processors.py
def user_roles(request):
    """
    اضافه کردن نقش‌های کاربر به context
    """
    if request.user.is_authenticated:
        return {
            'user_roles': request.user.roles.filter(is_active=True).values_list('role', flat=True),
            'is_contractor': request.user.roles.filter(role='contractor', is_active=True).exists(),
            'is_project_manager': request.user.roles.filter(role='project_manager', is_active=True).exists(),
            'is_employer': request.user.roles.filter(role='employer', is_active=True).exists(),
            'is_admin': request.user.is_superuser or request.user.roles.filter(role='admin', is_active=True).exists(),
        }
    return {}