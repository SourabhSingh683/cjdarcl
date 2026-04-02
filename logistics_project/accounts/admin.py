"""
accounts/admin.py
=================
Django admin registration for RBAC models.
"""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User

from .models import UserProfile, OTPRecord, Notification


# ─── Inline Profile inside User admin ────────────────────────────────────────

class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    verbose_name_plural = "Logistics Profile"
    fields = ["role", "phone", "vehicle_no", "customer_id", "is_phone_verified"]


class UserAdmin(BaseUserAdmin):
    inlines = [UserProfileInline]
    list_display = ["username", "email", "get_role", "is_active", "date_joined"]

    def get_role(self, obj):
        try:
            return obj.profile.get_role_display()
        except UserProfile.DoesNotExist:
            return "—"
    get_role.short_description = "Role"


# Re-register User with extended admin
admin.site.unregister(User)
admin.site.register(User, UserAdmin)


@admin.register(OTPRecord)
class OTPRecordAdmin(admin.ModelAdmin):
    list_display = ["phone", "otp", "created_at", "expires_at", "is_used"]
    list_filter = ["is_used"]
    search_fields = ["phone"]
    readonly_fields = ["created_at"]


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ["recipient", "notif_type", "title", "is_read", "created_at"]
    list_filter = ["notif_type", "is_read"]
    search_fields = ["recipient__username", "title", "shipment_ref"]
    readonly_fields = ["created_at"]
    actions = ["mark_as_read"]

    @admin.action(description="Mark selected as read")
    def mark_as_read(self, request, queryset):
        queryset.update(is_read=True)
