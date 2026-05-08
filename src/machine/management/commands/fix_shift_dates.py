from django.core.management.base import BaseCommand
from django.utils import timezone
from machine.models import ConnectionStatus
from machine.services.connection_status_service import ConnectionStatusService
import pytz
from datetime import datetime


class Command(BaseCommand):
    help = 'Fix wrong shift_date values in ConnectionStatus records'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be changed without making changes',
        )
        parser.add_argument(
            '--date-from',
            type=str,
            help='Start date (YYYY-MM-DD) - only fix records from this date onwards',
        )
        parser.add_argument(
            '--date-to',
            type=str,
            help='End date (YYYY-MM-DD) - only fix records up to this date',
        )
        parser.add_argument(
            '--equipment',
            type=str,
            help='Only fix specific equipment name',
        )

    def handle(self, *args, **options):
        dry_run = options.get('dry_run', False)
        date_from = options.get('date_from')
        date_to = options.get('date_to')
        equipment = options.get('equipment')

        self.stdout.write('🔧 Fixing shift_date values in ConnectionStatus...\n')

        # Build query
        query = ConnectionStatus.objects.all()

        if date_from:
            try:
                from_date = datetime.strptime(date_from, '%Y-%m-%d').date()
                query = query.filter(recorded_at__date__gte=from_date)
                self.stdout.write(f'  📅 From date: {from_date}')
            except ValueError:
                self.stdout.write(self.style.ERROR(f'❌ Invalid date format: {date_from}'))
                return

        if date_to:
            try:
                to_date = datetime.strptime(date_to, '%Y-%m-%d').date()
                query = query.filter(recorded_at__date__lte=to_date)
                self.stdout.write(f'  📅 To date: {to_date}')
            except ValueError:
                self.stdout.write(self.style.ERROR(f'❌ Invalid date format: {date_to}'))
                return

        if equipment:
            query = query.filter(equipment__name=equipment)
            self.stdout.write(f'  🏭 Equipment: {equipment}')

        self.stdout.write(f'\n  Total records to check: {query.count()}\n')

        # Track changes
        fixed_count = 0
        wrong_count = 0
        errors = []

        tz = pytz.timezone('Asia/Bangkok')

        for record in query.order_by('recorded_at'):
            try:
                # Get correct shift_date based on recorded_at time
                recorded_at_tz = record.recorded_at.astimezone(tz) if record.recorded_at.tzinfo else tz.localize(
                    record.recorded_at)
                correct_shift_date = ConnectionStatusService.get_shift_date(recorded_at_tz)
                current_shift = ConnectionStatusService.get_current_shift(recorded_at_tz)

                # Check if wrong
                if record.shift_date != correct_shift_date or record.shift != current_shift:
                    wrong_count += 1

                    old_shift_date = record.shift_date
                    old_shift = record.shift

                    # Show what will be changed
                    self.stdout.write(
                        f'  ❌ Record ID {record.id}:\n'
                        f'     Time: {recorded_at_tz}\n'
                        f'     Old: shift={old_shift}, shift_date={old_shift_date}\n'
                        f'     New: shift={current_shift}, shift_date={correct_shift_date}'
                    )

                    if not dry_run:
                        # Update the record
                        record.shift_date = correct_shift_date
                        record.shift = current_shift
                        record.save(update_fields=['shift_date', 'shift'])
                        self.stdout.write(self.style.SUCCESS(f'     ✅ Fixed!\n'))
                        fixed_count += 1
                    else:
                        self.stdout.write(self.style.WARNING(f'     (DRY RUN - not saved)\n'))
                        fixed_count += 1

            except Exception as e:
                errors.append({
                    'record_id': record.id,
                    'error': str(e)
                })
                self.stdout.write(self.style.ERROR(f'  ⚠️  Error processing record {record.id}: {str(e)}'))

        # Summary
        self.stdout.write('\n' + '='*60)
        self.stdout.write('📊 SUMMARY')
        self.stdout.write('='*60)
        self.stdout.write(f'  Total records checked: {query.count()}')
        self.stdout.write(f'  Records with wrong shift_date: {wrong_count}')
        self.stdout.write(f'  Records fixed: {fixed_count}')
        self.stdout.write(f'  Errors: {len(errors)}')

        if dry_run:
            self.stdout.write(self.style.WARNING('\n  🔍 DRY RUN MODE - No changes were made'))
            self.stdout.write(self.style.WARNING('  Run without --dry-run to actually fix the records'))

        if errors:
            self.stdout.write(self.style.ERROR('\n⚠️  Errors encountered:'))
            for error in errors:
                self.stdout.write(f'  - Record {error["record_id"]}: {error["error"]}')

        self.stdout.write('='*60 + '\n')