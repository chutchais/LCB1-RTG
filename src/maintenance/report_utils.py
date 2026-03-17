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
    """Get machine failure history with all failures (optimized for performance)"""
    from datetime import datetime, timedelta, time
    
    try:
        machine = Machine.objects.get(name=machine_name)
    except Machine.DoesNotExist:
        return None
    
    tz = get_timezone()
    now = datetime.now(tz=tz)
    two_weeks_ago = now - timedelta(days=14)
    one_week_ago = now - timedelta(days=7)
    
    # Optimize: Use only necessary fields with select_related and prefetch_related
    all_failures = Failure.objects.filter(
        machine=machine
    ).select_related(
        'machine', 'machine__machine_type', 'failure_category', 'user'
    ).prefetch_related('images').values(
        'id', 'start_date', 'end_date', 'category', 'failure_category__name',
        'details', 'rootcause', 'repair_action', 
        'status', 'user__username'
    ).order_by('-start_date')
    
    # Convert to list once (avoid multiple DB queries)
    all_failures_list = list(all_failures)
    
    if not all_failures_list:
        return None
    
    # Get LAST 30 failures only (with images - these are needed)
    recent_failures_ids = [f['id'] for f in all_failures_list[:30]]
    recent_failures_queryset = Failure.objects.filter(
        id__in=recent_failures_ids
    ).select_related('user', 'failure_category').prefetch_related('images').order_by('-start_date')
    
    # Build FAILURE TYPE breakdown using cached list (instead of category)
    failure_type_breakdown = {}
    for failure in all_failures_list:
        ftype = failure['failure_category__name'] or 'Uncategorized'
        failure_type_breakdown[ftype] = failure_type_breakdown.get(ftype, 0) + 1
    
    # Sort by count descending
    failure_type_breakdown = dict(sorted(failure_type_breakdown.items(), key=lambda x: x[1], reverse=True))
    
    # Helper function to calculate repair time in hours
    def calculate_repair_hours(start_date, end_date):
        if start_date and end_date:
            diff = end_date - start_date
            return diff.total_seconds() / 3600
        return 0
    
    # Build recent failures list with image data
    recent_failures = []
    for failure in recent_failures_queryset:
        repair_hours = calculate_repair_hours(failure.start_date, failure.end_date)
        
        # Get images for this failure
        images = []
        try:
            failure_images = failure.images.all()
            for img in failure_images:
                if hasattr(img, 'image') and img.image:
                    images.append({
                        'url': img.image.url,
                        'caption': getattr(img, 'caption', '') or ''
                    })
        except Exception as e:
            print(f"ERROR getting images for failure {failure.id}: {str(e)}")
        
        recent_failures.append({
            'id': failure.id,
            'start_date': failure.start_date.strftime('%Y-%m-%d %H:%M') if failure.start_date else '',
            'category': failure.category or 'Uncategorized',
            'failure_category': failure.failure_category.name if failure.failure_category else 'N/A',
            'details': failure.details or '',
            'repairing_time_hours': round(repair_hours, 2),
            'rootcause': failure.rootcause or '',
            'repair_action': failure.repair_action or '',
            'status': failure.status,
            'technician': failure.user.username if failure.user else 'N/A',
            'images': images
        })
    
    # Calculate performance metrics from cached list and queryset
    repair_times = []
    for failure in recent_failures_queryset:
        repair_hours = calculate_repair_hours(failure.start_date, failure.end_date)
        if repair_hours > 0:
            repair_times.append(repair_hours)
    
    avg_repair_time = sum(repair_times) / len(repair_times) if repair_times else 0
    
    # Generate exclusive advise (uses cached data)
    advise_list = generate_machine_advise_optimized(all_failures_list, recent_failures_queryset, two_weeks_ago, one_week_ago, calculate_repair_hours)
    
    # Count status breakdown from cached list
    open_count = sum(1 for f in all_failures_list if f['status'] == 'OPEN')
    closed_count = len(all_failures_list) - open_count
    
    # Count failures in time windows from cached list
    failures_this_week = sum(1 for f in all_failures_list if f['start_date'] >= one_week_ago)
    
    return {
        'machine_name': machine_name,
        'machine_type': machine.machine_type.name if machine.machine_type else 'Unknown',
        'total_failures': len(all_failures_list),
        'recent_failures': recent_failures,
        'category_breakdown': failure_type_breakdown,  # Now contains failure types, not categories
        'avg_repair_time': round(avg_repair_time, 2),
        'advise_list': advise_list,
        'performance_metrics': {
            'mttr_hours': round(avg_repair_time, 2),
            'total_failures_in_period': len(all_failures_list),
            'failures_this_week': failures_this_week,
            'status_breakdown': {
                'OPEN': open_count,
                'CLOSED': closed_count
            }
        }
    }


