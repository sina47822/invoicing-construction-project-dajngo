# urls.py
from django.urls import path
from . import views

app_name = 'projects' 

urlpatterns = [
    # پروژه‌ها
    path('', views.project_list, name='project_list'),
    path('create/', views.project_create, name='project_create'),
    path('<int:pk>/', views.project_detail, name='project_detail'),
    path('<int:pk>/edit/', views.project_edit, name='project_edit'),
    path('<int:pk>/delete/', views.project_delete, name='project_delete'),
        # اسناد
    # path('<int:project_pk>/documents/upload/', views.document_upload, name='document_upload'),
    
    # گزارش‌ها
    # path('<int:project_pk>/report/', views.project_report, name='project_report'),
    path('<int:pk>/duplicate/', views.project_duplicate, name='project_duplicate'),
    path('<int:pk>/toggle-status/', views.project_toggle_status, name='project_toggle_status'),
]