"""
Django Admin configuration for the Logistics Intelligence Dashboard.
Provides rich admin interface for managing shipments, routes, and uploads.
"""

from django.contrib import admin
from .models import Route, UploadLog, Shipment


@admin.register(Route)
class RouteAdmin(admin.ModelAdmin):
    list_display = ("id", "origin", "destination")
    search_fields = ("origin", "destination")
    list_filter = ("origin", "destination")


@admin.register(UploadLog)
class UploadLogAdmin(admin.ModelAdmin):
    list_display = (
        "id", "file_name", "uploaded_at", "status",
        "total_rows", "processed_rows", "error_rows", "processing_time_ms",
    )
    list_filter = ("status", "uploaded_at")
    readonly_fields = ("uploaded_at", "error_log")
    search_fields = ("file_name",)


@admin.register(Shipment)
class ShipmentAdmin(admin.ModelAdmin):
    list_display = (
        "shipment_id", "route", "dispatch_date", "delivery_date",
        "revenue", "vehicle_type", "delay_days", "is_on_time",
    )
    list_filter = ("is_on_time", "vehicle_type", "dispatch_date")
    search_fields = ("shipment_id", "route__origin", "route__destination")
    raw_id_fields = ("route", "upload")
    date_hierarchy = "dispatch_date"
