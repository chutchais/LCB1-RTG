from machine.api.services import get_items_data_filtered
from datetime import timedelta


def calculate_productivity(crane_on_minute_diff, number_of_move_diff):
    """
    Calculate productivity
    
    Formula: Productivity = Number of Move / (Crane On Minute / 60)
    
    This represents: Number of moves per hour of crane operation
    Higher is better (more moves per hour = more productive)
    
    Example:
    - If Crane On Minute = 120 (2 hours) and Number of Move = 10
    - Productivity = 10 / (120 / 60) = 10 / 2 = 5 moves/hour
    
    Args:
        crane_on_minute_diff: Difference in Crane On Minute (minutes)
        number_of_move_diff: Difference in Number of Move (count)
    
    Returns:
        float or None - Productivity value (moves per hour)
    """
    # Avoid division by zero
    if crane_on_minute_diff is None or crane_on_minute_diff == 0:
        return None
    
    if number_of_move_diff is None:
        return None
    
    try:
        # Convert minutes to hours
        crane_hours = float(crane_on_minute_diff) / 60
        moves = float(number_of_move_diff)
        
        # Productivity = moves per hour
        productivity = moves / crane_hours
        return round(productivity, 4)
    except (TypeError, ValueError, ZeroDivisionError):
        return None


def get_productivity_report(equipment_name=None, target_date=None, shift='all'):
    """
    Get productivity report in report-friendly format
    
    Layout:
    Machine | Morning Crane Hour | Morning Moves | Morning Productivity | 
            | Night Crane Hour   | Night Moves   | Night Productivity   |
            | Total Crane Hour   | Total Moves   | Total Productivity   |
    
    Args:
        equipment_name: str or None - Equipment name or None for all
        target_date: date/str or None - Date or None for last week
        shift: str - 'morning', 'night', or 'all' (default: 'all')
    
    Returns:
        {
            'status': 'success' or 'error',
            'error': str (if error),
            'data': {
                'date_range': {...},
                'shift_filter': str,
                'equipment_filter': str or None,
                'report': [
                    {
                        'equipment': 'RTG22',
                        'morning': {
                            'crane_on_minute': 3450,
                            'number_of_move': 145,
                            'productivity': 2.5217,
                            'first_record_time': '2026-05-07 08:15:45 +0700',
                            'last_record_time': '2026-05-07 19:45:30 +0700',
                        },
                        'night': {
                            'crane_on_minute': 2890,
                            'number_of_move': 123,
                            'productivity': 2.3915,
                            'first_record_time': '2026-05-08 20:15:00 +0700',
                            'last_record_time': '2026-05-09 08:00:00 +0700',
                        },
                        'total': {
                            'crane_on_minute': 6340,
                            'number_of_move': 268,
                            'productivity': 2.5395,
                            'first_record_time': '2026-05-07 08:15:45 +0700',
                            'last_record_time': '2026-05-09 08:00:00 +0700',
                        }
                    }
                ],
                'summary': {...},
                'timestamp': '2026-05-07 14:30:45 +0700'
            }
        }
    """
    
    # Get raw data using the smart API
    result = get_items_data_filtered(equipment_name, target_date, 'all', include_details=False)
    
    if result['status'] == 'error':
        return result
    
    # Transform data to report format
    report_data = {}
    
    for equipment_stat in result['data']['equipment_stats']:
        eq_name = equipment_stat['equipment']
        shift_type = equipment_stat['shift']
        
        # Initialize equipment if not exists
        if eq_name not in report_data:
            report_data[eq_name] = {
                'equipment': eq_name,
                'morning': None,
                'night': None,
                'total': {
                    'crane_on_minute': 0,
                    'number_of_move': 0,
                    'productivity': None,
                    'first_record_time': None,
                    'last_record_time': None,
                }
            }
        
        # Extract required items
        crane_on_minute_diff = None
        number_of_move_diff = None
        
        for item in equipment_stat['items']:
            if item['name'] == 'Crane On Minute':
                crane_on_minute_diff = item['difference']
            elif item['name'] == 'Number of Move':
                number_of_move_diff = item['difference']
        
        # Calculate productivity
        productivity = calculate_productivity(crane_on_minute_diff, number_of_move_diff)
        
        # ✅ Build shift data WITH TIMESTAMPS
        shift_data = {
            'crane_on_minute': crane_on_minute_diff,
            'number_of_move': number_of_move_diff,
            'productivity': productivity,
            'first_record_time': equipment_stat['first_record_time'],  # ✅ FROM equipment_stat
            'last_record_time': equipment_stat['last_record_time'],    # ✅ FROM equipment_stat
        }
        
        # Assign to morning/night
        if shift_type == 'morning':
            report_data[eq_name]['morning'] = shift_data
        elif shift_type == 'night':
            report_data[eq_name]['night'] = shift_data
        
        # Add to total
        if crane_on_minute_diff is not None:
            report_data[eq_name]['total']['crane_on_minute'] += crane_on_minute_diff
        if number_of_move_diff is not None:
            report_data[eq_name]['total']['number_of_move'] += number_of_move_diff
        
        # ✅ Update total times (keep earliest first, latest last)
        if report_data[eq_name]['total']['first_record_time'] is None:
            report_data[eq_name]['total']['first_record_time'] = equipment_stat['first_record_time']
        else:
            # Keep the earlier time
            current_first = report_data[eq_name]['total']['first_record_time']
            new_first = equipment_stat['first_record_time']
            if new_first < current_first:
                report_data[eq_name]['total']['first_record_time'] = new_first
        
        # Keep the later time
        if report_data[eq_name]['total']['last_record_time'] is None:
            report_data[eq_name]['total']['last_record_time'] = equipment_stat['last_record_time']
        else:
            current_last = report_data[eq_name]['total']['last_record_time']
            new_last = equipment_stat['last_record_time']
            if new_last > current_last:
                report_data[eq_name]['total']['last_record_time'] = new_last
    
    # Calculate total productivity for each equipment
    for eq_name in report_data:
        total = report_data[eq_name]['total']
        total['productivity'] = calculate_productivity(
            total['crane_on_minute'],
            total['number_of_move']
        )
    
    # Convert dict to sorted list
    report_list = sorted(report_data.values(), key=lambda x: x['equipment'])
    
    return {
        'status': 'success',
        'data': {
            'date_range': result['data']['date_range'],
            'shift_filter': result['data']['shift_filter'],
            'equipment_filter': result['data']['equipment_filter'],
            'report': report_list,
            'summary': {
                'total_equipment': len(report_list),
                'date_range_from': result['data']['date_range']['from'],
                'date_range_to': result['data']['date_range']['to'],
            },
            'timestamp': result['data']['timestamp'],
        }
    }


