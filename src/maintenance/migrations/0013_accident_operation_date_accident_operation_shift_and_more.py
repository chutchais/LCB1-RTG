# Generated by Django 4.1.2 on 2025-01-25 04:10

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('maintenance', '0012_failure_repair_cost_failure_service_cost_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='accident',
            name='operation_date',
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='accident',
            name='operation_shift',
            field=models.CharField(blank=True, choices=[('DAY', 'Day'), ('NIGHT', 'Night')], default='DAY', max_length=10, null=True),
        ),
        migrations.AddField(
            model_name='defect',
            name='operation_date',
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='defect',
            name='operation_shift',
            field=models.CharField(blank=True, choices=[('DAY', 'Day'), ('NIGHT', 'Night')], default='DAY', max_length=10, null=True),
        ),
        migrations.AddField(
            model_name='failure',
            name='operation_date',
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='failure',
            name='operation_shift',
            field=models.CharField(blank=True, choices=[('DAY', 'Day'), ('NIGHT', 'Night')], default='DAY', max_length=10, null=True),
        ),
        migrations.AddField(
            model_name='preventive',
            name='operation_date',
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='preventive',
            name='operation_shift',
            field=models.CharField(blank=True, choices=[('DAY', 'Day'), ('NIGHT', 'Night')], default='DAY', max_length=10, null=True),
        ),
    ]
