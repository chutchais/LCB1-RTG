from re import T
from django.db import models

# Create your models here.
from django.conf 	            import settings
from django.db.models.signals   import post_save
from django.dispatch            import receiver
from base.models                import BasicInfo
from base.utility               import update_transaction_date
from measuring.models           import FIELDS_TYPE_CHOICES, Parameter
import logging
# Department section
class Equipment(BasicInfo):
    name                = models.CharField(max_length=50,primary_key=True)
    title               = models.CharField(max_length=50,blank=True, null=True)
    ip                  = models.GenericIPAddressField(blank=True, null=True)
    user 			    = models.ForeignKey(settings.AUTH_USER_MODEL,
                            on_delete=models.CASCADE,
                            blank=True,null=True,related_name = 'sections')
    def __str__(self):
        return self.name

    class Meta(BasicInfo.Meta):
        db_table = 'equipment'

    def read_item_data(self, *args, **kwargs):
        from .plc_connection import read_multiple_values, plc_connect
        from .tasks import save_redis, save_previous_redis, get_previous_redis
        import datetime
        import pytz
        import logging
        
        logging.info(f'🔍 Start reading data of {self.name} ({self.ip})')
        
        tz = pytz.timezone('Asia/Bangkok')
        now_tz = datetime.datetime.now(tz=tz)
        value_dict = {}
        
        # ============ PRE-CHECK: DIAGNOSE CONNECTION ============
        logging.info(f'🔎 Running diagnostics on {self.ip}...')
        status = plc_connect(self.ip, 0, 2, 5)
        
        logging.info(f'  - Ping OK: {status["ping_ok"]}')
        logging.info(f'  - Snap7 OK: {status["snap7_ok"]}')
        logging.info(f'  - Status: {status["status"]}')
        
        if status['status'] == 'ping_only':
            # Special case: ping works but Snap7 fails
            logging.error(f'⚠️  DIAGNOSTIC: PLC responds to ping but Snap7 connection failed!')
            logging.error(f'   This usually means:')
            logging.error(f'   1. Snap7 service is not running on PLC')
            logging.error(f'   2. TCP port 102 is blocked')
            logging.error(f'   3. Wrong Rack/Slot configuration')
            logging.error(f'   4. Network issues between app and PLC')
            
            error_data = {
                'Equipment': self.name,
                'status': 'error',
                'error': 'Ping OK but Snap7 connection failed',
                'diagnostic': 'Check PLC configuration, firewall, or Snap7 service',
                'timestamp': now_tz.isoformat(),
                'DateTime': now_tz.strftime("%b %d %H:%M")
            }
            try:
                save_redis(f'{self.name}:LATEST', error_data)
            except:
                pass
            return error_data
        
        if not status['connected']:
            logging.error(f'❌ PLC connection check failed: {status["error"]}')
            
            error_data = {
                'Equipment': self.name,
                'status': 'error',
                'error': status['error'],
                'timestamp': now_tz.isoformat(),
                'DateTime': now_tz.strftime("%b %d %H:%M")
            }
            try:
                save_redis(f'{self.name}:LATEST', error_data)
            except:
                pass
            return error_data
        
        # ============ REST OF YOUR FUNCTION... ============
        # (previous code continues here)
        
        # ============ BUILD READS ARRAY ============
        reads = []
        items_list = list(self.items.all())
        
        for item in items_list:
            if item.monitor:
                continue  # skip if monitor parameter is True
            
            db_number = item.parameter.db_number
            offset = item.parameter.offset
            field_type = item.parameter.field_type
            label = item.name
            
            reads.append((db_number, offset, field_type, label))
        
        if not reads:
            logging.warning(f'⚠️  No items configured for {self.name}')
            
            # Save error status
            error_data = {
                'Equipment': self.name,
                'status': 'error',
                'error': 'No items configured',
                'timestamp': now_tz.isoformat(),
                'DateTime': now_tz.strftime("%b %d %H:%M")
            }
            try:
                save_redis(f'{self.name}:LATEST', error_data)
            except Exception as e:
                logging.error(f'Error saving error status to Redis: {e}')
            
            return error_data
        
        logging.info(f'  📋 Will read {len(reads)} items from PLC')
        
        # ============ READ ALL VALUES IN ONE CONNECTION ============
        try:
            values = read_multiple_values(
                ip=self.ip,
                reads=reads,
                rack=0,
                slot=2,
                timeout=5
            )
            
            logging.info(f'✓ Read complete from {self.name}')
            
        except Exception as e:
            logging.error(f'❌ Exception reading from PLC: {e}')
            
            # Save error status
            error_data = {
                'Equipment': self.name,
                'status': 'error',
                'error': str(e),
                'timestamp': now_tz.isoformat(),
                'DateTime': now_tz.strftime("%b %d %H:%M")
            }
            try:
                save_redis(f'{self.name}:LATEST', error_data)
            except:
                pass
            
            return error_data
        
        # ============ PROCESS READ VALUES ============
        failed_items = []
        success_items = []
        
        for item in items_list:
            if item.monitor:
                continue
            
            label = item.name
            value = values.get(label, -1)
            
            key = f'{self.name}:{item.parameter.name}:PREVIOUS'
            
            if value == -1:
                # Read failed - try to get previous value
                logging.warning(f'⚠️  Unable to read data: {key} --> {value}')
                
                previous_value = get_previous_redis(key)
                print(f'📦 Get previous value of: {key} --> {previous_value}')
                
                value_dict[item.name] = previous_value
                failed_items.append(item.name)
            else:
                # Read successful
                save_previous_redis(key, value)
                item.current_value = value
                item.save()
                
                print(f'✓ Saved current value of {key} --> {value}')
                logging.info(f'{item} --> {value} {item.units}')
                print(f'{item} --> {value} {item.units}')
                
                value_dict[item.name] = value
                success_items.append(item.name)
        
        # ============ ADD METADATA ============
        value_dict['Equipment']     = self.name
        value_dict['DateTime']      = now_tz.strftime("%b %d %H:%M")
        value_dict['timestamp']     = now_tz.strftime("%b %d %H:%M")#now_tz.isoformat()
        
        # Add status
        if len(failed_items) == len(items_list):
            # All failed - PLC connection error
            value_dict['status'] = 'error'
            value_dict['error'] = 'PLC connection failed - All items failed to read'
            logging.error(f'❌ FAILED: All {len(items_list)} items failed - PLC CONNECTION ERROR')
        elif len(failed_items) > 0:
            # Partial success
            value_dict['status'] = 'partial'
            value_dict['items_read'] = len(success_items)
            value_dict['items_failed'] = len(failed_items)
            value_dict['failed_items'] = failed_items
            logging.warning(f'⚠️  Partial read: {len(success_items)} success, {len(failed_items)} failed')
        else:
            # All success
            value_dict['status'] = 'success'
            logging.info(f'✅ All {len(success_items)} items read successfully')
        
        # ============ SAVE TO REDIS ============
        try:
            key = f'{self.name}:LATEST'
            save_redis(key, value_dict)
            print(f"✓ Data saved to Redis: {key}")
            print(f"  Status: {value_dict.get('status', 'unknown')}")
        except Exception as e:
            logging.error(f'❌ Error saving to Redis: {e}')
            import traceback
            traceback.print_exc()
        
        return value_dict
   
    # def read_item_data(self, *args, **kwargs):
    #     from .plc_connection import read_value
    #     from .tasks import  save_redis, save_previous_redis, get_previous_redis
    #     import datetime, pytz
    #     logging.info(f'Start reading data of {self.name} ({self.ip})')
        
    #     tz = pytz.timezone('Asia/Bangkok')
    #     now_tz = datetime.datetime.now(tz=tz)
    #     value_dict = {}

        
    #     for item in self.items.all():
    #         if item.monitor: 
    #             continue  # skip if monitor parameter is True
            
    #         ip = self.ip
    #         db_number = item.parameter.db_number
    #         offset = item.parameter.offset
    #         field_type = item.parameter.field_type
    #         value = read_value(ip, db_number, offset, field_type)

    #         key = f'{self.name}:{item.parameter.name}:PREVIOUS'
            
    #         if value == -1:
    #             logging.warn(f'Unable to read data from machine: {key} -->{value}')
    #             value = get_previous_redis(key)
    #             print(f'Get current value of : {key} -->{value}')
    #         else:
    #             save_previous_redis(key, value)
    #             item.current_value = value
    #             item.save()
    #             print(f'Save to current value of {key}-->{value} -- Successful')

    #         value_dict[item.name] = value
    #         logging.info(f'{item} -->{value} {item.units}')
    #         print(f'{item} -->{value} {item.units}')
        
    #     value_dict['Equipment'] = self.name
        
    #     # ==================== ADD THIS BLOCK ====================
    #     # Save to Redis with original format and machine format
    #     try:
    #         key = f'{self.name}:LATEST'
    #         save_redis(key, value_dict)
    #         print(f"✓ Data saved to Redis: {key}")
    #     except Exception as e:
    #         print(f"✗ Error saving to Redis: {e}")
    #         import traceback
    #         traceback.print_exc()
    #     # ========================================================
        
    #     return value_dict
    
    def read_monitor_data(self, *args, **kwargs):
        from .tasks import read_bit,read_value,save_redis,save_previous_redis,save_redis_stack
        import datetime, pytz
        logging.info(f'Start reading data of {self.name} ({self.ip})')
        # print(f'Start reading data of {self.name} ({self.ip})')
        tz      = pytz.timezone('Asia/Bangkok')
        now_tz  =   datetime.datetime.now(tz=tz)
        value_dict = {}
        for item in self.items.all():
            if not item.monitor : continue #skip if monitor parameter is False
            ip          = self.ip
            db_number   = item.parameter.db_number
            offset      = item.parameter.offset
            field_type  = item.parameter.field_type
            bit_number  = item.parameter.bit_number

            if field_type == 'bit':
                value       = read_bit(ip,db_number,offset,bit_number)
            else:
                value       = read_value(ip,db_number,offset,field_type)


            key = f'{self.name}:{item.parameter.name}:MONITOR'
            # if value == -1 :
            #     logging.warn(f'Get previous value of : {key} -->{value}')              
            # else:
            save_previous_redis(key,value)
            item.current_value = value
            item.save()
            

            value_dict[item.name] = value
            logging.info(f'{item} -->{value} {item.units}')
            # print(f'{item} -->{value} {item.units}')
            # Added on July 16,2024 -- To record last 12 data
            key_lastest     = f'{self.name}:{item.parameter.name}:LASTEST'
            # Modify on Aug 17,2024 -- if value is -1 change to 0
            # value_latest    = save_redis_stack(key_lastest,0 if (value == -1 or value == '-1') else value)
            # Modify on Aug 20,2024 -- To keep actual value
            value_latest    = save_redis_stack(key_lastest,value)
            value_dict[f'{item.name}:LIST'] = ','.join(value_latest)
            # ------------------------------------------------
            print(f'Save to monitor value of {key}-->{value} -- Successful')
        
        value_dict['Equipment']     = self.name
        value_dict['DateTime']      = now_tz.strftime("%b %d %H:%M")#now_tz.strftime("%Y-%m-%d %H:%M:%S")

        # Save to Redis (DB0), key = {Name}{item.name} , value = Reading value
        key = f'{self.name}:MONITOR'
        save_redis(key,value_dict)

    def save_logged(self,log_for_yesterday:bool=False):
        from .tasks import save_logged_item
        # import datetime, pytz
        logging.info(f'Start recording data of {self.name} ({self.ip})')
        # tz      =   pytz.timezone('Asia/Bangkok')
        # now_tz  =   datetime.datetime.now(tz=tz)
        for item in self.items.all():
            save_logged_item(item,log_for_yesterday)
        logging.info(f'Complete recording data of {self.name} ({self.ip})')


            

