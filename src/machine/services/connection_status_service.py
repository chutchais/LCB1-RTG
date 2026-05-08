# import logging
# import pytz
# from datetime import datetime, timedelta, date
# from django.utils import timezone
# from machine.models import ConnectionStatus

# logger = logging.getLogger(__name__)


# class ConnectionStatusService:
#     """Service to record equipment connection status"""
    
#     @staticmethod
#     def get_current_shift(dt=None):
#         """
#         Determine current shift based on time
#         Morning: 08:00 - 20:00
#         Night: 20:00 - 08:00 (next day)
#         """
#         if dt is None:
#             dt = timezone.now()
        
#         # Convert to Bangkok time if needed
#         tz = pytz.timezone('Asia/Bangkok')
#         if dt.tzinfo is None:
#             dt = tz.localize(dt)
#         else:
#             dt = dt.astimezone(tz)
        
#         hour = dt.hour
        
#         if 8 <= hour < 20:
#             return 'morning'
#         else:
#             return 'night'
    
#     @staticmethod
#     def get_shift_date(dt=None):
#         """
#         Get shift date (morning uses same day, night uses previous day)
#         """
#         if dt is None:
#             dt = timezone.now()
        
#         tz = pytz.timezone('Asia/Bangkok')
#         if dt.tzinfo is None:
#             dt = tz.localize(dt)
#         else:
#             dt = dt.astimezone(tz)
        
#         shift = ConnectionStatusService.get_current_shift(dt)
#         current_date = dt.date()
        
#         if shift == 'morning':
#             return current_date
#         else:  # night shift
#             return current_date - timedelta(days=1)
    
#     @staticmethod
#     def get_shift_date_range(shift_date, shift):
#         """Get start and end time for a shift"""
#         tz = pytz.timezone('Asia/Bangkok')
        
#         if shift == 'morning':
#             start = tz.localize(datetime.combine(shift_date, datetime.min.time().replace(hour=8)))
#             end = tz.localize(datetime.combine(shift_date, datetime.min.time().replace(hour=20)))
#         else:  # night
#             start = tz.localize(datetime.combine(shift_date, datetime.min.time().replace(hour=20)))
#             next_day = shift_date + timedelta(days=1)
#             end = tz.localize(datetime.combine(next_day, datetime.min.time().replace(hour=8)))
        
#         return start, end
    
#     @staticmethod
#     def record_status(equipment_name, connection_status, error_message='', items_data=None):
#         """
#         Record connection status for equipment
        
#         Args:
#             equipment_name: Equipment name (str)
#             connection_status: 'success', 'failed', 'timeout', 'partial'
#             error_message: Error message if failed
#             items_data: Dict of item readings
#         """
#         from machine.models import Equipment
        
#         try:
#             # Validate connection_status value
#             valid_statuses = ['success', 'failed', 'timeout', 'partial']
#             if connection_status not in valid_statuses:
#                 logger.error(f"❌ Invalid connection_status: {connection_status}. Must be one of {valid_statuses}")
#                 return None
            
#             # Get equipment
#             try:
#                 equipment = Equipment.objects.get(name=equipment_name)
#             except Equipment.DoesNotExist:
#                 logger.error(f"❌ Equipment not found: {equipment_name}")
#                 return None
            
#             logger.info(f"📝 Recording status for {equipment_name}: {connection_status}")
            
#             # Get current time and shift info
#             now = timezone.now()
#             tz = pytz.timezone('Asia/Bangkok')
#             now_tz = now.astimezone(tz) if now.tzinfo else tz.localize(now)
            
#             shift = ConnectionStatusService.get_current_shift(now_tz)
#             shift_date = ConnectionStatusService.get_shift_date(now_tz)
            
#             # Prepare items data
#             if items_data is None:
#                 items_data = {}
            
#             # logger.info(f"  Equipment ID: {equipment.id}")
#             logger.info(f"  Connection Status: {connection_status}")
#             logger.info(f"  Shift: {shift}")
#             logger.info(f"  Shift Date: {shift_date}")
#             logger.info(f"  Recorded At: {now_tz}")
#             logger.info(f"  Items Data: {len(items_data)} items")
            
