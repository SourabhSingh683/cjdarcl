"""
accounts/signals.py
===================
Simplified signals for CJ Darcl LMS.
"""

import logging
from django.db.models.signals import post_save
from django.dispatch import receiver, Signal

logger = logging.getLogger("accounts")

# Custom signal previously used for POD uploads
pod_uploaded = Signal() 

@receiver(pod_uploaded)
def notify_on_pod_upload(sender, **kwargs):
    # Simplified: No notifications for now
    pass
