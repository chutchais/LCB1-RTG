# import pytz
# from datetime import datetime, timedelta
# from django.utils import timezone
# import logging

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
#         Get shift date based on time
        
#         ✅ CORRECT LOGIC:
#         - Morning shift (08:00-20:00) on May 8 → shift_date = May 8
#         - Night shift (20:00-08:00) on May 9 at 01:30 AM → shift_date = May 8
        
#         Night shift spans from 20:00 on one day to 08:00 the next day
#         So a night shift record at May 9 1:30 AM belongs to the night shift that started on May 8 at 20:00
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
#             # Morning: 08:00-20:00 uses same day
#             return current_date
#         else:  # night shift
#             # Night: 20:00-08:00 uses PREVIOUS day
#             # Because night shift starts at 20:00 on previous day and ends at 08:00 on current day
#             if dt.hour < 8:
#                 # Between 00:00-08:00, belongs to night shift of previous day
#                 return current_date - timedelta(days=1)
#             else:
#                 # This shouldn't happen in night shift, but just in case
#                 return current_date
        
#     @staticmethod
#     def get_shift_date_range(shift_date, shift):
#         """
#         Get start and end time for a shift
        
#         ✅ FIXED: Night shift now spans from 20:00 on shift_date to 08:00 next day
#         """
#         tz = pytz.timezone('Asia/Bangkok')
        
#         if shift == 'morning':
#             # Morning: 08:00 to 20:00 on the same day
#             start = tz.localize(datetime.combine(shift_date, datetime.min.time().replace(hour=8)))
#             end = tz.localize(datetime.combine(shift_date, datetime.min.time().replace(hour=20)))
#         else:  # night
#             # Night: 20:00 on shift_date to 08:00 next day
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
#             shift_date = ConnectionStatusService.get_shift_date(now_tz)  # ✅ NOW USES CURRENT DATE
            
#             logger.debug(f"🕐 Current time (Bangkok): {now_tz}")
#             logger.debug(f"📅 Shift: {shift}, Shift Date: {shift_date}")
            
#             # Prepare items data
#             if items_data is None:
#                 items_data = {}
            
#             # Record status
#             from machine.models import ConnectionStatus
            
#             status_record = ConnectionStatus.objects.create(
#                 equipment=equipment,
#                 connection_status=connection_status,
#                 error_message=error_message,
#                 items_data=items_data,
#                 recorded_at=now_tz,
#                 shift=shift,
#                 shift_date=shift_date  # ✅ NOW CORRECT
#             )

            
#             logger.info(f"✅ Status recorded - Equipment: {equipment_name}, "
#                        f"Status: {connection_status}, Shift: {shift}, "
#                        f"Shift Date: {shift_date}")
            
#             return status_record
        
