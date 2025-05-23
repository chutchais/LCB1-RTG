from django.urls import path, include
from django.views.decorators.cache import cache_page
from . import views
from .views import index,by_equipment,FailureListView,FailureDetailView, \
                    MachineTypeDetailView,MachineListView,MachineDetailView
urlpatterns = [
    path('', index, name='index'),
    path('failures/', FailureListView.as_view(), name='failure-list'),
    path('failures/<pk>', FailureDetailView.as_view(), name='failure-detail'),
    path('<section>', by_equipment, name='detail'),

    path('machines/', MachineListView.as_view(), name='machine-list'),
    path('machines/<pk>', MachineDetailView.as_view(), name='machine-detail'),

    path('machinetype/<pk>', MachineTypeDetailView.as_view(), name='machinetype-detail'),
    # path('operation', operation, name='operation'),
    # path('operation-export', operation_export, name='operation-export'),
    # path('<pk>', MachineDetailView.as_view(), name='detail'),
    # path('api/latest', machine_latest, name='latest'),
]