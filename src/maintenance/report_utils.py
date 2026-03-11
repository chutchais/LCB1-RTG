# Add these functions to the end of report_utils.py

# Added on Mar 6, 2026 -- Failure Analysis Report utilities
from datetime import datetime, timedelta, time
from django.utils import timezone
import pytz
from django.db.models import Count, Avg, Q, F, Sum, Case, When, DecimalField
from .models import Failure, Machine, MachineType, FailureCategory,Section

import logging

logger = logging.getLogger(__name__)

def get_timezone():
    """Get Bangkok timezone"""
    return pytz.timezone('Asia/Bangkok')

def get_today_start_end():
    """Get today's start and end datetime"""
    tz = get_timezone()
    today = datetime.now(tz=tz)
    today_start = datetime.combine(today.date(), time.min).replace(tzinfo=tz)
    today_end = datetime.combine(today.date(), time.max).replace(tzinfo=tz)
    return today_start, today_end

def get_week_start_end():
    """Get this week's start and end datetime"""
    tz = get_timezone()
    today = datetime.now(tz=tz).date()
    week_start = today - timedelta(days=today.weekday())
    week_end = week_start + timedelta(days=6)
    
    week_start_dt = datetime.combine(week_start, time.min).replace(tzinfo=tz)
    week_end_dt = datetime.combine(week_end, time.max).replace(tzinfo=tz)
    return week_start_dt, week_end_dt

def get_today_failures_by_type(machine_type=None):
    """Get today's failures grouped by machine type and category"""
    today_start, today_end = get_today_start_end()
    
    queryset = Failure.objects.filter(
        start_date__range=[today_start, today_end]
    ).select_related('machine', 'machine__machine_type', 'failure_category')
    
    if machine_type:
        queryset = queryset.filter(machine__machine_type__name=machine_type)
    
    result = {
        'report_date': today_start.strftime('%Y-%m-%d'),
        'machine_types': [],
        'total_failures': queryset.count(),
    }
    
    all_repair_times = []
    
    # Get all machine types from MachineType model
    machine_types_from_db = MachineType.objects.all().order_by('name')
    
    for mt in machine_types_from_db:
        mt_failures = list(queryset.filter(machine__machine_type=mt))
        
        if not mt_failures:
            continue
        
        mt_data = {
            'machine_type': mt.name,
            'total_failures': len(mt_failures),
            'by_category': [],
            'status_breakdown': {
                'OPEN': sum(1 for f in mt_failures if f.status == 'OPEN'),
                'CLOSED': sum(1 for f in mt_failures if f.status == 'CLOSED'),
            }
        }
        
        # Calculate repairing times for this machine type
        mt_repair_times = []
        for failure in mt_failures:
            try:
                repair_time = failure.repairing_time
                if repair_time:
                    mt_repair_times.append(repair_time)
                    all_repair_times.append(repair_time)
            except:
                pass
        
        # Group by category level 0
        category_dict = {}
        for failure in mt_failures:
            cat = failure.category_level_0 or 'Uncategorized'
            if cat not in category_dict:
                category_dict[cat] = {'failures': [], 'machines': {}}
            category_dict[cat]['failures'].append(failure)
            
            machine_name = failure.machine.name
            if machine_name not in category_dict[cat]['machines']:
                category_dict[cat]['machines'][machine_name] = 0
            category_dict[cat]['machines'][machine_name] += 1
        
        # Build category data
        for cat_name in sorted(category_dict.keys(), key=lambda x: len(category_dict[x]['failures']), reverse=True):
            cat_data = category_dict[cat_name]
            cat_failures = cat_data['failures']
            cat_count = len(cat_failures)
            cat_pct = (cat_count / len(mt_failures) * 100) if len(mt_failures) > 0 else 0
            
            machines_data = []
            for machine_name, count in sorted(cat_data['machines'].items(), key=lambda x: x[1], reverse=True):
                machines_data.append({
                    'name': machine_name,
                    'count': count,
                    'url': f"/maintenance/reports/machine/{machine_name}/"
                })
            
            mt_data['by_category'].append({
                'category_level_0': cat_name,
                'count': cat_count,
                'percentage': round(cat_pct, 2),
                'machines': machines_data
            })
        
        result['machine_types'].append(mt_data)
    
    # Calculate avg repairing time
    if all_repair_times:
        avg_repair = sum(all_repair_times) / len(all_repair_times)
        result['avg_repairing_time_minutes'] = avg_repair
        result['avg_repairing_time_hours'] = round(avg_repair / 60, 2)
    else:
        result['avg_repairing_time_minutes'] = 0
        result['avg_repairing_time_hours'] = 0
    
    return result

def get_week_failures_by_type(machine_type=None):
    """Get this week's failures with daily breakdown"""
    week_start, week_end = get_week_start_end()
    
    queryset = Failure.objects.filter(
        start_date__range=[week_start, week_end]
    ).select_related('machine', 'machine__machine_type', 'failure_category')
    
    if machine_type:
        queryset = queryset.filter(machine__machine_type__name=machine_type)
    
    all_failures = list(queryset)
    
    # Get daily breakdown
    daily_data = []
    current_date = week_start.date()
    
    while current_date <= week_end.date():
        day_start = datetime.combine(current_date, time.min).replace(tzinfo=get_timezone())
        day_end = datetime.combine(current_date, time.max).replace(tzinfo=get_timezone())
        
        day_failures = [f for f in all_failures if day_start <= f.start_date <= day_end]
        
        # Build category breakdown
        category_dict = {}
        for failure in day_failures:
            cat = failure.category_level_0 or 'Uncategorized'
            if cat not in category_dict:
                category_dict[cat] = 0
            category_dict[cat] += 1
        
        # Build machine type breakdown
        machine_type_dict = {}
        for failure in day_failures:
            mt = failure.machine.machine_type.name if failure.machine.machine_type else 'Unknown'
            if mt not in machine_type_dict:
                machine_type_dict[mt] = 0
            machine_type_dict[mt] += 1
        
        daily_data.append({
            'date': current_date.strftime('%Y-%m-%d'),
            'day_name': current_date.strftime('%A'),
            'total_failures': len(day_failures),
            'by_category': [{'category_level_0': k, 'count': v} for k, v in sorted(category_dict.items(), key=lambda x: x[1], reverse=True)],
            'by_shift': {
                'Day': sum(1 for f in day_failures if f.operation_shift == 'Day'),
                'Night': sum(1 for f in day_failures if f.operation_shift == 'Night'),
            },
            'by_machine_type': [{'machine__machine_type__name': k, 'count': v} for k, v in sorted(machine_type_dict.items(), key=lambda x: x[1], reverse=True)]
        })
        
        current_date += timedelta(days=1)
    
    # Cumulative stats - build category breakdown
    category_dict = {}
    machine_type_dict = {}
    repair_times = []
    
    for failure in all_failures:
        cat = failure.category_level_0 or 'Uncategorized'
        if cat not in category_dict:
            category_dict[cat] = 0
        category_dict[cat] += 1
        
        mt = failure.machine.machine_type.name if failure.machine.machine_type else 'Unknown'
        if mt not in machine_type_dict:
            machine_type_dict[mt] = 0
        machine_type_dict[mt] += 1
        
        try:
            rt = failure.repairing_time
            if rt:
                repair_times.append(rt)
        except:
            pass
    
    avg_mttr = sum(repair_times) / len(repair_times) / 60 if repair_times else 0
    
    cumulative = {
        'total_failures': len(all_failures),
        'by_category': [{'category_level_0': k, 'count': v} for k, v in sorted(category_dict.items(), key=lambda x: x[1], reverse=True)],
        'by_machine_type': [{'machine__machine_type__name': k, 'count': v} for k, v in sorted(machine_type_dict.items(), key=lambda x: x[1], reverse=True)],
        'by_shift': {
            'Day': sum(1 for f in all_failures if f.operation_shift == 'Day'),
            'Night': sum(1 for f in all_failures if f.operation_shift == 'Night'),
        },
        'avg_mttr_hours': round(avg_mttr, 2)
    }
    
    return {
        'period_start': week_start.strftime('%Y-%m-%d'),
        'period_end': week_end.strftime('%Y-%m-%d'),
        'daily_data': daily_data,
        'cumulative': cumulative
    }

