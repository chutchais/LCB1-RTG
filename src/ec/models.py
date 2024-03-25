from django.db import models

# Create your models here.
from django.conf 	            import settings
from django.db.models.signals   import post_save
from django.dispatch            import receiver
from base.models                import BasicInfo
# from base.utility               import update_transaction_date
# from measuring.models           import FIELDS_TYPE_CHOICES, Parameter
import logging

from machine.models             import Equipment
# Department section
class Events(BasicInfo):
    gkey                = models.IntegerField(primary_key=True)
    timestamp           = models.DateTimeField()
    type_desc           = models.CharField(max_length=10.blank=True,null=True)
    equipment 			= models.ForeignKey(Equipment,
                            on_delete=models.CASCADE,
                            blank=True,null=True,related_name = 'events')
    operator_name       = models.CharField(max_length=20,blank=True,null=True)
    move_kind           = models.CharField(max_length=10,blank=True,null=True)
    unit_id             = models.CharField(max_length=30,blank=True,null=True)
    is_twin             = models.BooleanField(default=False)
    pow                 = models.CharField(max_length=30,blank=True,null=True)
    loc_slot            = models.CharField(max_length=20,blank=True,null=True)
    unladen_loc_slot    = models.CharField(max_length=20,blank=True,null=True)
    laden_loc_slot    = models.CharField(max_length=20,blank=True,null=True)

    def __str__(self):
        return self.equipment
