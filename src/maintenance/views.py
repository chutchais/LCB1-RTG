from django.shortcuts import render, get_object_or_404

# Create your views here.
from django.views.decorators.cache import cache_page
from django.core.cache import cache
from .models import MachineType,Machine,Failure,Preventive
from django.views.generic import DetailView,CreateView,UpdateView,DeleteView,ListView
from django.db.models import Q,F
from django.http import JsonResponse
import pytz
from datetime import datetime, time, timedelta




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
        start_date = (today_tz_00-timedelta(days=14)).strftime('%Y-%m-%d')
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


# ---------------------------------------------------------------------------
# Helper utilities for report views
# ---------------------------------------------------------------------------

def _get_thai_tz():
    return pytz.timezone('Asia/Bangkok')


def _get_today_range():
    tz = _get_thai_tz()
    now = datetime.now(tz=tz)
    start = tz.localize(datetime.combine(now.date(), time.min))
    end   = tz.localize(datetime.combine(now.date(), time.max))
    return start, end


def _get_week_range():
    tz = _get_thai_tz()
    now = datetime.now(tz=tz)
    week_start_date = now.date() - timedelta(days=now.weekday())   # Monday
    start = tz.localize(datetime.combine(week_start_date, time.min))
    end   = tz.localize(datetime.combine(now.date(), time.max))
    return start, end


def _failures_to_summary(queryset):
    """
    Given a Failure queryset, return aggregated data dicts:
      - by_machine_type: [{machine_type, count, machines:[{name, count, top_category}]}]
      - by_category:     [{category, count}]
      - records:         list of serialised failure dicts
    """
    by_machine_type = {}
    by_category = {}
    records = []

    for f in queryset.select_related('machine', 'machine__machine_type', 'failure_category'):
        # Machine-type aggregation
        mt_name = f.machine.machine_type.name if (f.machine and f.machine.machine_type) else 'Unknown'
        m_name  = f.machine.name if f.machine else 'Unknown'
        cat0    = f.category_level_0 or 'Uncategorised'

        if mt_name not in by_machine_type:
            by_machine_type[mt_name] = {'machine_type': mt_name, 'count': 0, 'machines': {}}
        by_machine_type[mt_name]['count'] += 1

        machines_dict = by_machine_type[mt_name]['machines']
        if m_name not in machines_dict:
            machines_dict[m_name] = {'name': m_name, 'count': 0, 'top_category': cat0}
        machines_dict[m_name]['count'] += 1

        # Category aggregation
        by_category[cat0] = by_category.get(cat0, 0) + 1

        # Serialise the failure record
        records.append({
            'id':             f.pk,
            'machine':        m_name,
            'machine_type':   mt_name,
            'details':        f.details or '',
            'status':         f.status,
            'category':       f.category,
            'category_level_0': cat0,
            'category_level_1': f.category_level_1 or '',
            'start_date':     f.start_date.strftime('%Y-%m-%d %H:%M') if f.start_date else '',
            'end_date':       f.end_date.strftime('%Y-%m-%d %H:%M')   if f.end_date   else '',
            'repairing_time': f.repairing_time if (f.start_date and f.end_date) else None,
            'operation_shift': f.operation_shift or '',
        })

    # Convert machine_type dict → list with machines as list
    machine_type_list = []
    for mt in by_machine_type.values():
        mt_copy = dict(mt)
        mt_copy['machines'] = sorted(mt['machines'].values(), key=lambda x: -x['count'])
        machine_type_list.append(mt_copy)
    machine_type_list.sort(key=lambda x: -x['count'])

    category_list = [{'category': k, 'count': v} for k, v in sorted(by_category.items(), key=lambda x: -x[1])]

    return machine_type_list, category_list, records


# ---------------------------------------------------------------------------
# API endpoints
# ---------------------------------------------------------------------------

def api_report_today(request):
    """JSON: today's failure report."""
    tz = _get_thai_tz()
    now = datetime.now(tz=tz)

    # Optional filters
    machine_type_filter = request.GET.get('machine_type')
    shift_filter        = request.GET.get('shift')

    start, end = _get_today_range()
    qs = Failure.objects.filter(start_date__gte=start, start_date__lte=end)

    if machine_type_filter:
        qs = qs.filter(machine__machine_type__name=machine_type_filter)
    if shift_filter:
        qs = qs.filter(operation_shift=shift_filter)

    machine_type_list, category_list, records = _failures_to_summary(qs)

    return JsonResponse({
        'date':            now.strftime('%Y-%m-%d'),
        'total_failures':  len(records),
        'by_machine_type': machine_type_list,
        'by_category':     category_list,
        'records':         records,
    })


