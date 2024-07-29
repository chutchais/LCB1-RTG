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
]
