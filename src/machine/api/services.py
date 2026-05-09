# from machine.models import ConnectionStatus, Equipment
# from django.utils import timezone
# from datetime import datetime, timedelta, date


# # List of items to include (hard-coded)
# REQUIRED_ITEMS = ['Crane On Hour', 'Crane On Minute', 'Number of Move']


# def calculate_difference_with_reset(all_values):
#     """
#     Calculate total difference considering meter resets starting from zero
    
#     Logic:
#     1. Scan through all_values
#     2. When next_value < previous_value → RESET detected
#     3. Before reset: difference = last_before_reset - first_segment
#     4. Reset point itself: difference = reset_value - 0 (assumes meter starts at 0)
#     5. After reset: continue from that point until next reset or end
    
#     Example:
#     [100, 200, 300, 50, 100, 150, 80, 120]
    
#     Segment 1 (0→3): 100→300, diff = 300-100 = 200
#     RESET at 3→4: 300→50, add reset value = 50-0 = 50
#     Segment 2 (4→5): 50→150, diff = 150-50 = 100
#     RESET at 5→6: 150→80, add reset value = 80-0 = 80
#     Segment 3 (6→7): 80→120, diff = 120-80 = 40
    
#     Total: 200 + 50 + 100 + 80 + 40 = 470
    
#     Args:
#         all_values: List of numeric values in order
    
#     Returns:
#         {
#             'total_difference': float,
#             'first_value': value,
#             'last_value': value,
#             'reset_detected': bool,
#             'reset_count': int,
#             'segments': list of calculation segments,
#         }
#     """
#     if not all_values or len(all_values) == 0:
#         return {
#             'total_difference': 0,
#             'first_value': None,
#             'last_value': None,
#             'reset_detected': False,
#             'reset_count': 0,
#             'segments': [],
#         }
    
#     # Convert to numeric
#     try:
#         numeric_values = []
#         for v in all_values:
#             numeric_values.append(float(v))
#     except (TypeError, ValueError):
#         return {
#             'total_difference': None,
#             'first_value': all_values[0],
#             'last_value': all_values[-1],
#             'reset_detected': False,
#             'reset_count': 0,
#             'segments': [],
#             'error': 'Non-numeric values'
#         }
    
#     first_value = numeric_values[0]
#     last_value = numeric_values[-1]
    
#     # Find all reset points (where value decreases)
#     reset_indices = []
#     for i in range(len(numeric_values) - 1):
#         if numeric_values[i + 1] < numeric_values[i]:
#             reset_indices.append(i)  # Index before reset
    
#     if not reset_indices:
#         # No reset detected - simple difference
#         total_difference = last_value - first_value
#         return {
#             'total_difference': total_difference,
#             'first_value': first_value,
#             'last_value': last_value,
#             'reset_detected': False,
#             'reset_count': 0,
#             'segments': [
#                 {
#                     'type': 'normal',
#                     'segment_num': 1,
#                     'start_index': 0,
#                     'end_index': len(numeric_values) - 1,
#                     'start_value': first_value,
#                     'end_value': last_value,
#                     'difference': total_difference,
#                     'calculation': f'{last_value} - {first_value} = {total_difference}'
#                 }
#             ],
#         }
    
#     # Multiple segments with resets
#     segments = []
#     total_difference = 0
#     segment_num = 1
#     current_start_idx = 0
    
#     for reset_idx in reset_indices:
#         # Segment before reset
#         segment_start_value = numeric_values[current_start_idx]
#         segment_end_value = numeric_values[reset_idx]
#         segment_diff = segment_end_value - segment_start_value
#         total_difference += segment_diff
        
#         segments.append({
#             'type': 'before_reset',
#             'segment_num': segment_num,
#             'start_index': current_start_idx,
#             'end_index': reset_idx,
#             'start_value': segment_start_value,
#             'end_value': segment_end_value,
#             'difference': segment_diff,
#             'calculation': f'{segment_end_value} - {segment_start_value} = {segment_diff}'
#         })
        
#         # Reset value (from 0 to reset point)
#         reset_value = numeric_values[reset_idx + 1]
#         reset_diff = reset_value - 0
#         total_difference += reset_diff
        
#         segments.append({
#             'type': 'reset',
#             'segment_num': segment_num,
#             'reset_index': reset_idx,
#             'before_reset': numeric_values[reset_idx],
#             'after_reset': reset_value,
#             'difference': reset_diff,
#             'calculation': f'{reset_value} - 0 = {reset_diff} (Meter reset, starts from 0)'
#         })
        
#         current_start_idx = reset_idx + 1
#         segment_num += 1
    
#     # Last segment (after last reset)
#     if current_start_idx < len(numeric_values) - 1:
#         segment_start_value = numeric_values[current_start_idx]
#         segment_end_value = numeric_values[-1]
#         segment_diff = segment_end_value - segment_start_value
#         total_difference += segment_diff
        
#         segments.append({
#             'type': 'after_reset',
#             'segment_num': segment_num,
#             'start_index': current_start_idx,
#             'end_index': len(numeric_values) - 1,
#             'start_value': segment_start_value,
#             'end_value': segment_end_value,
#             'difference': segment_diff,
#             'calculation': f'{segment_end_value} - {segment_start_value} = {segment_diff}'
#         })
    
