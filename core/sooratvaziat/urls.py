# urls.py
from django.urls import path
from . import views
from .views import (
    project_financial_report_list, session_list, riz_metre_financial, 
    riz_metre, MeasurementSessionView, detailed_session, 
    project_financial_report, riz_metre_discipline_list,
    riz_financial_discipline_list
)

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
]