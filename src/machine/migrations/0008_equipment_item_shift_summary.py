from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('machine', '0007_add_connection_status_model'),
    ]

    operations = [
        migrations.CreateModel(
            name='EquipmentItemShiftSummary',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('shift_date', models.DateField(help_text='Date of shift start (morning: same day, night: previous day)')),
                ('shift', models.CharField(choices=[('morning', 'Morning Shift (08:00 - 20:00)'), ('night', 'Night Shift (20:00 - 08:00)')], help_text='Shift this summary belongs to', max_length=10)),
                ('item_name', models.CharField(help_text='Item name from items_data JSON', max_length=100)),
                ('first_value', models.FloatField(blank=True, null=True)),
                ('last_value', models.FloatField(blank=True, null=True)),
                ('difference', models.FloatField(default=0)),
                ('reset_count', models.IntegerField(default=0)),
                ('has_reset', models.BooleanField(default=False)),
                ('record_count', models.IntegerField(default=0)),
                ('segments_json', models.JSONField(blank=True, default=list)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('equipment', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='item_shift_summaries', to='machine.equipment')),
            ],
            options={
                'db_table': 'equipment_item_shift_summary',
                'ordering': ['-shift_date', 'equipment', 'shift', 'item_name'],
            },
        ),
        migrations.AddConstraint(
            model_name='equipmentitemshiftsummary',
            constraint=models.UniqueConstraint(fields=('equipment', 'shift_date', 'shift', 'item_name'), name='uniq_item_shift_summary'),
        ),
        migrations.AddIndex(
            model_name='equipmentitemshiftsummary',
            index=models.Index(fields=['shift_date', 'equipment'], name='eiss_shift_date_equipment_idx'),
        ),
        migrations.AddIndex(
            model_name='equipmentitemshiftsummary',
            index=models.Index(fields=['shift_date', 'shift'], name='eiss_shift_date_shift_idx'),
        ),
        migrations.AddIndex(
            model_name='equipmentitemshiftsummary',
            index=models.Index(fields=['equipment', 'item_name'], name='eiss_equipment_item_idx'),
        ),
    ]
