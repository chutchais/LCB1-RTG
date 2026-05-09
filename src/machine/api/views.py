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

from django.http import HttpResponse
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from machine.api.report_services import get_productivity_report_daily
from machine.api.html_generators import json_to_html_table, json_to_plain_text_table, json_to_csv,json_to_excel  # ✅ ADD IMPORT

from datetime import datetime
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


@api_view(['GET'])
@permission_classes([AllowAny])
def productivity_report_daily_html(request):
    """
    Get productivity report as HTML table
    
    Query Parameters (all optional):
    - equipment: Equipment name (default: all equipment)
    - date: Start date in format YYYY-MM-DD (default: last 7 days)
    - shift: 'morning', 'night', or 'all' (default: 'all')
    
    Examples:
    - GET /api/productivity-report-daily-html/
      → Returns HTML table for last 7 days
    
    - GET /api/productivity-report-daily-html/?date=2026-05-08
      → Returns HTML table for 2026-05-08
    """
    
    equipment_name = request.query_params.get('equipment')
    target_date_str = request.query_params.get('date')
    shift = request.query_params.get('shift', 'all')
    
    # Get report data
    result = get_productivity_report_daily(equipment_name, target_date_str, shift)
    
    if result['status'] == 'error':
        html = f'<p style="color: red;">Error: {result["error"]}</p>'
        return HttpResponse(html, content_type='text/html')
    
    # Convert to HTML table
    html_table = json_to_html_table(result['data'])
    
    # Wrap in basic HTML
    html = f'''
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <title>Daily Productivity Report</title>
        <style>
            body {{
                font-family: Arial, sans-serif;
                padding: 20px;
                background-color: #f5f5f5;
            }}
            h1 {{
                color: #2c3e50;
            }}
            .info {{
                background-color: white;
                padding: 15px;
                border-radius: 5px;
                margin-bottom: 20px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            }}
            .info p {{
                margin: 5px 0;
            }}
            table {{
                background-color: white;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                margin: 20px 0;
            }}
            td, th {{
                padding: 8px 12px;
                text-align: center;
            }}
            th {{
                color: white;
            }}
            @media print {{
                body {{
                    background-color: white;
                }}
                .info {{
                    display: none;
                }}
            }}
        </style>
    </head>
    <body>
        <h1>📊 Daily Productivity Report</h1>
        <div class="info">
            <p><strong>Date Range:</strong> {result['data']['date_range']['from']} to {result['data']['date_range']['to']}</p>
            <p><strong>Equipment:</strong> {result['data']['summary']['total_equipment']}</p>
            <p><strong>Generated:</strong> {result['data'].get('timestamp', 'N/A')}</p>
        </div>
        {html_table}
    </body>
    </html>
    '''
    
    return HttpResponse(html, content_type='text/html')


@api_view(['GET'])
@permission_classes([AllowAny])
def productivity_report_daily_text(request):
    """
    Get productivity report as plain text table (for console/email)
    
    Query Parameters (all optional):
    - equipment: Equipment name (default: all equipment)
    - date: Start date in format YYYY-MM-DD (default: last 7 days)
    - shift: 'morning', 'night', or 'all' (default: 'all')
    """
    
    equipment_name = request.query_params.get('equipment')
    target_date_str = request.query_params.get('date')
    shift = request.query_params.get('shift', 'all')
    
    # Get report data
    result = get_productivity_report_daily(equipment_name, target_date_str, shift)
    
    if result['status'] == 'error':
        text = f'Error: {result["error"]}'
        return HttpResponse(text, content_type='text/plain')
    
    # Convert to plain text table
    text_table = json_to_plain_text_table(result['data'])
    
    # Add header info
    full_text = f'''
Daily Productivity Report
Date Range: {result['data']['date_range']['from']} to {result['data']['date_range']['to']}
Equipment: {result['data']['summary']['total_equipment']}
Generated: {result['data'].get('timestamp', 'N/A')}

{text_table}
    '''
    
    return HttpResponse(full_text, content_type='text/plain')


