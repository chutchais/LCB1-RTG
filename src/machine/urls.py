from django.urls import path, include
from django.views.decorators.cache import cache_page
from . import views
from .views import MachineDetailView

from .views import index,machine_latest
urlpatterns = [
    path('', index, name='index'),
    path('<pk>', MachineDetailView.as_view(), name='detail'),
    path('api/latest', machine_latest, name='latest'),
]