#             # Create connection status record
#             # NOTE: Don't set 'created', 'updated', 'status' - they're auto-set by BasicInfo
#             status_record = ConnectionStatus.objects.create(
#                 equipment=equipment,
#                 connection_status=connection_status,
#                 error_message=error_message or '',
#                 items_data=items_data,
#                 recorded_at=now_tz,
#                 shift=shift,
#                 shift_date=shift_date
#                 # 'created', 'updated', 'status' auto-filled by BasicInfo
#             )
            
#             logger.info(
#                 f"✓ Successfully recorded connection status: {equipment_name} - {connection_status} - {now_tz}"
#             )
            
#             return status_record
            
#         except Exception as e:
#             logger.error(f"❌ Error recording status: {str(e)}", exc_info=True)
#             import traceback
#             traceback.print_exc()
#             return None
    
#     @staticmethod
#     def get_equipment_timeline(equipment_name, hours=24):
#         """Get connection timeline for equipment in last N hours"""
#         from machine.models import Equipment
        
#         try:
#             equipment = Equipment.objects.get(name=equipment_name)
#             cutoff = timezone.now() - timedelta(hours=hours)
            
#             statuses = ConnectionStatus.objects.filter(
#                 equipment=equipment,
#                 recorded_at__gte=cutoff
#             ).order_by('-recorded_at')
            
#             return list(statuses)
#         except Exception as e:
#             logger.error(f"Error getting timeline: {e}", exc_info=True)
#             return []
    
#     @staticmethod
#     def get_shift_summary(shift, shift_date=None):
#         """Get summary statistics for a shift"""
#         if shift_date is None:
#             shift_date = ConnectionStatusService.get_shift_date()
        
#         statuses = ConnectionStatus.objects.filter(
#             shift=shift,
#             shift_date=shift_date
#         )
        
#         total = statuses.count()
#         if total == 0:
#             return {
#                 'shift': shift,
#                 'shift_date': shift_date.isoformat(),
#                 'total': 0,
#                 'success': 0,
#                 'failed': 0,
#                 'timeout': 0,
#                 'partial': 0,
#                 'success_rate': 0
#             }
        
#         success = statuses.filter(connection_status='success').count()
#         failed = statuses.filter(connection_status='failed').count()
#         timeout = statuses.filter(connection_status='timeout').count()
#         partial = statuses.filter(connection_status='partial').count()
        
#         success_rate = (success / total * 100) if total > 0 else 0
        
#         return {
#             'shift': shift,
#             'shift_label': 'Morning Shift (08:00 - 20:00)' if shift == 'morning' else 'Night Shift (20:00 - 08:00)',
#             'shift_date': shift_date.isoformat(),
#             'total': total,
#             'success': success,
#             'failed': failed,
#             'timeout': timeout,
#             'partial': partial,
#             'success_rate': round(success_rate, 2)
#         }
import pytz
from datetime import datetime, timedelta
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)


