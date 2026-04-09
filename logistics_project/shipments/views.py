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
from rest_framework.decorators import api_view, permission_classes
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response

from rest_framework.permissions import IsAuthenticated
from .models import Route, UploadLog, Shipment
from .serializers import (
    FileUploadSerializer, ShipmentSerializer, ShipmentListSerializer,
    UploadLogSerializer,
)
from .utils.data_cleaner import process_file, DataCleaningError
from .utils.kpi_engine import (
    get_summary_kpis, get_revenue_trends, get_top_routes,
    get_delayed_shipments, generate_insights, get_transporter_performance,
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
    Restrict queryset based on the authenticated user.
    Managers only see the data they have uploaded.
    """
    user = request.user
    if not user or not user.is_authenticated:
        return qs.none()
    
    # If the user is a superuser, they can see everything (optional, but good for debugging)
    if user.is_superuser:
        return qs
        
    return qs.filter(user=user)


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
@permission_classes([IsAuthenticated])
def upload_file(request):
    """POST /api/upload/ — Upload one or more Excel/CSV files with full processing."""
    # We support both 'file' (single) and 'files' (multiple)
    files = request.FILES.getlist("file")
    if not files:
        files = request.FILES.getlist("files")
    
    if not files:
        return Response({"error": "No files provided"}, status=status.HTTP_400_BAD_REQUEST)

    # Check for refresh flag
    if request.GET.get('refresh') == 'true':
        with transaction.atomic():
            Shipment.objects.filter(user=request.user).delete()

    results = []
    for uploaded_file in files:
        try:
            result = _process_single_file(uploaded_file, request)
            results.append(result)
        except Exception as e:
            logger.exception(f"Crash in upload loop for {uploaded_file.name}")
            results.append({
                "file_name": uploaded_file.name,
                "error": "Internal processor crash",
                "details": str(e)
            })

    # If any file reported duplicates and we didn't refresh, the frontend will see it
    has_error = any("error" in r for r in results)
    status_code = status.HTTP_207_MULTI_STATUS if (has_error and len(results) > 1) else status.HTTP_201_CREATED
    if any(r.get("error") == "DUPLICATES_FOUND" for r in results):
        status_code = status.HTTP_409_CONFLICT
    
    if len(results) == 1:
        return Response(results[0], status=status_code)
    
    return Response({
        "message": "Processing complete",
        "results": results
    }, status=status_code)


def _process_single_file(uploaded_file, request):
    """Helper to process a single uploaded file and return the result dict."""
    user = request.user
    file_name = uploaded_file.name
    # Ensure file pointer is at start
    if hasattr(uploaded_file, "seek"):
        uploaded_file.seek(0)

    # 1. Pre-cleaning check for duplicates if refresh is not requested
    # We only do this if the user hasn't already asked to force a refresh
    is_refresh = request.GET.get('refresh') == 'true'

    upload_log = UploadLog.objects.create(
        file_name=file_name, status=UploadLog.Status.PROCESSING,
        original_file=uploaded_file, user=user
    )
    # ⚠️ CRITICAL: UploadLog creation reads the whole file to save it.
    # We must seek back to 0 so process_file doesn't see an empty file.
    if hasattr(uploaded_file, "seek"):
        uploaded_file.seek(0)
    
    start_time = time.time()

    try:
        clean_df, errors, dup_count = process_file(uploaded_file, file_name)
        
        # Cross-file duplicate detection
        incoming_ids = set(clean_df["shipment_id"].tolist())
        existing_count = Shipment.objects.filter(user=user, shipment_id__in=incoming_ids).count()
        
        if existing_count > 0 and not is_refresh:
            upload_log.status = UploadLog.Status.FAILED
            upload_log.error_log = json.dumps({"fatal": "Duplicate records detected in system."})
            upload_log.save()
            return {
                "file_name": file_name,
                "error": "DUPLICATES_FOUND",
                "duplicate_count": existing_count,
                "message": "This file contains shipments that already exist in your dashboard. Would you like to Start Refresh?"
            }

        _bulk_insert_shipments(clean_df, upload_log, user)

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

        return {
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
        }

    except DataCleaningError as e:
        elapsed_ms = int((time.time() - start_time) * 1000)
        upload_log.status = UploadLog.Status.FAILED
        upload_log.error_log = json.dumps({"fatal": str(e)})
        upload_log.processing_time_ms = elapsed_ms
        upload_log.save()
        return {"file_name": file_name, "error": "Cleaning failed", "details": str(e)}
    except Exception as e:
        elapsed_ms = int((time.time() - start_time) * 1000)
        upload_log.status = UploadLog.Status.FAILED
        upload_log.error_log = json.dumps({"fatal": str(e)})
        upload_log.processing_time_ms = elapsed_ms
        upload_log.save()
        logger.exception(f"Unexpected error processing {file_name}")
        return {"file_name": file_name, "error": "Unexpected error", "details": str(e)}


@api_view(["DELETE"])
@permission_classes([IsAuthenticated])
def clear_all_data(request):
    """DELETE /api/clear-data/ — Truncate user's shipment data but preserve history."""
    with transaction.atomic():
        # User requested: "only affect dashboard, analytics, intel and alerts... not history"
        # Shipments = Dashboard data. UploadLogs = History.
        Shipment.objects.filter(user=request.user).delete()
    return Response({"message": "Dashboard data cleared successfully. History and AI templates preserved."}, status=status.HTTP_200_OK)


@api_view(["POST"])
def reprocess_upload(request, upload_id):
    """POST /api/uploads/<id>/reprocess/ — Re-run processing on a file from history."""
    try:
        upload_log = UploadLog.objects.get(id=upload_id)
        if not upload_log.original_file:
            return Response({"error": "Original file not found for this upload."}, status=status.HTTP_404_NOT_FOUND)
        
        # Deleting old shipments associated with this upload
        Shipment.objects.filter(upload=upload_log).delete()
        
        # Process the file again — ensure it's open and reset
        file_obj = upload_log.original_file
        file_obj.open("rb")
        file_obj.seek(0)
        
        clean_df, errors, dup_count = process_file(file_obj, upload_log.file_name)
        _bulk_insert_shipments(clean_df, upload_log, upload_log.user)

        upload_log.total_rows = len(clean_df) + len(errors) + dup_count
        upload_log.processed_rows = len(clean_df)
        upload_log.error_rows = len(errors)
        upload_log.duplicate_rows = dup_count
        upload_log.error_log = json.dumps(errors[:100], default=str)
        upload_log.status = (
            UploadLog.Status.COMPLETED if not errors else UploadLog.Status.PARTIAL
        )
        upload_log.save()

        # Re-compute quality
        quality = compute_upload_quality(upload_log)
        upload_log.data_quality_score = quality["data_quality_score"]
        upload_log.quality_issues = json.dumps(quality["issues"])
        upload_log.save()

        return Response({"message": "Reprocessing complete", "status": upload_log.status}, status=status.HTTP_200_OK)
    
    except UploadLog.DoesNotExist:
        return Response(status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        logger.exception(f"Reprocessing failed for upload {upload_id}")
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@transaction.atomic
def _bulk_insert_shipments(df, upload_log, user):
    """Bulk-insert with cross-file dedup on shipment_id."""
    # Routes
    route_pairs = df[["origin", "destination"]].drop_duplicates().values.tolist()
    # Optimize Routes: Pre-fetch based on origin and dest lists
    route_origins = [o for o, d in route_pairs]
    route_dests = [d for o, d in route_pairs]
    existing_routes = Route.objects.filter(origin__in=route_origins, destination__in=route_dests)
    route_cache = {(r.origin, r.destination): r for r in existing_routes}

    missing_routes = []
    for origin, destination in route_pairs:
        if (origin, destination) not in route_cache:
            missing_routes.append(Route(origin=origin, destination=destination))
            route_cache[(origin, destination)] = None  # mark as visited to prevent duplicates

    if missing_routes:
        # ignore_conflicts isn't strictly needed if we generated missing properly,
        # but it protects against concurrent uploads
        Route.objects.bulk_create(missing_routes, ignore_conflicts=True)
        existing_new = Route.objects.filter(origin__in=route_origins, destination__in=route_dests)
        for r in existing_new:
            route_cache[(r.origin, r.destination)] = r

    # Pre-fetch existing shipments for upsert
    incoming_ids = set(df["shipment_id"].tolist())
    existing_shipments_list = list(Shipment.objects.filter(shipment_id__in=incoming_ids))
    existing_shipments = {s.shipment_id: s for s in existing_shipments_list}

    to_create, to_update = [], []
    for _, row in df.iterrows():
        route = route_cache[(row["origin"], row["destination"])]
        data = _build_shipment_data(row, route, upload_log, user)

        sid = row["shipment_id"]
        if sid in existing_shipments:
            shipment = existing_shipments[sid]
            # Verify ownership before updating
            if shipment.user == user or user.is_superuser:
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
            "route", "upload", "user", "dispatch_date", "delivery_date",
            "expected_delivery_date", "vehicle_type", "vehicle_no",
            "revenue", "rate_per_mt", "total_amount", "freight_deduction",
            "penalty", "amount_receivable", "net_weight", "gross_weight",
            "charge_weight", "shortage", "transit_permissible", "transit_taken",
            "delay_days", "is_on_time", "has_shortage", "has_penalty",
            "total_distance", "pod_status", "billing_status",
            "customer_name", "transporter_name", "booking_region", "contract_id", "material_type",
            "consignor_name", "consignee_name",
        ], batch_size=500)


