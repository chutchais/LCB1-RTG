from django.db import models

# Create your models here.
from re import T
from django.db import models

from django.conf 	            import settings
from django.db.models.signals   import post_save
from django.dispatch            import receiver
from base.models                import BasicInfo
from base.utility               import update_transaction_date
from measuring.models           import FIELDS_TYPE_CHOICES, Parameter
import logging


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
        return Failure.objects.filter(machine__machine_type=self,status='OPEN').count()
 
    @property
    def machine_on_preventive(self):
        return Preventive.objects.filter(machine__machine_type=self,status='WORKING').count()
    # -------------------------------------------------------

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
    def __str__(self):
        return self.name
    
    @property
    def on_repair(self):
        return self.failures.filter(status='OPEN').count()

    @property
    def on_preventive(self):
        return self.pms.filter(status='WORKING').count()
    
    class Meta(BasicInfo.Meta):
        db_table = 'ma-machine'
        ordering = ('name',)

FAILURE_TYPE_CHOICES = (
    ("AO", "Assit Operation"),
    ("BO", "Breakdown outside operation"),
    ("BD", "Breakdown"),
    ("PC", "Power Cut")
)
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


    def __str__(self):
        return f'{self.start_date.strftime("%Y-%m-%d")} - {self.details[1:20]}'

    @property
    def defect_count(self):
        return self.defects.all().count()
    
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
    def __str__(self):
        return f'{self.period} {self.period_unit}'

   
    class Meta(BasicInfo.Meta):
        db_table = 'ma-pm'
        ordering = ('-created',)