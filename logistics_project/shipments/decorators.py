"""
shipments/decorators.py
========================
Re-exports the @role_required decorator from accounts.permissions
so it can also be imported directly from the shipments app.

Usage:
    from shipments.decorators import role_required

    @api_view(['GET'])
    @role_required(['manager'])
    def manager_only(request): ...
"""

from accounts.permissions import role_required  # noqa: F401

__all__ = ['role_required']