#     return {
#         'total_difference': total_difference,
#         'first_value': first_value,
#         'last_value': last_value,
#         'reset_detected': len(reset_indices) > 0,
#         'reset_count': len(reset_indices),
#         'segments': segments,
#     }


# # def get_items_data(equipment_name, target_date, shift='all', include_details=False):
# #     """
# #     Get items data for equipment on given date and shift
    
# #     Can be used by:
# #     - API endpoints
# #     - Internal services
# #     - Management commands
# #     - Background tasks
    
# #     Args:
# #         equipment_name: str - Equipment name (e.g., 'RTG25')
# #         target_date: date or str - Date in YYYY-MM-DD format or date object
# #         shift: str - 'morning', 'night', or 'all' (default: 'all')
# #         include_details: bool - Include detailed segments and all_values
    
# #     Returns:
# #         {
# #             'status': 'success' or 'error',
# #             'error': str (if error),
# #             'data': {
# #                 'target_date': str,
# #                 'shift_filter': str,
# #                 'equipment_filter': str,
# #                 'equipment_stats': [...],
# #                 'total_records': int,
# #                 'timestamp': datetime,
# #             }
# #         }
# #     """
    
# #     # Parse date if string
# #     if isinstance(target_date, str):
# #         try:
# #             target_date = datetime.strptime(target_date, '%Y-%m-%d').date()
# #         except ValueError:
# #             return {
# #                 'status': 'error',
# #                 'error': 'Invalid date format. Use YYYY-MM-DD',
# #                 'received': target_date
# #             }
    
# #     # Validate shift
# #     if shift not in ['morning', 'night', 'all']:
# #         return {
# #             'status': 'error',
# #             'error': f'Invalid shift. Must be morning, night, or all. Got: {shift}'
# #         }
    
# #     # Check if equipment exists
# #     try:
# #         equipment = Equipment.objects.get(name=equipment_name)
# #     except Equipment.DoesNotExist:
# #         available = list(Equipment.objects.values_list('name', flat=True).order_by('name'))
# #         return {
# #             'status': 'error',
# #             'error': f'Equipment "{equipment_name}" not found',
# #             'available_equipment': available
# #         }
    
# #     # Build query
# #     query = ConnectionStatus.objects.filter(
# #         equipment=equipment,
# #         recorded_at__date=target_date,
# #         connection_status='success'
# #     ).order_by('recorded_at')
    
# #     if shift != 'all':
# #         query = query.filter(shift=shift)
    
# #     # Group items by shift
# #     items_summary = {}
    
# #     for record in query:
# #         eq_name = record.equipment.name
# #         shift_type = record.shift
# #         key = f"{eq_name}_{shift_type}"
        
# #         if key not in items_summary:
# #             items_summary[key] = {
# #                 'equipment': eq_name,
# #                 'shift': shift_type,
# #                 'shift_label': 'Morning (08:00 - 20:00)' if shift_type == 'morning' else 'Night (20:00 - 08:00)',
# #                 'items': {},
# #                 'first_record_time': record.recorded_at,
# #                 'last_record_time': record.recorded_at,
# #                 'record_count': 0
# #             }
        
# #         items_summary[key]['last_record_time'] = record.recorded_at
# #         items_summary[key]['record_count'] += 1
        
# #         if record.items_data:
# #             for item_name, value in record.items_data.items():
# #                 if item_name not in items_summary[key]['items']:
# #                     items_summary[key]['items'][item_name] = {
# #                         'all_values': [],
# #                     }
                
# #                 items_summary[key]['items'][item_name]['all_values'].append(value)
    
# #     # Calculate differences with zero-based reset logic
# #     equipment_stats = []
# #     for key, summary in items_summary.items():
# #         items_with_diff = []
        
# #         for item_name, item_stats in summary['items'].items():
# #             all_values = item_stats['all_values']
            
# #             # Calculate difference
# #             calc_result = calculate_difference_with_reset(all_values)
            
# #             item_response = {
# #                 'name': item_name,
# #                 'first_value': calc_result['first_value'],
# #                 'last_value': calc_result['last_value'],
# #                 'difference': calc_result['total_difference'],
# #                 'reset_detected': calc_result['reset_detected'],
# #                 'reset_count': calc_result['reset_count'],
# #                 'count': len(all_values),
# #             }
            
# #             # Add detailed information if requested or if reset detected
# #             if include_details or calc_result['reset_detected']:
# #                 item_response['segments'] = calc_result['segments']
# #                 item_response['all_values'] = all_values
            
# #             items_with_diff.append(item_response)
        
# #         items_with_diff.sort(key=lambda x: x['name'])
        
# #         duration = int((summary['last_record_time'] - summary['first_record_time']).total_seconds() / 60)
        
# #         equipment_stats.append({
# #             'equipment': summary['equipment'],
# #             'shift': summary['shift'],
# #             'shift_label': summary['shift_label'],
# #             'items': items_with_diff,
# #             'first_record_time': summary['first_record_time'],
# #             'last_record_time': summary['last_record_time'],
# #             'record_count': summary['record_count'],
# #             'duration_minutes': duration,
# #         })
    
# #     return {
# #         'status': 'success',
# #         'data': {
# #             'target_date': target_date.strftime('%Y-%m-%d'),
# #             'shift_filter': shift,
# #             'equipment_filter': equipment_name,
# #             'equipment_stats': equipment_stats,
# #             'total_records': query.count(),
# #             'timestamp': timezone.now(),
# #         }
# #     }

