"""
API Views for the Logistics Intelligence Dashboard v2 — Decision Intelligence System.

Endpoints:
  - File upload with quality scoring
  - KPIs (summary, revenue trends, top routes, delayed shipments)
  - Analytics (root cause, risk prediction, shortage analysis)
  - Data quality scoring
  - Period comparison
  - Smart insights
  - Drill-down
  - Upload history
"""

import json
import time
import logging

from django.db import transaction
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response

from .models import Route, UploadLog, Shipment
from .serializers import (
    FileUploadSerializer, ShipmentSerializer, ShipmentListSerializer,
    UploadLogSerializer,
)
from .utils.data_cleaner import process_file, DataCleaningError
from .utils.kpi_engine import (
    get_summary_kpis, get_revenue_trends, get_top_routes,
    get_delayed_shipments, generate_insights,
)
from .utils.quality_engine import compute_upload_quality, compute_overall_quality
from .utils.analysis_engine import (
    get_full_root_cause, get_risk_summary, compare_periods,
    generate_smart_insights,
)

logger = logging.getLogger("shipments")

# Role-based filtering helper
def _filter_by_role(qs, request):
    """
    Restrict queryset based on the authenticated user's role.
      manager  — sees everything
      driver   — sees only shipments where vehicle_no matches their profile
      customer — sees only shipments where customer_name matches their customer_id
      anonymous / no profile — sees nothing (returns empty qs)
    """
    user = request.user
    if not user or not user.is_authenticated:
        return qs.none()
    profile = getattr(user, "profile", None)
    if not profile:
        return qs.none()
    if profile.role == "manager":
        return qs
    if profile.role == "driver":
        vehicle = profile.vehicle_no.strip()
        return qs.filter(vehicle_no__icontains=vehicle) if vehicle else qs.none()
    if profile.role == "customer":
        cust = profile.customer_id.strip()
        return qs.filter(customer_name__icontains=cust) if cust else qs.none()
    return qs.none()


# ─── Helpers ─────────────────────────────────────────────

def _apply_filters(qs, params):
    if date_from := params.get("date_from"):
        try:
            qs = qs.filter(dispatch_date__gte=date_from)
        except Exception:
            pass
    if date_to := params.get("date_to"):
        try:
            qs = qs.filter(dispatch_date__lte=date_to)
        except Exception:
            pass
    if origin := params.get("origin"):
        qs = qs.filter(route__origin__icontains=origin)
    if destination := params.get("destination"):
        qs = qs.filter(route__destination__icontains=destination)
    if vehicle_type := params.get("vehicle_type"):
        qs = qs.filter(vehicle_type__iexact=vehicle_type)
    if vehicle_no := params.get("vehicle_no"):
        qs = qs.filter(vehicle_no__icontains=vehicle_no)
    if transporter_name := params.get("transporter_name"):
        qs = qs.filter(transporter_name__icontains=transporter_name)
    if booking_region := params.get("booking_region"):
        qs = qs.filter(booking_region__icontains=booking_region)
    if material := params.get("material"):
        qs = qs.filter(material_type__icontains=material)
    if cnno := params.get("cnno"):
        qs = qs.filter(shipment_id__icontains=cnno)
    return qs


class StandardPagination(PageNumberPagination):
    page_size = 50
    page_size_query_param = "page_size"
    max_page_size = 5000


# ═══════════════════════════════════════════════════════════
# FILE UPLOAD
# ═══════════════════════════════════════════════════════════

