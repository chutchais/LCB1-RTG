from django.db import models

# Create your models here.
from re import T
from django.db import models

from django.conf 	            import settings
from django.db.models.signals   import post_save
from django.dispatch            import receiver
from base.models                import BasicInfo
from base.utility               import update_transaction_date,get_execution_time_in_minutes
from measuring.models           import FIELDS_TYPE_CHOICES, Parameter
import logging
from django.urls                import reverse
import os
import datetime

# Added on May 18,2025
from maintenance.mosquitto import get_mqtt_message


# maintenance section
TYPE_CHOICES = (
    ("RTG", "RTG"),
    ("CRANE", "CCrane"),
    ("HUSTLER", "Hustler"),
    ("TRAILER", "Trailer"),
    ("TOPLIFT", "TOP Lift"),
    ("RS", "Reach stacker"),
)

SECTION_CHOICES = (
    ("MOBILE", "Mobile"),
    ("CRANE", "Crane"),
)

STATUS_CHOICES = (
    ("OPEN", "Open"),
    ("CLOSED", "Closed"),
)

SYMPTOM_AREA_CHOICES = (
    ("AC","Air Condition"),
    ("BRAKE", "Brake"),
    ("ELECTRIC","Electric"),
    ("ENGINE", "Engine"),
    ("HYDRAULIC", "Hydraulic"),
    ("GEARBOX", "Gearbox"),
    ("TRANSMISSION", "Transmission"),
    ("SPREADER","Spreader"),
    ("OTHER","Other"),
)

TERMINAL_CHOICES = (
    ("LCMT", "LCMT"),
    ("LCB1", "LCB1"),
)

# Crane,Mobile,Fac,Store
class Section(BasicInfo):
    name                = models.CharField(max_length=50,primary_key=True)
    title               = models.CharField(max_length=50,blank=True, null=True)
    user 			    = models.ForeignKey(settings.AUTH_USER_MODEL,
                            on_delete=models.CASCADE,
                            blank=True,null=True,related_name = 'ma_sections')
    def __str__(self):
        return self.name
    
    def get_absolute_url(self):
        return reverse('maintenance:detail', kwargs={'section': self.name})
    
    @property
    def machine_type_count(self):
        return self.ma_machine_types.all().count()
    
    class Meta(BasicInfo.Meta):
        db_table = 'ma-section'
        ordering = ('name',)

class MachineType(BasicInfo):
    name                = models.CharField(max_length=50,primary_key=True)
    title               = models.CharField(max_length=50,blank=True, null=True)
    section             = models.ForeignKey(Section,
                            on_delete=models.CASCADE,
                            blank=True,null=True,related_name = 'ma_machine_types')
    target              = models.FloatField(default=0)
    user 			    = models.ForeignKey(settings.AUTH_USER_MODEL,
                            on_delete=models.CASCADE,
                            blank=True,null=True,related_name = 'ma_machine_types')
    def __str__(self):
        return self.name

    @property
    def machine_count(self):
        return self.ma_machines.all().count()

    # Added on Oct 3,2024 -- To count machine that on working
    @property
    def machine_on_working(self):
        return sum([ms.on_repair for ms in self.ma_machines.all()])
        # return Failure.objects.filter(machine__machine_type=self,status='OPEN').count()
 
    @property
    def machine_on_preventive(self):
        return sum([ms.on_preventive for ms in self.ma_machines.all()])
        # return Preventive.objects.filter(machine__machine_type=self,status='WORKING').count()
    
    @property
    def machine_available(self):
        return self.machine_count-(self.machine_on_working+self.machine_on_preventive)
    # -------------------------------------------------------
    # Added on Jan 22,2025 -- To support to get availability data
    @property
    def availability_data(self):
        import datetime, pytz
        tz 			= pytz.timezone('Asia/Bangkok')
        today_tz 	=   datetime.datetime.now(tz=tz)
        key = f'{today_tz.year}:{self.name}:AVAILABILITY'
        from maintenance.tasks import get_daily_data_all
        return get_daily_data_all(key)
    
    class Meta(BasicInfo.Meta):
        db_table = 'ma-machine_types'
        ordering = ('name',)


