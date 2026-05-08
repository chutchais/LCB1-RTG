from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from datetime import datetime

from machine.models import ConnectionStatus, Equipment
from machine.api.serializers import ConnectionStatusListSerializer
from machine.api.services import get_items_data, get_items_data_filtered


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


# ✅ NEW ENDPOINT WITH SMART DEFAULTS
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
        recorded_at__date=target_date,
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