# # Update the query building sections:

# def get_items_data(equipment_name, target_date, shift='all', include_details=False):
#     """
#     Get items data for equipment on given date and shift
#     Uses shift_date column (not recorded_at)
#     """
    
#     # Parse date if string
#     if isinstance(target_date, str):
#         try:
#             target_date = datetime.strptime(target_date, '%Y-%m-%d').date()
#         except ValueError:
#             return {
#                 'status': 'error',
#                 'error': 'Invalid date format. Use YYYY-MM-DD',
#                 'received': target_date
#             }
    
#     # Validate shift
#     if shift not in ['morning', 'night', 'all']:
#         return {
#             'status': 'error',
#             'error': f'Invalid shift. Must be morning, night, or all. Got: {shift}'
#         }
    
#     # Check if equipment exists
#     try:
#         equipment = Equipment.objects.get(name=equipment_name)
#     except Equipment.DoesNotExist:
#         available = list(Equipment.objects.values_list('name', flat=True).order_by('name'))
#         return {
#             'status': 'error',
#             'error': f'Equipment "{equipment_name}" not found',
#             'available_equipment': available
#         }
    
#     # ✅ BUILD QUERY USING shift_date (not recorded_at__date)
#     query = ConnectionStatus.objects.filter(
#         equipment=equipment,
#         shift_date=target_date,  # ✅ CHANGED: Use shift_date column
#         connection_status='success'
#     ).order_by('recorded_at')
    
#     if shift != 'all':
#         query = query.filter(shift=shift)
    
#     # Group items by shift
#     items_summary = {}
    
#     for record in query:
#         eq_name = record.equipment.name
#         shift_type = record.shift
#         key = f"{eq_name}_{shift_type}"
        
#         if key not in items_summary:
#             items_summary[key] = {
#                 'equipment': eq_name,
#                 'shift': shift_type,
#                 'shift_label': 'Morning (08:00 - 20:00)' if shift_type == 'morning' else 'Night (20:00 - 08:00)',
#                 'items': {},
#                 'first_record_time': record.recorded_at,
#                 'last_record_time': record.recorded_at,
#                 'record_count': 0
#             }
        
#         items_summary[key]['last_record_time'] = record.recorded_at
#         items_summary[key]['record_count'] += 1
        
#         if record.items_data:
#             for item_name, value in record.items_data.items():
#                 if item_name not in items_summary[key]['items']:
#                     items_summary[key]['items'][item_name] = {
#                         'all_values': [],
#                     }
                
#                 items_summary[key]['items'][item_name]['all_values'].append(value)
    
#     # Calculate differences with zero-based reset logic
#     equipment_stats = []
#     for key, summary in items_summary.items():
#         items_with_diff = []
        
#         for item_name, item_stats in summary['items'].items():
#             all_values = item_stats['all_values']
            
#             # Calculate difference
#             calc_result = calculate_difference_with_reset(all_values)
            
#             item_response = {
#                 'name': item_name,
#                 'first_value': calc_result['first_value'],
#                 'last_value': calc_result['last_value'],
#                 'difference': calc_result['total_difference'],
#                 'reset_detected': calc_result['reset_detected'],
#                 'reset_count': calc_result['reset_count'],
#                 'count': len(all_values),
#             }
            
#             # Add detailed information if requested or if reset detected
#             if include_details or calc_result['reset_detected']:
#                 item_response['segments'] = calc_result['segments']
#                 item_response['all_values'] = all_values
            
#             items_with_diff.append(item_response)
        
#         items_with_diff.sort(key=lambda x: x['name'])
        
#         duration = int((summary['last_record_time'] - summary['first_record_time']).total_seconds() / 60)
        
#         equipment_stats.append({
#             'equipment': summary['equipment'],
#             'shift': summary['shift'],
#             'shift_label': summary['shift_label'],
#             'items': items_with_diff,
#             'first_record_time': summary['first_record_time'],
#             'last_record_time': summary['last_record_time'],
#             'record_count': summary['record_count'],
#             'duration_minutes': duration,
#         })
    
#     return {
#         'status': 'success',
#         'data': {
#             'target_date': target_date.strftime('%Y-%m-%d'),
#             'shift_filter': shift,
#             'equipment_filter': equipment_name,
#             'equipment_stats': equipment_stats,
#             'total_records': query.count(),
#             'timestamp': timezone.now(),
#         }
#     }


# def get_items_data_filtered(equipment_name=None, target_date=None, shift='all', include_details=False):
#     """
#     Get items data with smart defaults
#     Uses shift_date column (not recorded_at)
    
#     Features:
#     1. If equipment_name is None → Get ALL equipment
#     2. Only returns: Crane On Hour, Crane On Minute, Number of Move
#     3. If target_date is None → Get last 7 days (whole week)
#     """
    
#     # ========== 1. HANDLE DATE RANGE ==========
#     date_auto = False
    
#     if target_date is None:
#         # Get last 7 days (whole week)
#         to_date = timezone.now().date()
#         from_date = to_date - timedelta(days=6)  # Last 7 days including today
#         date_auto = True
#     else:
#         # Parse single date
#         if isinstance(target_date, str):
#             try:
#                 target_date = datetime.strptime(target_date, '%Y-%m-%d').date()
#             except ValueError:
#                 return {
#                     'status': 'error',
#                     'error': 'Invalid date format. Use YYYY-MM-DD',
#                     'received': target_date
#                 }
        