def get_machine_performance_metrics(machine_type=None):
    """Get MTTR, MTBF, Availability metrics"""
    
    queryset = Failure.objects.filter(status='CLOSED').select_related(
        'machine', 'machine__machine_type'
    )
    
    if machine_type:
        queryset = queryset.filter(machine__machine_type__name=machine_type)
    
    all_failures = list(queryset)
    
    result = {
        'report_date': datetime.now(tz=get_timezone()).strftime('%Y-%m-%d'),
        'by_machine_type': []
    }
    
    # Get all machine types from MachineType model
    machine_types_from_db = MachineType.objects.all().order_by('name')
    
    for mt in machine_types_from_db:
        mt_failures = [f for f in all_failures if f.machine.machine_type == mt]
        
        if not mt_failures:
            continue
        
        # MTTR Calculation
        repair_times = []
        for failure in mt_failures:
            try:
                rt = failure.repairing_time
                if rt:
                    repair_times.append(rt)
            except:
                pass
        
        mttr_minutes = sum(repair_times) / len(repair_times) if repair_times else 0
        mttr_hours = mttr_minutes / 60
        
        # MTBF Calculation (simplified - based on engine hours)
        total_hours = 0
        machines = Machine.objects.filter(machine_type=mt)
        for machine in machines:
            try:
                engine_hour = float(machine.engine_hour or 0)
                total_hours += engine_hour
            except:
                pass
        
        mtbf_hours = total_hours / len(mt_failures) if len(mt_failures) > 0 else 0
        
        # Availability Calculation
        total_machines = machines.count()
        on_repair = sum([m.on_repair for m in machines])
        available = total_machines - on_repair
        availability_pct = (available / total_machines * 100) if total_machines > 0 else 0
        
        # On-time closure rate
        closed_on_time = sum(1 for f in mt_failures if f.expect_date and f.end_date and f.end_date <= f.expect_date)
        on_time_rate = (closed_on_time / len(mt_failures) * 100) if len(mt_failures) > 0 else 0
        
        # Machine-level metrics
        machines_data = []
        for machine in machines:
            machine_failures = [f for f in mt_failures if f.machine == machine]
            
            machine_repair_times = []
            for failure in machine_failures:
                try:
                    rt = failure.repairing_time
                    if rt:
                        machine_repair_times.append(rt)
                except:
                    pass
            
            machine_mttr = sum(machine_repair_times) / len(machine_repair_times) if machine_repair_times else 0
            
            machines_data.append({
                'name': machine.name,
                'mttr_hours': round(machine_mttr / 60, 2),
                'failures_count': len(machine_failures),
                'availability': 'Available' if not machine.on_repair else 'On Repair'
            })
        
        result['by_machine_type'].append({
            'machine_type': mt.name,
            'metrics': {
                'mttr_hours': round(mttr_hours, 2),
                'mtbf_hours': round(mtbf_hours, 2),
                'availability_percentage': round(availability_pct, 2),
                'on_time_closure_rate': round(on_time_rate, 2),
                'total_failures': len(mt_failures),
                'machines': machines_data
            }
        })
    
    return result

def get_machine_failure_history(machine_name, days=30):
    """Get detailed failure history for a specific machine"""
    
    try:
        machine = Machine.objects.get(name=machine_name)
    except Machine.DoesNotExist:
        return None
    
    tz = get_timezone()
    start_date = datetime.now(tz=tz) - timedelta(days=days)
    
    failures = list(machine.failures.filter(
        start_date__gte=start_date
    ).select_related('user').order_by('-start_date'))
    
    # Calculate metrics
    closed_failures = [f for f in failures if f.status == 'CLOSED']
    
    repair_times = []
    for failure in closed_failures:
        try:
            rt = failure.repairing_time
            if rt:
                repair_times.append(rt)
        except:
            pass
    
    mttr = sum(repair_times) / len(repair_times) if repair_times else 0
    
    # Count by category
    category_dict = {}
    for failure in failures:
        cat = failure.category_level_0 or 'Uncategorized'
        if cat not in category_dict:
            category_dict[cat] = 0
        category_dict[cat] += 1
    
    category_breakdown = sorted([{'category_level_0': k, 'count': v} for k, v in category_dict.items()], 
                                 key=lambda x: x['count'], reverse=True)
    
    # Prepare failure history
    failure_history = []
    for f in failures[:50]:  # Last 50 failures
        try:
            repairing_time = f.repairing_time or 0
            lead_time = f.lead_time or 0
            waiting_time = f.waitting_time or 0
        except:
            repairing_time = 0
            lead_time = 0
            waiting_time = 0
        
        failure_history.append({
            'id': f.id,
            'category': f.category_level_0 or 'Uncategorized',
            'full_path': f.category_full_path or '',
            'start_date': f.start_date.strftime('%Y-%m-%d %H:%M') if f.start_date else '',
            'end_date': f.end_date.strftime('%Y-%m-%d %H:%M') if f.end_date else '',
            'repairing_time_hours': round(repairing_time / 60, 2),
            'lead_time_hours': round(lead_time / 60, 2),
            'waiting_time_hours': round(waiting_time / 60, 2),
            'status': f.status,
            'details': f.details or '',
            'rootcause': f.rootcause or '',
            'repair_action': f.repair_action or '',
            'technician': f.user.username if f.user else 'N/A'
        })
    
    return {
        'machine_name': machine_name,
        'machine_type': machine.machine_type.name if machine.machine_type else 'N/A',
        'performance_metrics': {
            'mttr_hours': round(mttr / 60, 2),
            'total_failures_in_period': len(failures),
            'failures_this_week': sum(1 for f in failures if f.start_date >= datetime.now(tz=tz) - timedelta(days=7)),
            'status_breakdown': {
                'OPEN': sum(1 for f in failures if f.status == 'OPEN'),
                'CLOSED': sum(1 for f in failures if f.status == 'CLOSED'),
            }
        },
        'category_breakdown': category_breakdown,
        'recent_failures': failure_history
    }

