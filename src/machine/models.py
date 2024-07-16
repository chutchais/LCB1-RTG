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
        from .tasks import read_value,save_redis,save_previous_redis,get_previous_redis
        import datetime, pytz
        logging.info(f'Start reading data of {self.name} ({self.ip})')
        # print(f'Start reading data of {self.name} ({self.ip})')
        tz      = pytz.timezone('Asia/Bangkok')
        now_tz  =   datetime.datetime.now(tz=tz)
        value_dict = {}
        for item in self.items.all():
            if item.monitor : continue #skip if monitor parameter is True
            ip          = self.ip
            db_number   = item.parameter.db_number
            offset      = item.parameter.offset
            field_type  = item.parameter.field_type
            value       = read_value(ip,db_number,offset,field_type)

            # Added on Oct 21,2022 -- to add Online status
            # value_dict['live'] = True if value != -1 else False

            key = f'{self.name}:{item.parameter.name}:PREVIOUS'
            if value == -1 :
                logging.warn(f'Unable to read data from machine: {key} -->{value}')
                value = get_previous_redis(key)
                print(f'Get current value of : {key} -->{value}')
                
            else:
                # Added on July 11,2024 -- To ensure new read value more than current value
                # Edit on JUly 16,2024 -- To protect Over value , more than 30.
                # if value > item.current_value :
                offset_reading_value = 30
                if value > item.current_value and value < item.current_value + offset_reading_value   :
                    save_previous_redis(key,value)
                    # Added on Oct 21,2022 -- Save to Current value on Item
                    item.current_value = value
                    item.save()
                    print(f'Save to current value of {key}-->{value} -- Successful')
                else:
                    logging.warn(f'Reading value is less or more than current value of : {key} --> Read :{value} , Current : {item.current_value}')

            value_dict[item.name] = value
            logging.info(f'{item} -->{value} {item.units}')
            # print(f'{item} -->{value} {item.units}')
        
        value_dict['Equipment']     = self.name
        value_dict['DateTime']      = now_tz.strftime("%b %d %H:%M")#now_tz.strftime("%Y-%m-%d %H:%M:%S")

        # Save to Redis (DB0), key = {Name}{item.name} , value = Reading value
        key = f'{self.name}:LATEST'
        save_redis(key,value_dict)
        # print(value_dict)
    
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
            value_latest    = save_redis_stack(key_lastest,value)
            value_dict[f'{item.name}:LIST'] = value_latest
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