def _build_shipment_data(row, route, upload_log, user):
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
        "user": user,
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
    qs = _filter_by_role(Shipment.objects.all(), request)
    qs = _apply_filters(qs, request.GET)
    return Response(get_summary_kpis(qs))


@api_view(["GET"])
def kpi_revenue_trends(request):
    qs = _filter_by_role(Shipment.objects.all(), request)
    qs = _apply_filters(qs, request.GET)
    group_by = request.GET.get("group_by", "day")
    return Response(get_revenue_trends(qs, group_by=group_by))


@api_view(["GET"])
def kpi_top_routes(request):
    qs = _filter_by_role(Shipment.objects.all(), request)
    qs = _apply_filters(qs, request.GET)
    limit = min(int(request.GET.get("limit", 10)), 50)
    return Response(get_top_routes(qs, limit=limit))


@api_view(["GET"])
def kpi_delayed_shipments(request):
    qs = _filter_by_role(Shipment.objects.all(), request)
    qs = _apply_filters(qs, request.GET)
    delayed_qs = get_delayed_shipments(qs)
    paginator = StandardPagination()
    page = paginator.paginate_queryset(delayed_qs, request)
    serializer = ShipmentListSerializer(page, many=True)
    return paginator.get_paginated_response(serializer.data)


@api_view(["GET"])
def kpi_transporter_performance(request):
    qs = _filter_by_role(Shipment.objects.all(), request)
    qs = _apply_filters(qs, request.GET)
    limit = min(int(request.GET.get("limit", 5)), 20)
    return Response(get_transporter_performance(qs, limit=limit))


