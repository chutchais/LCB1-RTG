from django.urls import path, include
from django.views.decorators.cache import cache_page
from . import views
from .views import index,by_equipment,FailureListView,FailureDetailView, \
                    MachineTypeDetailView,MachineListView,MachineDetailView, \
                    report_today, report_week, report_metrics, \
                    api_report_today, api_report_week, api_report_machine, api_performance

urlpatterns = [
    path('', index, name='index'),
    path('failures/', FailureListView.as_view(), name='failure-list'),
    path('failures/<pk>', FailureDetailView.as_view(), name='failure-detail'),

    path('machines/', MachineListView.as_view(), name='machine-list'),
    path('machines/<pk>', MachineDetailView.as_view(), name='machine-detail'),

    path('machinetype/<pk>', MachineTypeDetailView.as_view(), name='machinetype-detail'),

    # --- Failure Analysis Report HTML views ---
    path('reports/today/', report_today, name='report-today'),
    path('reports/week/', report_week, name='report-week'),
    path('reports/metrics/', report_metrics, name='report-metrics'),

    # --- Failure Analysis Report JSON API endpoints ---
    path('api/report/today/', api_report_today, name='api-report-today'),
    path('api/report/week/', api_report_week, name='api-report-week'),
    path('api/report/machine/<str:machine_name>/', api_report_machine, name='api-report-machine'),
    path('api/performance/', api_performance, name='api-performance'),

    path('<section>', by_equipment, name='detail'),
]