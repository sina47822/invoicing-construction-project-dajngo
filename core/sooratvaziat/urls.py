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
    path('riz_metre/<int:project_id>/', riz_metre_discipline_list, name='riz_metre_discipline_list'),
    path('riz_metre/<int:project_id>/<str:discipline_choice>/', riz_metre, name='riz_metre'),
    path('riz_financial/<int:project_id>/', riz_financial_discipline_list, name='riz_financial_discipline_list'),
    path('riz_financial/<int:project_id>/<str:discipline_choice>/', riz_metre_financial, name='riz_financial'),
    path('sooratjalase/<int:project_id>/', MeasurementSessionView, name='sooratjalase'),
    path('session_list/<int:project_id>/', session_list, name='session_list'),
    path('detailed-session/<int:session_id>/', detailed_session, name='detailed_session'),
    path('financial/<int:project_id>/', project_financial_report, name='project_financial_report'),
    path('financial/', project_financial_report_list, name='project_financial_report_list'),

    # URL جدید برای جستجو
    path('search/', search, name='search'),
    path('search/<str:query>/', search, name='search_query'),

    # URL های جدید برای مدیریت پروژه
    # URL های مدیریت پروژه
    path('projects/', views.project_list, name='project_list'),
    path('projects/create/', views.project_create, name='project_create'),
    path('projects/<int:project_id>/', views.project_detail, name='project_detail'),
    path('projects/<int:project_id>/edit/', views.project_edit, name='project_edit'),
    path('projects/<int:project_id>/duplicate/', views.project_duplicate, name='project_duplicate'),
    path('projects/<int:project_id>/toggle-status/', views.project_toggle_status, name='project_toggle_status'),
    path('projects/<int:project_id>/delete/', views.project_delete, name='project_delete')
]