def get_productivity_report_detailed(equipment_name=None, target_date=None):
    """
    Get detailed productivity report with additional metrics
    
    Includes:
    - All shift data (morning, night, total)
    - Productivity calculations
    - Efficiency metrics
    - Record counts
    - Timestamps for each shift
    
    Args:
        equipment_name: str or None
        target_date: date/str or None
    
    Returns:
        Report data with detailed breakdown
    """
    
    result = get_productivity_report(equipment_name, target_date)
    
    if result['status'] == 'error':
        return result
    
    # Add additional metrics to each equipment
    for equipment in result['data']['report']:
        
        # Calculate efficiency for each shift
        for shift_key in ['morning', 'night']:
            if equipment[shift_key] is not None:
                shift = equipment[shift_key]
                
                shift['metrics'] = {
                    'total_crane_minutes': shift['crane_on_minute'],
                    'total_moves': shift['number_of_move'],
                    'hours_per_move': shift['productivity'],
                    'first_record_time': shift['first_record_time'],  # ✅ Include timestamps
                    'last_record_time': shift['last_record_time'],
                }
        
        # Total metrics
        total = equipment['total']
        total['metrics'] = {
            'total_crane_minutes': total['crane_on_minute'],
            'total_moves': total['number_of_move'],
            'hours_per_move': total['productivity'],
            'first_record_time': total['first_record_time'],  # ✅ Include timestamps
            'last_record_time': total['last_record_time'],
        }
    
    return result


def get_productivity_comparison_report(equipment_names=None, target_date=None):
    """
    Get productivity comparison report across multiple equipment
    
    Useful for comparing performance between machines
    Includes timestamps for each equipment
    
    Returns:
        Sorted report with best/worst performers highlighted
    """
    
    result = get_productivity_report(None, target_date)  # Get all equipment
    
    if result['status'] == 'error':
        return result
    
    # Filter by equipment if specified
    if equipment_names:
        filtered_report = [
            eq for eq in result['data']['report']
            if eq['equipment'] in equipment_names
        ]
    else:
        filtered_report = result['data']['report']
    
    # Calculate statistics
    productivities = []
    for eq in filtered_report:
        if eq['total']['productivity'] is not None:
            productivities.append({
                'equipment': eq['equipment'],
                'productivity': eq['total']['productivity'],
                'first_record_time': eq['total']['first_record_time'],  # ✅ Include
                'last_record_time': eq['total']['last_record_time'],    # ✅ Include
            })
    
    if productivities:
        # Sort by productivity
        productivities_sorted = sorted(productivities, key=lambda x: x['productivity'])
        
        best_equipment = productivities_sorted[-1]  # Highest productivity (last in sorted)
        worst_equipment = productivities_sorted[0]  # Lowest productivity (first in sorted)
        avg_productivity = sum(p['productivity'] for p in productivities) / len(productivities)
    else:
        best_equipment = None
        worst_equipment = None
        avg_productivity = None
    
    return {
        'status': 'success',
        'data': {
            'date_range': result['data']['date_range'],
            'report': filtered_report,
            'statistics': {
                'best_equipment': best_equipment,
                'worst_equipment': worst_equipment,
                'average_productivity': round(avg_productivity, 4) if avg_productivity else None,
                'total_equipment': len(filtered_report),
            },
            'timestamp': result['data']['timestamp'],
        }
    }


