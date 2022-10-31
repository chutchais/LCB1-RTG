from django.shortcuts import render
from django.http import JsonResponse
from django.conf import settings

# Create your views here.
from django.http import HttpResponse
import logging
import redis
from django.conf import settings

from django.views.generic import DetailView,CreateView,UpdateView,DeleteView,ListView
from .models import Equipment,Item,DataLogger

db = redis.StrictRedis('redis', 6379,db=settings.RTG_READING_VALUE_DB, 
                            charset="utf-8", decode_responses=True) #Production

def index(request):
    import json
    import pandas as pd
    # get all key that suffix is *:LATEST
    value_dict = [db.hgetall(k) for k in db.keys('*:LATEST')]
    # Get Parameter name from first Equipment (to be reference)
    from machine.models import Equipment
    first_eq = Equipment.objects.filter(name__contains='RTG').first()
    cols = [i.name for i in first_eq.items.all()]
    header = ['Equipment','DateTime'] + cols
    # df = pd.DataFrame(value_dict,columns=['equipment','datetime',
    #                     'Hoist Motor Working Hours','Trolly Motor Working hours',
    #                     'Gantry Motor Working hours','Diesel Working hours',
    #                     'Crane On Working hour','Move Container Total'])
    df = pd.DataFrame(value_dict,columns=header)
    sorted_df=df.sort_values(by=['Equipment'], ascending=True)
    # table = sorted_df.to_html()
    table = sorted_df.to_dict()
    context = {
        'rtgs' : table
    }
    # Render the HTML template index.html with the data in the context variable
    return render(request, 'machine/index.html', context=context)
    # return HttpResponse(table)

def machine_latest(request):
    import json
    # get all key that suffix is *:LATEST
    value_dict = [db.hgetall(k) for k in db.keys('*:LATEST')]

    response = JsonResponse(value_dict, safe=False)
    response['Access-Control-Allow-Origin'] = '*'
    response['Access-Control-Allow-Headers'] = '*'
    return response


class MachineDetailView(DetailView):
    model = Equipment
    def get_context_data(self,**kwargs):
        context = super(MachineDetailView,self).get_context_data(**kwargs)
        equipment_name          = f'{context["object"]}:LATEST'
        realtime_dict           = db.hgetall(equipment_name)
        if realtime_dict.get('Live'):
            del realtime_dict['Live']
        if realtime_dict.get('live'):
            del realtime_dict['live']
        if realtime_dict.get('Equipment'):
            del realtime_dict['Equipment']
        context['realtime']     = realtime_dict
        return context