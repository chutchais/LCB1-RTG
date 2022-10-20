from django.db                  import models

class BasicInfo(models.Model):
    created                 = models.DateTimeField(auto_now_add=True)
    updated                 = models.DateTimeField(blank=True, null=True,auto_now=True)
    status                  = models.BooleanField(default=True)
    created_year            = models.PositiveSmallIntegerField(default=2022)
    created_month           = models.PositiveSmallIntegerField(default=1)
    created_day             = models.PositiveSmallIntegerField(default=1)
    created_hour            = models.PositiveSmallIntegerField(default=0)
    created_week            = models.PositiveSmallIntegerField(default=1)

    class Meta:
        abstract = True

