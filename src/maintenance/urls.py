from django.urls import path, include
from django.views.decorators.cache import cache_page
from . import views
from .views import index,by_equipment

urlpatterns = [
    path('', index, name='index'),
    path('<section>', by_equipment, name='detail'),
    # path('operation', operation, name='operation'),
    # path('operation-export', operation_export, name='operation-export'),
    # path('<pk>', MachineDetailView.as_view(), name='detail'),
    # path('api/latest', machine_latest, name='latest'),
]