def get_productivity_report_daily(equipment_name=None, target_date=None, shift='all'):
    """
    Get productivity report broken down by individual days
    
    Returns one report per day (not summarized)
    Includes timestamps for each day/equipment/shift
    
    Args:
        equipment_name: str or None - Equipment name or None for all
        target_date: date/str or None - Start date or None for last 7 days
        shift: str - 'morning', 'night', or 'all'
    
    Returns:
        {
            'status': 'success' or 'error',
            'data': {
                'date_range': {...},
                'daily_reports': [
                    {
                        'date': '2026-05-07',
                        'equipment': [
                            {
                                'equipment': 'RTG22',
                                'morning': {
                                    'crane_on_minute': 3450,
                                    'number_of_move': 145,
                                    'productivity': 2.5217,
                                    'first_record_time': '2026-05-07 08:15:45 +0700',
                                    'last_record_time': '2026-05-07 19:45:30 +0700',
                                },
                                'night': {...},
                                'total': {...}
                            }
                        ]
                    }
                ],
                'summary': {...},
                'timestamp': '2026-05-07 14:30:45 +0700'
            }
        }
    """
    from django.utils import timezone
    from datetime import datetime
    
    # ========== 1. HANDLE DATE RANGE ==========
    if target_date is None:
        # Get last 7 days
        to_date = timezone.now().date()
        from_date = to_date - timedelta(days=6)
    else:
        # Parse single date
        if isinstance(target_date, str):
            try:
                target_date = datetime.strptime(target_date, '%Y-%m-%d').date()
            except ValueError:
                return {
                    'status': 'error',
                    'error': 'Invalid date format. Use YYYY-MM-DD',
                    'received': target_date
                }
        
        from_date = target_date
        to_date = target_date
    
    # ========== 2. BUILD DAILY REPORTS ==========
    daily_reports = []
    current_date = from_date
    
    while current_date <= to_date:
        # Get data for this specific day
        result = get_productivity_report(equipment_name, current_date.strftime('%Y-%m-%d'), shift)
        
        if result['status'] == 'error':
            # Skip days with no data
            current_date += timedelta(days=1)
            continue
        
        # Build daily report
        daily_report = {
            'date': current_date.strftime('%Y-%m-%d'),
            'equipment': result['data']['report']  # ✅ Already includes timestamps
        }
        
        daily_reports.append(daily_report)
        current_date += timedelta(days=1)
    
    return {
        'status': 'success',
        'data': {
            'date_range': {
                'from': from_date.strftime('%Y-%m-%d'),
                'to': to_date.strftime('%Y-%m-%d'),
            },
            'daily_reports': daily_reports,
            'summary': {
                'total_days': len(daily_reports),
                'total_equipment': len(daily_reports[0]['equipment']) if daily_reports else 0,
                'date_range_from': from_date.strftime('%Y-%m-%d'),
                'date_range_to': to_date.strftime('%Y-%m-%d'),
            },
            'timestamp': timezone.now().strftime('%Y-%m-%d %H:%M:%S %z'),
        }
    }


# def get_productivity_report_daily_detailed(equipment_name=None, target_date=None):
#     """
#     Get detailed daily productivity report with trends
    
#     Includes:
#     - Daily breakdown with timestamps
#     - Trend analysis (day-over-day comparison)
#     - Best/worst days with timestamps
    
#     Args:
#         equipment_name: str or None
#         target_date: date/str or None
    
#     Returns:
#         Report with daily breakdown and trend analysis
#     """
#     from django.utils import timezone
    
#     result = get_productivity_report_daily(equipment_name, target_date)
    
#     if result['status'] == 'error':
#         return result
    
