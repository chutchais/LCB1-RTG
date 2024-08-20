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

from django.views.decorators.cache import cache_page
from django.core.cache import cache
import pandas as pd

db = redis.StrictRedis('redis', 6379,db=settings.RTG_READING_VALUE_DB, 
                            charset="utf-8", decode_responses=True) #Production


@cache_page(60 * 5)
def index(request):
    import json
    import pandas as pd
    # get all key that suffix is *:LATEST
    value_dict = [db.hgetall(k) for k in db.keys('*:LATEST')]
    # Get Parameter name from first Equipment (to be reference)
    # from machine.models import Equipment
    # first_eq = Equipment.objects.filter(name__contains='RTG').first()
    cols = get_parameter_ordered(monitor=False)#[i.name for i in first_eq.items.all()]

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
    
    # Added on Nov 3,2022 -- to show current week for all equipment
    import datetime, pytz
    tz 			= pytz.timezone('Asia/Bangkok')
    today_tz 	=   datetime.datetime.now(tz=tz)
    from datetime import datetime, time
    today_tz_00 = datetime.combine(today_tz, time.min)
    import datetime
    start_week_day = today_tz_00 - datetime.timedelta(today_tz_00.weekday())

    key=f'CURRENT-WEEKS'
    dict = cache.get(key)
    if dict is None :
        dict=list(DataLogger.objects.filter(
                created__gte = start_week_day).order_by('created').values(
                    'created__date','item__name','last_value','current_value','item__equipment__name'))
        # Add Diff
        if dict :
            dict                    = [ {**d,'diff':calculate_diff(d['current_value'],d['last_value'])} for d in dict]
            df_weekly               = pd.DataFrame(dict)
            weekly_table            = df_weekly.pivot_table('diff',['item__name'],'item__equipment__name',aggfunc= 'sum').reindex(cols,level=0)
            context['currentweek']       = weekly_table.to_html()
            cache.set(key, weekly_table.to_html(),60*5)
        else :
            context['currentweek']       = None
    else:
        context['currentweek']        = dict #html
    

    # Added on Nov 7,2022 -- to show last week for all equipment
    import datetime, pytz
    tz 			= pytz.timezone('Asia/Bangkok')
    today_tz 	=   datetime.datetime.now(tz=tz)
    from datetime import datetime, time
    today_tz_00 = datetime.combine(today_tz, time.min)
    import datetime
    end_Last_week_day = today_tz_00 - datetime.timedelta(today_tz_00.weekday())
    start_Last_week_day = end_Last_week_day - datetime.timedelta(days=7)

    key=f'LAST-WEEKS'
    dict = cache.get(key)
    if dict is None :
        dict=list(DataLogger.objects.filter(
                created__range = [start_Last_week_day,end_Last_week_day]).order_by('created').values(
                    'created__date','item__name','last_value','current_value','item__equipment__name'))
        # Add Diff
        if dict :
            dict                    = [ {**d,'diff':calculate_diff(d['current_value'],d['last_value'])} for d in dict]
            df_weekly               = pd.DataFrame(dict)
            weekly_table            = df_weekly.pivot_table('diff',['item__name'],'item__equipment__name',aggfunc= 'sum').reindex(cols,level=0)
            context['lastweek']       = weekly_table.to_html()
            cache.set(key, weekly_table.to_html(),60*60*2)
        else :
            context['lastweek']       = None
    else:
        context['lastweek']        = dict #html

    # Render the HTML template index.html with the data in the context variable
    return render(request, 'machine/index.html', context=context)
    # return HttpResponse(table)