class Machine(BasicInfo):
    name                = models.CharField(max_length=50,primary_key=True)
    title               = models.CharField(max_length=50,blank=True, null=True)
    terminal            = models.CharField(max_length=10,choices=TERMINAL_CHOICES,default='LCMT')
    machine_type        = models.ForeignKey(MachineType,
                            on_delete=models.CASCADE,
                            blank=True,null=True,related_name = 'ma_machines')
    user 			    = models.ForeignKey(settings.AUTH_USER_MODEL,
                            on_delete=models.CASCADE,
                            blank=True,null=True,related_name = 'ma_machines')
    # Added on May 25,2025 -- To collect hour, move, and fault
    engine_hour_next_pm = models.DecimalField(max_digits=10, 
                                    decimal_places=2,default=0, blank=True,null=True) 
    engine_move_next_pm = models.IntegerField(default=0)

    def __str__(self):
        return self.name
    
    @property
    def on_repair(self):
        return 0 if self.failures.filter(status='OPEN').count() == 0 else 1

    @property
    def on_preventive(self):
        return 0 if self.pms.filter(status='WORKING').count() == 0 else 1
    # Added on Jan 22,2025 -- To support to get availability data
    @property
    def availability_data(self):
        import datetime, pytz
        tz 			= pytz.timezone('Asia/Bangkok')
        today_tz 	=   datetime.datetime.now(tz=tz)
        key = f'{today_tz.year}:{self.name}:AVAILABILITY'
        from maintenance.tasks import get_daily_data_all
        return get_daily_data_all(key)
    # Added on Jan 27,2025 -- TO support to get status
    @property
    def status_data(self):
        import datetime, pytz
        tz 			= pytz.timezone('Asia/Bangkok')
        today_tz 	=   datetime.datetime.now(tz=tz)
        key = f'{today_tz.year}:{self.name}:STATUS'
        from maintenance.tasks import get_daily_data_all
        return get_daily_data_all(key)

    # Added on May 18,2025 -- To support get data from MQTT
    @property
    def engine_hour(self):
        return get_mqtt_message(self.name,"hour")
    engine_hour.fget.short_description = 'Total engine hour (hour)'

    @property
    def engine_move(self):
        return get_mqtt_message(self.name,"move")
    engine_move.fget.short_description = 'Total move (time)'

    @property
    def engine_malfunction(self):
        return get_mqtt_message(self.name,"malfunction")
    engine_malfunction.fget.short_description = 'Engine Malfunction'

    @property
    def mqtt_updated(self):
        return get_mqtt_message(self.name,"updated")
    mqtt_updated.fget.short_description = 'Last updated'

    @property
    def is_overdue(self):
        engine_hour = 0 if self.engine_hour is None else self.engine_hour
        engine_move = 0 if self.engine_move is None else self.engine_move
        # return True if (self.engine_hour_next_pm >= engine_hour or 
        #                 self.engine_move_next_pm >= engine_move ) else False
        return False
    is_overdue.fget.short_description = 'Overdue'

    class Meta(BasicInfo.Meta):
        db_table = 'ma-machine'
        ordering = ('name',)

FAILURE_TYPE_CHOICES = (
    ("AO", "Assit Operation"),
    ("BO", "Breakdown outside operation"),
    ("BD", "Breakdown"),
    ("CM", "Corrective maintenance"),
    ("PC", "Power Cut")
)

SHIFT_CHOICES =(
    ("Day" , "Day"),
    ("Night" , "Night")
    )

# Added on Dec 28,2024 -- To collect vendor
class Vendor(BasicInfo):
    name                = models.CharField(max_length=50,primary_key=True)
    title               = models.CharField(max_length=50,blank=True, null=True)
    user 			    = models.ForeignKey(settings.AUTH_USER_MODEL,
                            on_delete=models.CASCADE,
                            blank=True,null=True,related_name = 'ma_vendors')
    def __str__(self):
        return self.name
    
    def get_absolute_url(self):
        return reverse('maintenance:vendor', kwargs={'vendor': self.name})
    