#     # Add trend analysis
#     daily_reports = result['data']['daily_reports']
    
#     # Calculate trends for each equipment
#     trends = {}
    
#     for day_report in daily_reports:
#         for equipment in day_report['equipment']:
#             eq_name = equipment['equipment']
            
#             if eq_name not in trends:
#                 trends[eq_name] = {
#                     'equipment': eq_name,
#                     'daily_productivities': [],
#                     'best_day': None,
#                     'worst_day': None,
#                 }
            
#             # Record daily productivity with timestamps
#             if equipment['total']['productivity'] is not None:
#                 trends[eq_name]['daily_productivities'].append({
#                     'date': day_report['date'],
#                     'productivity': equipment['total']['productivity'],
#                     'first_record_time': equipment['total']['first_record_time'],  # ✅ Include
#                     'last_record_time': equipment['total']['last_record_time'],    # ✅ Include
#                 })
    
#     # Find best/worst days for each equipment
#     for eq_name, trend_data in trends.items():
#         if trend_data['daily_productivities']:
#             sorted_by_productivity = sorted(
#                 trend_data['daily_productivities'],
#                 key=lambda x: x['productivity']
#             )
#             trend_data['best_day'] = sorted_by_productivity[-1]  # Highest productivity
#             trend_data['worst_day'] = sorted_by_productivity[0]  # Lowest productivity
#             trend_data['average_productivity'] = round(
#                 sum(d['productivity'] for d in trend_data['daily_productivities']) / 
#                 len(trend_data['daily_productivities']),
#                 4
#             )
    
#     result['data']['trends'] = list(trends.values())
    
#     return result
def get_productivity_report_daily_detailed(equipment_name=None, target_date=None):
    """
    Get detailed daily productivity report with trends
    
    Includes:
    - Daily breakdown with timestamps
    - Trend analysis (day-over-day comparison)
    - Best/worst days with timestamps and metrics
    - crane_on_minute and number_of_move for each day
    
    Args:
        equipment_name: str or None
        target_date: date/str or None
    
    Returns:
        Report with daily breakdown and trend analysis
    """
    from django.utils import timezone
    
    result = get_productivity_report_daily(equipment_name, target_date)
    
    if result['status'] == 'error':
        return result
    
    # Add trend analysis
    daily_reports = result['data']['daily_reports']
    
    # Calculate trends for each equipment
    trends = {}
    
    for day_report in daily_reports:
        for equipment in day_report['equipment']:
            eq_name = equipment['equipment']
            
            if eq_name not in trends:
                trends[eq_name] = {
                    'equipment': eq_name,
                    'daily_productivities': [],
                    'best_day': None,
                    'worst_day': None,
                }
            
            # Record daily productivity with timestamps and metrics ✅
            if equipment['total']['productivity'] is not None:
                trends[eq_name]['daily_productivities'].append({
                    'date': day_report['date'],
                    'crane_on_minute': equipment['total']['crane_on_minute'],      # ✅ ADD
                    'number_of_move': equipment['total']['number_of_move'],        # ✅ ADD
                    'productivity': equipment['total']['productivity'],
                    'first_record_time': equipment['total']['first_record_time'],
                    'last_record_time': equipment['total']['last_record_time'],
                })
    
    # Find best/worst days for each equipment
    for eq_name, trend_data in trends.items():
        if trend_data['daily_productivities']:
            sorted_by_productivity = sorted(
                trend_data['daily_productivities'],
                key=lambda x: x['productivity']
            )
            trend_data['best_day'] = sorted_by_productivity[-1]   # Highest productivity (includes all fields ✅)
            trend_data['worst_day'] = sorted_by_productivity[0]   # Lowest productivity (includes all fields ✅)
            trend_data['average_productivity'] = round(
                sum(d['productivity'] for d in trend_data['daily_productivities']) / 
                len(trend_data['daily_productivities']),
                4
            )
            
            # ✅ ADD SUMMARY METRICS
            total_crane_minutes = sum(d['crane_on_minute'] for d in trend_data['daily_productivities'] if d['crane_on_minute'])
            total_moves = sum(d['number_of_move'] for d in trend_data['daily_productivities'] if d['number_of_move'])
            
            trend_data['summary_metrics'] = {
                'total_crane_on_minute': total_crane_minutes,
                'total_number_of_move': total_moves,
                'average_daily_crane_minutes': round(total_crane_minutes / len(trend_data['daily_productivities']), 2),
                'average_daily_moves': round(total_moves / len(trend_data['daily_productivities']), 2),
            }
    
    result['data']['trends'] = list(trends.values())
    
    return result