#         from_date = target_date
#         to_date = target_date
    
#     # ========== 2. HANDLE EQUIPMENT ==========
#     equipment_auto = False
#     equipment_list = []
    
#     if equipment_name is None:
#         # Get ALL equipment
#         equipment_list = list(Equipment.objects.all().order_by('name'))
#         equipment_auto = True
#         equipment_filter_display = None
#     else:
#         # Get specific equipment
#         try:
#             equipment = Equipment.objects.get(name=equipment_name)
#             equipment_list = [equipment]
#             equipment_filter_display = equipment_name
#         except Equipment.DoesNotExist:
#             available = list(Equipment.objects.values_list('name', flat=True).order_by('name'))
#             return {
#                 'status': 'error',
#                 'error': f'Equipment "{equipment_name}" not found',
#                 'available_equipment': available
#             }
    
#     # ========== 3. VALIDATE SHIFT ==========
#     if shift not in ['morning', 'night', 'all']:
#         return {
#             'status': 'error',
#             'error': f'Invalid shift. Must be morning, night, or all. Got: {shift}'
#         }
    
#     # ========== 4. BUILD QUERY USING shift_date ==========
#     query = ConnectionStatus.objects.filter(
#         equipment__in=equipment_list,
#         shift_date__gte=from_date,  # ✅ CHANGED: Use shift_date__gte
#         shift_date__lte=to_date,    # ✅ CHANGED: Use shift_date__lte
#         connection_status='success'
#     ).order_by('equipment', 'recorded_at')
    
#     if shift != 'all':
#         query = query.filter(shift=shift)
    
#     # ========== 5. GROUP ITEMS BY EQUIPMENT & SHIFT ==========
#     items_summary = {}
    
#     for record in query:
#         eq_name = record.equipment.name
#         shift_type = record.shift
#         key = f"{eq_name}_{shift_type}"
        
#         if key not in items_summary:
#             items_summary[key] = {
#                 'equipment': eq_name,
#                 'shift': shift_type,
#                 'shift_label': 'Morning (08:00 - 20:00)' if shift_type == 'morning' else 'Night (20:00 - 08:00)',
#                 'items': {},
#                 'first_record_time': record.recorded_at,
#                 'last_record_time': record.recorded_at,
#                 'record_count': 0
#             }
        
#         items_summary[key]['last_record_time'] = record.recorded_at
#         items_summary[key]['record_count'] += 1
        
#         if record.items_data:
#             for item_name, value in record.items_data.items():
#                 # ✅ ONLY INCLUDE REQUIRED ITEMS
#                 if item_name not in REQUIRED_ITEMS:
#                     continue
                
#                 if item_name not in items_summary[key]['items']:
#                     items_summary[key]['items'][item_name] = {
#                         'all_values': [],
#                     }
                
#                 items_summary[key]['items'][item_name]['all_values'].append(value)
    
#     # ========== 6. CALCULATE DIFFERENCES ==========
#     equipment_stats = []
#     for key, summary in items_summary.items():
#         items_with_diff = []
        
#         for item_name, item_stats in summary['items'].items():
#             all_values = item_stats['all_values']
            
#             # Calculate difference
#             calc_result = calculate_difference_with_reset(all_values)
            
#             item_response = {
#                 'name': item_name,
#                 'first_value': calc_result['first_value'],
#                 'last_value': calc_result['last_value'],
#                 'difference': calc_result['total_difference'],
#                 'reset_detected': calc_result['reset_detected'],
#                 'reset_count': calc_result['reset_count'],
#                 'count': len(all_values),
#             }
            
#             # Add detailed information if requested or if reset detected
#             if include_details or calc_result['reset_detected']:
#                 item_response['segments'] = calc_result['segments']
#                 item_response['all_values'] = all_values
            
#             items_with_diff.append(item_response)
        
#         items_with_diff.sort(key=lambda x: x['name'])
        
#         # Only include if has items
#         if items_with_diff:
#             duration = int((summary['last_record_time'] - summary['first_record_time']).total_seconds() / 60)
            
#             equipment_stats.append({
#                 'equipment': summary['equipment'],
#                 'shift': summary['shift'],
#                 'shift_label': summary['shift_label'],
#                 'items': items_with_diff,
#                 'first_record_time': summary['first_record_time'],
#                 'last_record_time': summary['last_record_time'],
#                 'record_count': summary['record_count'],
#                 'duration_minutes': duration,
#             })
    
#     return {
#         'status': 'success',
#         'data': {
#             'date_range': {
#                 'from': from_date.strftime('%Y-%m-%d'),
#                 'to': to_date.strftime('%Y-%m-%d'),
#             },
#             'shift_filter': shift,
#             'equipment_filter': equipment_filter_display,
#             'filter_info': {
#                 'equipment_auto': equipment_auto,
#                 'date_auto': date_auto,
#                 'items_filtered': True,
#                 'items_included': REQUIRED_ITEMS,
#             },
#             'equipment_stats': equipment_stats,
#             'total_records': query.count(),
#             'timestamp': timezone.now(),
#         }
#     }

# def get_items_data_filtered(equipment_name=None, target_date=None, shift='all', include_details=False):
#     """
#     Get items data with smart defaults
    