def get_all_machine_types():
    """Get all machine types for dropdown filters"""
    return MachineType.objects.all().order_by('name').values_list('name', flat=True)

def get_failures_by_date_range(start_date_str, end_date_str, machine_type=None):
    """Get failures for a custom date range"""
    from datetime import datetime
    
    tz = get_timezone()
    
    # Parse dates
    start_date = datetime.strptime(start_date_str, '%Y-%m-%d').replace(hour=0, minute=0, second=0, tzinfo=tz)
    end_date = datetime.strptime(end_date_str, '%Y-%m-%d').replace(hour=23, minute=59, second=59, tzinfo=tz)
    
    queryset = Failure.objects.filter(
        start_date__range=[start_date, end_date]
    ).select_related('machine', 'machine__machine_type', 'failure_category')
    
    if machine_type:
        queryset = queryset.filter(machine__machine_type__name=machine_type)
    
    result = {
        'report_start': start_date_str,
        'report_end': end_date_str,
        'machine_types': [],
        'total_failures': queryset.count(),
    }
    
    all_repair_times = []
    
    # Get all machine types from MachineType model
    machine_types_from_db = MachineType.objects.all().order_by('name')
    
    for mt in machine_types_from_db:
        mt_failures = list(queryset.filter(machine__machine_type=mt))
        
        if not mt_failures:
            continue
        
        mt_data = {
            'machine_type': mt.name,
            'total_failures': len(mt_failures),
            'by_category': [],
            'status_breakdown': {
                'OPEN': sum(1 for f in mt_failures if f.status == 'OPEN'),
                'CLOSED': sum(1 for f in mt_failures if f.status == 'CLOSED'),
            }
        }
        
        # Calculate repairing times for this machine type
        mt_repair_times = []
        for failure in mt_failures:
            try:
                repair_time = failure.repairing_time
                if repair_time:
                    mt_repair_times.append(repair_time)
                    all_repair_times.append(repair_time)
            except:
                pass
        
        # Group by category level 0
        category_dict = {}
        for failure in mt_failures:
            cat = failure.category_level_0 or 'Uncategorized'
            if cat not in category_dict:
                category_dict[cat] = {'failures': [], 'machines': {}}
            category_dict[cat]['failures'].append(failure)
            
            machine_name = failure.machine.name
            if machine_name not in category_dict[cat]['machines']:
                category_dict[cat]['machines'][machine_name] = 0
            category_dict[cat]['machines'][machine_name] += 1
        
        # Build category data
        for cat_name in sorted(category_dict.keys(), key=lambda x: len(category_dict[x]['failures']), reverse=True):
            cat_data = category_dict[cat_name]
            cat_failures = cat_data['failures']
            cat_count = len(cat_failures)
            cat_pct = (cat_count / len(mt_failures) * 100) if len(mt_failures) > 0 else 0
            
            machines_data = []
            for machine_name, count in sorted(cat_data['machines'].items(), key=lambda x: x[1], reverse=True):
                machines_data.append({
                    'name': machine_name,
                    'count': count,
                    'url': f"/maintenance/reports/machine/{machine_name}/"
                })
            
            mt_data['by_category'].append({
                'category_level_0': cat_name,
                'count': cat_count,
                'percentage': round(cat_pct, 2),
                'machines': machines_data,
                'failures': cat_failures  # Include for API
            })
        
        result['machine_types'].append(mt_data)
    
    # Calculate avg repairing time
    if all_repair_times:
        avg_repair = sum(all_repair_times) / len(all_repair_times)
        result['avg_repairing_time_minutes'] = avg_repair
        result['avg_repairing_time_hours'] = round(avg_repair / 60, 2)
    else:
        result['avg_repairing_time_minutes'] = 0
        result['avg_repairing_time_hours'] = 0
    
    return result


def get_performance_metrics_by_date_range(start_date_str, end_date_str, machine_type=None):
    """Get performance metrics for a custom date range"""
    from datetime import datetime
    
    tz = get_timezone()
    
    # Parse dates
    start_date = datetime.strptime(start_date_str, '%Y-%m-%d').replace(hour=0, minute=0, second=0, tzinfo=tz)
    end_date = datetime.strptime(end_date_str, '%Y-%m-%d').replace(hour=23, minute=59, second=59, tzinfo=tz)
    
    queryset = Failure.objects.filter(
        status='CLOSED',
        start_date__range=[start_date, end_date]
    ).select_related('machine', 'machine__machine_type')
    
    if machine_type:
        queryset = queryset.filter(machine__machine_type__name=machine_type)
    
    all_failures = list(queryset)
    
    result = {
        'report_start': start_date_str,
        'report_end': end_date_str,
        'by_machine_type': []
    }
    
    # Get all machine types from MachineType model
    machine_types_from_db = MachineType.objects.all().order_by('name')
    
    for mt in machine_types_from_db:
        mt_failures = [f for f in all_failures if f.machine.machine_type == mt]
        
        if not mt_failures:
            continue
        
        # MTTR Calculation
        repair_times = []
        for failure in mt_failures:
            try:
                rt = failure.repairing_time
                if rt:
                    repair_times.append(rt)
            except:
                pass
        
        mttr_minutes = sum(repair_times) / len(repair_times) if repair_times else 0
        mttr_hours = mttr_minutes / 60
        
        # MTBF Calculation (simplified - based on engine hours)
        total_hours = 0
        machines = Machine.objects.filter(machine_type=mt)
        for machine in machines:
            try:
                engine_hour = float(machine.engine_hour or 0)
                total_hours += engine_hour
            except:
                pass
        
        mtbf_hours = total_hours / len(mt_failures) if len(mt_failures) > 0 else 0
        
        # Availability Calculation
        total_machines = machines.count()
        on_repair = sum([m.on_repair for m in machines])
        available = total_machines - on_repair
        availability_pct = (available / total_machines * 100) if total_machines > 0 else 0
        
        # On-time closure rate
        closed_on_time = sum(1 for f in mt_failures if f.expect_date and f.end_date and f.end_date <= f.expect_date)
        on_time_rate = (closed_on_time / len(mt_failures) * 100) if len(mt_failures) > 0 else 0
        
        # Machine-level metrics
        machines_data = []
        for machine in machines:
            machine_failures = [f for f in mt_failures if f.machine == machine]
            
            machine_repair_times = []
            for failure in machine_failures:
                try:
                    rt = failure.repairing_time
                    if rt:
                        machine_repair_times.append(rt)
                except:
                    pass
            
            machine_mttr = sum(machine_repair_times) / len(machine_repair_times) if machine_repair_times else 0
            
            machines_data.append({
                'name': machine.name,
                'mttr_hours': round(machine_mttr / 60, 2),
                'failures_count': len(machine_failures),
                'availability': 'Available' if not machine.on_repair else 'On Repair'
            })
        
        result['by_machine_type'].append({
            'machine_type': mt.name,
            'metrics': {
                'mttr_hours': round(mttr_hours, 2),
                'mtbf_hours': round(mtbf_hours, 2),
                'availability_percentage': round(availability_pct, 2),
                'on_time_closure_rate': round(on_time_rate, 2),
                'total_failures': len(mt_failures),
                'machines': machines_data
            }
        })
    
    return result

