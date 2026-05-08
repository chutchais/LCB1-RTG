from machine.api.services import get_items_data_filtered


# def calculate_productivity(crane_on_minute_diff, number_of_move_diff):
#     """
#     Calculate productivity
    
#     Formula: Productivity = (Crane On Minute / 60) / Number of Move
    
#     This represents: Hours of crane operation per move
    
#     Args:
#         crane_on_minute_diff: Difference in Crane On Minute (minutes)
#         number_of_move_diff: Difference in Number of Move (count)
    
#     Returns:
#         float or None - Productivity value
#     """
#     # Avoid division by zero
#     if number_of_move_diff is None or number_of_move_diff == 0:
#         return None
    
#     if crane_on_minute_diff is None:
#         return None
    
#     try:
#         # Convert minutes to hours
#         crane_hours = float(crane_on_minute_diff) / 60
#         moves = float(number_of_move_diff)
        
#         productivity = crane_hours / moves
#         return round(productivity, 4)
#     except (TypeError, ValueError):
#         return None

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
                'report': [
                    {
                        'equipment': 'RTG22',
                        'morning': {
                            'crane_on_minute': 3450,
                            'number_of_move': 145,
                            'productivity': 0.3966,  # Hours per move
                            'first_record_time': '2026-05-07 08:15:45 +0700',
                            'last_record_time': '2026-05-07 19:45:30 +0700',
                        },
                        'night': {
                            'crane_on_minute': 2890,
                            'number_of_move': 123,
                            'productivity': 0.3915,
                            'first_record_time': '2026-05-08 20:15:00 +0700',
                            'last_record_time': '2026-05-09 08:00:00 +0700',
                        },
                        'total': {
                            'crane_on_minute': 6340,
                            'number_of_move': 268,
                            'productivity': 0.3949,
                            'first_record_time': '2026-05-07 08:15:45 +0700',
                            'last_record_time': '2026-05-09 08:00:00 +0700',
                        }
                    },
                    {
                        'equipment': 'RTG25',
                        ...
                    }
                ],
                'summary': {
                    'total_equipment': 2,
                    'date_range_from': '2026-05-07',
                    'date_range_to': '2026-05-07',
                },
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
        
        # Build shift data
        shift_data = {
            'crane_on_minute': crane_on_minute_diff,
            'number_of_move': number_of_move_diff,
            'productivity': productivity,
            'first_record_time': equipment_stat['first_record_time'],
            'last_record_time': equipment_stat['last_record_time'],
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
        
        # Update total times (keep earliest first, latest last)
        if report_data[eq_name]['total']['first_record_time'] is None:
            report_data[eq_name]['total']['first_record_time'] = equipment_stat['first_record_time']
        if report_data[eq_name]['total']['last_record_time'] is None:
            report_data[eq_name]['total']['last_record_time'] = equipment_stat['last_record_time']
    
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
                
                # Crane utilization percentage (if we had max hours)
                # For now just add the raw metrics
                shift['metrics'] = {
                    'total_crane_minutes': shift['crane_on_minute'],
                    'total_moves': shift['number_of_move'],
                    'hours_per_move': shift['productivity'],
                }
        
        # Total metrics
        total = equipment['total']
        total['metrics'] = {
            'total_crane_minutes': total['crane_on_minute'],
            'total_moves': total['number_of_move'],
            'hours_per_move': total['productivity'],
        }
    
    return result


def get_productivity_comparison_report(equipment_names=None, target_date=None):
    """
    Get productivity comparison report across multiple equipment
    
    Useful for comparing performance between machines
    
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
                'productivity': eq['total']['productivity']
            })
    
    if productivities:
        # Sort by productivity
        productivities_sorted = sorted(productivities, key=lambda x: x['productivity'])
        
        best_equipment = productivities_sorted[0]
        worst_equipment = productivities_sorted[-1]
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