#     Features:
#     1. If equipment_name is None → Get ALL equipment
#     2. Only returns: Crane On Hour, Crane On Minute, Number of Move
#     3. If target_date is None → Get last 7 days (whole week)
    
#     Args:
#         equipment_name: str or None - Equipment name or None for all
#         target_date: date/str or None - Date or None for last week
#         shift: str - 'morning', 'night', or 'all' (default: 'all')
#         include_details: bool - Include detailed segments and all_values
    
#     Returns:
#         {
#             'status': 'success' or 'error',
#             'error': str (if error),
#             'data': {
#                 'date_range': {...},
#                 'shift_filter': str,
#                 'equipment_filter': str or None,
#                 'filter_info': {...},
#                 'equipment_stats': [...],
#                 'total_records': int,
#                 'timestamp': datetime,
#             }
#         }
#     """
    
#     # ========== 1. HANDLE DATE RANGE ==========
#     date_auto = False
    
#     if target_date is None:
#         # Get last 7 days (whole week)
#         to_date = timezone.now().date()
#         from_date = to_date - timedelta(days=6)  # Last 7 days including today
#         date_auto = True
#     else:
#         # Parse single date
#         if isinstance(target_date, str):
#             try:
#                 target_date = datetime.strptime(target_date, '%Y-%m-%d').date()
#             except ValueError:
#                 return {
#                     'status': 'error',
#                     'error': 'Invalid date format. Use YYYY-MM-DD',
#                     'received': target_date
#                 }
        
#         from_date = target_date
#         to_date = target_date
    
#     # ========== 2. HANDLE EQUIPMENT ==========
#     equipment_auto = False
#     equipment_list = []
    
#     if equipment_name is None:
#         # Get ALL equipment
#         equipment_list = list(Equipment.objects.all().order_by('name'))
#         equipment_auto = True
#         equipment_filter_display = None
#     else:
#         # Get specific equipment
#         try:
#             equipment = Equipment.objects.get(name=equipment_name)
#             equipment_list = [equipment]
#             equipment_filter_display = equipment_name
#         except Equipment.DoesNotExist:
#             available = list(Equipment.objects.values_list('name', flat=True).order_by('name'))
#             return {
#                 'status': 'error',
#                 'error': f'Equipment "{equipment_name}" not found',
#                 'available_equipment': available
#             }
    
#     # ========== 3. VALIDATE SHIFT ==========
#     if shift not in ['morning', 'night', 'all']:
#         return {
#             'status': 'error',
#             'error': f'Invalid shift. Must be morning, night, or all. Got: {shift}'
#         }
    
#     # ========== 4. BUILD QUERY ==========
#     query = ConnectionStatus.objects.filter(
#         equipment__in=equipment_list,
#         recorded_at__date__gte=from_date,
#         recorded_at__date__lte=to_date,
#         connection_status='success'
#     ).order_by('equipment', 'recorded_at')
    
#     if shift != 'all':
#         query = query.filter(shift=shift)
    
#     # ========== 5. GROUP ITEMS BY EQUIPMENT & SHIFT ==========
#     items_summary = {}
    
#     for record in query:
#         eq_name = record.equipment.name
#         shift_type = record.shift
#         key = f"{eq_name}_{shift_type}"
        
#         if key not in items_summary:
#             items_summary[key] = {
#                 'equipment': eq_name,
#                 'shift': shift_type,
#                 'shift_label': 'Morning (08:00 - 20:00)' if shift_type == 'morning' else 'Night (20:00 - 08:00)',
#                 'items': {},
#                 'first_record_time': record.recorded_at,
#                 'last_record_time': record.recorded_at,
#                 'record_count': 0
#             }
        
#         items_summary[key]['last_record_time'] = record.recorded_at
#         items_summary[key]['record_count'] += 1
        
#         if record.items_data:
#             for item_name, value in record.items_data.items():
#                 # ✅ ONLY INCLUDE REQUIRED ITEMS
#                 if item_name not in REQUIRED_ITEMS:
#                     continue
                
#                 if item_name not in items_summary[key]['items']:
#                     items_summary[key]['items'][item_name] = {
#                         'all_values': [],
#                     }
                
#                 items_summary[key]['items'][item_name]['all_values'].append(value)
    
#     # ========== 6. CALCULATE DIFFERENCES ==========
#     equipment_stats = []
#     for key, summary in items_summary.items():
#         items_with_diff = []
        
#         for item_name, item_stats in summary['items'].items():
#             all_values = item_stats['all_values']
            
#             # Calculate difference
#             calc_result = calculate_difference_with_reset(all_values)
            
#             item_response = {
#                 'name': item_name,
#                 'first_value': calc_result['first_value'],
#                 'last_value': calc_result['last_value'],
#                 'difference': calc_result['total_difference'],
#                 'reset_detected': calc_result['reset_detected'],
#                 'reset_count': calc_result['reset_count'],
#                 'count': len(all_values),
#             }
            
#             # Add detailed information if requested or if reset detected
#             if include_details or calc_result['reset_detected']:
#                 item_response['segments'] = calc_result['segments']
#                 item_response['all_values'] = all_values
            
#             items_with_diff.append(item_response)
        
#         items_with_diff.sort(key=lambda x: x['name'])
        
#         # Only include if has items
#         if items_with_diff:
#             duration = int((summary['last_record_time'] - summary['first_record_time']).total_seconds() / 60)
            
