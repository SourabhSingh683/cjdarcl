"""
Serializers for the Logistics Intelligence Dashboard v2.
"""

from rest_framework import serializers
from .models import Route, UploadLog, Shipment


class RouteSerializer(serializers.ModelSerializer):
    label = serializers.CharField(read_only=True)

    class Meta:
        model = Route
        fields = ["id", "origin", "destination", "label"]


class UploadLogSerializer(serializers.ModelSerializer):
    duration_display = serializers.SerializerMethodField()

    class Meta:
        model = UploadLog
        fields = [
            "id", "file_name", "uploaded_at", "status",
            "total_rows", "processed_rows", "error_rows", "duplicate_rows",
            "error_log", "processing_time_ms", "duration_display",
            "data_quality_score", "quality_issues",
        ]

    def get_duration_display(self, obj):
        if obj.processing_time_ms is not None:
            return f"{obj.processing_time_ms / 1000:.2f}s"
        return None


class ShipmentSerializer(serializers.ModelSerializer):
    origin = serializers.CharField(source="route.origin", read_only=True)
    destination = serializers.CharField(source="route.destination", read_only=True)
    status = serializers.SerializerMethodField()

    class Meta:
        model = Shipment
        fields = [
            "id", "shipment_id", "origin", "destination",
            "dispatch_date", "delivery_date", "expected_delivery_date",
            "vehicle_type", "vehicle_no",
            "revenue", "total_amount", "rate_per_mt",
            "freight_deduction", "penalty", "amount_receivable",
            "net_weight", "gross_weight", "charge_weight", "shortage",
            "transit_permissible", "transit_taken",
            "delay_days", "is_on_time", "has_shortage", "has_penalty",
            "status", "created_at",
            "consignor_name", "consignee_name", "customer_name", "transporter_name"
        ]

    def get_status(self, obj):
        return "on-time" if obj.is_on_time else "delayed"


class ShipmentListSerializer(serializers.ModelSerializer):
    origin = serializers.CharField(source="route.origin", read_only=True)
    destination = serializers.CharField(source="route.destination", read_only=True)

    class Meta:
        model = Shipment
        fields = [
            "id", "shipment_id", "origin", "destination",
            "dispatch_date", "delivery_date",
            "vehicle_type", "vehicle_no",
            "revenue", "penalty", "shortage",
            "transit_permissible", "transit_taken",
            "delay_days", "is_on_time", "has_shortage", "has_penalty",
            "consignor_name", "consignee_name", "customer_name", "transporter_name"
        ]


class FileUploadSerializer(serializers.Serializer):
    file = serializers.FileField()

    def validate_file(self, value):
        ext = value.name.rsplit(".", 1)[-1].lower() if "." in value.name else ""
        if ext not in ("csv", "xlsx", "xls"):
            raise serializers.ValidationError(
                f"Unsupported file type '.{ext}'. Accepted: .csv, .xlsx, .xls"
            )
        if value.size > 10 * 1024 * 1024:
            raise serializers.ValidationError("File too large. Maximum size is 10 MB.")
        return value
