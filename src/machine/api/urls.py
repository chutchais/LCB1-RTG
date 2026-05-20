from django.urls import path
from machine.api import views

from machine.api.views import (
    item_summary_api,
    item_summary_html,
    item_summary_excel,
)

app_name = 'api'

urlpatterns = [
    # Items data endpoints
    path('items-data/', views.items_data_api, name='items_data'),
    path('items-data-detailed/', views.items_data_detailed_api, name='items_data_detailed'),
    path('items-data-smart/', views.items_data_smart_api, name='items_data_smart'),
    
    # Productivity report endpoints
    path('productivity-report/', views.productivity_report_api, name='productivity_report'),
    path('productivity-report-detailed/', views.productivity_report_detailed_api, name='productivity_report_detailed'),
    path('productivity-comparison/', views.productivity_comparison_api, name='productivity_comparison'),
    
    # ✅ NEW: Daily report endpoints
    path('productivity-report-daily/', views.productivity_report_daily_api, name='productivity_report_daily'),
    path('productivity-report-daily-detailed/', views.productivity_report_daily_detailed_api, name='productivity_report_daily_detailed'),
    
        # ✅ NEW: HTML/Text/CSV endpoints
    path('productivity-report-daily-html/', views.productivity_report_daily_html, name='productivity_report_daily_html'),
    path('productivity-report-daily-text/', views.productivity_report_daily_text, name='productivity_report_daily_text'),
    path('productivity-report-daily-csv/', views.productivity_report_daily_csv_api, name='productivity_report_daily_csv'),
    path('productivity-report-daily-excel/', views.productivity_report_daily_excel, name='productivity_report_daily_excel'),  # ✅ ADD THIS

    # Diagnostic endpoints
    path('productivity-diagnostic/', views.productivity_diagnostic, name='productivity-diagnostic'),  # JSON API
    path('productivity-diagnostic-html/', views.productivity_diagnostic_html, name='productivity-diagnostic-html'),  # HTML page
    # Equipment endpoints
    path('equipment/', views.available_equipment_api, name='available_equipment'),

    # Item Summary Report
    path('item-summary/', item_summary_api, name='item-summary'),
    path('item-summary-html/', item_summary_html, name='item-summary-html'),
    path('item-summary-excel/', item_summary_excel, name='item-summary-excel'),
]