#             equipment_stats.append({
#                 'equipment': summary['equipment'],
#                 'shift': summary['shift'],
#                 'shift_label': summary['shift_label'],
#                 'items': items_with_diff,
#                 'first_record_time': summary['first_record_time'],
#                 'last_record_time': summary['last_record_time'],
#                 'record_count': summary['record_count'],
#                 'duration_minutes': duration,
#             })
    
#     return {
#         'status': 'success',
#         'data': {
#             'date_range': {
#                 'from': from_date.strftime('%Y-%m-%d'),
#                 'to': to_date.strftime('%Y-%m-%d'),
#             },
#             'shift_filter': shift,
#             'equipment_filter': equipment_filter_display,
#             'filter_info': {
#                 'equipment_auto': equipment_auto,
#                 'date_auto': date_auto,
#                 'items_filtered': True,
#                 'items_included': REQUIRED_ITEMS,
#             },
#             'equipment_stats': equipment_stats,
#             'total_records': query.count(),
#             'timestamp': timezone.now(),
#         }
#     }

from machine.models import ConnectionStatus, Equipment
from django.utils import timezone
from datetime import datetime, timedelta, date
import pytz


# List of items to include (hard-coded)
REQUIRED_ITEMS = ['Crane On Hour', 'Crane On Minute', 'Number of Move']

# Define timezone (adjust to your timezone)
LOCAL_TIMEZONE = pytz.timezone('Asia/Bangkok')  # ✅ Change this to your timezone


def convert_to_local_tz(dt):
    """
    Convert datetime to local timezone
    
    Args:
        dt: datetime object (can be naive or aware)
    
    Returns:
        datetime object in local timezone
    """
    if dt is None:
        return None
    
    # If naive datetime, assume UTC
    if dt.tzinfo is None:
        dt = pytz.utc.localize(dt)
    
    # Convert to local timezone
    return dt.astimezone(LOCAL_TIMEZONE)


def format_datetime_local(dt):
    """
    Format datetime as local time string
    
    Args:
        dt: datetime object
    
    Returns:
        Formatted string like "2026-05-07 14:30:45 +07:00"
    """
    if dt is None:
        return None
    
    local_dt = convert_to_local_tz(dt)
    return local_dt.strftime('%Y-%m-%d %H:%M:%S %z')


def calculate_difference_with_reset(all_values):
    """
    Calculate total difference considering meter resets starting from zero
    [Previous implementation - keep as is]
    """
    if not all_values or len(all_values) == 0:
        return {
            'total_difference': 0,
            'first_value': None,
            'last_value': None,
            'reset_detected': False,
            'reset_count': 0,
            'segments': [],
        }
    
    # Convert to numeric
    try:
        numeric_values = []
        for v in all_values:
            numeric_values.append(float(v))
    except (TypeError, ValueError):
        return {
            'total_difference': None,
            'first_value': all_values[0],
            'last_value': all_values[-1],
            'reset_detected': False,
            'reset_count': 0,
            'segments': [],
            'error': 'Non-numeric values'
        }
    
    first_value = numeric_values[0]
    last_value = numeric_values[-1]
    
    # Find all reset points (where value decreases)
    reset_indices = []
    for i in range(len(numeric_values) - 1):
        if numeric_values[i + 1] < numeric_values[i]:
            reset_indices.append(i)  # Index before reset
    
    if not reset_indices:
        # No reset detected - simple difference
        total_difference = last_value - first_value
        return {
            'total_difference': total_difference,
            'first_value': first_value,
            'last_value': last_value,
            'reset_detected': False,
            'reset_count': 0,
            'segments': [
                {
                    'type': 'normal',
                    'segment_num': 1,
                    'start_index': 0,
                    'end_index': len(numeric_values) - 1,
                    'start_value': first_value,
                    'end_value': last_value,
                    'difference': total_difference,
                    'calculation': f'{last_value} - {first_value} = {total_difference}'
                }
            ],
        }
    
    # Multiple segments with resets
    segments = []
    total_difference = 0
    segment_num = 1
    current_start_idx = 0
    
    for reset_idx in reset_indices:
        # Segment before reset
        segment_start_value = numeric_values[current_start_idx]
        segment_end_value = numeric_values[reset_idx]
        segment_diff = segment_end_value - segment_start_value
        total_difference += segment_diff
        
        segments.append({
            'type': 'before_reset',
            'segment_num': segment_num,
            'start_index': current_start_idx,
            'end_index': reset_idx,
            'start_value': segment_start_value,
            'end_value': segment_end_value,
            'difference': segment_diff,
            'calculation': f'{segment_end_value} - {segment_start_value} = {segment_diff}'
        })
        
        # Reset value (from 0 to reset point)
        reset_value = numeric_values[reset_idx + 1]
        reset_diff = reset_value - 0
        total_difference += reset_diff
        
        segments.append({
            'type': 'reset',
            'segment_num': segment_num,
            'reset_index': reset_idx,
            'before_reset': numeric_values[reset_idx],
            'after_reset': reset_value,
            'difference': reset_diff,
            'calculation': f'{reset_value} - 0 = {reset_diff} (Meter reset, starts from 0)'
        })
        
        current_start_idx = reset_idx + 1
        segment_num += 1
    
    # Last segment (after last reset)
    if current_start_idx < len(numeric_values) - 1:
        segment_start_value = numeric_values[current_start_idx]
        segment_end_value = numeric_values[-1]
        segment_diff = segment_end_value - segment_start_value
        total_difference += segment_diff
        
        segments.append({
            'type': 'after_reset',
            'segment_num': segment_num,
            'start_index': current_start_idx,
            'end_index': len(numeric_values) - 1,
            'start_value': segment_start_value,
            'end_value': segment_end_value,
            'difference': segment_diff,
            'calculation': f'{segment_end_value} - {segment_start_value} = {segment_diff}'
        })
    
    return {
        'total_difference': total_difference,
        'first_value': first_value,
        'last_value': last_value,
        'reset_detected': len(reset_indices) > 0,
        'reset_count': len(reset_indices),
        'segments': segments,
    }