def generate_machine_advise_optimized(failures_list, recent_failures_queryset, two_weeks_ago, one_week_ago, calculate_repair_hours):
    """Generate advise from pre-fetched failure data (no DB queries)"""
    
    advise_list = []
    
    if not failures_list:
        return advise_list
    
    # FILTER: Only generate advises for 'BD' category failures
    bd_failures = [f for f in failures_list if f['category'] == 'BD']
    
    if not bd_failures:
        return advise_list  # No advises if no BD failures
    
    # Helper to calculate repair time
    def get_repair_hours(start, end):
        if start and end:
            diff = end - start
            return diff.total_seconds() / 3600
        return 0
    
    # Check for recurring categories in last 2 weeks (BD only)
    category_counts_2weeks = {}
    failure_type_counts = {}
    failures_1week_count = 0
    open_count = 0
    
    for failure in bd_failures:  # Use BD failures only
        start_date = failure['start_date']
        
        # Count open failures
        if failure['status'] == 'OPEN':
            open_count += 1
        
        # Only process recent failures for time-based analysis
        if start_date >= two_weeks_ago:
            cat = failure['category'] or 'Uncategorized'
            category_counts_2weeks[cat] = category_counts_2weeks.get(cat, 0) + 1
            
            ftype = failure['failure_category__name'] or 'Unknown'
            failure_type_counts[ftype] = failure_type_counts.get(ftype, 0) + 1
        
        # Count failures in last week
        if start_date >= one_week_ago:
            failures_1week_count += 1
    
    # Generate advises (for BD category only)
    
    # 1. Recurring categories (3+ in 2 weeks)
    for category, count in category_counts_2weeks.items():
        if count >= 3:
            advise_list.append({
                'type': 'warning',
                'icon': '⚠️',
                'title': f'Recurring Issue: {category}',
                'message': f'Machine failed on <strong>{category}</strong> <strong>{count} times</strong> within last 2 weeks. Consider preventive maintenance or component replacement.',
                'severity': 'high' if count >= 4 else 'medium'
            })
    
    # 2. High failure rate (2+ per week)
    if failures_1week_count >= 2:
        advise_list.append({
            'type': 'alert',
            'icon': '🔴',
            'title': 'High Failure Rate',
            'message': f'<strong>{failures_1week_count} failures</strong> detected in the last 7 days. Machine may require immediate attention or inspection.',
            'severity': 'high' if failures_1week_count >= 4 else 'medium'
        })
    
    # 3. High MTTR (average > 8 hours) - Filter BD failures only
    repair_times = []
    bd_failure_ids = [f['id'] for f in bd_failures[:20]]
    for failure in recent_failures_queryset:
        if failure.id in bd_failure_ids:
            repair_hours = get_repair_hours(failure.start_date, failure.end_date)
            if repair_hours > 0:
                repair_times.append(repair_hours)
    
    if repair_times:
        avg_repair_time = sum(repair_times) / len(repair_times)
        if avg_repair_time > 8:
            advise_list.append({
                'type': 'info',
                'icon': '⏱️',
                'title': 'Long Repair Time',
                'message': f'Average repair time is <strong>{avg_repair_time:.1f} hours</strong>. Consider having spare parts available or improving repair procedures.',
                'severity': 'medium'
            })
    
    # 4. Specific failure types (2+ in 2 weeks)
    for ftype, count in failure_type_counts.items():
        if count >= 2 and ftype != 'Unknown':
            advise_list.append({
                'type': 'info',
                'icon': '💡',
                'title': f'Pattern: {ftype}',
                'message': f'<strong>{ftype}</strong> failure type occurred <strong>{count} times</strong> recently. Review maintenance procedures for this component.',
                'severity': 'low'
            })
    
    # 5. Open failures (BD only)
    if open_count >= 1:
        advise_list.append({
            'type': 'urgent',
            'icon': '🚨',
            'title': 'Unresolved Failures',
            'message': f'<strong>{open_count} failure(s)</strong> still open. Please close or address these issues.',
            'severity': 'high'
        })
    
    # Sort by severity and limit to top 5
    severity_order = {'high': 0, 'medium': 1, 'low': 2}
    advise_list.sort(key=lambda x: severity_order.get(x['severity'], 3))
    
    return advise_list[:5]

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