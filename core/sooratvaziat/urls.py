from django.urls import path
from . import views

app_name = 'sooratvaziat'

# در urls.py
urlpatterns = [
    # ریز متره
    path('project/<int:pk>/riz-metre/', views.riz_metre_discipline_list, name='riz_metre_discipline_list'),
    path('project/<int:pk>/riz-metre/<str:discipline>/', views.riz_metre, name='riz_metre'),
    path('project/<int:pk>/<str:discipline>/summary/', views.measurement_summary, name='price_list_summary'),
    path('project/<int:pk>/disciplines-summary/', views.discipline_summary, name='discipline_summary'),
    # ریز مالی
    path('project/<int:pk>/riz-financial/disciplines/', views.riz_financial_discipline_list, name='riz_financial_discipline_list'),
    path('project/<int:pk>/riz-financial/<str:discipline_choice>/', views.riz_metre_financial, name='riz_financial'),

    # صورت جلسات
    path('project/<int:pk>/sooratjalase/', views.MeasurementSessionView, name='sooratjalase'),
    path('project/<int:pk>/sessions/', views.session_list, name='session_list'),

    # مدیریت صورت جلسات
    path('projects/<int:project_pk>/sessions/create/', views.session_create, name='session_create'),
    path('projects/<int:project_pk>/sessions/<int:pk>/', views.session_detail, name='session_detail'),
    path('projects/<int:project_pk>/sessions/<int:pk>/edit/', views.session_edit, name='session_edit'),
    path('projects/<int:project_pk>/sessions/<int:pk>/delete/', views.delete_session, name='delete_session'),
    
    # مدیریت آیتم‌های صورت جلسه
    path('projects/<int:project_pk>/sessions/<int:session_pk>/items/add/', views.add_session_item, name='add_session_item'),
    path('projects/<int:project_pk>/sessions/<int:session_pk>/items/<int:item_pk>/edit/', views.edit_session_item, name='edit_session_item'),
    path('projects/<int:project_pk>/sessions/<int:session_pk>/items/<int:item_pk>/delete/', views.delete_session_item, name='delete_session_item'),
    path('projects/<int:project_pk>/sessions/<int:session_pk>/items/<int:item_pk>/revisions/', views.get_item_revisions, name='get_item_revisions'),
    path('projects/<int:project_pk>/sessions/<int:session_pk>/groups/<str:pricelist_number>/items/', 
        views.group_items_detail, 
        name='group_items_detail'),
    path('projects/<int:project_pk>/sessions/<int:session_pk>/groups/<str:pricelist_number>/delete/', 
        views.delete_session_items_by_pricelist, 
        name='delete_session_items_by_pricelist'),

    # گزارش‌های مالی کلی (لیست پروژه‌ها)
    path('financial-reports/', views.project_financial_report_list, name='project_financial_report_list'),
    path('project/<int:pk>/financial-report/', views.project_financial_report, name='project_financial_report'),

    # جستجو
    path('search/', views.search, name='search'),
    
    # AJAX URLs
    path('get-price-lists/', views.get_price_lists_by_discipline, name='get_price_lists'),
]