def engine_on(request):
    import json
    import pandas as pd
    # Modify on JUly 16,2024 -- to ignore 'LIST' key
    # value_dict = [db.hgetall(k) for k in db.keys('RTG??:MONITOR') if ':LIST' not in k]
    # Modify on Aug 17,2024 -- to remove Minute data
    value_dict = [db.hgetall(k) for k in db.keys('RTG??:MONITOR') if 'Crane On Minute' not in k]

    # Added on Aug 20,2024 -- To change number from -1 to 2 of 'Engine Power On:LIST'
    for i in value_dict:
        i['Engine Power On:LIST']=i['Engine Power On:LIST'].replace('-1','2')
    # ------------------------------------------------------------------------------

    # Comment on Aug 17,2024 --- to fix col
    # cols = get_parameter_ordered(monitor=True)#[i.name for i in first_eq.items.all()]
    # header = ['Equipment','DateTime'] + cols
    header = ['Equipment','DateTime','Engine Power On','Engine Power On:LIST']
    df = pd.DataFrame(value_dict,columns=header)
    sorted_df=df.sort_values(by=['Equipment'], ascending=True)
    # table = sorted_df.to_dict()
    # Modify on Aug 17,2024 -- to change dict to be table wise
    table = sorted_df.to_dict(orient='records')
    context = {
        'monitors' : table
    }
    return render(request, 'machine/engineon_track.html', context=context)

def get_parameter_ordered(monitor:bool):
    from machine.models import Equipment
    first_eq = Equipment.objects.filter(name__contains='RTG').first()
    cols = [i.name for i in first_eq.items.filter(monitor=monitor)]#MOdify on March 25,2024 -- To show only non-parameter
    return cols

def machine_latest(request):
    import json
    # get all key that suffix is *:LATEST
    value_dict = [db.hgetall(k) for k in db.keys('*:LATEST')]

    response = JsonResponse(value_dict, safe=False)
    response['Access-Control-Allow-Origin'] = '*'
    response['Access-Control-Allow-Headers'] = '*'
    return response

def calculate_diff(current:int,last:int):
    if current >= last:
        return current-last
    else:
        return (current+round(last,-3))-last

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

        import datetime, pytz
        tz 			= pytz.timezone('Asia/Bangkok')
        today_tz 	=   datetime.datetime.now(tz=tz)
        from datetime import datetime, time
        today_tz_00 = datetime.combine(today_tz, time.min) 
        # today_tz_24 = datetime.combine(today_tz, time.max)
        import datetime
        last_7_day = today_tz_00 - datetime.timedelta(7)
        last_7x5_day = today_tz_00 - datetime.timedelta(7*5)
        start_last_7x5_day 	= last_7x5_day - datetime.timedelta(last_7x5_day.weekday())
        # Added on Nov 3,2022
        last_2_month = today_tz_00 - datetime.timedelta(days=30*2)
        start_last_2_month 	= last_2_month - datetime.timedelta(last_2_month.weekday())

        # Added on Nov 9,2022 -- To order parameter
        cols = get_parameter_ordered(monitor=False)

        # Daily (last 7 days)
        key=f'{context["object"]}-7DAYS'
        dict = cache.get(key)
        if dict is None :
            dict=list(DataLogger.objects.filter(
                    item__equipment__name=context["object"],
                    created__gte = last_7_day).order_by('created').values(
                        'created__date','item__name','last_value','current_value'))
            # Add Diff
            dict = [ {**d,'diff':calculate_diff(d['current_value'],d['last_value'])} for d in dict]
            # Change crated__date format
            dict = [ {**d,'created__date':d['created__date'].strftime("%b %d")} for d in dict]

            
            if dict :
                df_daily                = pd.DataFrame(dict)
                daily_table             = df_daily.pivot_table('diff',['item__name'],'created__date').reindex(cols,level=0)
                context['daily']        = daily_table.to_html() #daily_table.reset_index().to_html()
                cache.set(key, daily_table.to_html(),60*60*2)
            else:
                context['daily']        = None
        else:
            context['daily']        = dict #html


        # Weekly (5 weeks)
        key=f'{context["object"]}-5WEEKS'
        dict = cache.get(key)
        if dict is None :
            dict=list(DataLogger.objects.filter(
                    item__equipment__name=context["object"],
                    created__gte = start_last_7x5_day).order_by('created').values(
                        'created__date','item__name','last_value','current_value','created_week'))
            # Add Diff
            if dict :
                dict                    = [ {**d,'diff':calculate_diff(d['current_value'],d['last_value'])} for d in dict]
                df_weekly               = pd.DataFrame(dict)
                weekly_table            = df_weekly.pivot_table('diff',['item__name'],'created_week',aggfunc= 'sum').reindex(cols,level=0)
                context['weekly']       = weekly_table.to_html()
                cache.set(key, weekly_table.to_html(),60*60*2)
            else :
                context['weekly']       = None
        else:
            context['weekly']        = dict #html
        
        #Monthly 2 (2 months) 
        key=f'{context["object"]}-2MONTH'
        dict = cache.get(key)
        if dict is None :
            dict=list(DataLogger.objects.filter(
                    item__equipment__name=context["object"],
                    created__gte = start_last_2_month).order_by('created').values(
                        'created__date','item__name','last_value','current_value','created_month'))
            # Add Diff
            if dict :
                dict                    = [ {**d,'diff':calculate_diff(d['current_value'],d['last_value'])} for d in dict]
                df_monthly               = pd.DataFrame(dict)
                monthly_table            = df_monthly.pivot_table('diff',['item__name'],'created_month',aggfunc= 'sum').reindex(cols,level=0)
                context['monthly']       = monthly_table.to_html()
                cache.set(key, monthly_table.to_html(),60*60*2)
            else :
                context['monthly']       = None
        else:
            context['monthly']        = dict #html

        return context


