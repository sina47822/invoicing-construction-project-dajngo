# urls.py
from django.urls import path
from . import views
from .views import (
    search,
    session_list, riz_metre_financial, 
    riz_metre, MeasurementSessionView, detailed_session, 
    project_financial_report, riz_metre_discipline_list,
    riz_financial_discipline_list, project_financial_report_list
)

app_name = 'sooratvaziat' 

urlpatterns = [
    path('riz_metre/<int:pk>/', riz_metre_discipline_list, name='riz_metre_discipline_list'),
    path('riz_metre/<int:pk>/<str:discipline_choice>/', riz_metre, name='riz_metre'),
    path('riz_financial/<int:pk>/', riz_financial_discipline_list, name='riz_financial_discipline_list'),
    path('riz_financial/<int:pk>/<str:discipline_choice>/', riz_metre_financial, name='riz_financial'),
    path('sooratjalase/<int:pk>/', MeasurementSessionView, name='sooratjalase'),
    # path('session_list/<int:pk>/', session_list, name='session_list'),
    path('detailed-session/<int:session_id>/', detailed_session, name='detailed_session'),
    path('financial/', project_financial_report_list, name='project_financial_report_list'),
    path('project/<int:pk>/financial-report/', views.project_financial_report, name='project_financial_report'),
    # URL جدید برای جستجو
    path('search/', search, name='search'),
    path('search/<str:query>/', search, name='search_query'),

    # URL های جدید برای مدیریت پروژه
    # URL های مدیریت پروژه
    # پروژه‌ها
    path('projects/', views.project_list, name='project_list'),
    path('projects/create/', views.project_create, name='project_create'),
    path('projects/<int:pk>/', views.project_detail, name='project_detail'),
    path('projects/<int:pk>/edit/', views.project_edit, name='project_edit'),
    path('projects/<int:pk>/delete/', views.project_delete, name='project_delete'),
    
    # صورت‌جلسات
    path('projects/<int:pk>/sessions/', views.session_list, name='session_list'),
    # path('projects/<int:project_pk>/sessions/create/', views.session_create, name='session_create'),
    # path('projects/<int:project_pk>/sessions/<int:pk>/', views.session_detail, name='session_detail'),
    # path('session/<int:session_id>/edit/', views.detailed_session_edit, name='session_edit'
    
    # پرداخت‌ها
    # path('projects/<int:project_pk>/payments/', views.payment_list, name='payment_list'),
    # path('projects/<int:project_pk>/payments/create/', views.payment_create, name='payment_create'),
    # path('projects/<int:project_pk>/payments/<int:pk>/', views.payment_detail, name='payment_detail'),
    
    # اسناد
    # path('projects/<int:project_pk>/documents/upload/', views.document_upload, name='document_upload'),
    
    # گزارش‌ها
    # path('projects/<int:project_pk>/report/', views.project_report, name='project_report'),
    path('projects/<int:pk>/duplicate/', views.project_duplicate, name='project_duplicate'),
    path('projects/<int:pk>/toggle-status/', views.project_toggle_status, name='project_toggle_status'),
]