class Failure(BasicInfo):
    machine             = models.ForeignKey(Machine,
                            on_delete=models.SET_NULL,
                            blank=True,null=True,related_name = 'failures')
    start_date          = models.DateTimeField(blank=True,null=True)
    expect_date         = models.DateTimeField(blank=True,null=True)
    end_date            = models.DateTimeField(blank=True,null=True)
    status              = models.CharField(max_length=10,choices=STATUS_CHOICES,default='OPEN')
    category            = models.CharField(max_length=10,choices=FAILURE_TYPE_CHOICES,default='BD')
    details             = models.TextField(max_length=200,blank=True, null=True)
    user 			    = models.ForeignKey(settings.AUTH_USER_MODEL,
                            on_delete=models.CASCADE,
                            blank=True,null=True,related_name = 'failures')
    # Added on Dec 20,2024 -- To collect rootcause and repair_action
    rootcause            = models.TextField(max_length=200,blank=True, null=True)
    repair_action       = models.TextField(max_length=200,blank=True, null=True)

    # Added on Dec 28,2024 -- To collect vendor, repair cost, and service cost
    vendor               = models.ForeignKey(Vendor,
                            on_delete=models.SET_NULL,
                            blank=True, null=True,related_name="failures")
    repair_cost          = models.DecimalField(max_digits=10, 
                                               decimal_places=2, blank=True,null=True)
    service_cost         = models.DecimalField(max_digits=10, 
                                               decimal_places=2, blank=True,null=True)
    # Added on Jan 25, 2025 -- To collect operation date and working shift
    operation_date       = models.DateField(blank=True,null=True)
    operation_shift      = models.CharField(blank=True,null=True,
                                            max_length=10,choices=SHIFT_CHOICES,default='DAY')
    # Added on March 21,2025 -- To collect machine receiving date
    receiving_date          = models.DateTimeField(blank=True,null=True)
    # Added on May 25,2025 -- To collect hour, move, and fault
    engine_hour             = models.DecimalField(max_digits=10, 
                                    decimal_places=2, default=0, blank=True,null=True) 
    engine_move             = models.IntegerField(default=0)
    engine_malfunction      = models.CharField(max_length=1,default='0')

    def __str__(self):
        return f'{self.machine} - {self.details[1:20]}'
    
    def get_absolute_url(self):
        return reverse('maintenance:failure-detail', kwargs={'pk': self.pk})

    @property
    def defect_count(self):
        return self.defects.all().count()
    
    @property
    def image_count(self):
        return self.images.all().count()

    @property
    def repairing_time(self):
        # Return in minute
        if self.start_date and self.end_date :
            return get_execution_time_in_minutes(self.start_date,self.end_date)
        else:
            # Job is on going
            from datetime import datetime
            from django.utils import timezone
            tz = timezone.get_current_timezone()
            today = timezone.now().astimezone(tz)#.date()
            return get_execution_time_in_minutes(self.start_date,today)

    repairing_time.fget.short_description = 'Repairing time (minute)'

# Added on March 22,2025 --
    @property
    def lead_time(self):
        # Return in minute
        # MOdify on March 24,2025 - To fix in case No receiving date assigned.
        if self.receiving_date :
            if self.end_date :#if job is done.
                return get_execution_time_in_minutes(self.receiving_date,self.end_date)
            else:
                # Job is on going
                from datetime import datetime
                from django.utils import timezone
                tz = timezone.get_current_timezone()
                today = timezone.now().astimezone(tz)#.date()
                return get_execution_time_in_minutes(self.receiving_date,today)
        else:
            return self.elapsed_time
    lead_time.fget.short_description = 'Lead time (minute)'

# Added on Apr 3,2025 --
    @property
    def waitting_time(self):
        # Return in minute
        # MOdify on March 24,2025 - To fix in case No receiving date assigned.
        if self.receiving_date and self.start_date :
            return get_execution_time_in_minutes(self.receiving_date,self.start_date)
        else:
            # Job is on going
            from datetime import datetime
            from django.utils import timezone
            tz = timezone.get_current_timezone()
            today = timezone.now().astimezone(tz)#.date()
            return get_execution_time_in_minutes(self.receiving_date,today)
        
    waitting_time.fget.short_description = 'Waitting time (minute)'

    class Meta(BasicInfo.Meta):
        db_table = 'ma-failure'
        ordering = ('-start_date',)


REPAIR_ACTION_CHOICES = (
    ("FIX", "Fix"),
    ("REPLACE", "Repalce"),
    ("CHECK", "Check"),
)