@api_view(['GET'])
@permission_classes([AllowAny])
def productivity_report_daily_csv_api(request):
    """
    Get productivity report as CSV file
    
    Query Parameters (all optional):
    - equipment: Equipment name (default: all equipment)
    - date: Start date in format YYYY-MM-DD (default: last 7 days)
    - shift: 'morning', 'night', or 'all' (default: 'all')
    """
    
    equipment_name = request.query_params.get('equipment')
    target_date_str = request.query_params.get('date')
    shift = request.query_params.get('shift', 'all')
    
    # Get report data
    result = get_productivity_report_daily(equipment_name, target_date_str, shift)
    
    if result['status'] == 'error':
        return HttpResponse(f'Error: {result["error"]}', content_type='text/plain', status=404)
    
    # Convert to CSV
    csv_data = json_to_csv(result['data'])
    
    # Return as downloadable file
    response = HttpResponse(csv_data, content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="productivity-report-{datetime.now().strftime("%Y-%m-%d")}.csv"'
    
    return response

@api_view(['GET'])
@permission_classes([AllowAny])
def productivity_report_daily_excel(request):
    """
    Get productivity report as Excel file (.xlsx)
    
    Query Parameters (all optional):
    - equipment: Equipment name (default: all equipment)
    - date: Start date in format YYYY-MM-DD (default: last 7 days)
    - shift: 'morning', 'night', or 'all' (default: 'all')
    
    Examples:
    - GET /api/productivity-report-daily-excel/
      → Downloads Excel file for last 7 days
    
    - GET /api/productivity-report-daily-excel/?date=2026-05-08
      → Downloads Excel file for 2026-05-08
    """
    
    equipment_name = request.query_params.get('equipment')
    target_date_str = request.query_params.get('date')
    shift = request.query_params.get('shift', 'all')
    
    # Get report data
    result = get_productivity_report_daily(equipment_name, target_date_str, shift)
    
    if result['status'] == 'error':
        return HttpResponse(f'Error: {result["error"]}', content_type='text/plain', status=404)
    
    # Convert to Excel
    try:
        excel_data = json_to_excel(result['data'])
        
        # Return as downloadable file
        response = HttpResponse(
            excel_data,
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = f'attachment; filename="productivity-report-{datetime.now().strftime("%Y-%m-%d")}.xlsx"'
        
        return response
    except Exception as e:
        return HttpResponse(f'Error generating Excel: {str(e)}', content_type='text/plain', status=500)


# =========== DIAGNOSTIC ENDPOINTS ============
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from machine.api.report_services import get_productivity_report
from machine.api.services import get_items_data_filtered
import logging

logger = logging.getLogger(__name__)

@require_http_methods(["GET"])
def productivity_diagnostic(request):
    """
    Diagnostic page to investigate productivity calculations
    
    Shows:
    1. Productivity report (summary with hour, move, productivity)
    2. Raw items-data-smart (detailed segments and all_values)
    3. Side-by-side comparison to identify calculation errors
    4. ✅ Connection status timeline (24 hours by shift)
    
    Usage:
    ?date=2026-05-09&equipment=RTG21
    """
    
    from machine.models import ConnectionStatus
    import pytz
    from datetime import datetime, timedelta
    
    # Get parameters
    date_str = request.GET.get('date')
    equipment_name = request.GET.get('equipment')
    
    if not date_str or not equipment_name:
        return JsonResponse({
            'status': 'error',
            'error': 'Missing parameters: date and equipment required',
            'example': '/machine/api/productivity-diagnostic/?date=2026-05-09&equipment=RTG21'
        }, status=400)
    
    logger.info(f"🔍 Diagnostic request: date={date_str}, equipment={equipment_name}")
    
    try:
        # Get productivity report (summary)
        report_result = get_productivity_report(
            equipment_name=equipment_name,
            target_date=date_str,
            shift='all'
        )
        
        logger.info(f"📊 Report result: {report_result['status']}")
        if report_result['status'] == 'error':
            return JsonResponse(report_result, status=400)
        
        # Get raw items data (with details)
        items_result = get_items_data_filtered(
            equipment_name=equipment_name,
            target_date=date_str,
            shift='all',
            include_details=True
        )
        
        logger.info(f"📊 Items result: {items_result['status']}")
        if items_result['status'] == 'error':
            return JsonResponse(items_result, status=400)
        
        # Build diagnostic response
        diagnostic_data = {
            'status': 'success',
            'parameters': {
                'date': date_str,
                'equipment': equipment_name,
            },
            'summary': {
                'morning': None,
                'night': None,
                'total': None,
            },
            'raw_data': {},
            'comparison': {},
            'timeline': {}  # ✅ NEW: Timeline data
        }
        
        # ✅ EXTRACT SUMMARY DATA FROM REPORT
        logger.info(f"📋 Extracting summary from report...")
        if report_result['data'].get('daily_reports'):
            for day_report in report_result['data']['daily_reports']:
                logger.info(f"📅 Checking day: {day_report.get('date')}")
                for eq_stat in day_report.get('equipment', []):
                    if eq_stat.get('equipment') == equipment_name:
                        logger.info(f"✅ Found equipment: {equipment_name}")
                        
                        diagnostic_data['summary'] = {
                            'equipment': equipment_name,
                            'morning': eq_stat.get('morning'),
                            'night': eq_stat.get('night'),
                            'total': eq_stat.get('total'),
                        }
        
        # ✅ EXTRACT RAW DATA FROM ITEMS
        logger.info(f"📋 Extracting raw data from items...")
        if items_result['data'].get('equipment_stats'):
            for eq_stat in items_result['data']['equipment_stats']:
                if eq_stat.get('equipment') == equipment_name:
                    shift_key = eq_stat['shift']
                    logger.info(f"✅ Found shift: {shift_key}")
                    
                    diagnostic_data['raw_data'][shift_key] = {
                        'equipment': eq_stat['equipment'],
                        'shift': eq_stat['shift'],
                        'shift_label': eq_stat.get('shift_label', ''),
                        'first_record_time': eq_stat.get('first_record_time', ''),
                        'last_record_time': eq_stat.get('last_record_time', ''),
                        'record_count': eq_stat.get('record_count', 0),
                        'duration_minutes': eq_stat.get('duration_minutes', 0),
                        'items': {}
                    }
                    
                    for item in eq_stat.get('items', []):
                        item_name = item.get('name', 'Unknown')
                        
                        diagnostic_data['raw_data'][shift_key]['items'][item_name] = {
                            'first_value': item.get('first_value'),
                            'last_value': item.get('last_value'),
                            'difference': float(item.get('difference', 0) or 0),
                            'reset_detected': item.get('reset_detected', False),
                            'reset_count': item.get('reset_count', 0),
                            'count': item.get('count', 0),
                            'segments': item.get('segments', []),
                            'all_values': item.get('all_values', [])
                        }
        
        # ✅ BUILD COMPARISON/VERIFICATION
        logger.info(f"📋 Building comparisons...")
        for shift_key in ['morning', 'night']:
            summary_shift = diagnostic_data['summary'].get(shift_key)
            raw_shift = diagnostic_data['raw_data'].get(shift_key)
            
            if summary_shift and raw_shift:
                logger.info(f"✅ Creating comparison for {shift_key}")
                verification = _verify_calculation(summary_shift, raw_shift)
                
                diagnostic_data['comparison'][shift_key] = {
                    'summary': summary_shift,
                    'raw': raw_shift,
                    'verification': verification
                }
        
        # ✅ BUILD TIMELINE (24 hours by shift)
        logger.info(f"📋 Building timeline...")
        diagnostic_data['timeline'] = _build_connection_timeline(equipment_name, date_str)
        logger.info(f"   Timeline: {len(diagnostic_data['timeline']['hours'])} hour records")
        
        logger.info(f"✅ Diagnostic complete")
        return JsonResponse(diagnostic_data, safe=False)
    
    except Exception as e:
        logger.error(f"Error in diagnostic: {e}", exc_info=True)
        return JsonResponse({
            'status': 'error',
            'error': f'Diagnostic error: {str(e)}'
        }, status=500)

# def _build_connection_timeline(equipment_name, date_str):
#     """
#     Build 24-hour timeline of connection status records
    
#     Shows:
#     - Morning shift: 08:00 - 19:59 (12 hours)
#     - Night shift: 20:00 - 07:59 (12 hours)
    
#     Each hour is represented by all records in that hour
#     Status: success=green, failed=red, timeout=orange, partial=yellow
#     """
#     from machine.models import ConnectionStatus, Equipment
#     from datetime import datetime, timedelta
#     import pytz
    
#     try:
#         equipment = Equipment.objects.get(name=equipment_name)
#     except Equipment.DoesNotExist:
#         return {'status': 'error', 'message': f'Equipment not found: {equipment_name}'}
    
#     # Parse date
#     try:
#         target_date = datetime.strptime(date_str, '%Y-%m-%d').date()
#     except ValueError:
#         return {'status': 'error', 'message': f'Invalid date format: {date_str}'}
    
#     tz = pytz.timezone('Asia/Bangkok')
    
#     # Get all records for this equipment on this date
#     records = ConnectionStatus.objects.filter(
#         equipment=equipment,
#         shift_date__in=[target_date, target_date - timedelta(days=1)]
#     ).order_by('recorded_at','id')
    
#     timeline_data = {
#         'date': date_str,
#         'equipment': equipment_name,
#         'hours': [],
#         'summary': {
#             'total_records': 0,
#             'success_count': 0,
#             'failed_count': 0,
#             'timeout_count': 0,
#             'partial_count': 0,
#         }
#     }
    
#     hours_data = {}
    
#     # Initialize 24 hours
#     for hour in range(24):
#         hours_data[hour] = {
#             'hour': hour,
#             'hour_display': f'{hour:02d}:00',
#             'shift': 'morning' if 8 <= hour < 20 else 'night',
#             'records': [],
#             'status': 'no_data',
#             'status_color': '#cccccc',
#             'success_count': 0,
#             'failed_count': 0,
#             'timeout_count': 0,
#             'partial_count': 0,
#         }
    
#     # Group records by hour
#     for record in records:
#         record_time = record.recorded_at.astimezone(tz)
        
#         record_date = record_time.date()
#         record_hour = record_time.hour
        
#         # Check if this record belongs to our timeline
#         is_in_timeline = False
#         if record_date == target_date and 8 <= record_hour < 20:
#             is_in_timeline = True
#         elif record_date == target_date and 20 <= record_hour < 24:
#             is_in_timeline = True
#         elif record_date == target_date - timedelta(days=1) and 0 <= record_hour < 8:
#             is_in_timeline = True
        
#         if not is_in_timeline:
#             continue
        
#         timeline_data['summary']['total_records'] += 1
        
#         status = record.connection_status
#         if status == 'success':
#             timeline_data['summary']['success_count'] += 1
#         elif status == 'failed':
#             timeline_data['summary']['failed_count'] += 1
#         elif status == 'timeout':
#             timeline_data['summary']['timeout_count'] += 1
#         elif status == 'partial':
#             timeline_data['summary']['partial_count'] += 1
        
#         hour_key = record_hour
        
#         # ✅ BUILD DETAILED RECORD INFO
#         record_detail = {
#             'time': record_time.strftime('%H:%M:%S'),
#             'status': status,
#             'error_message': record.error_message or '',
#             'items': {}
#         }
        
#         # Extract item data if available
#         if record.items_data:
#             if 'Crane On Minute' in record.items_data:
#                 record_detail['items']['crane_on_minute'] = record.items_data['Crane On Minute']
#             if 'Number of Move' in record.items_data:
#                 record_detail['items']['number_of_move'] = record.items_data['Number of Move']
        
#         hours_data[hour_key]['records'].append(record_detail)
        
#         # Update hour counts
#         if status == 'success':
#             hours_data[hour_key]['success_count'] += 1
#         elif status == 'failed':
#             hours_data[hour_key]['failed_count'] += 1
#         elif status == 'timeout':
#             hours_data[hour_key]['timeout_count'] += 1
#         elif status == 'partial':
#             hours_data[hour_key]['partial_count'] += 1
    
#     # Determine status for each hour
#     for hour_key in sorted(hours_data.keys()):
#         hour_data = hours_data[hour_key]
        
#         if len(hour_data['records']) == 0:
#             hour_data['status'] = 'no_data'
#             hour_data['status_color'] = '#cccccc'
#         elif hour_data['success_count'] > 0 and hour_data['failed_count'] == 0 and hour_data['timeout_count'] == 0:
#             hour_data['status'] = 'success'
#             hour_data['status_color'] = '#4CAF50'
#         elif hour_data['failed_count'] > 0:
#             hour_data['status'] = 'failed'
#             hour_data['status_color'] = '#f44336'
#         elif hour_data['timeout_count'] > 0:
#             hour_data['status'] = 'timeout'
#             hour_data['status_color'] = '#ff9800'
#         elif hour_data['partial_count'] > 0:
#             hour_data['status'] = 'partial'
#             hour_data['status_color'] = '#ffeb3b'
#         else:
#             hour_data['status'] = 'mixed'
#             hour_data['status_color'] = '#9e9e9e'
        
#         timeline_data['hours'].append(hour_data)
    
#     logger.info(f"Timeline complete: {timeline_data['summary']['total_records']} records")
    
#     return timeline_data


def _build_connection_timeline(equipment_name, date_str):
    """
    Build 24-hour timeline of connection status records
    
    Timeline structure:
    - Morning shift: 08:00 - 19:59 (Hours 8-19) on target_date
    - Night shift: 20:00 - 07:59 (Hours 20-23 on target_date + Hours 0-7 on target_date+1)
    
    Status: success=green, failed=red, timeout=orange, partial=yellow
    """
    from machine.models import ConnectionStatus, Equipment
    from datetime import datetime, timedelta
    import pytz
    
    try:
        equipment = Equipment.objects.get(name=equipment_name)
    except Equipment.DoesNotExist:
        return {'status': 'error', 'message': f'Equipment not found: {equipment_name}'}
    
    # Parse date
    try:
        target_date = datetime.strptime(date_str, '%Y-%m-%d').date()
    except ValueError:
        return {'status': 'error', 'message': f'Invalid date format: {date_str}'}
    
    tz = pytz.timezone('Asia/Bangkok')
    next_date = target_date + timedelta(days=1)
    
    logger.info(f"📅 Building timeline for {equipment_name} on {target_date}")
    logger.info(f"   Morning: {target_date} 08:00 - 19:59")
    logger.info(f"   Night: {target_date} 20:00 - {next_date} 07:59")
    
    # Get all records for this equipment
    # Include: target_date (for morning + start of night)
    #          next_date (for end of night shift)
    records = ConnectionStatus.objects.filter(
        equipment=equipment,
        shift_date__in=[target_date, next_date]
    ).order_by('recorded_at','id')
    
    logger.info(f"📊 Found {records.count()} total records")
    
    timeline_data = {
        'date': date_str,
        'equipment': equipment_name,
        'hours': [],
        'summary': {
            'total_records': 0,
            'success_count': 0,
            'failed_count': 0,
            'timeout_count': 0,
            'partial_count': 0,
        }
    }
    
    hours_data = {}
    
    # Initialize 24 hours (0-23 in Bangkok time)
    for hour in range(24):
        hours_data[hour] = {
            'hour': hour,
            'hour_display': f'{hour:02d}:00',
            'shift': 'morning' if 8 <= hour < 20 else 'night',
            'records': [],
            'status': 'no_data',
            'status_color': '#cccccc',
            'success_count': 0,
            'failed_count': 0,
            'timeout_count': 0,
            'partial_count': 0,
        }
    
    # Group records by hour
    for record in records:
        record_time = record.recorded_at.astimezone(tz)
        record_date = record_time.date()
        record_hour = record_time.hour
        
        # ✅ IMPROVED: Check if record belongs to our 24-hour window
        is_in_timeline = False
        
        # Morning shift: 08:00-19:59 on target_date
        if record_date == target_date and 8 <= record_hour < 20:
            is_in_timeline = True
            logger.debug(f"   ✓ Morning: {record_time}")
        
        # Night shift part 1: 20:00-23:59 on target_date
        elif record_date == target_date and 20 <= record_hour < 24:
            is_in_timeline = True
            logger.debug(f"   ✓ Night (first part): {record_time}")
        
        # Night shift part 2: 00:00-07:59 on next_date
        elif record_date == next_date and 0 <= record_hour < 8:
            is_in_timeline = True
            logger.debug(f"   ✓ Night (second part): {record_time}")
        
        if not is_in_timeline:
            logger.debug(f"   ✗ Out of timeline: {record_time} (date: {record_date}, hour: {record_hour})")
            continue
        
        timeline_data['summary']['total_records'] += 1
        
        status = record.connection_status
        if status == 'success':
            timeline_data['summary']['success_count'] += 1
        elif status == 'failed':
            timeline_data['summary']['failed_count'] += 1
        elif status == 'timeout':
            timeline_data['summary']['timeout_count'] += 1
        elif status == 'partial':
            timeline_data['summary']['partial_count'] += 1
        
        hour_key = record_hour
        
        # ✅ BUILD DETAILED RECORD INFO
        record_detail = {
            'time': record_time.strftime('%H:%M:%S'),
            'status': status,
            'error_message': record.error_message or '',
            'items': {}
        }
        
        # Extract item data if available
        if record.items_data:
            if 'Crane On Minute' in record.items_data:
                record_detail['items']['crane_on_minute'] = record.items_data['Crane On Minute']
            if 'Number of Move' in record.items_data:
                record_detail['items']['number_of_move'] = record.items_data['Number of Move']
        
        hours_data[hour_key]['records'].append(record_detail)
        
        # Update hour counts
        if status == 'success':
            hours_data[hour_key]['success_count'] += 1
        elif status == 'failed':
            hours_data[hour_key]['failed_count'] += 1
        elif status == 'timeout':
            hours_data[hour_key]['timeout_count'] += 1
        elif status == 'partial':
            hours_data[hour_key]['partial_count'] += 1
    
    # Determine status for each hour
    for hour_key in sorted(hours_data.keys()):
        hour_data = hours_data[hour_key]
        
        if len(hour_data['records']) == 0:
            hour_data['status'] = 'no_data'
            hour_data['status_color'] = '#cccccc'  # Gray
        elif hour_data['success_count'] > 0 and hour_data['failed_count'] == 0 and hour_data['timeout_count'] == 0 and hour_data['partial_count'] == 0:
            hour_data['status'] = 'success'
            hour_data['status_color'] = '#4CAF50'  # Green
        elif hour_data['failed_count'] > 0:
            hour_data['status'] = 'failed'
            hour_data['status_color'] = '#f44336'  # Red
        elif hour_data['timeout_count'] > 0:
            hour_data['status'] = 'timeout'
            hour_data['status_color'] = '#ff9800'  # Orange
        elif hour_data['partial_count'] > 0:
            hour_data['status'] = 'partial'
            hour_data['status_color'] = '#ffeb3b'  # Yellow
        else:
            hour_data['status'] = 'mixed'
            hour_data['status_color'] = '#9e9e9e'  # Gray
        
        timeline_data['hours'].append(hour_data)
    
    logger.info(f"✅ Timeline complete: {timeline_data['summary']['total_records']} records processed")
    logger.info(f"   Success: {timeline_data['summary']['success_count']}, "
                f"Failed: {timeline_data['summary']['failed_count']}, "
                f"Timeout: {timeline_data['summary']['timeout_count']}, "
                f"Partial: {timeline_data['summary']['partial_count']}")
    
    return timeline_data

# @require_http_methods(["GET"])
# def productivity_diagnostic(request):
#     """
#     Diagnostic page to investigate productivity calculations
    
#     Shows:
#     1. Productivity report (summary with hour, move, productivity)
#     2. Raw items-data-smart (detailed segments and all_values)
#     3. Side-by-side comparison to identify calculation errors
    
#     Usage:
#     ?date=2026-05-09&equipment=RTG21
#     """
    
#     # Get parameters
#     date_str = request.GET.get('date')
#     equipment_name = request.GET.get('equipment')
    
#     if not date_str or not equipment_name:
#         return JsonResponse({
#             'status': 'error',
#             'error': 'Missing parameters: date and equipment required',
#             'example': '/machine/api/productivity-diagnostic/?date=2026-05-09&equipment=RTG21'
#         }, status=400)
    
#     logger.info(f"🔍 Diagnostic request: date={date_str}, equipment={equipment_name}")
    
#     try:
#         # Get productivity report (summary)
#         report_result = get_productivity_report(
#             equipment_name=equipment_name,
#             target_date=date_str,
#             shift='all'
#         )
        
#         logger.info(f"📊 Report result: {report_result['status']}")
#         if report_result['status'] == 'error':
#             return JsonResponse(report_result, status=400)
        
#         # Get raw items data (with details)
#         items_result = get_items_data_filtered(
#             equipment_name=equipment_name,
#             target_date=date_str,
#             shift='all',
#             include_details=True  # ✅ Include detailed segments
#         )
        
#         logger.info(f"📊 Items result: {items_result['status']}")
#         if items_result['status'] == 'error':
#             return JsonResponse(items_result, status=400)
        
#         # Build diagnostic response
#         diagnostic_data = {
#             'status': 'success',
#             'parameters': {
#                 'date': date_str,
#                 'equipment': equipment_name,
#             },
#             'summary': {
#                 'morning': None,
#                 'night': None,
#                 'total': None,
#             },
#             'raw_data': {},
#             'comparison': {}
#         }
        
#         # ✅ EXTRACT SUMMARY DATA FROM REPORT
#         logger.info(f"📋 Extracting summary from report...")
#         if report_result['data'].get('daily_reports'):
#             for day_report in report_result['data']['daily_reports']:
#                 logger.info(f"📅 Checking day: {day_report.get('date')}")
#                 for eq_stat in day_report.get('equipment', []):
#                     if eq_stat.get('equipment') == equipment_name:
#                         logger.info(f"✅ Found equipment: {equipment_name}")
                        
#                         diagnostic_data['summary'] = {
#                             'equipment': equipment_name,
#                             'morning': eq_stat.get('morning'),
#                             'night': eq_stat.get('night'),
#                             'total': eq_stat.get('total'),
#                         }
                        
#                         logger.info(f"   Morning: {eq_stat.get('morning')}")
#                         logger.info(f"   Night: {eq_stat.get('night')}")
#                         logger.info(f"   Total: {eq_stat.get('total')}")
        
#         # ✅ EXTRACT RAW DATA FROM ITEMS
#         logger.info(f"📋 Extracting raw data from items...")
#         if items_result['data'].get('equipment_stats'):
#             for eq_stat in items_result['data']['equipment_stats']:
#                 if eq_stat.get('equipment') == equipment_name:
#                     shift_key = eq_stat['shift']
#                     logger.info(f"✅ Found shift: {shift_key}")
                    
#                     diagnostic_data['raw_data'][shift_key] = {
#                         'equipment': eq_stat['equipment'],
#                         'shift': eq_stat['shift'],
#                         'shift_label': eq_stat.get('shift_label', ''),
#                         'first_record_time': eq_stat.get('first_record_time', ''),
#                         'last_record_time': eq_stat.get('last_record_time', ''),
#                         'record_count': eq_stat.get('record_count', 0),
#                         'duration_minutes': eq_stat.get('duration_minutes', 0),
#                         'items': {}
#                     }
                    
#                     for item in eq_stat.get('items', []):
#                         item_name = item.get('name', 'Unknown')
#                         logger.info(f"   Item: {item_name}, Diff: {item.get('difference')}")
                        
#                         diagnostic_data['raw_data'][shift_key]['items'][item_name] = {
#                             'first_value': item.get('first_value'),
#                             'last_value': item.get('last_value'),
#                             'difference': float(item.get('difference', 0) or 0),
#                             'reset_detected': item.get('reset_detected', False),
#                             'reset_count': item.get('reset_count', 0),
#                             'count': item.get('count', 0),
#                             'segments': item.get('segments', []),
#                             'all_values': item.get('all_values', [])
#                         }
        
#         # ✅ BUILD COMPARISON/VERIFICATION
#         logger.info(f"📋 Building comparisons...")
#         for shift_key in ['morning', 'night']:
#             summary_shift = diagnostic_data['summary'].get(shift_key)
#             raw_shift = diagnostic_data['raw_data'].get(shift_key)
            
#             if summary_shift and raw_shift:
#                 logger.info(f"✅ Creating comparison for {shift_key}")
#                 verification = _verify_calculation(summary_shift, raw_shift)
                
#                 diagnostic_data['comparison'][shift_key] = {
#                     'summary': summary_shift,
#                     'raw': raw_shift,
#                     'verification': verification
#                 }
#                 logger.info(f"   Verification status: {verification.get('status')}")
#             else:
#                 logger.info(f"⏭️  Skipping {shift_key} - missing summary={bool(summary_shift)} or raw={bool(raw_shift)}")
        
#         logger.info(f"✅ Diagnostic complete. Comparisons: {list(diagnostic_data['comparison'].keys())}")
#         return JsonResponse(diagnostic_data, safe=False)
    
#     except Exception as e:
#         logger.error(f"Error in diagnostic: {e}", exc_info=True)
#         return JsonResponse({
#             'status': 'error',
#             'error': f'Diagnostic error: {str(e)}'
#         }, status=500)


def _verify_calculation(summary, raw_data):
    """
    Verify if summary calculations match raw data
    
    Returns verification status and any discrepancies
    """
    if not summary or not raw_data:
        return {
            'status': 'incomplete',
            'message': 'Missing summary or raw data',
            'checks': [],
            'discrepancies': []
        }
    
    verification = {
        'status': 'ok',
        'checks': [],
        'discrepancies': []
    }
    
    try:
        # Check Crane On Minute
        if 'Crane On Minute' in raw_data['items']:
            crane_item = raw_data['items']['Crane On Minute']
            crane_diff = crane_item.get('difference', 0)
            summary_crane = summary.get('crane_on_minute', 0)
            
            check = {
                'field': 'Crane On Minute',
                'raw_difference': float(crane_diff) if crane_diff is not None else 0,
                'summary_value': float(summary_crane) if summary_crane is not None else 0,
                'match': abs(float(crane_diff or 0) - float(summary_crane or 0)) < 0.01
            }
            verification['checks'].append(check)
            
            if not check['match']:
                verification['discrepancies'].append({
                    'field': 'Crane On Minute',
                    'issue': f"Raw difference ({crane_diff}) ≠ Summary ({summary_crane})",
                    'possible_causes': [
                        'Reset detection error',
                        'Data ordering issue',
                        'Calculation rounding error'
                    ]
                })
        
        # Check Number of Move
        if 'Number of Move' in raw_data['items']:
            move_item = raw_data['items']['Number of Move']
            move_diff = move_item.get('difference', 0)
            summary_move = summary.get('number_of_move', 0)
            
            check = {
                'field': 'Number of Move',
                'raw_difference': float(move_diff) if move_diff is not None else 0,
                'summary_value': float(summary_move) if summary_move is not None else 0,
                'match': abs(float(move_diff or 0) - float(summary_move or 0)) < 0.01
            }
            verification['checks'].append(check)
            
            if not check['match']:
                verification['discrepancies'].append({
                    'field': 'Number of Move',
                    'issue': f"Raw difference ({move_diff}) ≠ Summary ({summary_move})",
                    'possible_causes': [
                        'Reset detection error',
                        'Data ordering issue',
                        'Calculation rounding error'
                    ]
                })
        
        # Check Productivity calculation
        if 'Crane On Minute' in raw_data['items'] and 'Number of Move' in raw_data['items']:
            crane_diff = float(raw_data['items']['Crane On Minute'].get('difference', 0) or 0)
            move_diff = float(raw_data['items']['Number of Move'].get('difference', 0) or 0)
            
            if crane_diff > 0:
                calculated_productivity = move_diff / (crane_diff / 60)
                summary_productivity = float(summary.get('productivity', 0) or 0)
                
                check = {
                    'field': 'Productivity',
                    'calculation': f"{move_diff} / ({crane_diff} / 60) = {round(calculated_productivity, 2)}",
                    'calculated_value': round(calculated_productivity, 2),
                    'summary_value': round(summary_productivity, 2),
                    'match': abs(calculated_productivity - summary_productivity) < 0.01
                }
                verification['checks'].append(check)
                
                if not check['match']:
                    verification['discrepancies'].append({
                        'field': 'Productivity',
                        'issue': f"Calculated ({round(calculated_productivity, 2)}) ≠ Summary ({round(summary_productivity, 2)})",
                        'possible_causes': [
                            'Rounding error in hour calculation',
                            'Wrong hour/move values used',
                            'Precision loss in division'
                        ]
                    })
        
        # Set overall status
        if verification['discrepancies']:
            verification['status'] = 'error'
        
        return verification
    
    except Exception as e:
        logger.error(f"Error in verification: {e}", exc_info=True)
        return {
            'status': 'error',
            'message': f'Verification error: {str(e)}',
            'checks': [],
            'discrepancies': []
        }

from django.shortcuts import render
def productivity_diagnostic_html(request):
    """Render diagnostic page"""
    return render(request, 'machine/productivity_diagnostic.html')