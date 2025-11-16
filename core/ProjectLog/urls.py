from django.urls import path
from .views import audit_log_list, audit_log_detail

urlpatterns = [
    path('logs/', audit_log_list, name='audit_log_list'),
    path('logs/<int:log_id>/', audit_log_detail, name='audit_log_detail'),
]