#         except Exception as e:
#             logger.error(f"❌ Error recording status: {str(e)}", exc_info=True)
#             return None

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
        Get shift date based on time
        
        ✅ CORRECT LOGIC:
        - Morning shift (08:00-20:00) on May 8 → shift_date = May 8
        - Night shift (20:00-08:00) on May 9 at 01:30 AM → shift_date = May 8
        """
        if dt is None:
            dt = timezone.now()
        
        tz = pytz.timezone('Asia/Bangkok')
        if dt.tzinfo is None:
            dt = tz.localize(dt)
        else:
            dt = dt.astimezone(tz)
        
        shift = ConnectionStatusService.get_current_shift(dt)
        current_date = dt.date()
        
        if shift == 'morning':
            return current_date
        else:  # night shift
            if dt.hour < 8:
                # Between 00:00-08:00, belongs to night shift of previous day
                return current_date - timedelta(days=1)
            else:
                return current_date
    
    @staticmethod
    def get_shift_date_range(shift_date, shift):
        """Get start and end time for a shift"""
        tz = pytz.timezone('Asia/Bangkok')
        
        if shift == 'morning':
            start = tz.localize(datetime.combine(shift_date, datetime.min.time().replace(hour=8)))
            end = tz.localize(datetime.combine(shift_date, datetime.min.time().replace(hour=20)))
        else:  # night
            start = tz.localize(datetime.combine(shift_date, datetime.min.time().replace(hour=20)))
            next_day = shift_date + timedelta(days=1)
            end = tz.localize(datetime.combine(next_day, datetime.min.time().replace(hour=8)))
        
        return start, end
    
    # 
    @staticmethod
    def check_shift_change(equipment_name):
        """
        Check if shift has just changed (only in first 30 minutes after shift change)
        
        ✅ OPTIMIZED: Only executes during:
        - 08:00-08:30 (morning shift starts)
        - 20:00-20:30 (night shift starts)
        
        No need to check at other times (saves processing time)
        
        Returns:
            - None if no shift change or not in shift change window
            - 'morning' if just changed to morning shift
            - 'night' if just changed to night shift
        """
        from machine.models import ConnectionStatus, Equipment
        
        # Get current time in Bangkok timezone
        now = timezone.now()
        tz = pytz.timezone('Asia/Bangkok')
        now_tz = now.astimezone(tz) if now.tzinfo else tz.localize(now)
        
        hour = now_tz.hour
        minute = now_tz.minute
        
        # ✅ ONLY CHECK IN FIRST 30 MINUTES OF SHIFT CHANGE
        # Morning shift starts at 08:00
        is_morning_change_window = (hour == 8 and minute < 30)
        # Night shift starts at 20:00
        is_night_change_window = (hour == 20 and minute < 30)
        
        if not (is_morning_change_window or is_night_change_window):
            # Not in shift change window, skip check to save time
            logger.debug(f"⏭️  Shift change check skipped for {equipment_name} (outside window: {hour}:{minute:02d})")
            return None

        try:
            equipment = Equipment.objects.get(name=equipment_name)
        except Equipment.DoesNotExist:
            return None
             
        logger.debug(f"🔍 Checking shift change for {equipment_name} at {hour}:{minute:02d}")
        
        current_shift = ConnectionStatusService.get_current_shift(now_tz)
        current_shift_date = ConnectionStatusService.get_shift_date(now_tz)
        
        # Get last successful record
        last_record = ConnectionStatus.objects.filter(
            equipment=equipment,
            connection_status='success'
        ).order_by('-recorded_at').first()
        
        if not last_record:
            # No previous record, no shift change to detect
            logger.debug(f"ℹ️  No previous record for {equipment_name}, skipping shift change detection")
            return None
        
        # Check if shift has changed
        if last_record.shift != current_shift or last_record.shift_date != current_shift_date:
            logger.info(f"✅ SHIFT CHANGE DETECTED: {equipment_name}")
            logger.info(f"   Last shift: {last_record.shift} ({last_record.shift_date})")
            logger.info(f"   New shift: {current_shift} ({current_shift_date})")
            return current_shift
        
        logger.debug(f"ℹ️  No shift change detected for {equipment_name} (same shift)")
        return None
    
    @staticmethod
    def record_status(equipment_name, connection_status, error_message='', items_data=None):
        """
        Record connection status for equipment
        
        ✅ ENHANCED: Creates initial record on shift change
        
        Args:
            equipment_name: Equipment name (str)
            connection_status: 'success', 'failed', 'timeout', 'partial'
            error_message: Error message if failed
            items_data: Dict of item readings
        """
        from machine.models import Equipment, ConnectionStatus
        
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
            shift_date = ConnectionStatusService.get_shift_date(now_tz)
            
            logger.debug(f"🕐 Current time (Bangkok): {now_tz}")
            logger.debug(f"📅 Shift: {shift}, Shift Date: {shift_date}")
            
            # ✅ Cancelled shift change check to avoid performance issues
            # # ✅ CHECK FOR SHIFT CHANGE AND CREATE INITIAL RECORD
            # shift_changed = ConnectionStatusService.check_shift_change(equipment_name)
            
            # if shift_changed:
            #     # Get last successful record to copy
            #     last_success = ConnectionStatus.objects.filter(
            #         equipment=equipment,
            #         connection_status='success'
            #     ).order_by('-recorded_at').first()
                
            #     if last_success and last_success.items_data:
            #         logger.info(f"✅ Creating initial record for shift change: {equipment_name}")
                    
            #         # Create new initial record with copied items data
            #         initial_record = ConnectionStatus.objects.create(
            #             equipment=equipment,
            #             connection_status='success',
            #             error_message='',  # No error for initial record
            #             items_data=last_success.items_data,  # ✅ COPY ITEMS DATA
            #             recorded_at=now_tz,
            #             shift=shift,
            #             shift_date=shift_date
            #         )
                    
            #         logger.info(f"✅ Initial record created (ID: {initial_record.id}) for shift change")
            #         logger.info(f"   Equipment: {equipment_name}, Shift: {shift}, Shift Date: {shift_date}")
            #         logger.info(f"   Copied items data from previous shift")
            
            # Prepare items data
            if items_data is None:
                items_data = {}
            
            # Record the actual status
            status_record = ConnectionStatus.objects.create(
                equipment=equipment,
                connection_status=connection_status,
                error_message=error_message,
                items_data=items_data,
                recorded_at=now_tz,
                shift=shift,
                shift_date=shift_date
            )
            
            logger.info(f"✅ Status recorded - Equipment: {equipment_name}, "
                       f"Status: {connection_status}, Shift: {shift}, "
                       f"Shift Date: {shift_date}")
            
            return status_record
        
        except Exception as e:
            logger.error(f"❌ Error recording status: {str(e)}", exc_info=True)
            return None