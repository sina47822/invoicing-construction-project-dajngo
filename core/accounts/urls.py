from django.urls import path
from django.contrib.auth import views as auth_views
from . import views
from .views import RegisterView 

app_name = 'accounts' 

urlpatterns = [
    # URLهای authentication
    path('login/', auth_views.LoginView.as_view(template_name='accounts/registration/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='/'), name='logout'),  # بعد از خروج به صفحه اصلی برمی‌گرده
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
]