# Add this function to get detailed failures for a specific date

def get_failures_by_date_and_shift(date_str, shift=None):
    """Get detailed failures for a specific date and optional shift"""
    from datetime import datetime, time
    
    tz = get_timezone()
    
    # Parse date
    date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
    date_start = datetime.combine(date_obj, time.min).replace(tzinfo=tz)
    date_end = datetime.combine(date_obj, time.max).replace(tzinfo=tz)
    
    queryset = Failure.objects.filter(
        start_date__range=[date_start, date_end]
    ).select_related('machine', 'machine__machine_type', 'failure_category', 'user').order_by('-start_date')
    
    if shift and shift != 'all':
        queryset = queryset.filter(operation_shift=shift)
    
    failures = list(queryset)
    
    result = {
        'date': date_str,
        'shift': shift or 'all',
        'total_count': len(failures),
        'failures': []
    }
    
    for failure in failures:
        try:
            repairing_time = failure.repairing_time or 0
        except:
            repairing_time = 0
        
        result['failures'].append({
            'id': failure.id,
            'machine_name': failure.machine.name if failure.machine else 'Unknown',
            'machine_type': failure.machine.machine_type.name if failure.machine and failure.machine.machine_type else 'Unknown',  # ADD THIS LINE
            'details': failure.details or '-',
            'category_level_0': failure.category_level_0 or 'Uncategorized',
            'failure_category': failure.category_level_1 or '-',
            'status': failure.status,
            'start_date': failure.start_date.strftime('%Y-%m-%d %H:%M') if failure.start_date else '',
            'repairing_time_hours': round(repairing_time / 60, 2),
            'user': failure.user.username if failure.user else 'N/A'
        })
    
    return result

def get_failures_by_date_shift_and_type(date_str, shift=None, machine_type=None):
    """Get detailed failures for a specific date, shift, and machine type"""
    from datetime import datetime, time
    
    tz = get_timezone()
    
    # Parse date
    date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
    date_start = datetime.combine(date_obj, time.min).replace(tzinfo=tz)
    date_end = datetime.combine(date_obj, time.max).replace(tzinfo=tz)
    
    queryset = Failure.objects.filter(
        start_date__range=[date_start, date_end]
    ).select_related('machine', 'machine__machine_type', 'failure_category', 'user').order_by('-start_date')
    
    if shift and shift != 'all':
        queryset = queryset.filter(operation_shift=shift)
    
    if machine_type:
        queryset = queryset.filter(machine__machine_type__name=machine_type)
    
    failures = list(queryset)
    
    result = {
        'date': date_str,
        'shift': shift or 'all',
        'machine_type': machine_type or 'all',
        'total_count': len(failures),
        'failures': []
    }
    
    for failure in failures:
        try:
            repairing_time = failure.repairing_time or 0
        except:
            repairing_time = 0
        
        result['failures'].append({
            'id': failure.id,
            'machine_name': failure.machine.name if failure.machine else 'Unknown',
            'machine_type': failure.machine.machine_type.name if failure.machine and failure.machine.machine_type else 'Unknown',
            'details': failure.details or '-',
            'category_level_0': failure.category_level_0 or 'Uncategorized',
            'failure_category': failure.category_level_1 or '-',
            'status': failure.status,
            'start_date': failure.start_date.strftime('%Y-%m-%d %H:%M') if failure.start_date else '',
            'repairing_time_hours': round(repairing_time / 60, 2),
            'user': failure.user.username if failure.user else 'N/A'
        })
    
    return result

# Add this new function to get sections

def get_all_sections():
    """Get all sections"""
    return Section.objects.all().order_by('name').values_list('name', flat=True)

def get_machine_types_by_section(section_name):
    """Get all machine types in a section"""
    try:
        section = Section.objects.get(name=section_name)
        return section.ma_machine_types.all().order_by('name')
    except Section.DoesNotExist:
        return MachineType.objects.none()

# Modify the existing functions to filter by section

