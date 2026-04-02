"""
accounts/permissions.py
=======================
Custom DRF permission classes and a role_required decorator
for enforcing RBAC across the CJ Darcl LMS.

Usage (class-based views):
    permission_classes = [IsAuthenticated, IsManager]

Usage (function-based views):
    @role_required(['manager', 'driver'])
    def my_view(request): ...
"""

from functools import wraps

from rest_framework.exceptions import PermissionDenied, NotAuthenticated
from rest_framework.permissions import BasePermission


# ─── DRF Permission Classes ───────────────────────────────────────────────────

class HasProfile(BasePermission):
    """Ensures the authenticated user has a UserProfile (role) record."""
    message = "User profile not found. Please contact your administrator."

    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and hasattr(request.user, "profile")
        )


class IsManager(BasePermission):
    """Allow Branch Managers and Employees only."""
    message = "Access restricted to Branch Managers and Employees."

    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and hasattr(request.user, "profile")
            and request.user.profile.role == "manager"
        )


class IsDriver(BasePermission):
    """Allow Drivers only."""
    message = "Access restricted to Drivers."

    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and hasattr(request.user, "profile")
            and request.user.profile.role == "driver"
        )


class IsCustomer(BasePermission):
    """Allow Customers only."""
    message = "Access restricted to Customers."

    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and hasattr(request.user, "profile")
            and request.user.profile.role == "customer"
        )


class IsManagerOrDriver(BasePermission):
    """Allow Managers or Drivers."""
    message = "Access restricted to Managers and Drivers."

    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and hasattr(request.user, "profile")
            and request.user.profile.role in ("manager", "driver")
        )


# ─── @role_required Decorator ────────────────────────────────────────────────

def role_required(allowed_roles: list):
    """
    Decorator for DRF @api_view function-based views.

    Enforces:
      1. User is authenticated (JWT validated by DRF).
      2. User has a profile with a role in `allowed_roles`.

    Example:
        @api_view(['GET'])
        @role_required(['manager'])
        def manager_only_view(request):
            ...
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if not request.user or not request.user.is_authenticated:
                raise NotAuthenticated("Authentication credentials were not provided.")

            if not hasattr(request.user, "profile"):
                raise PermissionDenied("User profile not configured. Contact admin.")

            user_role = request.user.profile.role
            if user_role not in allowed_roles:
                raise PermissionDenied(
                    f"Your role '{user_role}' does not have access to this resource. "
                    f"Required: {allowed_roles}."
                )

            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator
