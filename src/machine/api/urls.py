from django.urls import path
from machine.api import views

app_name = 'api'

urlpatterns = [
    # Items data endpoints
    path('items-data/', views.items_data_api, name='items_data'),
    path('items-data-detailed/', views.items_data_detailed_api, name='items_data_detailed'),
    
    # ✅ NEW: Smart endpoint with defaults
    path('items-data-smart/', views.items_data_smart_api, name='items_data_smart'),
    
    # Equipment endpoints
    path('equipment/', views.available_equipment_api, name='available_equipment'),
]