def get_today_failures_by_section(section_name):
    """Get today's failures grouped by section and machine type"""
    today_start, today_end = get_today_start_end()
    
    queryset = Failure.objects.filter(
        start_date__range=[today_start, today_end],
        machine__machine_type__section__name=section_name
    ).select_related('machine', 'machine__machine_type', 'failure_category')
    
    result = {
        'report_date': today_start.strftime('%Y-%m-%d'),
        'section': section_name,
        'machine_types': [],
        'total_failures': queryset.count(),
    }
    
    all_repair_times = []
    
    # Get machine types in this section
    section_obj = Section.objects.get(name=section_name)
    machine_types_in_section = section_obj.ma_machine_types.all().order_by('name')
    
    for mt in machine_types_in_section:
        mt_failures = list(queryset.filter(machine__machine_type=mt))
        
        if not mt_failures:
            continue
        
        mt_data = {
            'machine_type': mt.name,
            'total_failures': len(mt_failures),
            'by_category': [],
            'status_breakdown': {
                'OPEN': sum(1 for f in mt_failures if f.status == 'OPEN'),
                'CLOSED': sum(1 for f in mt_failures if f.status == 'CLOSED'),
            }
        }
        
        # Calculate repairing times for this machine type
        for failure in mt_failures:
            try:
                repair_time = failure.repairing_time
                if repair_time:
                    all_repair_times.append(repair_time)
            except:
                pass
        
        # Group by category level 0
        category_dict = {}
        for failure in mt_failures:
            cat = failure.category_level_0 or 'Uncategorized'
            if cat not in category_dict:
                category_dict[cat] = {'failures': [], 'machines': {}}
            category_dict[cat]['failures'].append(failure)
            
            machine_name = failure.machine.name
            if machine_name not in category_dict[cat]['machines']:
                category_dict[cat]['machines'][machine_name] = 0
            category_dict[cat]['machines'][machine_name] += 1
        
        # Build category data
        for cat_name in sorted(category_dict.keys(), key=lambda x: len(category_dict[x]['failures']), reverse=True):
            cat_data = category_dict[cat_name]
            cat_failures = cat_data['failures']
            cat_count = len(cat_failures)
            cat_pct = (cat_count / len(mt_failures) * 100) if len(mt_failures) > 0 else 0
            
            machines_data = []
            for machine_name, count in sorted(cat_data['machines'].items(), key=lambda x: x[1], reverse=True):
                machines_data.append({
                    'name': machine_name,
                    'count': count,
                    'url': f"/maintenance/reports/machine/{machine_name}/"
                })
            
            mt_data['by_category'].append({
                'category_level_0': cat_name,
                'count': cat_count,
                'percentage': round(cat_pct, 2),
                'machines': machines_data
            })
        
        result['machine_types'].append(mt_data)
    
    # Calculate avg repairing time
    if all_repair_times:
        avg_repair = sum(all_repair_times) / len(all_repair_times)
        result['avg_repairing_time_minutes'] = avg_repair
        result['avg_repairing_time_hours'] = round(avg_repair / 60, 2)
    else:
        result['avg_repairing_time_minutes'] = 0
        result['avg_repairing_time_hours'] = 0
    
    return result

def get_week_failures_by_section(section_name):
    """Get this week's failures for a specific section"""
    from datetime import datetime, time, timedelta
    from collections import defaultdict
    
    week_start, week_end = get_week_start_end()
    
    queryset = Failure.objects.filter(
        start_date__range=[week_start, week_end],
        machine__machine_type__section__name=section_name
    ).select_related('machine', 'machine__machine_type', 'failure_category', 'user').order_by('machine__name', 'start_date')
    
    all_failures = list(queryset)
    
    # Get all machine types in this section for consistent series
    section_obj = Section.objects.get(name=section_name)
    machine_types_in_section = section_obj.ma_machine_types.all().order_by('name')
    machine_type_names = [mt.name for mt in machine_types_in_section]
    
    # Build daily_data as dict for charts
    daily_data_dict = {}
    daily_details = []
    current_date = week_start.date()
    
    while current_date <= week_end.date():
        day_start = datetime.combine(current_date, time.min).replace(tzinfo=get_timezone())
        day_end = datetime.combine(current_date, time.max).replace(tzinfo=get_timezone())
        
        day_failures = [f for f in all_failures if day_start <= f.start_date <= day_end]
        
        # Build machine type breakdown for this day
        machine_type_dict = {}
        for mt_name in machine_type_names:
            machine_type_dict[mt_name] = 0
        
        for failure in day_failures:
            mt = failure.machine.machine_type.name if failure.machine.machine_type else 'Unknown'
            if mt in machine_type_dict:
                machine_type_dict[mt] += 1
        
        daily_data_dict[current_date.strftime('%Y-%m-%d')] = machine_type_dict
        
        # Build category breakdown
        category_dict = {}
        for failure in day_failures:
            cat = failure.category_level_0 or 'Uncategorized'
            if cat not in category_dict:
                category_dict[cat] = 0
            category_dict[cat] += 1
        
        daily_details.append({
            'date': current_date.strftime('%Y-%m-%d'),
            'day_name': current_date.strftime('%A'),
            'total_failures': len(day_failures),
            'by_category': [{'category_level_0': k, 'count': v} for k, v in sorted(category_dict.items(), key=lambda x: x[1], reverse=True)],
            'by_shift': {
                'Day': sum(1 for f in day_failures if hasattr(f, 'operation_shift') and f.operation_shift == 'Day'),
                'Night': sum(1 for f in day_failures if hasattr(f, 'operation_shift') and f.operation_shift == 'Night'),
            },
            'by_machine_type': machine_type_dict
        })
        
        current_date += timedelta(days=1)
    
    # Build pareto data
    pareto_data = {}
    for mt_name in machine_type_names:
        mt_failures = [f for f in all_failures if f.machine and f.machine.machine_type and f.machine.machine_type.name == mt_name]
        
        # Count by category
        category_counts = defaultdict(int)
        for failure in mt_failures:
            category = failure.category_level_0 or 'Uncategorized'
            category_counts[category] += 1
        
        # Sort and calculate cumulative
        sorted_categories = sorted(category_counts.items(), key=lambda x: x[1], reverse=True)
        total_count = sum(count for _, count in sorted_categories)
        
        pareto_list = []
        cumulative = 0
        for category, count in sorted_categories:
            cumulative += count
            cumulative_pct = (cumulative / total_count * 100) if total_count > 0 else 0
            pareto_list.append({
                'category': category,
                'count': count,
                'cumulative_percentage': cumulative_pct
            })
        
        pareto_data[mt_name] = pareto_list
    
    # Build failures list
    failures_list = []
    for failure in all_failures:
        try:
            repairing_time = failure.repairing_time or 0
        except:
            repairing_time = 0
        
        # failures_list.append({
        #     'id': failure.id,
        #     'machine_name': failure.machine.name if failure.machine else 'Unknown',
        #     'details': failure.details or '',
        #     'category_level_0': failure.category_level_0 or 'Uncategorized',
        #     'failure_category': failure.category_level_1 or '',
        #     'status': failure.status,
        #     'rootcause': failure.rootcause or '',
        #     'repair_action': failure.repair_action or '',
        #     'start_date': failure.start_date.strftime('%Y-%m-%d %H:%M') if failure.start_date else '',
        #     'repairing_time_hours': round(repairing_time / 60, 2) if repairing_time else 0,
        # })
        # In the function that builds failure_list, add machine_type
        failures_list.append({
            'id': failure.id,
            'machine_name': failure.machine.name if failure.machine else 'Unknown',
            'machine_type': failure.machine.machine_type.name if failure.machine and failure.machine.machine_type else 'Unknown',  # ADD THIS LINE
            'details': failure.details or '',
            'category_level_0': failure.category_level_0 or 'Uncategorized',
            'failure_category': failure.category_level_1 or '',
            'status': failure.status,
            'rootcause': failure.rootcause or '',
            'repair_action': failure.repair_action or '',
            'start_date': failure.start_date.strftime('%Y-%m-%d %H:%M') if failure.start_date else '',
            'repairing_time_hours': round(repairing_time / 60, 2) if repairing_time else 0,
        })
    
    # Cumulative stats
    category_dict = {}
    machine_type_dict = {}
    repair_times = []
    
    for mt_name in machine_type_names:
        machine_type_dict[mt_name] = 0
    
    for failure in all_failures:
        cat = failure.category_level_0 or 'Uncategorized'
        if cat not in category_dict:
            category_dict[cat] = 0
        category_dict[cat] += 1
        
        mt = failure.machine.machine_type.name if failure.machine.machine_type else 'Unknown'
        if mt in machine_type_dict:
            machine_type_dict[mt] += 1
        
        try:
            rt = failure.repairing_time
            if rt:
                repair_times.append(rt)
        except:
            pass
    
    avg_mttr = sum(repair_times) / len(repair_times) / 60 if repair_times else 0
    
    cumulative = {
        'total_failures': len(all_failures),
        'by_category': [{'category_level_0': k, 'count': v} for k, v in sorted(category_dict.items(), key=lambda x: x[1], reverse=True)],
        'by_machine_type': machine_type_dict,
        'machine_type_names': machine_type_names,
        'by_shift': {
            'Day': sum(1 for f in all_failures if hasattr(f, 'operation_shift') and f.operation_shift == 'Day'),
            'Night': sum(1 for f in all_failures if hasattr(f, 'operation_shift') and f.operation_shift == 'Night'),
        },
        'avg_mttr_hours': round(avg_mttr, 2)
    }
    
    
    return {
        'period_start': week_start.strftime('%Y-%m-%d'),
        'period_end': week_end.strftime('%Y-%m-%d'),
        'section': section_name,
        'total_failures': len(all_failures),
        'avg_mttr_hours': round(avg_mttr, 2),
        'daily_data': daily_data_dict,  # Dict for chart
        'daily_details': daily_details,  # Old format for compatibility
        'machine_type_names': machine_type_names,
        'pareto_data': pareto_data,
        'failures': failures_list,
        'cumulative': cumulative
    }
