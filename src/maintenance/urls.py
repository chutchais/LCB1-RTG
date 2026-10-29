# from django.urls import path, include
# from django.views.decorators.cache import cache_page
# from . import views
# from .views import index,by_equipment,FailureListView,FailureDetailView, \
#                     MachineTypeDetailView,MachineListView,MachineDetailView
# urlpatterns = [
#     path('', index, name='index'),
#     path('failures/', FailureListView.as_view(), name='failure-list'),
#     path('failures/<pk>', FailureDetailView.as_view(), name='failure-detail'),
#     path('<section>', by_equipment, name='detail'),

#     path('machines/', MachineListView.as_view(), name='machine-list'),
#     path('machines/<pk>', MachineDetailView.as_view(), name='machine-detail'),

#     path('machinetype/<pk>', MachineTypeDetailView.as_view(), name='machinetype-detail'),
# ]
from django.urls import path, include
from django.views.decorators.cache import cache_page
from . import views
from . import technician_views
from django.contrib.auth.views import LoginView, LogoutView
from django.views.decorators.http import require_POST
from .report_views import (
    TodayFailureReportView,
    WeekFailureReportView,
    PerformanceMetricsView,
    MachineDetailReportView,
    ReportDateRangeView,
    CustomDateRangeFailureReportView,
    CustomDateRangePerformanceView,
    TodayFailureReportAPIView,
    WeekFailureReportAPIView,
    PerformanceMetricsAPIView,
    MachineDetailAPIView,
    CustomDateRangeFailureAPIView,
    CustomDateRangePerformanceAPIView,
    DailyFailureDetailsAPIView,
    DailyFailuresRangeAPIView,
    CustomFailuresWithChartsAPIView
)
from .views import (
    index, by_equipment, FailureListView, FailureDetailView,
    MachineTypeDetailView, MachineListView, MachineDetailView
)

urlpatterns = [
    path('jobs/login/', LoginView.as_view(
        template_name='maintenance/technician/login.html',
        next_page='maintenance:technician-board',
        redirect_authenticated_user=True,
    ), name='technician-login'),
    path('jobs/logout/', require_POST(LogoutView.as_view(next_page='maintenance:technician-login')),
         name='technician-logout'),
    path('jobs/', technician_views.job_board, name='technician-board'),
    path('jobs/new/', technician_views.report_failure, name='technician-report'),
    path('jobs/<int:pk>/', technician_views.job_detail, name='technician-job'),
    path('jobs/<int:pk>/action/', technician_views.job_action, name='technician-action'),
    path('jobs/<int:pk>/photos/', technician_views.upload_photo, name='technician-photo'),
    # Existing paths
    path('', index, name='index'),
    path('failures/', FailureListView.as_view(), name='failure-list'),
    path('failures/<pk>', FailureDetailView.as_view(), name='failure-detail'),
    path('machines/', MachineListView.as_view(), name='machine-list'),
    path('machines/<pk>', MachineDetailView.as_view(), name='machine-detail'),
    path('machinetype/<pk>', MachineTypeDetailView.as_view(), name='machinetype-detail'),

    # Report paths
    path('reports/today/', TodayFailureReportView.as_view(), name='report-today'),
    path('reports/week/', WeekFailureReportView.as_view(), name='report-week'),
    path('reports/metrics/', PerformanceMetricsView.as_view(), name='report-metrics'),
    path('reports/machine/<str:machine_name>/', MachineDetailReportView.as_view(), name='report-machine'),

    # Date range selection
    path('reports/date-range/', ReportDateRangeView.as_view(), name='report-date-range'),
    path('reports/custom-failures/', CustomDateRangeFailureReportView.as_view(), name='report-custom-failures'),
    path('reports/custom-performance/', CustomDateRangePerformanceView.as_view(), name='report-custom-performance'),

    # API paths
    path('api/report/today/', TodayFailureReportAPIView.as_view(), name='api-report-today'),
    path('api/report/week/', WeekFailureReportAPIView.as_view(), name='api-report-week'),
    path('api/performance/', PerformanceMetricsAPIView.as_view(), name='api-performance'),
    path('api/report/machine/<str:machine_name>/', MachineDetailAPIView.as_view(), name='api-machine-detail'),
    path('api/report/machine/<str:machine_name>/', MachineDetailAPIView.as_view(), name='api-report-machine'),
    path('api/report/custom-failures/', CustomDateRangeFailureAPIView.as_view(), name='api-custom-failures'),
    path('api/report/custom-performance/', CustomDateRangePerformanceAPIView.as_view(), name='api-custom-performance'),
    path('api/report/daily-failures/<str:date>/', DailyFailureDetailsAPIView.as_view(), name='api-daily-failures'),
    path('<section>', by_equipment, name='detail'),
    path('api/report/daily-failures-range/', DailyFailuresRangeAPIView.as_view(), name='api-daily-failures-range'),
    path('api/report/custom-failures-with-charts/', CustomFailuresWithChartsAPIView.as_view(), name='api-custom-failures-with-charts'),

    path('api/search-machines/', views.api_search_machines, name='api_search_machines'),
]