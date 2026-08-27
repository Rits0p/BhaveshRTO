import datetime

from django.core.management.base import BaseCommand
from django.utils import timezone

from customers.models import Customer


class Command(BaseCommand):
    help = 'Flags customers whose end_date falls within the next 30 days as needing a reminder, and clears the flag for everyone else. Intended to run daily (see README for scheduling options).'

    def add_arguments(self, parser):
        parser.add_argument('--days', type=int, default=30, help='Expiry window size in days (default: 30).')

    def handle(self, *args, **options):
        days = options['days']
        today = timezone.localdate()
        window_end = today + datetime.timedelta(days=days)

        flagged = Customer.objects.filter(
            end_date__gte=today, end_date__lte=window_end, needs_reminder=False,
        ).update(needs_reminder=True)

        cleared = Customer.objects.filter(needs_reminder=True).exclude(
            end_date__gte=today, end_date__lte=window_end,
        ).update(needs_reminder=False)

        self.stdout.write(self.style.SUCCESS(
            f'Expiry scan complete: flagged {flagged} customer(s) as needing a reminder, cleared {cleared}.'
        ))