def api_report_week(request):
    """JSON: this week's failure report with daily trend."""
    tz = _get_thai_tz()
    now = datetime.now(tz=tz)

    machine_type_filter = request.GET.get('machine_type')
    shift_filter        = request.GET.get('shift')

    start, end = _get_week_range()
    qs = Failure.objects.filter(start_date__gte=start, start_date__lte=end)

    if machine_type_filter:
        qs = qs.filter(machine__machine_type__name=machine_type_filter)
    if shift_filter:
        qs = qs.filter(operation_shift=shift_filter)

    machine_type_list, category_list, records = _failures_to_summary(qs)

    # Daily trend
    daily_counts = {}
    for r in records:
        day = r['start_date'][:10] if r['start_date'] else 'Unknown'
        daily_counts[day] = daily_counts.get(day, 0) + 1

    daily_trend = [{'date': d, 'count': c} for d, c in sorted(daily_counts.items())]

    return JsonResponse({
        'week_start':      start.strftime('%Y-%m-%d'),
        'week_end':        end.strftime('%Y-%m-%d'),
        'total_failures':  len(records),
        'daily_trend':     daily_trend,
        'by_machine_type': machine_type_list,
        'by_category':     category_list,
        'records':         records,
    })


def api_report_machine(request, machine_name):
    """JSON: drilldown for a specific machine."""
    machine = get_object_or_404(Machine, name=machine_name)

    # Optional date-range filters
    date_from = request.GET.get('date_from')
    date_to   = request.GET.get('date_to')

    tz  = _get_thai_tz()
    qs  = Failure.objects.filter(machine=machine)

    if date_from:
        try:
            dt_from = tz.localize(datetime.strptime(date_from, '%Y-%m-%d'))
            qs = qs.filter(start_date__gte=dt_from)
        except ValueError:
            pass
    if date_to:
        try:
            dt_to = tz.localize(datetime.combine(datetime.strptime(date_to, '%Y-%m-%d').date(), time.max))
            qs = qs.filter(start_date__lte=dt_to)
        except ValueError:
            pass

    _, category_list, records = _failures_to_summary(qs)

    # Performance metrics
    closed = [r for r in records if r['status'] == 'CLOSED' and r['repairing_time'] is not None]
    total_failures     = len(records)
    closed_failures    = len(closed)
    mttr               = (sum(r['repairing_time'] for r in closed) / closed_failures) if closed_failures else 0

    return JsonResponse({
        'machine':         machine_name,
        'machine_type':    machine.machine_type.name if machine.machine_type else '',
        'total_failures':  total_failures,
        'by_category':     category_list,
        'metrics': {
            'mttr':             round(mttr, 1),
            'total_failures':   total_failures,
            'closed_failures':  closed_failures,
        },
        'records': records,
    })


