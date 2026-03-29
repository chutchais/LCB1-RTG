# Generated migration for CMRP fields - March 29, 2026

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('maintenance', '0019_alter_failurecategory_code'),  # Replace with your last migration
    ]

    operations = [
        # Add commissioned_date to Machine model
        migrations.AddField(
            model_name='machine',
            name='commissioned_date',
            field=models.DateField(blank=True, null=True, help_text='Date when machine was commissioned'),
        ),
        
        # Add is_human_error to Failure model
        migrations.AddField(
            model_name='failure',
            name='is_human_error',
            field=models.BooleanField(default=False, help_text='Flag if failure was caused by human error'),
        ),
        
        # Add human_error_details to Failure model
        migrations.AddField(
            model_name='failure',
            name='human_error_details',
            field=models.TextField(blank=True, null=True, help_text='Details about the human error that caused the failure'),
        ),
    ]