def get_items_data(equipment_name, target_date, shift='all', include_details=False):
    """
    Get items data for equipment on given date and shift
    Uses shift_date column and converts times to local timezone
    """
    
    # Parse date if string
    if isinstance(target_date, str):
        try:
            target_date = datetime.strptime(target_date, '%Y-%m-%d').date()
        except ValueError:
            return {
                'status': 'error',
                'error': 'Invalid date format. Use YYYY-MM-DD',
                'received': target_date
            }
    
    # Validate shift
    if shift not in ['morning', 'night', 'all']:
        return {
            'status': 'error',
            'error': f'Invalid shift. Must be morning, night, or all. Got: {shift}'
        }
    
    # Check if equipment exists
    try:
        equipment = Equipment.objects.get(name=equipment_name)
    except Equipment.DoesNotExist:
        available = list(Equipment.objects.values_list('name', flat=True).order_by('name'))
        return {
            'status': 'error',
            'error': f'Equipment "{equipment_name}" not found',
            'available_equipment': available
        }
    
    # Build query using shift_date
    # query = ConnectionStatus.objects.filter(
    #     equipment=equipment,
    #     shift_date=target_date,
    #     connection_status='success'
    # ).order_by('recorded_at')
    # Build query using shift_date
    query = ConnectionStatus.objects.filter(
        equipment=equipment,
        shift_date=target_date,
        connection_status='success'
    ).order_by('recorded_at', 'id')  # ✅ ADD 'id' as tiebreaker!
    
    if shift != 'all':
        query = query.filter(shift=shift)
    
    # Group items by shift
    items_summary = {}
    
    for record in query:
        eq_name = record.equipment.name
        shift_type = record.shift
        key = f"{eq_name}_{shift_type}"
        
        if key not in items_summary:
            items_summary[key] = {
                'equipment': eq_name,
                'shift': shift_type,
                'shift_label': 'Morning (08:00 - 20:00)' if shift_type == 'morning' else 'Night (20:00 - 08:00)',
                'items': {},
                'first_record_time': record.recorded_at,
                'last_record_time': record.recorded_at,
                'record_count': 0
            }
        
        items_summary[key]['last_record_time'] = record.recorded_at
        items_summary[key]['record_count'] += 1
        
        if record.items_data:
            for item_name, value in record.items_data.items():
                if item_name not in items_summary[key]['items']:
                    items_summary[key]['items'][item_name] = {
                        'all_values': [],
                    }
                
                items_summary[key]['items'][item_name]['all_values'].append(value)
    
    # Calculate differences with zero-based reset logic
    equipment_stats = []
    for key, summary in items_summary.items():
        items_with_diff = []
        
        for item_name, item_stats in summary['items'].items():
            all_values = item_stats['all_values']
            
            # Calculate difference
            calc_result = calculate_difference_with_reset(all_values)
            
            item_response = {
                'name': item_name,
                'first_value': calc_result['first_value'],
                'last_value': calc_result['last_value'],
                'difference': calc_result['total_difference'],
                'reset_detected': calc_result['reset_detected'],
                'reset_count': calc_result['reset_count'],
                'count': len(all_values),
            }
            
            # Add detailed information if requested or if reset detected
            if include_details or calc_result['reset_detected']:
                item_response['segments'] = calc_result['segments']
                item_response['all_values'] = all_values
            
            items_with_diff.append(item_response)
        
        items_with_diff.sort(key=lambda x: x['name'])
        
        duration = int((summary['last_record_time'] - summary['first_record_time']).total_seconds() / 60)
        
        equipment_stats.append({
            'equipment': summary['equipment'],
            'shift': summary['shift'],
            'shift_label': summary['shift_label'],
            'items': items_with_diff,
            'first_record_time': format_datetime_local(summary['first_record_time']),  # ✅ CONVERT TO LOCAL TZ
            'last_record_time': format_datetime_local(summary['last_record_time']),    # ✅ CONVERT TO LOCAL TZ
            'record_count': summary['record_count'],
            'duration_minutes': duration,
        })
    
    return {
        'status': 'success',
        'data': {
            'target_date': target_date.strftime('%Y-%m-%d'),
            'shift_filter': shift,
            'equipment_filter': equipment_name,
            'equipment_stats': equipment_stats,
            'total_records': query.count(),
            'timestamp': format_datetime_local(timezone.now()),  # ✅ CONVERT TO LOCAL TZ
        }
    }


