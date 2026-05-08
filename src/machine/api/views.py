from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from datetime import datetime

from machine.models import ConnectionStatus, Equipment
from machine.api.serializers import ConnectionStatusListSerializer
from machine.api.services import get_items_data, get_items_data_filtered
from machine.api.report_services import (
    get_productivity_report,
    get_productivity_report_detailed,
    get_productivity_comparison_report,
    get_productivity_report_daily,
    get_productivity_report_daily_detailed
)


# ============ ITEMS DATA ENDPOINTS ============

@api_view(['GET'])
# @permission_classes([IsAuthenticated])
def items_data_api(request):
    """
    Get items data with zero-based reset detection
    
    Query Parameters:
    - equipment: Equipment name (required)
    - date: Date in format YYYY-MM-DD (required)
    - shift: 'morning', 'night', or 'all' (default: 'all')
    - include_details: 'true' to include segments and all_values (default: false)
    """
    
    # Get parameters
    equipment_name = request.query_params.get('equipment')
    target_date_str = request.query_params.get('date')
    shift = request.query_params.get('shift', 'all')
    include_details = request.query_params.get('include_details', 'false').lower() == 'true'
    
    # Validate required parameters
    if not equipment_name:
        return Response({
            'error': 'equipment parameter is required',
            'example': '/api/items-data/?equipment=RTG25&date=2026-05-07&shift=morning'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    if not target_date_str:
        return Response({
            'error': 'date parameter is required',
            'format': 'YYYY-MM-DD'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # Call service
    result = get_items_data(equipment_name, target_date_str, shift, include_details)
    
    if result['status'] == 'error':
        return Response(result, status=status.HTTP_404_NOT_FOUND)
    
    return Response({
        'status': 'success',
        'data': result['data']
    })


@api_view(['GET'])
# @permission_classes([IsAuthenticated])
def items_data_smart_api(request):
    """
    Get items data with smart defaults
    
    Features:
    1. equipment: Optional - If not specified, returns ALL equipment
    2. date: Optional - If not specified, returns LAST 7 DAYS (whole week)
    3. Items: Hard-coded to return only: Crane On Hour, Crane On Minute, Number of Move
    
    Query Parameters (all optional):
    - equipment: Equipment name (default: all equipment)
    - date: Date in format YYYY-MM-DD (default: last 7 days)
    - shift: 'morning', 'night', or 'all' (default: 'all')
    - include_details: 'true' to include segments (default: false)
    
    Examples:
    - GET /api/items-data-smart/
      → Get ALL equipment for LAST 7 DAYS, only required items
    
    - GET /api/items-data-smart/?equipment=RTG25
      → Get RTG25 for LAST 7 DAYS, only required items
    
    - GET /api/items-data-smart/?date=2026-05-07
      → Get ALL equipment for 2026-05-07, only required items
    
    - GET /api/items-data-smart/?equipment=RTG25&date=2026-05-07&shift=morning
      → Get RTG25 on 2026-05-07 morning shift, only required items
    """
    
    # Get optional parameters
    equipment_name = request.query_params.get('equipment')  # None = all equipment
    target_date_str = request.query_params.get('date')      # None = last 7 days
    shift = request.query_params.get('shift', 'all')
    include_details = request.query_params.get('include_details', 'false').lower() == 'true'
    
    # Validate shift
    if shift not in ['morning', 'night', 'all']:
        return Response({
            'error': 'shift must be morning, night, or all',
            'received': shift
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # Call service with smart defaults
    result = get_items_data_filtered(equipment_name, target_date_str, shift, include_details)
    
    if result['status'] == 'error':
        return Response(result, status=status.HTTP_404_NOT_FOUND)
    
    return Response({
        'status': 'success',
        'data': result['data']
    })


@api_view(['GET'])
# @permission_classes([IsAuthenticated])
def items_data_detailed_api(request):
    """
    Get detailed items data with all records and zero-based reset logic
    """
    
    equipment_name = request.query_params.get('equipment')
    target_date_str = request.query_params.get('date')
    shift = request.query_params.get('shift', 'all')
    
    if not equipment_name or not target_date_str:
        return Response({
            'error': 'equipment and date parameters are required'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # Call service with include_details=True
    result = get_items_data(equipment_name, target_date_str, shift, include_details=True)
    
    if result['status'] == 'error':
        return Response(result, status=status.HTTP_404_NOT_FOUND)
    
    # Parse date
    try:
        target_date = datetime.strptime(target_date_str, '%Y-%m-%d').date()
    except ValueError:
        target_date = target_date_str
    
    # Get equipment for query
    try:
        equipment = Equipment.objects.get(name=equipment_name)
    except Equipment.DoesNotExist:
        return Response({'error': 'Equipment not found'}, status=status.HTTP_404_NOT_FOUND)
    
    # Build query for all records
    query = ConnectionStatus.objects.filter(
        equipment=equipment,
        shift_date=target_date,
        connection_status='success'
    ).order_by('recorded_at')
    
    if shift != 'all':
        query = query.filter(shift=shift)
    
    records_serializer = ConnectionStatusListSerializer(query, many=True)
    
    return Response({
        'status': 'success',
        'data': {
            **result['data'],
            'records': records_serializer.data,
        }
    })


# ============ PRODUCTIVITY REPORT ENDPOINTS ============

@api_view(['GET'])
# @permission_classes([IsAuthenticated])
def productivity_report_api(request):
    """
    Get productivity report with flexible format options
    
    Query Parameters (all optional):
    - equipment: Equipment name (default: all equipment)
    - date: Date in format YYYY-MM-DD (default: last 7 days)
    - format: 'daily' for daily breakdown or 'summary' for 7-day summary (default: 'summary')
    - shift: 'morning', 'night', or 'all' (default: 'all')
    
    Format Options:
    - 'summary': Returns aggregated data for entire period (default)
      Response: One entry per equipment with morning/night/total
    
    - 'daily': Returns daily breakdown (one report per day)
      Response: Multiple reports, one for each day with equipment data
    
    Examples:
    ============ SUMMARY FORMAT (default) ============
    - GET /api/productivity-report/
      → All equipment, Last 7 days, SUMMARIZED
    
    - GET /api/productivity-report/?date=2026-05-07
      → All equipment, 2026-05-07, SUMMARIZED
    
    - GET /api/productivity-report/?equipment=RTG22
      → RTG22, Last 7 days, SUMMARIZED
    
    ============ DAILY FORMAT ============
    - GET /api/productivity-report/?format=daily
      → All equipment, Last 7 days, DAILY BREAKDOWN (7 reports)
    
    - GET /api/productivity-report/?format=daily&date=2026-05-07
      → All equipment, starting 2026-05-07, DAILY BREAKDOWN
    
    - GET /api/productivity-report/?format=daily&equipment=RTG22
      → RTG22, Last 7 days, DAILY BREAKDOWN
    """
    
    # Get parameters
    equipment_name = request.query_params.get('equipment')
    target_date_str = request.query_params.get('date')
    format_type = request.query_params.get('format', 'summary')
    shift = request.query_params.get('shift', 'all')
    
    # Validate format
    if format_type not in ['summary', 'daily']:
        return Response({
            'error': 'Invalid format. Must be "summary" or "daily"',
            'received': format_type,
            'examples': {
                'summary': '/api/productivity-report/?format=summary',
                'daily': '/api/productivity-report/?format=daily'
            }
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # ✅ GET REPORT BASED ON FORMAT
    if format_type == 'daily':
        result = get_productivity_report_daily(equipment_name, target_date_str, shift)
    else:  # summary
        result = get_productivity_report(equipment_name, target_date_str, shift)
    
    if result['status'] == 'error':
        return Response(result, status=status.HTTP_404_NOT_FOUND)
    
    return Response({
        'status': 'success',
        'format': format_type,
        'data': result['data']
    })


@api_view(['GET'])
# @permission_classes([IsAuthenticated])
def productivity_report_detailed_api(request):
    """
    Get detailed productivity report with flexible format options
    
    Query Parameters (all optional):
    - equipment: Equipment name (default: all equipment)
    - date: Date in format YYYY-MM-DD (default: last 7 days)
    - format: 'daily' for daily + trends or 'summary' for detailed summary (default: 'summary')
    
    Format Options:
    - 'summary': Returns detailed metrics for aggregated period
    - 'daily': Returns daily breakdown with trend analysis
    
    Examples:
    - GET /api/productivity-report-detailed/?format=summary
    - GET /api/productivity-report-detailed/?format=daily
    """
    
    equipment_name = request.query_params.get('equipment')
    target_date_str = request.query_params.get('date')
    format_type = request.query_params.get('format', 'summary')
    
    # Validate format
    if format_type not in ['summary', 'daily']:
        return Response({
            'error': 'Invalid format. Must be "summary" or "daily"',
            'received': format_type
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # ✅ GET DETAILED REPORT BASED ON FORMAT
    if format_type == 'daily':
        result = get_productivity_report_daily_detailed(equipment_name, target_date_str)
    else:  # summary
        result = get_productivity_report_detailed(equipment_name, target_date_str)
    
    if result['status'] == 'error':
        return Response(result, status=status.HTTP_404_NOT_FOUND)
    
    return Response({
        'status': 'success',
        'format': format_type,
        'data': result['data']
    })


# ✅ NEW: Daily report endpoints

@api_view(['GET'])
# @permission_classes([IsAuthenticated])
def productivity_report_daily_api(request):
    """
    Get productivity report broken down by individual days
    
    Returns one report per day (not summarized)
    
    Query Parameters (all optional):
    - equipment: Equipment name (default: all equipment)
    - date: Start date in format YYYY-MM-DD (default: last 7 days)
    - shift: 'morning', 'night', or 'all' (default: 'all')
    
    Examples:
    - GET /api/productivity-report-daily/
      → Get ALL equipment for LAST 7 DAYS (one report per day)
    
    - GET /api/productivity-report-daily/?date=2026-05-07
      → Get ALL equipment starting from 2026-05-07
    
    - GET /api/productivity-report-daily/?equipment=RTG22
      → Get RTG22 for LAST 7 DAYS (one report per day)
    
    - GET /api/productivity-report-daily/?equipment=RTG22&date=2026-05-07
      → Get RTG22 starting from 2026-05-07
    """
    
    equipment_name = request.query_params.get('equipment')
    target_date_str = request.query_params.get('date')
    shift = request.query_params.get('shift', 'all')
    
    result = get_productivity_report_daily(equipment_name, target_date_str, shift)
    
    if result['status'] == 'error':
        return Response(result, status=status.HTTP_404_NOT_FOUND)
    
    return Response({
        'status': 'success',
        'data': result['data']
    })


@api_view(['GET'])
# @permission_classes([IsAuthenticated])
def productivity_report_daily_detailed_api(request):
    """
    Get detailed daily productivity report with trend analysis
    
    Includes:
    - Daily breakdown
    - Trend analysis
    - Best/worst performing days
    - Summary metrics (total crane minutes, total moves, averages)
    
    Query Parameters (all optional):
    - equipment: Equipment name (default: all equipment)
    - date: Start date in format YYYY-MM-DD (default: last 7 days)
    
    Examples:
    - GET /api/productivity-report-daily-detailed/
      → Last 7 days with trends
    
    - GET /api/productivity-report-daily-detailed/?date=2026-05-01
      → Starting from 2026-05-01 with trends
    
    - GET /api/productivity-report-daily-detailed/?equipment=RTG22
      → RTG22 last 7 days with trends
    """
    
    equipment_name = request.query_params.get('equipment')
    target_date_str = request.query_params.get('date')
    
    result = get_productivity_report_daily_detailed(equipment_name, target_date_str)
    
    if result['status'] == 'error':
        return Response(result, status=status.HTTP_404_NOT_FOUND)
    
    return Response({
        'status': 'success',
        'data': result['data']
    })


@api_view(['GET'])
# @permission_classes([IsAuthenticated])
def productivity_comparison_api(request):
    """
    Get productivity comparison report
    
    Shows best/worst performing equipment and statistics
    
    Query Parameters (optional):
    - equipment: Comma-separated equipment names (default: all)
    - date: Date in format YYYY-MM-DD (default: last 7 days)
    
    Example:
    - GET /api/productivity-comparison/
    - GET /api/productivity-comparison/?equipment=RTG22,RTG25
    - GET /api/productivity-comparison/?date=2026-05-07
    """
    
    equipment_param = request.query_params.get('equipment')
    target_date_str = request.query_params.get('date')
    
    # Parse equipment list
    equipment_names = None
    if equipment_param:
        equipment_names = [e.strip() for e in equipment_param.split(',')]
    
    result = get_productivity_comparison_report(equipment_names, target_date_str)
    
    if result['status'] == 'error':
        return Response(result, status=status.HTTP_404_NOT_FOUND)
    
    return Response({
        'status': 'success',
        'data': result['data']
    })


# ============ EQUIPMENT ENDPOINTS ============

@api_view(['GET'])
# @permission_classes([IsAuthenticated])
def available_equipment_api(request):
    """
    Get list of all available equipment
    """
    equipment_list = list(
        Equipment.objects.values('id', 'name', 'ip').order_by('name')
    )
    
    return Response({
        'status': 'success',
        'count': len(equipment_list),
        'data': equipment_list
    })