from django.apps import AppConfig


class MaintenanceConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'maintenance'

    def ready(self):
        import logging
        logger = logging.getLogger(__name__)
        try:
            from django.conf import settings
            from django_q.models import Schedule

            schedule_time = getattr(settings, 'PM_REPORT_SCHEDULE_TIME', '06:00')
            hour, minute = schedule_time.split(':')
            cron_expr = f'{minute} {hour} * * *'

            Schedule.objects.get_or_create(
                func='maintenance.tasks.send_pm_status_report_with_monitoring',
                defaults={
                    'name': 'PM Status Report with Data Monitoring',
                    'schedule_type': Schedule.CRON,
                    'cron': cron_expr,
                    'repeats': -1,
                }
            )
        except Exception as exc:
            logger.warning('Could not register PM status report schedule: %s', exc)