def get_items_data_filtered(equipment_name=None, target_date=None, shift='all', include_details=False):
    """
    Get items data with smart defaults
    Uses shift_date column and converts times to local timezone
    """
    
    # ========== 1. HANDLE DATE RANGE ==========
    date_auto = False
    
    if target_date is None:
        # Get last 7 days (whole week)
        to_date = timezone.now().date()
        from_date = to_date - timedelta(days=6)  # Last 7 days including today
        date_auto = True
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
    
    # ========== 2. HANDLE EQUIPMENT ==========
    equipment_auto = False
    equipment_list = []
    
    if equipment_name is None:
        # Get ALL equipment
        equipment_list = list(Equipment.objects.all().order_by('name'))
        equipment_auto = True
        equipment_filter_display = None
    else:
        # Get specific equipment
        try:
            equipment = Equipment.objects.get(name=equipment_name)
            equipment_list = [equipment]
            equipment_filter_display = equipment_name
        except Equipment.DoesNotExist:
            available = list(Equipment.objects.values_list('name', flat=True).order_by('name'))
            return {
                'status': 'error',
                'error': f'Equipment "{equipment_name}" not found',
                'available_equipment': available
            }
    
    # ========== 3. VALIDATE SHIFT ==========
    if shift not in ['morning', 'night', 'all']:
        return {
            'status': 'error',
            'error': f'Invalid shift. Must be morning, night, or all. Got: {shift}'
        }
    
    # ========== 4. BUILD QUERY USING shift_date ==========
    # query = ConnectionStatus.objects.filter(
    #     equipment__in=equipment_list,
    #     shift_date__gte=from_date,
    #     shift_date__lte=to_date,
    #     connection_status='success'
    # ).order_by('equipment', 'recorded_at')
    # ✅ FIXED: Add secondary sort by ID for stable ordering
    query = ConnectionStatus.objects.filter(
        equipment__in=equipment_list,
        shift_date__gte=from_date,
        shift_date__lte=to_date,
        connection_status='success'
    ).order_by('equipment', 'recorded_at', 'id')  # ✅ ADD 'id' as tiebreaker!
    
    if shift != 'all':
        query = query.filter(shift=shift)
    
    # ========== 5. GROUP ITEMS BY EQUIPMENT & SHIFT ==========
    items_summary = {}
    
    for record in query:
        eq_name = record.equipment.name
        shift_type = record.shift
        key = f"{eq_name}_{shift_type}"
        
        if key not in items_summary:
            items_summary[key] = {
                'equipment': eq_name,
                'shift': shift_type,
                'shift_label': 'Morning (08:00 - 20:00)' if shift_type == 'morning' else 'Night (20:00 - 08:00)',
                'items': {},
                'first_record_time': record.recorded_at,
                'last_record_time': record.recorded_at,
                'record_count': 0
            }
        
        items_summary[key]['last_record_time'] = record.recorded_at
        items_summary[key]['record_count'] += 1
        
        if record.items_data:
            for item_name, value in record.items_data.items():
                # ✅ ONLY INCLUDE REQUIRED ITEMS
                if item_name not in REQUIRED_ITEMS:
                    continue
                
                if item_name not in items_summary[key]['items']:
                    items_summary[key]['items'][item_name] = {
                        'all_values': [],
                    }
                
                items_summary[key]['items'][item_name]['all_values'].append(value)
    
    # ========== 6. CALCULATE DIFFERENCES ==========
    equipment_stats = []
    for key, summary in items_summary.items():
        items_with_diff = []
        
        for item_name, item_stats in summary['items'].items():
            all_values = item_stats['all_values']
            
            # Calculate difference
            calc_result = calculate_difference_with_reset(all_values)
            
            item_response = {
                'name': item_name,
                'first_value': calc_result['first_value'],
                'last_value': calc_result['last_value'],
                'difference': calc_result['total_difference'],
                'reset_detected': calc_result['reset_detected'],
                'reset_count': calc_result['reset_count'],
                'count': len(all_values),
            }
            
            # Add detailed information if requested or if reset detected
            if include_details or calc_result['reset_detected']:
                item_response['segments'] = calc_result['segments']
                item_response['all_values'] = all_values
            
            items_with_diff.append(item_response)
        
        items_with_diff.sort(key=lambda x: x['name'])
        
        # Only include if has items
        if items_with_diff:
            duration = int((summary['last_record_time'] - summary['first_record_time']).total_seconds() / 60)
            
            equipment_stats.append({
                'equipment': summary['equipment'],
                'shift': summary['shift'],
                'shift_label': summary['shift_label'],
                'items': items_with_diff,
                'first_record_time': format_datetime_local(summary['first_record_time']),  # ✅ CONVERT TO LOCAL TZ
                'last_record_time': format_datetime_local(summary['last_record_time']),    # ✅ CONVERT TO LOCAL TZ
                'record_count': summary['record_count'],
                'duration_minutes': duration,
            })
    
    return {
        'status': 'success',
        'data': {
            'date_range': {
                'from': from_date.strftime('%Y-%m-%d'),
                'to': to_date.strftime('%Y-%m-%d'),
            },
            'shift_filter': shift,
            'equipment_filter': equipment_filter_display,
            'filter_info': {
                'equipment_auto': equipment_auto,
                'date_auto': date_auto,
                'items_filtered': True,
                'items_included': REQUIRED_ITEMS,
            },
            'equipment_stats': equipment_stats,
            'total_records': query.count(),
            'timestamp': format_datetime_local(timezone.now()),  # ✅ CONVERT TO LOCAL TZ
        }
    }