# def get_week_failures_by_section(section_name):
#     """Get this week's failures for a specific section"""
#     week_start, week_end = get_week_start_end()
    
#     queryset = Failure.objects.filter(
#         start_date__range=[week_start, week_end],
#         machine__machine_type__section__name=section_name
#     ).select_related('machine', 'machine__machine_type', 'failure_category')
    
#     all_failures = list(queryset)
    
#     # Get all machine types in this section for consistent series
#     section_obj = Section.objects.get(name=section_name)
#     machine_types_in_section = section_obj.ma_machine_types.all().order_by('name')
#     machine_type_names = [mt.name for mt in machine_types_in_section]
    
#     # Get daily breakdown
#     daily_data = []
#     current_date = week_start.date()
    
#     while current_date <= week_end.date():
#         day_start = datetime.combine(current_date, time.min).replace(tzinfo=get_timezone())
#         day_end = datetime.combine(current_date, time.max).replace(tzinfo=get_timezone())
        
#         day_failures = [f for f in all_failures if day_start <= f.start_date <= day_end]
        
#         # Build machine type breakdown for this day
#         machine_type_dict = {}
#         for mt_name in machine_type_names:
#             machine_type_dict[mt_name] = 0
        
#         for failure in day_failures:
#             mt = failure.machine.machine_type.name if failure.machine.machine_type else 'Unknown'
#             if mt in machine_type_dict:
#                 machine_type_dict[mt] += 1
        
#         # Build category breakdown
#         category_dict = {}
#         for failure in day_failures:
#             cat = failure.category_level_0 or 'Uncategorized'
#             if cat not in category_dict:
#                 category_dict[cat] = 0
#             category_dict[cat] += 1
        
#         daily_data.append({
#             'date': current_date.strftime('%Y-%m-%d'),
#             'day_name': current_date.strftime('%A'),
#             'total_failures': len(day_failures),
#             'by_category': [{'category_level_0': k, 'count': v} for k, v in sorted(category_dict.items(), key=lambda x: x[1], reverse=True)],
#             'by_shift': {
#                 'Day': sum(1 for f in day_failures if f.operation_shift == 'Day'),
#                 'Night': sum(1 for f in day_failures if f.operation_shift == 'Night'),
#             },
#             'by_machine_type': machine_type_dict  # Changed from list to dict
#         })
        
#         current_date += timedelta(days=1)
    
#     # Cumulative stats
#     category_dict = {}
#     machine_type_dict = {}
#     repair_times = []
    
#     for mt_name in machine_type_names:
#         machine_type_dict[mt_name] = 0
    
#     for failure in all_failures:
#         cat = failure.category_level_0 or 'Uncategorized'
#         if cat not in category_dict:
#             category_dict[cat] = 0
#         category_dict[cat] += 1
        
#         mt = failure.machine.machine_type.name if failure.machine.machine_type else 'Unknown'
#         if mt in machine_type_dict:
#             machine_type_dict[mt] += 1
        
#         try:
#             rt = failure.repairing_time
#             if rt:
#                 repair_times.append(rt)
#         except:
#             pass
    
#     avg_mttr = sum(repair_times) / len(repair_times) / 60 if repair_times else 0
    
#     cumulative = {
#         'total_failures': len(all_failures),
#         'by_category': [{'category_level_0': k, 'count': v} for k, v in sorted(category_dict.items(), key=lambda x: x[1], reverse=True)],
#         'by_machine_type': machine_type_dict,
#         'machine_type_names': machine_type_names,  # Add this for frontend
#         'by_shift': {
#             'Day': sum(1 for f in all_failures if f.operation_shift == 'Day'),
#             'Night': sum(1 for f in all_failures if f.operation_shift == 'Night'),
#         },
#         'avg_mttr_hours': round(avg_mttr, 2)
#     }
    
#     return {
#         'period_start': week_start.strftime('%Y-%m-%d'),
#         'period_end': week_end.strftime('%Y-%m-%d'),
#         'section': section_name,
#         'daily_data': daily_data,
#         'cumulative': cumulative,
#         'machine_type_names': machine_type_names  # Add this for frontend
#     }


