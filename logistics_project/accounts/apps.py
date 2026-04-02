"""
accounts/apps.py
================
AppConfig for the accounts app.
Registers signals on app ready.
"""

from django.apps import AppConfig


class AccountsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "accounts"
    verbose_name = "Accounts & Auth"

    def ready(self):
        # Import signals so they are registered with Django's signal dispatcher
        import accounts.signals  # noqa: F401
