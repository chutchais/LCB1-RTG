from django.urls import path, include
from django.views.decorators.cache import cache_page
from . import views

from .views import index,machine_latest
urlpatterns = [
    path('', index, name='index'),
    path('api/latest', machine_latest, name='latest'),
]
