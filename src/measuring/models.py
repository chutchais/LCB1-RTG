from django.db import models

# Create your models here.
from django.conf 	            import settings
from django.db.models.signals   import post_save
from django.dispatch            import receiver
from base.models                import BasicInfo
from base.utility               import update_transaction_date


FIELDS_TYPE_CHOICES = (
        ('int', 'int'), #2byte
        ('dint', 'dint'),#4byte
        ('real', 'real'),#4byte
        ('word', 'word'),#4byte
    )

class Parameter(BasicInfo):
    name                = models.CharField(max_length=50,primary_key=True)
    title               = models.CharField(max_length=50,blank=True, null=True)
    db_number           = models.IntegerField(default=1)
    offset              = models.IntegerField(default=0)
    field_type          = models.CharField(max_length=10,blank=True,null=True
                            ,choices=FIELDS_TYPE_CHOICES,default='int')
    user 			    = models.ForeignKey(settings.AUTH_USER_MODEL,
                            on_delete=models.CASCADE,
                            blank=True,null=True,related_name = 'parameters')
    def __str__(self):
        return f'{self.name} DB:{self.db_number} Offset:{self.offset} {self.field_type}'

    class Meta(BasicInfo.Meta):
        db_table = 'parameter'

@receiver(post_save, sender=Parameter)
def update_parameter_created(sender, instance, created, **kwargs):
    if created:
        update_transaction_date(instance)