from django.urls import path
from django.contrib.auth import views as auth_views
from . import views
from .views import RegisterView 
from django.contrib.auth.views import LogoutView

app_name = 'accounts' 

urlpatterns = [
    # URLهای authentication
    path('login/', auth_views.LoginView.as_view(template_name='accounts/registration/login.html'), name='login'),
    path('logout/', views.custom_logout, name='logout'),
    path('register/', RegisterView.as_view(), name='register'),  # ثبت‌نام
    path('password-reset/', auth_views.PasswordResetView.as_view(template_name='registration/password_reset_form.html'), name='password_reset'),
    path('password-reset/done/', auth_views.PasswordResetDoneView.as_view(template_name='registration/password_reset_done.html'), name='password_reset_done'),
    path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(template_name='registration/password_reset_confirm.html'), name='password_reset_confirm'),
    path('reset/done/', auth_views.PasswordResetCompleteView.as_view(template_name='registration/password_reset_complete.html'), name='password_reset_complete'),

    # اگر می‌خوای یک dashboard ساده داشته باشی (مثلاً صفحه اصلی بعد از ورود که navbar رو نشون می‌ده)
    path("settings/", views.settings_view, name="settings"),
    path('profile/', views.profile_view, name='profile'),
    path('dashboard/', views.dashboard, name='dashboard'),
    
    path('users/create/', views.user_create, name='user_create'),
    path('users/', views.user_list, name='user_list'),

    # مدیریت نقش‌ها
    path('users/<int:user_id>/roles/', views.manage_user_roles, name='manage_roles'),
    path('users/<int:user_id>/roles/add/', views.add_role, name='add_role'),
    path('users/<int:user_id>/roles/<int:role_id>/activate/', views.activate_role, name='activate_role'),
    path('users/<int:user_id>/roles/<int:role_id>/deactivate/', views.deactivate_role, name='deactivate_role'),
    path('users/<int:user_id>/roles/<int:role_id>/delete/', views.delete_role, name='delete_role'),
]