class Defect(BasicInfo):
    failure             = models.ForeignKey(Failure,
                            on_delete=models.CASCADE,
                            blank=True,null=True,related_name = 'defects')
    symptom_area        = models.CharField(max_length=20,choices=SYMPTOM_AREA_CHOICES,default='Engine')
    details             = models.TextField(max_length=200,blank=True, null=True)
    status              = models.CharField(max_length=10,choices=STATUS_CHOICES,default='OPEN')
    repair              = models.CharField(max_length=20,choices=REPAIR_ACTION_CHOICES,default='FIX')
    repair_details      = models.TextField(max_length=200,blank=True, null=True)
    repair_done         = models.BooleanField(default=False)
    user 			    = models.ForeignKey(settings.AUTH_USER_MODEL,
                            on_delete=models.CASCADE,
                            blank=True,null=True,related_name = 'defects')
    # Added on Jan 25, 2025 -- To collect operation date and working shift
    operation_date       = models.DateField(blank=True,null=True)
    operation_shift      = models.CharField(blank=True,null=True,
                                            max_length=10,choices=SHIFT_CHOICES,default='DAY')

    def __str__(self):
        return self.symptom_area

    class Meta(BasicInfo.Meta):
        db_table = 'ma-defect'
        ordering = ('-created',)


PM_STATUS_CHOICES = (
    ("PLAN", "PLAN"),
    ("WORKING", "WORKING"),
    ("DONE", "DONE"),
)

PM_PERIOD_CHOICES = (
    ("HR", "Hour"),
    ("KM", "Kilometer"),
    ("MOVE", "Move"),
)
class Preventive(BasicInfo):
    machine             = models.ForeignKey(Machine,
                            on_delete=models.SET_NULL,
                            blank=True,null=True,related_name = 'pms')
    details             = models.TextField(max_length=200,blank=True, null=True)
    period              = models.SmallIntegerField(blank=True,null=True,default=500)
    period_unit         = models.CharField(max_length=10,choices=PM_PERIOD_CHOICES,default='HR')
    start_date          = models.DateTimeField(blank=True,null=True)
    end_date            = models.DateTimeField(blank=True,null=True)
    status              = models.CharField(max_length=10,choices=PM_STATUS_CHOICES,default='PLAN')
    user 			    = models.ForeignKey(settings.AUTH_USER_MODEL,
                            on_delete=models.CASCADE,
                            blank=True,null=True,related_name = 'pms')
    # Added on Jan 25, 2025 -- To collect operation date and working shift
    operation_date       = models.DateField(blank=True,null=True)
    operation_shift      = models.CharField(blank=True,null=True,
                                            max_length=10,choices=SHIFT_CHOICES,default='DAY')

    # Added on May 25,2025 -- To collect hour, move, and fault
    engine_hour             = models.DecimalField(max_digits=10, 
                                    decimal_places=2, blank=True,null=True) 
    engine_move             = models.IntegerField(default=0)
    engine_malfunction      = models.CharField(max_length=1,default='0')

    def __str__(self):
        return f'{self.period} {self.period_unit}'

    @property
    def image_count(self):
        return self.images.all().count()

    def get_absolute_url(self):
        return reverse('maintenance:preventive-detail', kwargs={'pk': self.pk})
   
    class Meta(BasicInfo.Meta):
        db_table = 'ma-pm'
        ordering = ('-created',)


def failure_upload_path(instance, filename):
    # name = instance.__class__.__name__.lower()
    return os.path.join('failure/{}/{}/{}/{}/{}/{}'.format(
        datetime.datetime.now().year,
        datetime.datetime.now().month,
        datetime.datetime.now().day,
        instance.failure.machine.machine_type,
        instance.failure.machine,filename))

def accident_upload_path(instance, filename):
    # name = instance.__class__.__name__.lower()
    return os.path.join('accident/{}/{}/{}/{}/{}/{}'.format(
        datetime.datetime.now().year,
        datetime.datetime.now().month,
        datetime.datetime.now().day,
        instance.accident.machine.machine_type,
        instance.accident.machine,filename))

# Added on Dec 19,2024 -- To support image for PM
def preventive_upload_path(instance, filename):
    # name = instance.__class__.__name__.lower()
    return os.path.join('pm/{}/{}/{}/{}/{}/{}'.format(
        datetime.datetime.now().year,
        datetime.datetime.now().month,
        datetime.datetime.now().day,
        instance.preventive.machine.machine_type,
        instance.preventive.machine,filename))