@cache_page(60 * 5)
def operation(request):
    import json
    import pandas as pd
    context = {}

    # Added on Aug 18,2024 -- To set report show in Hour mode or Minute mode
    hour_mode = True

    
    # Added on Nov 3,2022 -- to show current week for all equipment
    import datetime, pytz
    tz 			= pytz.timezone('Asia/Bangkok')
    today_tz 	=   datetime.datetime.now(tz=tz)
    from datetime import datetime, time
    today_tz_00 = datetime.combine(today_tz, time.min)
    import datetime
    start_week_day = today_tz_00 - datetime.timedelta(today_tz_00.weekday())
    last_7_days = today_tz_00 - datetime.timedelta(days=7)
    yesterdays = today_tz_00 - datetime.timedelta(days=1)

    key=f'CRANE_ON_LAST7DAYS'
    dict = cache.get(key)


    # Added on JUly 19,2024 -- To handle with non-hybrid RTG
    remove_rtgs=['RTG16','RTG17','RTG18','RTG19','RTG20','RTG21','RTG22','RTG23','RTG24',
              'RTG25','RTG26','RTG27','RTG28','RTG29','RTG30','RTG31','RTG32','RTG33',
              'RTG34','RTG35']

    if dict is None :
        # Check Last record date on DataLogger
        last_record_date_tz = DataLogger.objects.last().created.astimezone(tz)
        last_record_date_00 = datetime.datetime.combine(last_record_date_tz, time.min)

        # # Modify on Aug 18,2024 -- To to add 'Crane On Minute' parameter ,remove 'Crane On Hour'
        # dict_yesterday=list(DataLogger.objects.filter(
        #         created__gte = last_record_date_00,item__name__in =[
        #             'Crane On Hour','Engine Working Hour','Crane On Minute']).order_by(
        #             'item__equipment__name','created').values(
        #             'created__date','item__name','last_value','current_value',
        #             'item__equipment__name','item__current_value'))
        # # Select Engine Working Hour only Hybrid RTG
        # dict_yesterday =  [
        #                     i for i in dict_yesterday 
        #                     if i['item__name'] in ['Crane On Hour','Crane On Minute'] or 
        #                     (i['item__equipment__name'] not in remove_rtgs and i['item__name']=='Engine Working Hour')
        #                  ]
        # # Added on Aug 18,2024 -- To remove 'Crane On Hour' for eRTG
        # dict_yesterday =  [
        #     i for i in dict_yesterday
        #     if i['item__equipment__name'] in ['RTG33','RTG34','RTG35'] or
        #       (i['item__name']!='Crane On Hour' and i['item__equipment__name'] not in ['RTG33','RTG34','RTG35'])
            
        # ]
        # # -------------------------------------------------------------------------------------------

        # # if dict_yesterday :
        # dict_yesterday  = [ {**d,'diff':calculate_diff(d['item__current_value'],d['current_value'])} for d in dict_yesterday]
        
        # for i in dict_yesterday:
        #     # After midnight
        #     # if day_diff == 2 and today_tz.hour >= 0 :
        #     i['created__date'] = last_record_date_tz+datetime.timedelta(days=1)
        #     i['created__date'] =datetime.datetime.strftime(i['created__date'], "%b-%d")
        #     # # Added on Aug 18,2024 -- To change Diff to either Hour or Minute mode
        #     i['diff'] = i['diff']*60 if i['item__name'] != 'Crane On Minute' else i['diff']
        #     # {i['diff']//60}:{i['diff']%60}

        # df_today      = pd.DataFrame(dict_yesterday)
        # today_table   = pd.pivot_table(df_today,values='diff',index=['item__equipment__name'],
        #                 columns=['created__date'],aggfunc="sum")

        today_found_data,today_table = get_data_by_start_date(last_record_date_00,today_report=True)

        # # Modify on 19 JUly -- to support Hybrid RTG
        dict=list(DataLogger.objects.filter(
                created__gte = last_7_days,item__name__in =[
                    'Engine Working Hour','Crane On Minute']).order_by(
                    'item__equipment__name','created').values(
                    'created__date','item__name','last_value','current_value',
                    'item__equipment__name','item__current_value'))
        # dict =  [
        #         i for i in dict 
        #         if i['item__name']=='Crane On Hour' or 
        #         (i['item__equipment__name'] not in remove_rtgs and i['item__name']=='Engine Working Hour')
        #         ]
        dict =  [
                    i for i in dict 
                    if i['item__name'] in ['Crane On Hour','Crane On Minute'] or 
                    (i['item__equipment__name'] not in remove_rtgs and i['item__name']=='Engine Working Hour')
                    ]
        # dict =  [
        #     i for i in dict
        #     if i['item__equipment__name'] in ['RTG33','RTG34','RTG35'] or
        #     (i['item__name']!='Crane On Hour' and i['item__equipment__name'] not in ['RTG33','RTG34','RTG35'])
        # ]
        # Add Diff
        if dict :
            dict                    = [ {**d,'diff':calculate_diff(d['current_value'],d['last_value'])} for d in dict]
            for i in dict:
                i['created__date']=datetime.datetime.strftime(i['created__date'], "%b-%d")
                # # Added on Aug 18,2024 -- To change Diff to either Hour or Minute mode
                i['diff'] = i['diff']*60 if i['item__name'] != 'Crane On Minute' else i['diff']  

            df_weekly               = pd.DataFrame(dict)
            # weekly_table            = df_weekly.pivot_table('diff',['item__name'],'item__equipment__name',aggfunc= 'sum').reindex(cols,level=0)
            weekly_table            =pd.pivot_table(df_weekly,values='diff',index=['item__equipment__name'],
                   columns=['created__date'],aggfunc="sum")


            # Merge table
            if today_found_data :
                final_df =pd.merge(weekly_table,today_table, on="item__equipment__name")
            else:
                final_df = weekly_table

            # Added JUly 29,2024 -- To save final DF to Redis
            save_df_to_redis ('OPS_7DAYS_ENGINE_ON',final_df)
            # -----------------------------------------------

            context['currentweek']       = final_df.to_html()
            cache.set(key, final_df.to_html(),60*5)
        else :
            context['currentweek']       = None
    else:
        context['currentweek']        = dict #html

    # Render the HTML template index.html with the data in the context variable
    return render(request, 'machine/operation.html', context=context)

