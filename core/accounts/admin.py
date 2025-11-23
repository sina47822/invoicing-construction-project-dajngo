from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User
from .models import UserRole, UserProfile, ProjectUser

class UserRoleInline(admin.TabularInline):
    model = UserRole
    extra = 1
    fields = ('role', 'is_active')
    verbose_name_plural = 'نقش‌های کاربر'

class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    verbose_name_plural = 'پروفایل'
    fields = (
        'phone_number', 'national_id', 'company_name', 'position',
        'address', 'is_verified', 'avatar', 'bio'
    )

class CustomUserAdmin(UserAdmin):
    inlines = [UserProfileInline, UserRoleInline]
    list_display = ('username', 'email', 'first_name', 'last_name', 'is_staff', 'get_company', 'get_roles')
    list_filter = ('is_staff', 'is_superuser', 'is_active', 'groups')
    search_fields = ('username', 'first_name', 'last_name', 'email', 'profile__company_name')
    
    def get_company(self, obj):
        return obj.profile.company_name if hasattr(obj, 'profile') else '---'
    get_company.short_description = 'شرکت'
    
    def get_roles(self, obj):
        roles = obj.roles.filter(is_active=True)
        return ", ".join([role.get_role_display() for role in roles])
    get_roles.short_description = 'نقش‌ها'

# Unregister default User admin and register custom one
admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)

@admin.register(UserRole)
class UserRoleAdmin(admin.ModelAdmin):
    list_display = ('user', 'role_display', 'is_active', 'created_at')
    list_filter = ('role', 'is_active', 'created_at')
    search_fields = ('user__username', 'user__first_name', 'user__last_name')
    raw_id_fields = ('user',)
    
    def role_display(self, obj):
        return obj.get_role_display()
    role_display.short_description = 'نقش'

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'company_name', 'phone_number', 'is_verified', 'created_at')
    list_filter = ('is_verified', 'created_at')
    search_fields = ('user__username', 'company_name', 'phone_number', 'national_id')
    raw_id_fields = ('user',)

@admin.register(ProjectUser)
class ProjectUserAdmin(admin.ModelAdmin):
    list_display = (
        'user', 
        'project_display', 
        'role_display', 
        'is_primary', 
        'is_active', 
        'start_date', 
        'end_date'
    )
    list_filter = ('role', 'is_primary', 'is_active', 'start_date')
    search_fields = (
        'user__username', 
        'project__project_name', 
        'project__project_code'
    )
    raw_id_fields = ('user', 'project', 'assigned_by')
    date_hierarchy = 'start_date'
    
    def project_display(self, obj):
        return f"{obj.project.project_code} - {obj.project.project_name}"
    project_display.short_description = 'پروژه'
    
    def role_display(self, obj):
        return obj.get_role_display()
    role_display.short_description = 'نقش'