@api_view(["POST"])
def upload_file(request):
    """POST /api/upload/ — Upload Excel/CSV with full processing + quality scoring."""
    serializer = FileUploadSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(
            {"error": "Invalid file", "details": serializer.errors},
            status=status.HTTP_400_BAD_REQUEST,
        )

    uploaded_file = serializer.validated_data["file"]
    file_name = uploaded_file.name

    upload_log = UploadLog.objects.create(
        file_name=file_name, status=UploadLog.Status.PROCESSING,
    )
    start_time = time.time()

    try:
        clean_df, errors, dup_count = process_file(uploaded_file, file_name)
        _bulk_insert_shipments(clean_df, upload_log)

        elapsed_ms = int((time.time() - start_time) * 1000)
        upload_log.total_rows = len(clean_df) + len(errors) + dup_count
        upload_log.processed_rows = len(clean_df)
        upload_log.error_rows = len(errors)
        upload_log.duplicate_rows = dup_count
        upload_log.error_log = json.dumps(errors[:100], default=str)
        upload_log.processing_time_ms = elapsed_ms
        upload_log.status = (
            UploadLog.Status.COMPLETED if not errors else UploadLog.Status.PARTIAL
        )
        upload_log.save()

        # Compute data quality score
        quality = compute_upload_quality(upload_log)
        upload_log.data_quality_score = quality["data_quality_score"]
        upload_log.quality_issues = json.dumps(quality["issues"])
        upload_log.save()

        return Response({
            "message": "File processed successfully",
            "upload_id": upload_log.id,
            "file_name": file_name,
            "total_rows": upload_log.total_rows,
            "processed_rows": upload_log.processed_rows,
            "error_rows": upload_log.error_rows,
            "duplicates_removed": dup_count,
            "processing_time": f"{elapsed_ms}ms",
            "status": upload_log.status,
            "data_quality_score": quality["data_quality_score"],
            "quality_issues": quality["issues"],
            "errors": errors[:20],
        }, status=status.HTTP_201_CREATED)

    except DataCleaningError as e:
        elapsed_ms = int((time.time() - start_time) * 1000)
        upload_log.status = UploadLog.Status.FAILED
        upload_log.error_log = json.dumps({"fatal": str(e)})
        upload_log.processing_time_ms = elapsed_ms
        upload_log.save()
        return Response(
            {"error": "File processing failed", "details": str(e)},
            status=status.HTTP_422_UNPROCESSABLE_ENTITY,
        )
    except Exception as e:
        elapsed_ms = int((time.time() - start_time) * 1000)
        upload_log.status = UploadLog.Status.FAILED
        upload_log.error_log = json.dumps({"fatal": str(e)})
        upload_log.processing_time_ms = elapsed_ms
        upload_log.save()
        logger.exception(f"Unexpected error processing {file_name}")
        return Response(
            {"error": "An unexpected error occurred", "details": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@transaction.atomic
def _bulk_insert_shipments(df, upload_log):
    """Bulk-insert with cross-file dedup on shipment_id."""
    # Routes
    route_pairs = df[["origin", "destination"]].drop_duplicates().values.tolist()
    route_cache = {}
    for origin, destination in route_pairs:
        route, _ = Route.objects.get_or_create(origin=origin, destination=destination)
        route_cache[(origin, destination)] = route

    # Existing IDs for upsert
    incoming_ids = set(df["shipment_id"].tolist())
    existing_ids = set(
        Shipment.objects.filter(shipment_id__in=incoming_ids)
        .values_list("shipment_id", flat=True)
    )

    to_create, to_update = [], []
    for _, row in df.iterrows():
        route = route_cache[(row["origin"], row["destination"])]
        data = _build_shipment_data(row, route, upload_log)

        if row["shipment_id"] in existing_ids:
            shipment = Shipment.objects.get(shipment_id=row["shipment_id"])
            for key, value in data.items():
                if key != "shipment_id":
                    setattr(shipment, key, value)
            to_update.append(shipment)
        else:
            to_create.append(Shipment(**data))

    if to_create:
        Shipment.objects.bulk_create(to_create, batch_size=500)
    if to_update:
        Shipment.objects.bulk_update(to_update, fields=[
            "route", "upload", "dispatch_date", "delivery_date",
            "expected_delivery_date", "vehicle_type", "vehicle_no",
            "revenue", "rate_per_mt", "total_amount", "freight_deduction",
            "penalty", "amount_receivable", "net_weight", "gross_weight",
            "charge_weight", "shortage", "transit_permissible", "transit_taken",
            "delay_days", "is_on_time", "has_shortage", "has_penalty",
            "total_distance", "pod_status", "billing_status",
            "customer_name", "transporter_name", "booking_region", "contract_id", "material_type",
            "consignor_name", "consignee_name",
        ], batch_size=500)


def _build_shipment_data(row, route, upload_log):
    """Build shipment dict from a cleaned DataFrame row."""
    import pandas as pd

    def _safe_date(val):
        if pd.isna(val):
            return None
        return val.date() if hasattr(val, "date") else val

    return {
        "shipment_id": row["shipment_id"],
        "route": route,
        "upload": upload_log,
        "dispatch_date": _safe_date(row["dispatch_date"]),
        "delivery_date": _safe_date(row.get("delivery_date")),
        "expected_delivery_date": _safe_date(row.get("expected_delivery_date")),
        "vehicle_type": row.get("vehicle_type", "other"),
        "vehicle_no": row.get("vehicle_no", ""),
        "revenue": float(row.get("revenue", 0)),
        "rate_per_mt": float(row.get("rate_per_mt", 0)),
        "total_amount": float(row.get("total_amount", 0)),
        "freight_deduction": float(row.get("freight_deduction", 0)),
        "penalty": float(row.get("penalty", 0)),
        "amount_receivable": float(row.get("amount_receivable", 0)),
        "net_weight": float(row.get("net_weight", 0)),
        "gross_weight": float(row.get("gross_weight", 0)),
        "charge_weight": float(row.get("charge_weight", 0)),
        "shortage": float(row.get("shortage", 0)),
        "transit_permissible": int(row.get("transit_permissible", 0)),
        "transit_taken": int(row.get("transit_taken", 0)),
        "delay_days": int(row.get("delay_days", 0)),
        "is_on_time": bool(row.get("is_on_time", True)),
        "has_shortage": bool(row.get("has_shortage", False)),
        "has_penalty": bool(row.get("has_penalty", False)),
        "total_distance": float(row.get("total_distance", 0)) if pd.notna(row.get("total_distance")) else None,
        "pod_status": str(row.get("pod_status", ""))[:50] if pd.notna(row.get("pod_status")) else "",
        "billing_status": str(row.get("billing_status", ""))[:50] if pd.notna(row.get("billing_status")) else "",
        "customer_name": str(row.get("customer_name", ""))[:255] if pd.notna(row.get("customer_name")) else "",
        "transporter_name": str(row.get("transporter_name", ""))[:255] if pd.notna(row.get("transporter_name")) else "",
        "booking_region": str(row.get("booking_region", ""))[:100] if pd.notna(row.get("booking_region")) else "",
        "contract_id": str(row.get("contract_id", ""))[:100] if pd.notna(row.get("contract_id")) else "",
        "material_type": str(row.get("material_type", ""))[:150] if pd.notna(row.get("material_type")) else "",
        "consignor_name": str(row.get("consignor_name", ""))[:255] if pd.notna(row.get("consignor_name")) else "",
        "consignee_name": str(row.get("consignee_name", ""))[:255] if pd.notna(row.get("consignee_name")) else "",
    }


# ═══════════════════════════════════════════════════════════
# KPI ENDPOINTS
# ═══════════════════════════════════════════════════════════

@api_view(["GET"])
def kpi_summary(request):
    qs = _apply_filters(Shipment.objects.all(), request.GET)
    return Response(get_summary_kpis(qs))


@api_view(["GET"])
def kpi_revenue_trends(request):
    qs = _apply_filters(Shipment.objects.all(), request.GET)
    group_by = request.GET.get("group_by", "day")
    return Response(get_revenue_trends(qs, group_by=group_by))


@api_view(["GET"])
def kpi_top_routes(request):
    qs = _apply_filters(Shipment.objects.all(), request.GET)
    limit = min(int(request.GET.get("limit", 10)), 50)
    return Response(get_top_routes(qs, limit=limit))


@api_view(["GET"])
def kpi_delayed_shipments(request):
    qs = _apply_filters(Shipment.objects.all(), request.GET)
    delayed_qs = get_delayed_shipments(qs)
    paginator = StandardPagination()
    page = paginator.paginate_queryset(delayed_qs, request)
    serializer = ShipmentListSerializer(page, many=True)
    return paginator.get_paginated_response(serializer.data)


# ═══════════════════════════════════════════════════════════
# ANALYTICS ENDPOINTS (NEW)
# ═══════════════════════════════════════════════════════════

@api_view(["GET"])
def analysis_root_cause(request):
    """GET /api/analysis/root-cause/ — Full root cause analysis."""
    qs = _apply_filters(Shipment.objects.all(), request.GET)
    return Response(get_full_root_cause(qs))


@api_view(["GET"])
def analysis_risk(request):
    """GET /api/analysis/risk/ — Risk prediction for routes and vehicles."""
    qs = _apply_filters(Shipment.objects.all(), request.GET)
    return Response(get_risk_summary(qs))


@api_view(["GET"])
def analysis_shortage(request):
    """GET /api/analysis/shortage/ — Shortage analysis."""
    from .utils.analysis_engine import analyze_shortages
    qs = _apply_filters(Shipment.objects.all(), request.GET)
    return Response(analyze_shortages(qs))


@api_view(["GET"])
def data_quality(request):
    """GET /api/quality/ — Overall data quality score."""
    return Response(compute_overall_quality())


@api_view(["GET"])
def period_comparison(request):
    """GET /api/kpis/comparison/?days=30 — Period comparison."""
    qs = _apply_filters(Shipment.objects.all(), request.GET)
    days = int(request.GET.get("days", 30))
    return Response(compare_periods(qs, days=days))


@api_view(["GET"])
def smart_insights(request):
    """GET /api/insights/smart/ — Enhanced context-aware insights."""
    qs = _apply_filters(Shipment.objects.all(), request.GET)
    return Response({"insights": generate_smart_insights(qs)})


@api_view(["GET"])
def kpi_drilldown(request):
    """
    GET /api/kpis/drilldown/?filter=delayed|on_time|shortage|penalty
    Returns paginated detailed records for the selected KPI.
    """
    qs = _apply_filters(Shipment.objects.select_related("route").all(), request.GET)
    filter_type = request.GET.get("filter", "all")

    if filter_type == "delayed":
        qs = qs.filter(is_on_time=False).order_by("-delay_days")
    elif filter_type == "on_time":
        qs = qs.filter(is_on_time=True)
    elif filter_type == "shortage":
        qs = qs.filter(has_shortage=True).order_by("-shortage")
    elif filter_type == "penalty":
        qs = qs.filter(has_penalty=True).order_by("-penalty")

    paginator = StandardPagination()
    page = paginator.paginate_queryset(qs, request)
    serializer = ShipmentSerializer(page, many=True)
    return paginator.get_paginated_response(serializer.data)


# ═══════════════════════════════════════════════════════════
# EXISTING ENDPOINTS (kept for backward compat)
# ═══════════════════════════════════════════════════════════

@api_view(["GET"])
def insights(request):
    qs = _apply_filters(Shipment.objects.all(), request.GET)
    return Response({"insights": generate_insights(qs)})


@api_view(["GET"])
def upload_history(request):
    uploads = UploadLog.objects.all()
    paginator = StandardPagination()
    page = paginator.paginate_queryset(uploads, request)
    serializer = UploadLogSerializer(page, many=True)
    return paginator.get_paginated_response(serializer.data)


@api_view(["DELETE"])
def delete_upload(request, upload_id):
    try:
        upload = UploadLog.objects.get(id=upload_id)
        # Delete associated shipments manually because on_delete is SET_NULL
        Shipment.objects.filter(upload=upload).delete()
        upload.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
    except UploadLog.DoesNotExist:
        return Response(status=status.HTTP_404_NOT_FOUND)


@api_view(["GET"])
def shipment_list(request):
    """
    GET /api/shipments/
    Role-aware shipment list:
      - manager  → all shipments
      - driver   → only shipments matching their vehicle_no
      - customer → only shipments matching their customer_id
      - anonymous → all shipments (backward compat for existing dashboard)
    """
    qs = _apply_filters(
        Shipment.objects.select_related("route").all(), request.GET
    )
    # Apply role filter only when authenticated
    if request.user and request.user.is_authenticated:
        qs = _filter_by_role(qs, request)

    paginator = StandardPagination()
    page = paginator.paginate_queryset(qs, request)
    serializer = ShipmentListSerializer(page, many=True)
    return paginator.get_paginated_response(serializer.data)


@api_view(["POST"])
def pod_upload(request, shipment_id):
    """
    POST /api/shipments/<shipment_id>/pod/
    Upload a POD document for a shipment.
    Only the assigned driver (or a manager) may upload.
    After upload:
      - Sets pod_status = "Uploaded"
      - Fires pod_uploaded signal → notifies all managers
    """
    from django.utils import timezone
    from rest_framework.parsers import MultiPartParser
    from rest_framework.permissions import IsAuthenticated
    from accounts.signals import pod_uploaded

    if not request.user or not request.user.is_authenticated:
        return Response({"error": "Authentication required."}, status=status.HTTP_401_UNAUTHORIZED)

    profile = getattr(request.user, "profile", None)
    if not profile:
        return Response({"error": "User profile not found."}, status=status.HTTP_403_FORBIDDEN)
    if profile.role not in ("driver", "manager"):
        return Response({"error": "Only drivers and managers can upload POD."}, status=status.HTTP_403_FORBIDDEN)

    try:
        shipment = Shipment.objects.get(shipment_id=shipment_id)
    except Shipment.DoesNotExist:
        return Response({"error": "Shipment not found."}, status=status.HTTP_404_NOT_FOUND)

    # Drivers may only upload for their own vehicle
    if profile.role == "driver":
        vehicle = profile.vehicle_no.strip()
        if vehicle and vehicle.lower() not in shipment.vehicle_no.lower():
            return Response(
                {"error": "You can only upload POD for shipments assigned to your vehicle."},
                status=status.HTTP_403_FORBIDDEN,
            )

    pod_file = request.FILES.get("pod_file")
    if not pod_file:
        return Response({"error": "No file provided. Use key 'pod_file'."}, status=status.HTTP_400_BAD_REQUEST)

    # Persist POD
    shipment.pod_file = pod_file
    shipment.pod_uploaded_at = timezone.now()
    shipment.pod_status = "Uploaded"
    shipment.assigned_driver = request.user
    shipment.save(update_fields=["pod_file", "pod_uploaded_at", "pod_status", "assigned_driver"])

    # Fire signal → managers get notified
    pod_uploaded.send(
        sender=Shipment,
        shipment_id=shipment.shipment_id,
        driver_user=request.user,
    )

    logger.info(f"POD uploaded by {request.user.username} for shipment {shipment.shipment_id}")
    return Response(
        {
            "message": "POD uploaded successfully.",
            "shipment_id": shipment.shipment_id,
            "pod_status": shipment.pod_status,
            "uploaded_at": shipment.pod_uploaded_at.isoformat(),
        },
        status=status.HTTP_200_OK,
    )


@api_view(["GET"])
def generate_invoice_view(request, shipment_id):
    """
    GET /api/shipments/<shipment_id>/invoice/
    Stream a professional PDF invoice for the given shipment.
    Managers and authenticated users may download invoices.
    """
    from django.http import HttpResponse
    from shipments.services.pdf_generator import generate_invoice

    try:
        pdf_bytes = generate_invoice(shipment_id)
    except Shipment.DoesNotExist:
        return Response({"error": "Shipment not found."}, status=status.HTTP_404_NOT_FOUND)
    except Exception as exc:
        logger.exception(f"Invoice generation failed for {shipment_id}: {exc}")
        return Response({"error": "Invoice generation failed.", "details": str(exc)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    response = HttpResponse(pdf_bytes, content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="invoice_{shipment_id}.pdf"'
    return response


# ═══════════════════════════════════════════════════════════
# AI ANALYSIS (GEMINI)
# ═══════════════════════════════════════════════════════════

@api_view(["POST"])
def ai_analyze(request):
    """POST /api/ai/analyze/ — Gemini-powered AI analysis."""
    from .utils.gemini_engine import analyze_with_gemini

    qs = _apply_filters(Shipment.objects.all(), request.data)
    question = request.data.get("question", None)
    result = analyze_with_gemini(qs, user_question=question)
    return Response(result)

