"""
accounts/management/commands/send_pod_reminders.py
====================================================
Management command to send daily POD upload reminders to active drivers.

Run daily via cron or Celery beat:
    python manage.py send_pod_reminders

Cron example (every day at 8 AM IST):
    0 2 * * * /path/to/venv/bin/python /path/to/manage.py send_pod_reminders
"""

from django.core.management.base import BaseCommand

from accounts.signals import create_daily_pod_reminders


class Command(BaseCommand):
    help = "Send daily POD upload reminder notifications to active drivers."

    def handle(self, *args, **options):
        self.stdout.write("Dispatching daily POD reminders...")
        create_daily_pod_reminders()
        self.stdout.write(self.style.SUCCESS("✓ POD reminders dispatched successfully."))
