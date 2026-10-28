from datetime import datetime, timedelta
import pytz

from machine.models import EquipmentItemShiftSummary


def _resolve_date_range(period_mode=None, from_date=None, to_date=None):
    tz = pytz.timezone('Asia/Bangkok')
    now_date = datetime.now(tz=tz).date()

    if from_date or to_date:
        if from_date is None:
            from_date = to_date
        if to_date is None:
            to_date = from_date
        return from_date, to_date, f"{from_date} to {to_date}"

    if period_mode == 'current_month_window':
        start = now_date.replace(day=1)
        if start.month == 12:
            next_month = start.replace(year=start.year + 1, month=1, day=1)
        else:
            next_month = start.replace(month=start.month + 1, day=1)
        end = next_month - timedelta(days=1)
        return start, end, f"Month of {start.strftime('%Y-%m')}"

    if period_mode == 'last_month_window':
        this_month_start = now_date.replace(day=1)
        end = this_month_start - timedelta(days=1)
        start = end.replace(day=1)
        return start, end, f"Month of {start.strftime('%Y-%m')}"

    start = now_date - timedelta(days=6)
    end = now_date
    return start, end, f"Week of {start.strftime('%Y-%m-%d')}"


def get_item_shift_summary_report(
    period_mode=None,
    from_date=None,
    to_date=None,
    equipment_name=None,
    shift='all',
    item_name=None
):
    """
    Build matrix report from EquipmentItemShiftSummary.
    """
    start_date, end_date, period_label = _resolve_date_range(
        period_mode=period_mode,
        from_date=from_date,
        to_date=to_date
    )

    if start_date > end_date:
        return {
            'status': 'error',
            'error': 'from_date cannot be greater than to_date'
        }

    queryset = EquipmentItemShiftSummary.objects.select_related('equipment').filter(
        shift_date__gte=start_date,
        shift_date__lte=end_date
    )

    if equipment_name:
        queryset = queryset.filter(equipment__name=equipment_name)
    if shift in ['morning', 'night']:
        queryset = queryset.filter(shift=shift)
    if item_name:
        queryset = queryset.filter(item_name=item_name)

    items_data = {}
    equipment_set = set()

    for row in queryset:
        eq_name = row.equipment.name
        equipment_set.add(eq_name)

        if row.item_name not in items_data:
            items_data[row.item_name] = {}
        if eq_name not in items_data[row.item_name]:
            items_data[row.item_name][eq_name] = 0

        items_data[row.item_name][eq_name] += row.difference or 0

    if not items_data:
        return {
            'status': 'error',
            'error': f'No summary data available for {period_label}'
        }

    equipment_list = sorted(equipment_set)
    for key in items_data:
        for eq in equipment_list:
            if eq not in items_data[key]:
                items_data[key][eq] = 0

    sorted_items = sorted(items_data.keys())
    tz = pytz.timezone('Asia/Bangkok')
    now_tz = datetime.now(tz=tz)

    return {
        'status': 'success',
        'data': {
            'period': 'custom' if (from_date or to_date) else (period_mode or 'week'),
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
            },
            'timestamp': now_tz.strftime('%Y-%m-%d %H:%M:%S %z'),
        }
    }
