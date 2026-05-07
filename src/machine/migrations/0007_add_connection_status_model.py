from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('machine', '0006_item_monitor'),
    ]

    operations = [
        migrations.CreateModel(
            name='ConnectionStatus',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                
                # Own timestamp fields
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                
                # ConnectionStatus specific fields
                ('connection_status', models.CharField(
                    choices=[
                        ('success', 'Successfully connected'),
                        ('failed', 'Connection failed'),
                        ('timeout', 'Connection timeout'),
                        ('partial', 'Partial read (some items failed)'),
                    ],
                    help_text='Connection status (success/failed/timeout/partial)',
                    max_length=20
                )),
                ('error_message', models.CharField(
                    blank=True,
                    help_text='Error message if failed',
                    max_length=255
                )),
                ('items_data', models.JSONField(
                    blank=True,
                    default=dict,
                    help_text="Item readings data: {'Crane On Hour': 1720, 'Production Count': 5432, ...}"
                )),
                ('recorded_at', models.DateTimeField(
                    help_text='When this status was recorded'
                )),
                ('shift', models.CharField(
                    choices=[
                        ('morning', 'Morning Shift (08:00 - 20:00)'),
                        ('night', 'Night Shift (20:00 - 08:00)'),
                    ],
                    default='morning',
                    help_text='Which shift this status was recorded during',
                    max_length=10
                )),
                ('shift_date', models.DateField(
                    help_text='Date of shift start (morning: same day, night: previous day)'
                )),
                
                # Foreign key
                ('equipment', models.ForeignKey(
                    help_text='Equipment this status is for',
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='connection_statuses',
                    to='machine.equipment'
                )),
            ],
            options={
                'db_table': 'equipment_connection_status',
                'ordering': ['-recorded_at'],
            },
        ),
        
        # Add indexes
        migrations.AddIndex(
            model_name='connectionstatus',
            index=models.Index(fields=['equipment', '-recorded_at'], name='conn_equip_rec_idx'),
        ),
        migrations.AddIndex(
            model_name='connectionstatus',
            index=models.Index(fields=['-recorded_at'], name='conn_rec_idx'),
        ),
        migrations.AddIndex(
            model_name='connectionstatus',
            index=models.Index(fields=['equipment', 'shift', 'shift_date'], name='conn_equip_shift_idx'),
        ),
        migrations.AddIndex(
            model_name='connectionstatus',
            index=models.Index(fields=['shift', 'shift_date'], name='conn_shift_date_idx'),
        ),
    ]