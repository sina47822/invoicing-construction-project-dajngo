# urls.py
from django.urls import path
from . import views
from .views import (
    search,
    session_list, riz_metre_financial, 
    riz_metre, MeasurementSessionView,  
    project_financial_report, riz_metre_discipline_list,
    riz_financial_discipline_list, project_financial_report_list
)

app_name = 'sooratvaziat' 

urlpatterns = [
    # path('riz_metre/<int:pk>/', riz_metre_discipline_list, name='riz_metre_discipline_list'),
    # path('riz_metre/<int:pk>/<str:discipline_choice>/', riz_metre, name='riz_metre'),
    path('riz_financial/<int:pk>/', riz_financial_discipline_list, name='riz_financial_discipline_list'),
    path('riz_financial/<int:pk>/<str:discipline_choice>/', riz_metre_financial, name='riz_financial'),
    path('sooratjalase/<int:pk>/', MeasurementSessionView, name='sooratjalase'),
    # path('session_list/<int:pk>/', session_list, name='session_list'),
    # path('detailed-session/<int:session_id>/', detailed_session, name='detailed_session'),
    path('financial/', project_financial_report_list, name='project_financial_report_list'),
    path('project/<int:pk>/financial-report/', views.project_financial_report, name='project_financial_report'),
    # URL جدید برای جستجو
    path('search/', search, name='search'),
    path('search/<str:query>/', search, name='search_query'),

    # URL های جدید برای مدیریت پروژه
    # URL های مدیریت پروژه

    # صورت‌جلسات
    # مدیریت صورت جلسات
    path('projects/<int:project_pk>/sessions/create/', views.session_create, name='session_create'),
    path('projects/<int:project_pk>/sessions/<int:pk>/', views.session_detail, name='session_detail'),
    path('projects/<int:project_pk>/sessions/<int:pk>/edit/', views.session_edit, name='session_edit'),
    path('projects/<int:project_pk>/sessions/<int:pk>/delete/', views.delete_session, name='delete_session'),
    path('projects/<int:pk>/sessions/', views.session_list, name='session_list'),
    # مدیریت آیتم‌های صورت جلسه
    path('projects/<int:project_pk>/sessions/<int:session_pk>/items/add/', views.add_session_item, name='add_session_item'),
    path('projects/<int:project_pk>/sessions/<int:session_pk>/items/<int:item_pk>/edit/', views.edit_session_item, name='edit_session_item'),
    path('projects/<int:project_pk>/sessions/<int:session_pk>/items/<int:item_pk>/delete/', views.delete_session_item, name='delete_session_item'),
    # ریز متره
    path('project/<int:pk>/riz-metre/disciplines/', views.riz_metre_discipline_list, name='riz_metre_discipline_list'),
    path('project/<int:pk>/riz-metre/<str:discipline_choice>/', views.riz_metre, name='riz_metre'),
    # پرداخت‌ها
    # path('projects/<int:project_pk>/payments/', views.payment_list, name='payment_list'),
    # path('projects/<int:project_pk>/payments/create/', views.payment_create, name='payment_create'),
    # path('projects/<int:project_pk>/payments/<int:pk>/', views.payment_detail, name='payment_detail'),
    

]