@receiver(post_save, sender=Equipment)
def update_section_created(sender, instance, created, **kwargs):
    if created:
        update_transaction_date(instance)


class Item(BasicInfo):
    name                = models.CharField(max_length=50)
    seq                 = models.IntegerField(default=50)
    equipment           = models.ForeignKey(Equipment,
                            on_delete=models.CASCADE,
                            related_name = 'items')
    parameter           = models.ForeignKey(Parameter,
                            on_delete=models.CASCADE,
                            related_name = 'items')
    units               = models.CharField(max_length=15,blank=True, null=True)
    user 			    = models.ForeignKey(settings.AUTH_USER_MODEL,
                            on_delete=models.CASCADE,
                            blank=True,null=True,related_name = 'items')
    # Added on Oct 21,2022 --To save current reading value
    current_value       = models.IntegerField(default=0)
    # Added on March 19,2024 -- To specific type of parameter Monitor(true)/Report
    monitor             = models.BooleanField(default=False)

    def __str__(self):
        return f'{self.name} on {self.equipment.name}'

    class Meta(BasicInfo.Meta):
        db_table = 'equipment_item'
        ordering = ['seq']


class DataLogger(BasicInfo):
    item                 = models.ForeignKey(Item,
                            on_delete=models.CASCADE,
                            related_name = 'loggers')
    last_value           = models.IntegerField(default=0)
    current_value        = models.IntegerField(default=0)

    @property
    def diff(self):
        return self.current_value - self.last_value

    def __str__(self):
        return f'Reding value :{self.current_value}'

@receiver(post_save, sender=DataLogger)
def update_datalogger_created(sender, instance, created, **kwargs):
    if created:
        update_transaction_date(instance)