# ═══════════════════════════════════════════════════════════
# ANALYTICS ENDPOINTS (NEW)
# ═══════════════════════════════════════════════════════════

@api_view(["GET"])
def operational_intelligence(request):
    """GET /api/analysis/operational-intelligence/ — Operational alerts and analytics."""
    from .utils.operational_engine import get_operational_intelligence
    qs = _filter_by_role(Shipment.objects.all(), request)
    qs = _apply_filters(qs, request.GET)
    return Response(get_operational_intelligence(qs))

@api_view(["GET"])
def analysis_root_cause(request):
    """GET /api/analysis/root-cause/ — Full root cause analysis."""
    qs = _filter_by_role(Shipment.objects.all(), request)
    qs = _apply_filters(qs, request.GET)
    return Response(get_full_root_cause(qs))


@api_view(["GET"])
def analysis_risk(request):
    """GET /api/analysis/risk/ — Risk prediction for routes and vehicles."""
    qs = _filter_by_role(Shipment.objects.all(), request)
    qs = _apply_filters(qs, request.GET)
    return Response(get_risk_summary(qs))


@api_view(["GET"])
def analysis_shortage(request):
    """GET /api/analysis/shortage/ — Shortage analysis."""
    from .utils.analysis_engine import analyze_shortages
    qs = _filter_by_role(Shipment.objects.all(), request)
    qs = _apply_filters(qs, request.GET)
    return Response(analyze_shortages(qs))


@api_view(["GET"])
def data_quality(request):
    """GET /api/quality/ — Overall data quality score."""
    qs = _filter_by_role(Shipment.objects.all(), request)
    return Response(compute_overall_quality(qs))


@api_view(["GET"])
def period_comparison(request):
    """GET /api/kpis/comparison/?days=30 — Period comparison."""
    qs = _filter_by_role(Shipment.objects.all(), request)
    qs = _apply_filters(qs, request.GET)
    days = int(request.GET.get("days", 30))
    return Response(compare_periods(qs, days=days))