class FailureImage(BasicInfo):
    failure             = models.ForeignKey(Failure,
                            on_delete=models.SET_NULL,
                            blank=True,null=True,related_name = 'images')
    image               = models.ImageField(upload_to=failure_upload_path)
    details             = models.CharField(max_length=100,blank=True, null=True)
    user 			    = models.ForeignKey(settings.AUTH_USER_MODEL,
                            on_delete=models.CASCADE,
                            blank=True,null=True,related_name = 'failure_images')
    
    def filename(self):
        return os.path.basename(self.image.name)

    def __str__(self):
        return f'{self.filename()}'

    class Meta(BasicInfo.Meta):
        db_table = 'ma-failure-image'
        ordering = ('-created',)


class Accident(BasicInfo):
    machine             = models.ForeignKey(Machine,
                            on_delete=models.SET_NULL,
                            blank=True,null=True,related_name = 'accidents')
    details             = models.TextField(max_length=200,blank=True, null=True)
    status              = models.CharField(max_length=10,choices=STATUS_CHOICES,default='OPEN')
    user 			    = models.ForeignKey(settings.AUTH_USER_MODEL,
                            on_delete=models.CASCADE,
                            blank=True,null=True,related_name = 'accidents')
    # Added on Jan 25, 2025 -- To collect operation date and working shift
    operation_date       = models.DateField(blank=True,null=True)
    operation_shift      = models.CharField(blank=True,null=True,
                                            max_length=10,choices=SHIFT_CHOICES,default='DAY')
    @property
    def image_count(self):
        return self.images.all().count()
    
    def __str__(self):
        return f'{self.machine} - {self.details[1:20]}'
    
    class Meta(BasicInfo.Meta):
        db_table = 'ma-accident'
        ordering = ('-created',)

class AccidentImage(BasicInfo):
    accident             = models.ForeignKey(Accident,
                            on_delete=models.SET_NULL,
                            blank=True,null=True,related_name = 'images')
    image               = models.ImageField(upload_to=accident_upload_path)
    details             = models.CharField(max_length=100,blank=True, null=True)
    user 			    = models.ForeignKey(settings.AUTH_USER_MODEL,
                            on_delete=models.CASCADE,
                            blank=True,null=True,related_name = 'accident_images')
    
    def filename(self):
        return os.path.basename(self.image.name)

    def __str__(self):
        return f'{self.filename()}'

    class Meta(BasicInfo.Meta):
        db_table = 'ma-accident-image'
        ordering = ('-created',)


# Added on Dec 19,2024 -- To support PM image
class PreventiveImage(BasicInfo):
    preventive          = models.ForeignKey(Preventive,
                            on_delete=models.SET_NULL,
                            blank=True,null=True,related_name = 'images')
    image               = models.ImageField(upload_to=preventive_upload_path)
    details             = models.CharField(max_length=100,blank=True, null=True)
    user 			    = models.ForeignKey(settings.AUTH_USER_MODEL,
                            on_delete=models.CASCADE,
                            blank=True,null=True,related_name = 'preventive_images')
    
    def filename(self):
        return os.path.basename(self.image.name)

    def __str__(self):
        return f'{self.filename()}'

    class Meta(BasicInfo.Meta):
        db_table = 'ma-preventive-image'
        ordering = ('-created',)


# class ContentManager(models.Manager):
#     def all(self):
#         qs = super().all()
#         return qs

#     def filter_by_instance(self, instance):
#         content_type = ContentType.objects.get_for_model(instance.__class__)
#         obj_id = instance.id
#         qs = super().filter(
#             content_type=content_type, object_id=obj_id)
#         return qs
    
# Support multiple image for each contianer
# class Media(models.Model):
#     image           = models.ImageField(upload_to=get_upload_path)
#     details         = models.TextField(max_length=100,blank=True, null=True)
#     content_type    = models.ForeignKey(ContentType, on_delete=models.CASCADE)
#     object_id       = models.PositiveIntegerField()
#     content_object  = GenericForeignKey('content_type', 'object_id')
#     created_date    = models.DateTimeField(auto_now_add=True)
#     modified_date   = models.DateTimeField(auto_now=True)

#     objects = ContentManager()

#     class Meta:
#         default_related_name = 'media'
#         verbose_name = 'media'
#         verbose_name_plural = 'media'
#         # ordering = ['order']

#     def get_object(self):
#         ct = ContentType.objects.get_for_model(self.content_object)
#         obj = ct.get_object_for_this_type(pk=self.object_id)
#         return obj

#     def filename(self):
#         return os.path.basename(self.image.name)

#     def __str__(self):
#         return self.filename()