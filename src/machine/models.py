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
            ip          = self.ip
            db_number   = item.parameter.db_number
            offset      = item.parameter.offset
            field_type  = item.parameter.field_type
            value       = read_value(ip,db_number,offset,field_type)

            key = f'{self.name}:{item.parameter.name}:PREVIOUS'
            if value == -1 :
                logging.warn(f'Get previous value of : {key} -->{value}')
                value = get_previous_redis(key)
                print(f'Get previous value of : {key} -->{value}')
                
            else:
                save_previous_redis(key,value)
                print(f'Save to previous value of {key}-->{value} -- Successful')

            value_dict[item.name] = value
            logging.info(f'{item} -->{value} {item.units}')
            # print(f'{item} -->{value} {item.units}')
        
        value_dict['Equipment']     = self.name
        value_dict['DateTime']      = now_tz.strftime("%b %d %H:%M")#now_tz.strftime("%Y-%m-%d %H:%M:%S")

        # Save to Redis (DB0), key = {Name}{item.name} , value = Reading value
        key = f'{self.name}:LATEST'
        save_redis(key,value_dict)
        # print(value_dict)


            

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
    def __str__(self):
        return self.name

    class Meta(BasicInfo.Meta):
        db_table = 'equipment_item'
        ordering = ['seq']