@api_view(["GET"])
def smart_insights(request):
    """GET /api/insights/smart/ — Enhanced context-aware insights."""
    qs = _filter_by_role(Shipment.objects.all(), request)
    qs = _apply_filters(qs, request.GET)
    return Response({"insights": generate_smart_insights(qs)})


@api_view(["GET"])
def kpi_drilldown(request):
    """
    GET /api/kpis/drilldown/?filter=delayed|on_time|shortage|penalty
    Returns paginated detailed records for the selected KPI.
    """
    base_qs = _filter_by_role(Shipment.objects.select_related("route"), request)
    qs = _apply_filters(base_qs, request.GET)
    filter_type = request.GET.get("filter", "all")

    if filter_type == "delayed":
        qs = qs.filter(is_on_time=False).order_by("-delay_days")
    elif filter_type == "delayed_1_2":
        qs = qs.filter(delay_days__gte=1, delay_days__lte=2).order_by("-delay_days")
    elif filter_type == "delayed_3_4":
        qs = qs.filter(delay_days__gte=3, delay_days__lte=4).order_by("-delay_days")
    elif filter_type == "delayed_5_7":
        qs = qs.filter(delay_days__gte=5, delay_days__lte=7).order_by("-delay_days")
    elif filter_type == "delayed_8_plus":
        qs = qs.filter(delay_days__gt=7).order_by("-delay_days")
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
    uploads = _filter_by_role(UploadLog.objects.all(), request)
    paginator = StandardPagination()
    page = paginator.paginate_queryset(uploads, request)
    serializer = UploadLogSerializer(page, many=True, context={"request": request})
    return paginator.get_paginated_response(serializer.data)


@api_view(["DELETE"])
@permission_classes([IsAuthenticated])
def delete_upload(request, upload_id):
    """DELETE /api/uploads/<id>/ — Remove one upload and its shipments."""
    try:
        qs = _filter_by_role(UploadLog.objects.all(), request)
        upload = qs.get(id=upload_id)
        # Delete associated shipments manually because on_delete is SET_NULL
        Shipment.objects.filter(upload=upload).delete()
        upload.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
    except UploadLog.DoesNotExist:
        return Response({"error": "Upload not found"}, status=status.HTTP_404_NOT_FOUND)

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def bulk_delete_uploads(request):
    """POST /api/uploads/bulk-delete/ — Remove multiple uploads."""
    ids = request.data.get("ids", [])
    if not ids:
        return Response({"error": "No IDs provided"}, status=status.HTTP_400_BAD_REQUEST)
    
    with transaction.atomic():
        qs = _filter_by_role(UploadLog.objects.all(), request)
        uploads = qs.filter(id__in=ids)
        # Delete associated shipments
        Shipment.objects.filter(upload__in=uploads).delete()
        count = uploads.count()
        uploads.delete()
        
    return Response({"message": f"Successfully deleted {count} uploads."}, status=status.HTTP_200_OK)


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


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def generate_invoice_view(request, shipment_id):
    """
    GET /api/shipments/<shipment_id>/invoice/
    Stream a professional PDF invoice for the given shipment.
    """
    from shipments.services.pdf_generator import generate_invoice
    from django.http import HttpResponse

    try:
        # Everyone authenticated is a manager, so hide_financials is always False
        pdf_bytes = generate_invoice(shipment_id, hide_financials=False)
    except Shipment.DoesNotExist:
        return Response({"error": "Shipment not found."}, status=status.HTTP_404_NOT_FOUND)
    except Exception as exc:
        logger.exception(f"Invoice generation failed for {shipment_id}: {exc}")
        return Response({"error": "Invoice generation failed.", "details": str(exc)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    response = HttpResponse(pdf_bytes, content_type="application/pdf")
    response["Content-Disposition"] = f'inline; filename="invoice_{shipment_id}.pdf"'
    return response
    


# ═══════════════════════════════════════════════════════════
# AI ANALYSIS (GEMINI)
# ═══════════════════════════════════════════════════════════

@api_view(["POST"])
def ai_analyze(request):
    """POST /api/ai/analyze/ — Gemini-powered AI analysis."""
    from .utils.gemini_engine import analyze_with_gemini
    
    base_qs = _filter_by_role(Shipment.objects.all(), request)
    qs = _apply_filters(base_qs, request.data)
    question = request.data.get("question", None)
    result = analyze_with_gemini(qs, user_question=question)
    return Response(result)
