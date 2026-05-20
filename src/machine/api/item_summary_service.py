""" Item Summary Report Service

Generates cross-equipment item summary reports:
- Rows: Item names
- Columns: Equipment names
- Values: Item values (total/average based on period)

Date handling:
- Blank/None = This week (Monday-based)
- YYYY-MM-DD = Single date
- YYYY-MM = Entire month
"""

from datetime import datetime, timedelta
from django.utils import timezone
from machine.api.services import get_items_data_filtered
import pytz
import logging

logger = logging.getLogger(__name__)


def get_item_summary_report(date_param=None):
    """
    Get item summary report across all equipment
    
    Args:
        date_param: None (this week), 'YYYY-MM-DD' (single date)
    
    Returns:
        {
            'status': 'success',
            'data': {
                'period': 'week' | 'date' | 'month',
                'date_range': {'from': '...', 'to': '...'},
                'items': ['Crane On Minute', 'Number of Move', ...],
                'equipment': ['RTG09', 'RTG10', ...],
                'data': {
                    'Crane On Minute': {
                        'RTG09': 1500.5,
                        'RTG10': 1200.3,
                        ...
                    },
                    ...
                },
                'timestamp': '...'
            }
        }
    """
    
    # ✅ DETERMINE DATE RANGE
    tz = pytz.timezone('Asia/Bangkok')
    now = datetime.now(tz=tz)
    
    if date_param is None:
        # This week (Monday-based)
        start_date = now.date() - timedelta(days=now.weekday())  # Monday
        end_date = start_date + timedelta(days=6)  # Sunday
        period = 'week'
        period_label = f"Week of {start_date.strftime('%Y-%m-%d')}"
        date_list = _get_date_range(start_date, end_date)
        
    else:
        # Single date (YYYY-MM-DD) , meaning week of that date
        try:
            target_date = datetime.strptime(date_param, '%Y-%m-%d').date()
            start_date = target_date - timedelta(days=target_date.weekday())  # Monday of that week
            end_date = start_date + timedelta(days=6)  # Sunday of that week
            period = 'week'
            period_label = f"Week of {target_date.strftime('%Y-%m-%d')}"
            date_list = _get_date_range(start_date, end_date)
        except ValueError:
            return {
                'status': 'error',
                'error': f'Invalid date format: {date_param}. Use YYYY-MM-DD or YYYY-MM'
            }

    
    logger.info(f"📊 Generating item summary for {period}: {start_date} to {end_date}")
    logger.info(f"   Date list: {date_list}")
    
    try:
        # ✅ BUILD ITEM SUMMARY MATRIX (aggregate across all dates)
        items_data = {}  # {'Item Name': {'RTG09': total_value, ...}}
        equipment_set = set()
        
        # ✅ LOOP THROUGH ALL DATES IN RANGE
        for target_date in date_list:
            logger.info(f"   Fetching data for {target_date}")
            
            result = get_items_data_filtered(
                equipment_name=None,  # All equipment
                target_date=target_date.strftime('%Y-%m-%d'),
                shift='all',
                include_details=False,
                filter_items=None  # ✅ Get ALL items, not just
            )
            
            if result['status'] == 'error':
                logger.warning(f"   Error for {target_date}: {result.get('error')}")
                continue
            
            # Extract items from this date
            for equipment_stat in result['data']['equipment_stats']:
                equipment_name = equipment_stat['equipment']
                equipment_set.add(equipment_name)
                
                # Extract items
                for item in equipment_stat.get('items', []):
                    item_name = item.get('name')
                    item_value = item.get('difference', 0)
                    
                    if item_name not in items_data:
                        items_data[item_name] = {}
                    
                    # ✅ ACCUMULATE VALUES (sum across all dates)
                    if equipment_name not in items_data[item_name]:
                        items_data[item_name][equipment_name] = 0
                    
                    items_data[item_name][equipment_name] += item_value
        
        if not items_data or not equipment_set:
            logger.warning("No data found for the requested period")
            return {
                'status': 'error',
                'error': f'No data available for {period_label}'
            }
        
        # ✅ FILL MISSING VALUES WITH 0
        equipment_list = sorted(equipment_set)
        for item_name in items_data:
            for equipment in equipment_list:
                if equipment not in items_data[item_name]:
                    items_data[item_name][equipment] = 0
        
        # Sort items by name
        sorted_items = sorted(items_data.keys())
        
        logger.info(f"✅ Item summary complete: {len(sorted_items)} items, {len(equipment_list)} equipment")
        
        return {
            'status': 'success',
            'data': {
                'period': period,
                'period_label': period_label,
                'date_range': {
                    'from': start_date.strftime('%Y-%m-%d'),
                    'to': end_date.strftime('%Y-%m-%d'),
                },
                'items': sorted_items,
                'equipment': equipment_list,
                'data': items_data,
                'summary': {
                    'total_items': len(sorted_items),
                    'total_equipment': len(equipment_list),
                    'date_count': len(date_list),
                },
                'timestamp': now.strftime('%Y-%m-%d %H:%M:%S %z'),
            }
        }
    
    except Exception as e:
        logger.error(f"Error generating item summary: {e}", exc_info=True)
        return {
            'status': 'error',
            'error': str(e)
        }


def _get_date_range(start_date, end_date):
    """
    Get list of dates from start_date to end_date (inclusive)
    
    Args:
        start_date: datetime.date
        end_date: datetime.date
    
    Returns:
        List of datetime.date objects
    """
    date_list = []
    current = start_date
    
    while current <= end_date:
        date_list.append(current)
        current += timedelta(days=1)
    
    return date_list