def save_df_to_redis(key,df):
    data = df.to_json()
    db.set(key,data)

def get_df_from_redis(key):
    import pandas as pd
    blob = db.get(key)
    return pd.read_json(blob)

def operation_export(request):
    import pandas as pd
    from io import BytesIO
    from django.http import HttpResponse
    df = get_df_from_redis('OPS_7DAYS_ENGINE_ON')
    response = HttpResponse(content_type='application/xlsx')
    response['Content-Disposition'] = f'attachment; filename="EngineOn.xlsx"'
    with pd.ExcelWriter(response) as writer:
        df.to_excel(writer, sheet_name='last7days')

    return response
    # with BytesIO() as b:
    #     # Use the StringIO object as the filehandle.
    #     writer = pd.ExcelWriter(b, engine='xlsxwriter')
    #     df.to_excel(writer, sheet_name='Sheet1')
    #     writer.save()
    #     filename = 'Last7day'
    #     content_type = 'application/vnd.ms-excel'
    #     response = HttpResponse(b.getvalue(), content_type=content_type)
    #     response['Content-Disposition'] = 'attachment; filename="' + filename + '.xlsx"'
    #     return response

# Added on Aug 18,2024 -- Function to get data by starting date
def get_data_by_start_date(start_date_00,today_report):
        import datetime, pytz
        tz 			= pytz.timezone('Asia/Bangkok')
        today_tz 	=   datetime.datetime.now(tz=tz)
        from datetime import datetime, time
        today_tz_00 = datetime.combine(today_tz, time.min)
        import datetime

        # Added on JUly 19,2024 -- To handle with non-hybrid RTG
        remove_rtgs=['RTG16','RTG17','RTG18','RTG19','RTG20','RTG21','RTG22','RTG23','RTG24',
              'RTG25','RTG26','RTG27','RTG28','RTG29','RTG30','RTG31','RTG32','RTG33',
              'RTG34','RTG35']
            # Modify on Aug 18,2024 -- To to add 'Crane On Minute' parameter ,remove 'Crane On Hour'
        dict_yesterday=list(DataLogger.objects.filter(
                created__gte = start_date_00,item__name__in =[
                    'Engine Working Hour','Crane On Minute']).order_by(
                    'item__equipment__name','created').values(
                    'created__date','item__name','last_value','current_value',
                    'item__equipment__name','item__current_value'))
        
        if not dict_yesterday:
            return False,None

        # Select Engine Working Hour only Hybrid RTG
        dict_yesterday =  [
                            i for i in dict_yesterday 
                            if i['item__name'] in ['Crane On Hour','Crane On Minute'] or 
                            (i['item__equipment__name'] not in remove_rtgs and i['item__name']=='Engine Working Hour')
                         ]
        # Added on Aug 18,2024 -- To remove 'Crane On Hour' for eRTG
        # dict_yesterday =  [
        #     i for i in dict_yesterday
        #     if i['item__equipment__name'] in ['RTG33','RTG34','RTG35'] or
        #       (i['item__name']!='Crane On Hour' and i['item__equipment__name'] not in ['RTG33','RTG34','RTG35'])
            
        # ]
        # -------------------------------------------------------------------------------------------

        # if dict_yesterday :
        dict_yesterday  = [ {**d,'diff':calculate_diff(d['item__current_value'],d['current_value'])} for d in dict_yesterday]
        
        for i in dict_yesterday:
            # After midnight
            # if day_diff == 2 and today_tz.hour >= 0 :
            if today_report :
                i['created__date'] = start_date_00 + datetime.timedelta(days=1)
            i['created__date'] =datetime.datetime.strftime(i['created__date'], "%b-%d")
            # # Added on Aug 18,2024 -- To change Diff to either Hour or Minute mode
            i['diff'] = i['diff']*60 if i['item__name'] != 'Crane On Minute' else i['diff']
            # {i['diff']//60}:{i['diff']%60}

        df      = pd.DataFrame(dict_yesterday)
        table   = pd.pivot_table(df,values='diff',index=['item__equipment__name'],
                        columns=['created__date'],aggfunc="sum")
        
        return True , table