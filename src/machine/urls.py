from django.urls import path, include
from django.views.decorators.cache import cache_page
from . import views
from .views import MachineDetailView

from .views import index,machine_latest,engine_on,operation,operation_export
urlpatterns = [
    path('', index, name='index'),
    path('engine-on', engine_on, name='engine_on'),
    path('operation', operation, name='operation'),
    path('operation-export', operation_export, name='operation-export'),
    path('<pk>', MachineDetailView.as_view(), name='detail'),
    path('api/latest', machine_latest, name='latest'),
    # ============ NEW API URLS ============
    path('api/', include('machine.api.urls')),  # Include all API endpoints
    
    # ============ NEW DASHBOARD URLS ============
    # path('dashboard/', views.DashboardView.as_view(), name='dashboard'),
    # path('dashboard/equipment/<str:equipment_name>/', views.EquipmentDetailView.as_view(), name='equipment_detail'),
    # path('items-dashboard/', views.ItemsDashboardView.as_view(), name='items_dashboard'),
    # path('items-dashboard-realtime/', views.TemplateView.as_view(template_name='machine/items_dashboard_realtime.html'), name='items_dashboard_realtime'),
]
