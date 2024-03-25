from django.urls import path, include
from django.views.decorators.cache import cache_page
from . import views
from .views import MachineDetailView

from .views import index,machine_latest,engine_on
urlpatterns = [
    path('', index, name='index'),
    path('engine-on', engine_on, name='engine_on'),
    path('<pk>', MachineDetailView.as_view(), name='detail'),
    path('api/latest', machine_latest, name='latest'),
]