def api_performance(request):
    """JSON: MTTR, MTBF, and availability metrics."""
    tz = _get_thai_tz()
    now = datetime.now(tz=tz)

    # Default: year-to-date
    year_start = tz.localize(datetime(now.year, 1, 1))
    date_from  = request.GET.get('date_from')
    date_to    = request.GET.get('date_to')
    machine_type_filter = request.GET.get('machine_type')

    start = year_start
    end   = now

    if date_from:
        try:
            start = tz.localize(datetime.strptime(date_from, '%Y-%m-%d'))
        except ValueError:
            pass
    if date_to:
        try:
            end = tz.localize(datetime.combine(datetime.strptime(date_to, '%Y-%m-%d').date(), time.max))
        except ValueError:
            pass

    period_minutes = max((end - start).total_seconds() / 60, 1)

    qs = Failure.objects.filter(start_date__gte=start, start_date__lte=end).select_related(
        'machine', 'machine__machine_type')

    if machine_type_filter:
        qs = qs.filter(machine__machine_type__name=machine_type_filter)

    # Aggregate per machine
    machine_data = {}
    for f in qs:
        m_name = f.machine.name if f.machine else 'Unknown'
        mt_name = f.machine.machine_type.name if (f.machine and f.machine.machine_type) else 'Unknown'

        if m_name not in machine_data:
            machine_data[m_name] = {
                'machine':      m_name,
                'machine_type': mt_name,
                'total':        0,
                'closed':       0,
                'repair_mins':  0,
            }
        machine_data[m_name]['total'] += 1
        if f.status == 'CLOSED' and f.start_date and f.end_date:
            machine_data[m_name]['closed'] += 1
            machine_data[m_name]['repair_mins'] += f.repairing_time or 0

    # Build per-machine metrics
    by_machine = []
    for d in machine_data.values():
        total        = d['total']
        repair_mins  = d['repair_mins']
        mttr         = round(repair_mins / d['closed'], 1) if d['closed'] else 0
        mtbf         = round((period_minutes - repair_mins) / total, 1) if total else 0
        availability = round((period_minutes - repair_mins) / period_minutes * 100, 1)
        by_machine.append({
            'machine':       d['machine'],
            'machine_type':  d['machine_type'],
            'total_failures': total,
            'closed_failures': d['closed'],
            'mttr':          mttr,
            'mtbf':          mtbf,
            'availability':  availability,
        })
    by_machine.sort(key=lambda x: (x['machine_type'], x['machine']))

    # Aggregate per machine type
    mt_data = {}
    for d in machine_data.values():
        mt = d['machine_type']
        if mt not in mt_data:
            mt_data[mt] = {'machine_type': mt, 'total': 0, 'closed': 0, 'repair_mins': 0, 'machines': 0}
        mt_data[mt]['total']       += d['total']
        mt_data[mt]['closed']      += d['closed']
        mt_data[mt]['repair_mins'] += d['repair_mins']
        mt_data[mt]['machines']    += 1

    by_machine_type = []
    for d in mt_data.values():
        mt_period = period_minutes * d['machines']
        repair_mins = d['repair_mins']
        mttr = round(repair_mins / d['closed'], 1) if d['closed'] else 0
        mtbf = round((mt_period - repair_mins) / d['total'], 1) if d['total'] else 0
        availability = round((mt_period - repair_mins) / mt_period * 100, 1) if mt_period else 100.0
        by_machine_type.append({
            'machine_type':   d['machine_type'],
            'total_failures': d['total'],
            'closed_failures': d['closed'],
            'mttr':           mttr,
            'mtbf':           mtbf,
            'availability':   availability,
        })
    by_machine_type.sort(key=lambda x: x['machine_type'])

    return JsonResponse({
        'period_start':    start.strftime('%Y-%m-%d'),
        'period_end':      end.strftime('%Y-%m-%d'),
        'by_machine_type': by_machine_type,
        'by_machine':      by_machine,
    })


# ---------------------------------------------------------------------------
# HTML report views
# ---------------------------------------------------------------------------

def report_today(request):
    tz = _get_thai_tz()
    now = datetime.now(tz=tz)
    machine_types = MachineType.objects.all().order_by('name')
    context = {
        'today':         now.strftime('%Y-%m-%d'),
        'machine_types': machine_types,
    }
    return render(request, 'maintenance/report_today.html', context)


def report_week(request):
    tz = _get_thai_tz()
    now = datetime.now(tz=tz)
    week_start = now.date() - timedelta(days=now.weekday())
    machine_types = MachineType.objects.all().order_by('name')
    context = {
        'today':         now.strftime('%Y-%m-%d'),
        'week_start':    week_start.strftime('%Y-%m-%d'),
        'machine_types': machine_types,
    }
    return render(request, 'maintenance/report_week.html', context)


def report_metrics(request):
    tz = _get_thai_tz()
    now = datetime.now(tz=tz)
    machine_types = MachineType.objects.all().order_by('name')
    year_start = datetime(now.year, 1, 1).strftime('%Y-%m-%d')
    context = {
        'today':         now.strftime('%Y-%m-%d'),
        'year_start':    year_start,
        'machine_types': machine_types,
    }
    return render(request, 'maintenance/report_metrics.html', context)


from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from .models import Machine

@require_http_methods(["GET"])
def api_search_machines(request):
    """Search machines by name across entire system"""
    search_text = request.GET.get('q', '').strip()
    
    if not search_text or len(search_text) < 2:
        return JsonResponse({'machines': []})
    
    # Search for machines containing the search text
    machines = Machine.objects.filter(
        name__icontains=search_text
    ).select_related('machine_type', 'machine_type__section').order_by('name').values(
        'name', 'machine_type__name', 'machine_type__section__name'
    )[:50]  # Limit to 50 results
    
    results = []
    for machine in machines:
        results.append({
            'name': machine['name'],
            'machine_type': machine['machine_type__name'] or 'Unknown',
            'section': machine['machine_type__section__name'] or 'Unknown'
        })
    
    return JsonResponse({'machines': results})