def get_timezone():
    """Get Bangkok timezone"""
    return pytz.timezone('Asia/Bangkok')

def get_today_start_end():
    """Get today's start and end datetime"""
    tz = get_timezone()
    today = datetime.now(tz=tz)
    today_start = datetime.combine(today.date(), time.min).replace(tzinfo=tz)
    today_end = datetime.combine(today.date(), time.max).replace(tzinfo=tz)
    return today_start, today_end

def get_week_start_end():
    """Get this week's start and end datetime"""
    tz = get_timezone()
    today = datetime.now(tz=tz).date()
    week_start = today - timedelta(days=today.weekday())
    week_end = week_start + timedelta(days=6)
    
    week_start_dt = datetime.combine(week_start, time.min).replace(tzinfo=tz)
    week_end_dt = datetime.combine(week_end, time.max).replace(tzinfo=tz)
    return week_start_dt, week_end_dt


def get_failures_by_date_shift_section(date_str, shift='all', section=None):
    """Get failures by date, shift, and section with proper logging"""
    from datetime import datetime, time
    
    try:
        logger.info(f"Getting failures for date={date_str}, shift={shift}, section={section}")
        
        tz = get_timezone()
        
        # Parse date
        date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
        date_start = datetime.combine(date_obj, time.min).replace(tzinfo=tz)
        date_end = datetime.combine(date_obj, time.max).replace(tzinfo=tz)
        
        logger.info(f"Date range: {date_start} to {date_end}")
        
        # Build base query
        queryset = Failure.objects.filter(
            start_date__range=[date_start, date_end]
        ).select_related(
            'machine', 
            'machine__machine_type', 
            'machine__machine_type__section',
            'failure_category', 
            'user'
        ).order_by('machine__name', 'start_date')  # Order by machine name, then datetime
        
        logger.info(f"Total failures in date range: {queryset.count()}")
        
        # Filter by section if provided
        if section:
            queryset = queryset.filter(machine__machine_type__section__name=section)
            logger.info(f"After section filter '{section}': {queryset.count()}")
        
        # Filter by shift - check which field name is used
        if shift and shift != 'all':
            # Try both shift and operation_shift field names
            try:
                queryset = queryset.filter(shift=shift)
                logger.info(f"Filtered by shift='{shift}': {queryset.count()}")
            except:
                queryset = queryset.filter(operation_shift=shift)
                logger.info(f"Filtered by operation_shift='{shift}': {queryset.count()}")
        
        failures = list(queryset)
        logger.info(f"Final failures count: {len(failures)}")
        
        result = {
            'date': date_str,
            'shift': shift,
            'section': section or 'All Sections',
            'total_count': len(failures),
            'failures': []
        }
        
        for failure in failures:
            try:
                repairing_time = failure.repairing_time or 0
            except:
                repairing_time = 0
            
            result['failures'].append({
                'id': failure.id,
                'machine_name': failure.machine.name if failure.machine else 'Unknown',
                'machine_type': failure.machine.machine_type.name if failure.machine and failure.machine.machine_type else 'Unknown',  # ADD THIS LINE
                'details': failure.details or '',
                'category_level_0': failure.category_level_0 or 'Uncategorized',
                'failure_category': failure.category_level_1 or (failure.get_failure_category_display() if hasattr(failure, 'get_failure_category_display') else ''),
                'status': failure.status,
                'rootcause': failure.rootcause or '',
                'repair_action': failure.repair_action or '',
                'start_date': failure.start_date.strftime('%Y-%m-%d %H:%M') if failure.start_date else '',
                'repairing_time_hours': round(repairing_time / 60, 2) if repairing_time else 0,
                'user': failure.user.username if failure.user else 'N/A',
                'shift': failure.shift if hasattr(failure, 'shift') and failure.shift else (failure.operation_shift if hasattr(failure, 'operation_shift') else 'Unknown')
            })
        
        logger.info(f"Returning {len(result['failures'])} failures ordered by machine name and datetime")
        return result
    
    except Exception as e:
        logger.error(f"Error getting failures by date/shift/section: {str(e)}", exc_info=True)
        return {
            'date': date_str,
            'shift': shift,
            'section': section or 'All Sections',
            'total_count': 0,
            'failures': [],
            'error': str(e)
        }

def get_failures_by_date_range_section(start_date_str, end_date_str, section=None):
    """Get failures by date range and section"""
    from datetime import datetime, time
    
    try:
        logger.info(f"Getting failures for range {start_date_str} to {end_date_str}, section={section}")
        
        tz = get_timezone()
        
        # Parse dates
        start_date_obj = datetime.strptime(start_date_str, '%Y-%m-%d').date()
        end_date_obj = datetime.strptime(end_date_str, '%Y-%m-%d').date()
        
        range_start = datetime.combine(start_date_obj, time.min).replace(tzinfo=tz)
        range_end = datetime.combine(end_date_obj, time.max).replace(tzinfo=tz)
        
        logger.info(f"Date range: {range_start} to {range_end}")
        
        # Build query
        queryset = Failure.objects.filter(
            start_date__range=[range_start, range_end]
        ).select_related(
            'machine', 
            'machine__machine_type', 
            'machine__machine_type__section',
            'failure_category', 
            'user'
        ).order_by('machine__name', 'start_date')
        
        logger.info(f"Total failures in date range: {queryset.count()}")
        
        # Filter by section if provided
        if section:
            queryset = queryset.filter(machine__machine_type__section__name=section)
            logger.info(f"After section filter '{section}': {queryset.count()}")
        
        failures = list(queryset)
        
        # Calculate metrics
        total_mttr = 0
        for failure in failures:
            if failure.repairing_time:
                total_mttr += failure.repairing_time
        
        avg_mttr_hours = (total_mttr / len(failures) / 60) if failures else 0
        
        result = {
            'start_date': start_date_str,
            'end_date': end_date_str,
            'section': section or 'All Sections',
            'total_count': len(failures),
            'avg_mttr_hours': round(avg_mttr_hours, 2),
            'failures': []
        }
        
        for failure in failures:
            try:
                repairing_time = failure.repairing_time or 0
            except:
                repairing_time = 0
            
            # result['failures'].append({
            #     'id': failure.id,
            #     'machine_name': failure.machine.name if failure.machine else 'Unknown',
            #     'details': failure.details or '',
            #     'category_level_0': failure.category_level_0 or 'Uncategorized',
            #     'failure_category': failure.category_level_1 or (failure.get_failure_category_display() if hasattr(failure, 'get_failure_category_display') else ''),
            #     'status': failure.status,
            #     'rootcause': failure.rootcause or '',
            #     'repair_action': failure.repair_action or '',
            #     'start_date': failure.start_date.strftime('%Y-%m-%d %H:%M') if failure.start_date else '',
            #     'repairing_time_hours': round(repairing_time / 60, 2) if repairing_time else 0,
            #     'user': failure.user.username if failure.user else 'N/A',
            # })
            result['failures'].append({
                'id': failure.id,
                'machine_name': failure.machine.name if failure.machine else 'Unknown',
                'machine_type': failure.machine.machine_type.name if failure.machine and failure.machine.machine_type else 'Unknown',  # ADD THIS LINE
                'details': failure.details or '',
                'category_level_0': failure.category_level_0 or 'Uncategorized',
                'failure_category': failure.category_level_1 or (failure.get_failure_category_display() if hasattr(failure, 'get_failure_category_display') else ''),
                'status': failure.status,
                'rootcause': failure.rootcause or '',
                'repair_action': failure.repair_action or '',
                'start_date': failure.start_date.strftime('%Y-%m-%d %H:%M') if failure.start_date else '',
                'repairing_time_hours': round(repairing_time / 60, 2) if repairing_time else 0,
                'user': failure.user.username if failure.user else 'N/A',
            })
        
        logger.info(f"Returning {len(result['failures'])} failures")
        return result
    
    except Exception as e:
        logger.error(f"Error getting failures by date range/section: {str(e)}", exc_info=True)
        return {
            'start_date': start_date_str,
            'end_date': end_date_str,
            'section': section or 'All Sections',
            'total_count': 0,
            'avg_mttr_hours': 0,
            'failures': [],
            'error': str(e)
        }

