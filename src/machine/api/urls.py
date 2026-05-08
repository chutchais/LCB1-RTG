from django.urls import path
from machine.api import views

app_name = 'api'

urlpatterns = [
    # Items data endpoints
    path('items-data/', views.items_data_api, name='items_data'),
    path('items-data-detailed/', views.items_data_detailed_api, name='items_data_detailed'),
    
    # ✅ NEW: Smart endpoint with defaults
    path('items-data-smart/', views.items_data_smart_api, name='items_data_smart'),
    
    # ✅ NEW: Productivity report endpoints
    path('productivity-report/', views.productivity_report_api, name='productivity_report'),
    path('productivity-report-detailed/', views.productivity_report_detailed_api, name='productivity_report_detailed'),
    path('productivity-comparison/', views.productivity_comparison_api, name='productivity_comparison'),
    
    # Equipment endpoints
    path('equipment/', views.available_equipment_api, name='available_equipment'),
]