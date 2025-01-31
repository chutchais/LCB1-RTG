from django.shortcuts import render

# Create your views here.
from django.views.decorators.cache import cache_page
from django.core.cache import cache
from .models import MachineType,Machine,Failure,Preventive
from django.views.generic import DetailView,CreateView,UpdateView,DeleteView,ListView
from django.db.models import Q,F




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
    context['overall']      = MachineType.objects.all().order_by('section__name','name')
    context['repair']       = Failure.objects.filter(status='OPEN').order_by('start_date')
    context['preventive']   = Preventive.objects.filter(status='WORKING').order_by('start_date')
    context['plan']         = Preventive.objects.filter(status='PLAN').order_by('start_date')
    return render(request, 'maintenance/index.html', context=context)

def by_equipment(request,section):
    context = {}
    context['overall']      = MachineType.objects.filter(section=section)
    context['repair']       = Failure.objects.filter(machine__in=Machine.objects.filter(
                                machine_type__in = MachineType.objects.filter(
                                section__name=section)),status='OPEN')
    context['preventive']   = Preventive.objects.filter(machine__in=Machine.objects.filter(
                                machine_type__in = MachineType.objects.filter(
                                section__name=section)),status='WORKING')
    return render(request, 'maintenance/section.html', context=context)

class MachineTypeDetailView(DetailView):
    model = MachineType
    def get_context_data(self, **kwargs):
        context = super(MachineTypeDetailView, self).get_context_data(**kwargs)
        context['failures'] = Failure.objects.filter(
                            machine__machine_type =self.object).order_by('-start_date')[:50]
        context['machinetypes'] = MachineType.objects.all().exclude(name=self.object.name)
        # Added Jan 31,2025 - to send start date of year
        import datetime, pytz
        tz 			= pytz.timezone('Asia/Bangkok')
        today_tz 	=   datetime.datetime.now(tz=tz)
        from datetime import datetime, time
        today_tz_00 = datetime.combine(today_tz, time.min)
        start_date = today_tz_00.replace(month=1, day=1).strftime('%Y-%m-%d')
        context['start_date'] = start_date
        return context

def failure(request):
    return render(request, 'maintenance/failure_list.html', context={})

class FailureDetailView(DetailView):
    model = Failure
    def get_context_data(self, **kwargs):
        context = super(FailureDetailView, self).get_context_data(**kwargs)
        # Added Jan 31,2025 - to send start date of year
        import datetime, pytz
        tz 			= pytz.timezone('Asia/Bangkok')
        today_tz 	=   datetime.datetime.now(tz=tz)
        from datetime import datetime, time
        today_tz_00 = datetime.combine(today_tz, time.min)
        start_date = today_tz_00.replace(month=1, day=1).strftime('%Y-%m-%d')
        context['start_date'] = start_date
        return context

    
class FailureListView(ListView):
    model = Failure
    paginate_by = 50
    def get_queryset(self):
        query = self.request.GET.get('q')
        # lacking_stock = self.request.GET.get('lacking')
        # over_stock = self.request.GET.get('over')
        if query :
            return Failure.objects.filter(Q(machine__name__icontains=query) |
                                    Q(details__icontains=query) |
                                    Q(rootcause__icontains=query) |
                                    Q(repair_action__icontains=query)).select_related('machine').order_by('-start_date')
        return Failure.objects.all().order_by('-start_date')[:50]

# 'Added on Oct 4,2024'
def send_eq_availability_report(to_email,send_email,
                                url='http://10.24.50.96:8080/maintenance/',
                                server='192.168.1.15'):
    import smtplib  
    from email.message import EmailMessage

    import datetime, pytz
    tz 		    = pytz.timezone('Asia/Bangkok')
    today_tz 	=   datetime.datetime.now(tz=tz)

    import urllib.request  
    response = urllib.request.urlopen(url)  
    html = response.read().decode('utf-8')
    
    msg = EmailMessage()  
    msg['Subject'] = f'Equipment Availability Report : {today_tz.strftime("%d-%b-%Y %H:%M")}'  
    msg['From'] = send_email 
    msg['To'] = to_email 
    msg.set_content(html, subtype='html')  
    # ส่งอีเมล  
    with smtplib.SMTP(server) as server:  
        server.send_message(msg) 


class MachineListView(ListView):
    model = Machine
    paginate_by = 30
    def get_context_data(self, **kwargs):
        context = super(MachineListView, self).get_context_data(**kwargs)
        # Added Jan 31,2025 - to send start date of year
        import datetime, pytz
        tz 			= pytz.timezone('Asia/Bangkok')
        today_tz 	=   datetime.datetime.now(tz=tz)
        from datetime import datetime, time,timedelta
        today_tz_00 = datetime.combine(today_tz, time.min)
        start_date = (today_tz_00-timedelta(days=7)).strftime('%Y-%m-%d')
        context['start_date'] = start_date
        return context
    def get_queryset(self):
        query = self.request.GET.get('q')
        if query :
            return Machine.objects.filter(name__icontains=query)[:30]
        return Machine.objects.all()[:30]

class MachineDetailView(DetailView):
    model = Machine
    def get_context_data(self, **kwargs):
        context = super(MachineDetailView, self).get_context_data(**kwargs)
        # Added Jan 31,2025 - to send start date of year
        import datetime, pytz
        tz 			= pytz.timezone('Asia/Bangkok')
        today_tz 	=   datetime.datetime.now(tz=tz)
        from datetime import datetime, time
        today_tz_00 = datetime.combine(today_tz, time.min)
        start_date = today_tz_00.replace(month=1, day=1).strftime('%Y-%m-%d')
        context['start_date'] = start_date
        return context