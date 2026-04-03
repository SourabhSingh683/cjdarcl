"""
accounts/signals.py
===================
Django signals that drive the notification system for CJ Darcl LMS.

Events:
  1. Shipment assigned to a driver     → Notification to that driver
  2. POD uploaded by a driver          → Notification to ALL managers
"""

import logging

from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver, Signal

from .models import Notification, UserProfile

logger = logging.getLogger("accounts")

# ─── Custom Signal ────────────────────────────────────────────────────────────
# Fired manually from shipments/views.py after a POD upload succeeds.
pod_uploaded = Signal()  # kwargs: shipment_id, driver_user


# ─── Signal Handlers ──────────────────────────────────────────────────────────

@receiver(pod_uploaded)
def notify_managers_on_pod_upload(sender, shipment_id, driver_user, **kwargs):
    """
    When a driver uploads POD, notify all Branch Managers.
    """
    manager_users = User.objects.filter(
        profile__role="manager", is_active=True
    ).select_related("profile")

    driver_name = driver_user.get_full_name() or driver_user.username
    notifications = [
        Notification(
            recipient=manager,
            notif_type="pod_uploaded",
            title="POD Submitted",
            message=(
                f"Driver {driver_name} has submitted POD for CN {shipment_id}"
            ),
            shipment_ref=str(shipment_id),
        )
        for manager in manager_users
    ]
    if notifications:
        Notification.objects.bulk_create(notifications)
        logger.info(
            f"POD upload notification sent to {len(notifications)} managers "
            f"for shipment {shipment_id}"
        )


def notify_driver_on_shipment_assigned(driver_user, shipment_id, vehicle_no):
    """
    Called from shipments app (not via signal) when a shipment
    is assigned/linked to a driver's vehicle_no.
    """
    Notification.objects.create(
        recipient=driver_user,
        notif_type="shipment_assigned",
        title="New Shipment Assigned",
        message=(
            f"A new shipment ({shipment_id}) has been assigned to your "
            f"vehicle ({vehicle_no}). Please check your dashboard."
        ),
        shipment_ref=str(shipment_id),
    )
    logger.info(f"Shipment-assigned notification sent to driver {driver_user.username}")


def create_daily_pod_reminders():
    """
    Called by a management command / Celery beat task.
    Notifies all drivers who have active (undelivered) shipments
    to upload their POD.
    """
    from shipments.models import Shipment  # local import to avoid circular

    driver_profiles = UserProfile.objects.filter(
        role="driver", user__is_active=True
    ).select_related("user")

    for profile in driver_profiles:
        if not profile.vehicle_no:
            continue
        # Check if this driver has any shipment with missing POD
        has_pending = Shipment.objects.filter(
            vehicle_no__icontains=profile.vehicle_no,
            pod_status="",
        ).exists()
        if has_pending:
            Notification.objects.create(
                recipient=profile.user,
                notif_type="daily_pod_reminder",
                title="POD Upload Reminder",
                message=(
                    "You have shipment(s) awaiting Proof of Delivery upload. "
                    "Please upload POD documents at your earliest convenience."
                ),
            )
    logger.info("Daily POD reminders dispatched to active drivers.")
