from django.shortcuts import render

# Create your views here.
from django.views.decorators.cache import cache_page
from django.core.cache import cache
from .models import MachineType,Failure,Preventive




def get_overall_dataframe():
    import pandas as pd
    ms      = MachineType.objects.all()
    dict      =[{'name':m.name,'total':m.machine_count,'target':m.target,
                 'on_repair':m.machine_on_working,'on_preventive':m.machine_on_preventive} for m in ms]
    df      = pd.DataFrame(dict)
    return df

def get_failure_dataframe():
    import pandas as pd
    dict            = list(Failure.objects.filter(status='OPEN').values('machine__name','details',
                                                        'status','start_date','expect_date'))
    df              = pd.DataFrame(dict)
    return df

def get_preventive_dataframe():
    import pandas as pd
    dict            = list(Preventive.objects.filter(status='WORKING').values('machine__name','details',
                                                        'status','start_date','end_date'))
    df              = pd.DataFrame(dict)
    return df


# @cache_page(60 * 5)
def index(request):
    context = {}
    # context['overall']  = get_overall_dataframe().to_html()
    # context['repair']   = get_failure_dataframe().to_html()
    # context['preventive']  = get_preventive_dataframe().to_html()
    context['overall']      = MachineType.objects.all()
    context['repair']       = Failure.objects.filter(status='OPEN').values('machine__name','details',
                                                        'status','start_date','expect_date','updated')
    context['preventive']   = Preventive.objects.filter(status='WORKING').values('machine__name','details',
                                                        'status','start_date','end_date','updated')
    context['plan']   = Preventive.objects.filter(status='PLAN').values('machine__name','details',
                                                        'status','start_date','end_date','updated')
    return render(request, 'maintenance/index.html', context=context)