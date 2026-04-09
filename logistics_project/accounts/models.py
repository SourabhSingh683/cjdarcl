"""
accounts/models.py
==================
User profile (extends Django's built-in User), OTP records, and Notifications
for the CJ Darcl Logistics Management System.

Roles:
  manager  — Branch Manager / Employee (full access)
  driver   — Driver (filtered to assigned shipments)
  customer — Customer (filtered to their shipments)
"""

from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone


class UserProfile(models.Model):
    """
    One-to-one extension of Django's User model.
    Stores the user's role and logistics-specific identifiers.
    """

    ROLE_CHOICES = [
        ("manager",  "Branch Manager / Employee"),
    ]

    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name="profile",
    )
    role = models.CharField(
        max_length=20, choices=ROLE_CHOICES, default="manager", db_index=True,
    )
    phone = models.CharField(
        max_length=15, unique=True, null=True, blank=True,
        help_text="Mobile number used for OTP login",
    )
    is_phone_verified = models.BooleanField(default=False)

    class Meta:
        ordering = ["user__username"]
        verbose_name = "User Profile"
        verbose_name_plural = "User Profiles"

    def __str__(self):
        return f"{self.user.username} (Manager)"

    @property
    def display_name(self):
        return self.user.get_full_name() or self.user.username


class OTPRecord(models.Model):
    """
    Stores one-time-passwords for mobile OTP login flow.
    OTPs expire after 10 minutes and are invalidated after use.
    """

    phone = models.CharField(max_length=15, db_index=True)
    otp = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    is_used = models.BooleanField(default=False)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "OTP Record"

    def __str__(self):
        return f"OTP for {self.phone} ({'used' if self.is_used else 'active'})"

    @property
    def is_valid(self):
        """Returns True if OTP is not used and not expired."""
        return not self.is_used and timezone.now() < self.expires_at


class Notification(models.Model):
    """
    In-database notification record.
    Created by Django signals on key events (POD upload, shipment assignment).
    """

    TYPE_CHOICES = [
        ("general", "General"),
    ]

    recipient = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="notifications",
    )
    notif_type = models.CharField(
        max_length=30, choices=TYPE_CHOICES, default="general", db_index=True,
    )
    title = models.CharField(max_length=255)
    message = models.TextField()
    shipment_ref = models.CharField(
        max_length=100, blank=True, default="",
        help_text="Shipment ID this notification relates to",
    )
    is_read = models.BooleanField(default=False, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Notification"
        verbose_name_plural = "Notifications"

    def __str__(self):
        return f"[{self.notif_type}] → {self.recipient.username}: {self.title}"