class ConnectionStatusService:
    """Service to record equipment connection status"""
    
    @staticmethod
    def get_current_shift(dt=None):
        """
        Determine current shift based on time
        Morning: 08:00 - 20:00
        Night: 20:00 - 08:00 (next day)
        """
        if dt is None:
            dt = timezone.now()
        
        # Convert to Bangkok time if needed
        tz = pytz.timezone('Asia/Bangkok')
        if dt.tzinfo is None:
            dt = tz.localize(dt)
        else:
            dt = dt.astimezone(tz)
        
        hour = dt.hour
        
        if 8 <= hour < 20:
            return 'morning'
        else:
            return 'night'
    
    @staticmethod
    def get_shift_date(dt=None):
        """
        Get shift date (morning uses same day, night uses SAME day - current day)
        
        ✅ FIXED LOGIC:
        - Morning shift (08:00-20:00) on May 8 → shift_date = May 8
        - Night shift (20:00-08:00) on May 8 → shift_date = May 8 (not May 7!)
        
        The shift_date represents the DATE OF THE SHIFT, not the start date
        A night shift happening on May 8 at 8:36 PM belongs to May 8's night shift
        """
        if dt is None:
            dt = timezone.now()
        
        tz = pytz.timezone('Asia/Bangkok')
        if dt.tzinfo is None:
            dt = tz.localize(dt)
        else:
            dt = dt.astimezone(tz)
        
        # ✅ SIMPLY RETURN CURRENT DATE (same day)
        # Night shift from 8:36 PM May 8 to 8:00 AM May 9 belongs to May 8
        return dt.date()
    
    @staticmethod
    def get_shift_date_range(shift_date, shift):
        """
        Get start and end time for a shift
        
        ✅ FIXED: Night shift now spans from 20:00 on shift_date to 08:00 next day
        """
        tz = pytz.timezone('Asia/Bangkok')
        
        if shift == 'morning':
            # Morning: 08:00 to 20:00 on the same day
            start = tz.localize(datetime.combine(shift_date, datetime.min.time().replace(hour=8)))
            end = tz.localize(datetime.combine(shift_date, datetime.min.time().replace(hour=20)))
        else:  # night
            # Night: 20:00 on shift_date to 08:00 next day
            start = tz.localize(datetime.combine(shift_date, datetime.min.time().replace(hour=20)))
            next_day = shift_date + timedelta(days=1)
            end = tz.localize(datetime.combine(next_day, datetime.min.time().replace(hour=8)))
        
        return start, end
    
    @staticmethod
    def record_status(equipment_name, connection_status, error_message='', items_data=None):
        """
        Record connection status for equipment
        
        Args:
            equipment_name: Equipment name (str)
            connection_status: 'success', 'failed', 'timeout', 'partial'
            error_message: Error message if failed
            items_data: Dict of item readings
        """
        from machine.models import Equipment
        
        try:
            # Validate connection_status value
            valid_statuses = ['success', 'failed', 'timeout', 'partial']
            if connection_status not in valid_statuses:
                logger.error(f"❌ Invalid connection_status: {connection_status}. Must be one of {valid_statuses}")
                return None
            
            # Get equipment
            try:
                equipment = Equipment.objects.get(name=equipment_name)
            except Equipment.DoesNotExist:
                logger.error(f"❌ Equipment not found: {equipment_name}")
                return None
            
            logger.info(f"📝 Recording status for {equipment_name}: {connection_status}")
            
            # Get current time and shift info
            now = timezone.now()
            tz = pytz.timezone('Asia/Bangkok')
            now_tz = now.astimezone(tz) if now.tzinfo else tz.localize(now)
            
            shift = ConnectionStatusService.get_current_shift(now_tz)
            shift_date = ConnectionStatusService.get_shift_date(now_tz)  # ✅ NOW USES CURRENT DATE
            
            logger.debug(f"🕐 Current time (Bangkok): {now_tz}")
            logger.debug(f"📅 Shift: {shift}, Shift Date: {shift_date}")
            
            # Prepare items data
            if items_data is None:
                items_data = {}
            
            # Record status
            from machine.models import ConnectionStatus
            
            status_record = ConnectionStatus.objects.create(
                equipment=equipment,
                connection_status=connection_status,
                error_message=error_message,
                items_data=items_data,
                recorded_at=now_tz,
                shift=shift,
                shift_date=shift_date  # ✅ NOW CORRECT
            )

            #             status_record = ConnectionStatus.objects.create(
#                 equipment=equipment,
#                 connection_status=connection_status,
#                 error_message=error_message or '',
#                 items_data=items_data,
#                 recorded_at=now_tz,
#                 shift=shift,
#                 shift_date=shift_date
#                 # 'created', 'updated', 'status' auto-filled by BasicInfo
#             )
            
            logger.info(f"✅ Status recorded - Equipment: {equipment_name}, "
                       f"Status: {connection_status}, Shift: {shift}, "
                       f"Shift Date: {shift_date}")
            
            return status_record
        
        except Exception as e:
            logger.error(f"❌ Error recording status: {str(e)}", exc_info=True)
            return None