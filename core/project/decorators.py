# project/decorators.py
from django.http import HttpResponseForbidden
from django.contrib.auth.decorators import user_passes_test
from functools import wraps
from accounts.models import ProjectUser

def project_access_required(required_roles=None, allow_superuser=True):
    """
    دکوراتور برای بررسی دسترسی به پروژه
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if allow_superuser and request.user.is_superuser:
                return view_func(request, *args, **kwargs)
            
            project_id = kwargs.get('pk') or kwargs.get('project_pk')
            if not project_id:
                return HttpResponseForbidden("دسترسی غیر مجاز")
            
            from .models import Project
            try:
                project = Project.objects.get(pk=project_id, is_active=True)
                if project.has_access(request.user, required_roles):
                    return view_func(request, *args, **kwargs)
                else:
                    return HttpResponseForbidden("دسترسی غیر مجاز")
            except Project.DoesNotExist:
                return HttpResponseForbidden("پروژه یافت نشد")
        
        return _wrapped_view
    return decorator

def role_required(roles, allow_superuser=True):
    """
    دکوراتور برای بررسی نقش کاربر
    """
    if isinstance(roles, str):
        roles = [roles]
    
    def check_roles(user):
        if allow_superuser and user.is_superuser:
            return True
        
        # بررسی نقش در پروژه‌ها
        return ProjectUser.objects.filter(
            user=user,
            role__name__in=roles,
            is_active=True
        ).exists()
    
    return user_passes_test(check_roles)