def get_failures_by_date_range_with_charts(start_date_str, end_date_str, section=None):
    """Get failures by date range with chart data (daily trend and pareto)"""
    from datetime import datetime, time
    from collections import defaultdict
    
    try:
        logger.info(f"Getting failures with charts for range {start_date_str} to {end_date_str}, section={section}")
        
        tz = get_timezone()
        
        # Parse dates
        start_date_obj = datetime.strptime(start_date_str, '%Y-%m-%d').date()
        end_date_obj = datetime.strptime(end_date_str, '%Y-%m-%d').date()
        
        range_start = datetime.combine(start_date_obj, time.min).replace(tzinfo=tz)
        range_end = datetime.combine(end_date_obj, time.max).replace(tzinfo=tz)
        
        # Build query
        queryset = Failure.objects.filter(
            start_date__range=[range_start, range_end]
        ).select_related(
            'machine', 
            'machine__machine_type', 
            'machine__machine_type__section',
            'failure_category', 
            'user'
        ).order_by('machine__name', 'start_date')
        
        # Filter by section
        if section:
            queryset = queryset.filter(machine__machine_type__section__name=section)
        
        failures = list(queryset)
        
        # Get all machine types in results
        machine_types = set()
        for failure in failures:
            if failure.machine and failure.machine.machine_type:
                machine_types.add(failure.machine.machine_type.name)
        machine_type_names = sorted(list(machine_types))
        
        # Calculate metrics
        total_mttr = 0
        for failure in failures:
            if failure.repairing_time:
                total_mttr += failure.repairing_time
        
        avg_mttr_hours = (total_mttr / len(failures) / 60) if failures else 0
        
        # Build daily trend data
        daily_data = defaultdict(lambda: defaultdict(int))
        for failure in failures:
            date = failure.start_date.strftime('%Y-%m-%d') if failure.start_date else 'Unknown'
            mt_name = failure.machine.machine_type.name if failure.machine and failure.machine.machine_type else 'Unknown'
            daily_data[date][mt_name] += 1
        
        # Convert to regular dict and fill missing machine types
        daily_data_dict = {}
        for date in sorted(daily_data.keys()):
            daily_data_dict[date] = {}
            for mt in machine_type_names:
                daily_data_dict[date][mt] = daily_data[date][mt]
        
        # Build pareto data
        pareto_data = {}
        for mt_name in machine_type_names:
            mt_failures = [f for f in failures if f.machine and f.machine.machine_type and f.machine.machine_type.name == mt_name]
            
            # Count by category
            category_counts = defaultdict(int)
            for failure in mt_failures:
                category = failure.category_level_0 or 'Uncategorized'
                category_counts[category] += 1
            
            # Sort and calculate cumulative
            sorted_categories = sorted(category_counts.items(), key=lambda x: x[1], reverse=True)
            total_count = sum(count for _, count in sorted_categories)
            
            pareto_list = []
            cumulative = 0
            for category, count in sorted_categories:
                cumulative += count
                cumulative_pct = (cumulative / total_count * 100) if total_count > 0 else 0
                pareto_list.append({
                    'category': category,
                    'count': count,
                    'cumulative_percentage': cumulative_pct
                })
            
            pareto_data[mt_name] = pareto_list
        
        # Build failure list
        failure_list = []
        for failure in failures:
            try:
                repairing_time = failure.repairing_time or 0
            except:
                repairing_time = 0
            
            failure_list.append({
                'id': failure.id,
                'machine_name': failure.machine.name if failure.machine else 'Unknown',
                'machine_type': failure.machine.machine_type.name if failure.machine and failure.machine.machine_type else 'Unknown',  # ADD THIS LINE
                'details': failure.details or '',
                'category_level_0': failure.category_level_0 or 'Uncategorized',
                'failure_category': failure.category_level_1 or '',
                'status': failure.status,
                'rootcause': failure.rootcause or '',
                'repair_action': failure.repair_action or '',
                'start_date': failure.start_date.strftime('%Y-%m-%d %H:%M') if failure.start_date else '',
                'repairing_time_hours': round(repairing_time / 60, 2) if repairing_time else 0,
            })
        
        return {
            'start_date': start_date_str,
            'end_date': end_date_str,
            'section': section or 'All Sections',
            'total_count': len(failures),
            'avg_mttr_hours': round(avg_mttr_hours, 2),
            'machine_type_names': machine_type_names,
            'daily_data': daily_data_dict,
            'pareto_data': pareto_data,
            'failures': failure_list
        }
    
    except Exception as e:
        # logger.error(f"Error getting failures with charts: {str(e)}", exc_info=True)
        return {
            'start_date': start_date_str,
            'end_date': end_date_str,
            'section': section or 'All Sections',
            'total_count': 0,
            'avg_mttr_hours': 0,
            'machine_type_names': [],
            'daily_data': {},
            'pareto_data': {},
            'failures': [],
            'error': str(e)
        }