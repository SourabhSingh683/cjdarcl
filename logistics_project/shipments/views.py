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
import threading
from io import BytesIO

from django.db import transaction
from django.db.models import Q
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response

from rest_framework.permissions import IsAuthenticated
from .models import Route, UploadLog, Shipment, ProfitRecord
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


def _apply_profit_filters(qs, params):
    """Filter ProfitRecord queryset based on GET params."""
    if val := params.get("from"):
        qs = qs.filter(cn_date__gte=val)
    if val := params.get("to"):
        qs = qs.filter(cn_date__lte=val)
    if val := params.get("orig"):
        qs = qs.filter(loading_city__icontains=val)
    if val := params.get("dest"):
        qs = qs.filter(delivery_city__icontains=val)
    if val := params.get("cn"):
        # Search both delivery and external no
        qs = qs.filter(Q(sap_delivery_no__icontains=val) | Q(sap_external_no__icontains=val))
    if val := params.get("mat"):
        qs = qs.filter(material_name__icontains=val)
    if val := params.get("trans"):
        keywords = val.split()
        for kw in keywords:
            qs = qs.filter(service_agent__icontains=kw)
    if val := params.get("reg"):
        qs = qs.filter(booking_branch__icontains=val)
    if val := params.get("cust"):
        keywords = val.split()
        for kw in keywords:
            qs = qs.filter(customer_name__icontains=kw)
    if val := params.get("margin_type"):
        if val == "profit":
            qs = qs.filter(gm1__gt=0)
        elif val == "loss":
            qs = qs.filter(gm1__lt=0)
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
    """POST /api/upload/ — Upload files. Returns 202 immediately, processes in background."""
    files = request.FILES.getlist("file")
    if not files:
        files = request.FILES.getlist("files")
    if not files:
        return Response({"error": "No files provided"}, status=status.HTTP_400_BAD_REQUEST)

    is_refresh = request.GET.get('refresh') == 'true'
    user = request.user

    # Check for refresh flag — clear existing data first
    if is_refresh:
        with transaction.atomic():
            if user.is_superuser:
                Shipment.objects.all().delete()
            else:
                Shipment.objects.filter(user=user).delete()

    # Read file content into memory NOW (before request closes)
    uploaded_file = files[0]  # Process one file at a time
    file_name = uploaded_file.name
    file_content = uploaded_file.read()

    # Create upload log immediately
    uploaded_file.seek(0)
    upload_log = UploadLog.objects.create(
        file_name=file_name, status=UploadLog.Status.PROCESSING,
        original_file=uploaded_file, user=user
    )

    # Check for duplicates (quick check before background processing)
    if not is_refresh:
        from .utils.data_cleaner import read_file, auto_map_columns
        try:
            import pandas as pd
            df_check = read_file(BytesIO(file_content), file_name)
            mapped, _ = auto_map_columns(df_check)
            if "shipment_id" in mapped:
                sid_col = mapped["shipment_id"]
                sample_ids = set(df_check[sid_col].dropna().astype(str).str.strip().head(100).tolist())
                existing_count = Shipment.objects.filter(user=user, shipment_id__in=sample_ids).count()
                if existing_count > 0:
                    upload_log.status = UploadLog.Status.FAILED
                    upload_log.error_log = json.dumps({"fatal": "Duplicate records detected in system."})
                    upload_log.save()
                    return Response({
                        "file_name": file_name,
                        "error": "DUPLICATES_FOUND",
                        "duplicate_count": existing_count,
                        "message": "This file contains shipments that already exist. Use Start Refresh."
                    }, status=status.HTTP_409_CONFLICT)
            del df_check
        except Exception:
            pass  # If check fails, proceed with processing anyway

    # Start background processing thread
    thread = threading.Thread(
        target=_process_upload_in_background,
        args=(file_content, file_name, upload_log.pk, user.pk, is_refresh),
        daemon=True
    )
    thread.start()

    # Return immediately with upload_id for polling
    return Response({
        "status": "processing",
        "upload_id": upload_log.pk,
        "file_name": file_name,
        "message": "File accepted. Processing in background."
    }, status=status.HTTP_202_ACCEPTED)


def _process_upload_in_background(file_content, file_name, upload_log_id, user_id, is_refresh):
    """Background thread: process uploaded file and update UploadLog."""
    import django
    django.setup()  # Ensure Django is initialized in this thread

    from django.contrib.auth.models import User
    import gc

    try:
        upload_log = UploadLog.objects.get(pk=upload_log_id)
        user = User.objects.get(pk=user_id)
    except (UploadLog.DoesNotExist, User.DoesNotExist):
        logger.error(f"Background: upload_log={upload_log_id} or user={user_id} not found")
        return

    start_time = time.time()
    try:
        logger.info(f"Background processing: {file_name} ({len(file_content)} bytes)")
        clean_df, errors, dup_count = process_file(BytesIO(file_content), file_name)

        # Free the raw file content from memory
        del file_content
        gc.collect()

        logger.info(f"Background: cleaning done, {len(clean_df)} clean rows. Starting bulk insert...")
        _bulk_insert_shipments(clean_df, upload_log, user)
        logger.info(f"Background: bulk insert done for {file_name}")

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
        logger.info(f"Background: DONE {file_name} in {elapsed_ms}ms, quality={quality['data_quality_score']}")

    except DataCleaningError as e:
        elapsed_ms = int((time.time() - start_time) * 1000)
        upload_log.status = UploadLog.Status.FAILED
        upload_log.error_log = json.dumps({"fatal": str(e)})
        upload_log.processing_time_ms = elapsed_ms
        upload_log.save()
        logger.error(f"Background: cleaning failed for {file_name}: {e}")
    except Exception as e:
        elapsed_ms = int((time.time() - start_time) * 1000)
        upload_log.status = UploadLog.Status.FAILED
        upload_log.error_log = json.dumps({"fatal": str(e)})
        upload_log.processing_time_ms = elapsed_ms
        upload_log.save()
        logger.exception(f"Background: unexpected error for {file_name}")


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def upload_status(request, upload_id):
    """GET /api/uploads/<id>/status/ — Poll upload processing status."""
    try:
        upload_log = UploadLog.objects.get(pk=upload_id, user=request.user)
    except UploadLog.DoesNotExist:
        return Response({"error": "Upload not found"}, status=status.HTTP_404_NOT_FOUND)

    result = {
        "upload_id": upload_log.pk,
        "file_name": upload_log.file_name,
        "status": upload_log.status,
        "total_rows": upload_log.total_rows,
        "processed_rows": upload_log.processed_rows,
        "error_rows": upload_log.error_rows,
        "duplicate_rows": upload_log.duplicate_rows,
        "data_quality_score": upload_log.data_quality_score,
        "processing_time_ms": upload_log.processing_time_ms,
    }

    if upload_log.status in (UploadLog.Status.COMPLETED, UploadLog.Status.PARTIAL):
        result["message"] = "File processed successfully"
    elif upload_log.status == UploadLog.Status.FAILED:
        try:
            result["error_details"] = json.loads(upload_log.error_log)
        except Exception:
            result["error_details"] = upload_log.error_log

    return Response(result)


@api_view(["DELETE"])
@permission_classes([IsAuthenticated])
def clear_all_data(request):
    """DELETE /api/clear-data/ — Truncate user's shipment data but preserve history."""
    user = request.user
    with transaction.atomic():
        # User requested: "only affect dashboard, analytics, intel and alerts... not history"
        # Shipments = Dashboard data. UploadLogs = History.
        if user.is_superuser:
            # Superusers clear everything they see (including orphaned legacy records)
            Shipment.objects.all().delete()
            ProfitRecord.objects.all().delete()
        else:
            Shipment.objects.filter(user=user).delete()
            ProfitRecord.objects.filter(user=user).delete()

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


def _bulk_insert_shipments(df, upload_log, user):
    """Bulk-insert with cross-file dedup on shipment_id. Optimized for speed and reliability."""
    import gc
    from django.db.models import Q

    # 1. Routes — batch create missing ones with case-insensitive normalization
    df["origin"] = df["origin"].astype(str).str.strip().str.upper()
    df["destination"] = df["destination"].astype(str).str.strip().str.upper()
    
    route_pairs = df[["origin", "destination"]].drop_duplicates().values.tolist()
    route_origins = set(o for o, d in route_pairs)
    route_dests = set(d for o, d in route_pairs)
    
    # Pre-fetch existing routes. We use UPPER() lookups to be safe.
    existing_routes = Route.objects.filter(origin__in=route_origins, destination__in=route_dests)
    # Key is (origin.upper(), destination.upper()) to avoid casing mismatch
    route_cache = {(r.origin.upper(), r.destination.upper()): r for r in existing_routes}

    missing_routes = []
    for origin, destination in route_pairs:
        if (origin, destination) not in route_cache:
            missing_routes.append(Route(origin=origin, destination=destination))

    if missing_routes:
        logger.info(f"Creating {len(missing_routes)} new routes...")
        Route.objects.bulk_create(missing_routes, ignore_conflicts=True)
        # Refresh cache
        new_routes = Route.objects.filter(origin__in=route_origins, destination__in=route_dests)
        route_cache = {(r.origin.upper(), r.destination.upper()): r for r in new_routes}

    # 2. Pre-fetch existing shipments for upsert (only for relevant user)
    incoming_ids = set(df["shipment_id"].tolist())
    logger.info(f"Checking {len(incoming_ids)} shipment IDs for existence...")
    
    # Significant optimization: only fetch ID and shipment_id to save memory
    existing_map = {
        s_id: s_pk 
        for s_pk, s_id in Shipment.objects.filter(shipment_id__in=incoming_ids).values_list("pk", "shipment_id")
    }

    # 3. Build shipment objects
    to_create, to_update = [], []
    records = df.to_dict("records")
    
    skipped_count = 0
    for row in records:
        origin_up = str(row["origin"]).upper()
        dest_up = str(row["destination"]).upper()
        route = route_cache.get((origin_up, dest_up))
        
        if not route:
            skipped_count += 1
            continue
            
        data = _build_shipment_data(row, route, upload_log, user)
        sid = str(row["shipment_id"]).strip()

        if sid in existing_map:
            # For updates, we need the actual object. 
            # To avoid loading all objects at once, we'll update in smaller batches later
            # For now, let's keep the PK
            data["pk"] = existing_map[sid]
            to_update.append(data)
        else:
            to_create.append(Shipment(**data))

    logger.info(f"Ingestion plan: {len(to_create)} to create, {len(to_update)} to update. {skipped_count} skipped (no route).")

    # 4. Bulk operations
    BATCH_SIZE = 500
    
    if to_create:
        for i in range(0, len(to_create), BATCH_SIZE):
            Shipment.objects.bulk_create(to_create[i:i + BATCH_SIZE], batch_size=BATCH_SIZE)
            logger.info(f"Created batch {i // BATCH_SIZE + 1}...")

    if to_update:
        # Since bulk_update needs objects, we fetch them in batches to save memory
        update_fields = [
            "route", "upload", "user", "dispatch_date", "delivery_date",
            "expected_delivery_date", "vehicle_type", "vehicle_no",
            "revenue", "rate_per_mt", "total_amount", "freight_deduction",
            "penalty", "amount_receivable", "net_weight", "gross_weight",
            "charge_weight", "shortage", "transit_permissible", "transit_taken",
            "delay_days", "is_on_time", "has_shortage", "has_penalty",
            "total_distance", "pod_status", "billing_status",
            "customer_name", "transporter_name", "booking_region", "contract_id", "material_type",
            "consignor_name", "consignee_name",
        ]
        
        for i in range(0, len(to_update), BATCH_SIZE):
            batch_data = to_update[i:i + BATCH_SIZE]
            batch_pks = [d["pk"] for d in batch_data]
            
            # Fetch objects for this batch
            objects_to_update = Shipment.objects.filter(pk__in=batch_pks)
            obj_map = {obj.pk: obj for obj in objects_to_update}
            
            final_update_list = []
            for data in batch_data:
                obj = obj_map.get(data["pk"])
                if obj:
                    # Update fields except ID/PK/Shipment_ID
                    for field, value in data.items():
                        if field not in ("pk", "shipment_id"):
                            setattr(obj, field, value)
                    final_update_list.append(obj)
            
            if final_update_list:
                Shipment.objects.bulk_update(final_update_list, fields=update_fields, batch_size=BATCH_SIZE)
                logger.info(f"Updated batch {i // BATCH_SIZE + 1}...")

    # Free memory
    del to_create, to_update, records, route_cache, existing_map
    gc.collect()


def _build_shipment_data(row, route, upload_log, user):
    """Build shipment dict from a cleaned DataFrame row (dict or Series)."""
    import math

    def _is_na(val):
        if val is None:
            return True
        try:
            return math.isnan(val)
        except (TypeError, ValueError):
            return False

    def _safe_date(val):
        if _is_na(val):
            return None
        return val.date() if hasattr(val, "date") else val

    def _safe_float(val, default=0):
        if _is_na(val):
            return default
        try:
            return float(val)
        except (TypeError, ValueError):
            return default

    def _safe_int(val, default=0):
        if _is_na(val):
            return default
        try:
            return int(val)
        except (TypeError, ValueError):
            return default

    def _safe_str(val, max_len=255, default=""):
        if _is_na(val) or str(val).lower() in ("nan", "none", ""):
            return default
        return str(val)[:max_len]

    return {
        "shipment_id": row["shipment_id"],
        "route": route,
        "upload": upload_log,
        "user": user,
        "dispatch_date": _safe_date(row.get("dispatch_date")),
        "delivery_date": _safe_date(row.get("delivery_date")),
        "expected_delivery_date": _safe_date(row.get("expected_delivery_date")),
        "vehicle_type": _safe_str(row.get("vehicle_type"), 50, "other"),
        "vehicle_no": _safe_str(row.get("vehicle_no"), 50, ""),
        "revenue": _safe_float(row.get("revenue")),
        "rate_per_mt": _safe_float(row.get("rate_per_mt")),
        "total_amount": _safe_float(row.get("total_amount")),
        "freight_deduction": _safe_float(row.get("freight_deduction")),
        "penalty": _safe_float(row.get("penalty")),
        "amount_receivable": _safe_float(row.get("amount_receivable")),
        "net_weight": _safe_float(row.get("net_weight")),
        "gross_weight": _safe_float(row.get("gross_weight")),
        "charge_weight": _safe_float(row.get("charge_weight")),
        "shortage": _safe_float(row.get("shortage")),
        "transit_permissible": _safe_int(row.get("transit_permissible")),
        "transit_taken": _safe_int(row.get("transit_taken")),
        "delay_days": _safe_int(row.get("delay_days")),
        "is_on_time": bool(row.get("is_on_time", True)),
        "has_shortage": bool(row.get("has_shortage", False)),
        "has_penalty": bool(row.get("has_penalty", False)),
        "total_distance": _safe_float(row.get("total_distance"), None) if not _is_na(row.get("total_distance")) else None,
        "pod_status": _safe_str(row.get("pod_status"), 50, ""),
        "billing_status": _safe_str(row.get("billing_status"), 50, ""),
        "customer_name": _safe_str(row.get("customer_name"), 255, ""),
        "transporter_name": _safe_str(row.get("transporter_name"), 255, ""),
        "booking_region": _safe_str(row.get("booking_region"), 100, ""),
        "contract_id": _safe_str(row.get("contract_id"), 100, ""),
        "material_type": _safe_str(row.get("material_type"), 150, ""),
        "consignor_name": _safe_str(row.get("consignor_name"), 255, ""),
        "consignee_name": _safe_str(row.get("consignee_name"), 255, ""),
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


# ═══════════════════════════════════════════════════════════
# PROFIT ANALYSIS
# ═══════════════════════════════════════════════════════════

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def profit_upload(request):
    """POST /api/profit/upload/ — Upload Gross Margin MIS Excel file."""
    from .utils.profit_data_cleaner import process_profit_file, ProfitDataError

    files = request.FILES.getlist("file")
    if not files:
        files = request.FILES.getlist("files")
    if not files:
        return Response({"error": "No files provided"}, status=status.HTTP_400_BAD_REQUEST)

    user = request.user

    # Check for refresh flag
    if request.GET.get('refresh') == 'true':
        with transaction.atomic():
            if user.is_superuser:
                ProfitRecord.objects.all().delete()
            else:
                ProfitRecord.objects.filter(user=user).delete()

    results = []
    for uploaded_file in files:
        file_name = uploaded_file.name
        if hasattr(uploaded_file, "seek"):
            uploaded_file.seek(0)

        upload_log = UploadLog.objects.create(
            file_name=f"[PROFIT] {file_name}",
            status=UploadLog.Status.PROCESSING,
            original_file=uploaded_file,
            user=user,
        )
        if hasattr(uploaded_file, "seek"):
            uploaded_file.seek(0)

        start_time = time.time()

        try:
            clean_df, errors, dup_count = process_profit_file(uploaded_file, file_name)

            # Cross-file duplicate detection
            incoming_ids = set(clean_df["sap_delivery_no"].tolist()) if len(clean_df) > 0 else set()
            existing_count = ProfitRecord.objects.filter(user=user, sap_delivery_no__in=incoming_ids).count() if incoming_ids else 0

            is_refresh = request.GET.get('refresh') == 'true'
            if existing_count > 0 and not is_refresh:
                upload_log.status = UploadLog.Status.FAILED
                upload_log.error_log = json.dumps({"fatal": "Duplicate records detected."})
                upload_log.save()
                results.append({
                    "file_name": file_name,
                    "error": "DUPLICATES_FOUND",
                    "duplicate_count": existing_count,
                    "message": "This file contains profit records already in your system. Would you like to Start Refresh?"
                })
                continue

            # Bulk insert
            records = []
            for _, row in clean_df.iterrows():
                r = dict(row)
                r["upload"] = upload_log
                r["user"] = user
                records.append(ProfitRecord(**r))

            ProfitRecord.objects.bulk_create(records, batch_size=500)

            elapsed_ms = int((time.time() - start_time) * 1000)
            upload_log.total_rows = len(clean_df) + len(errors) + dup_count
            upload_log.processed_rows = len(clean_df)
            upload_log.error_rows = len(errors)
            upload_log.duplicate_rows = dup_count
            upload_log.error_log = json.dumps(errors[:50], default=str)
            upload_log.processing_time_ms = elapsed_ms
            upload_log.status = UploadLog.Status.COMPLETED if not errors else UploadLog.Status.PARTIAL
            upload_log.save()

            results.append({
                "file_name": file_name,
                "message": f"Processed {len(clean_df)} profit records",
                "processed": len(clean_df),
                "errors": len(errors),
                "duplicates": dup_count,
                "time_ms": elapsed_ms,
            })

        except ProfitDataError as e:
            upload_log.status = UploadLog.Status.FAILED
            upload_log.error_log = json.dumps({"fatal": str(e)})
            upload_log.save()
            results.append({"file_name": file_name, "error": str(e)})
        except Exception as e:
            logger.exception(f"Profit upload crash for {file_name}")
            upload_log.status = UploadLog.Status.FAILED
            upload_log.save()
            results.append({"file_name": file_name, "error": f"Processing error: {e}"})

    has_dup = any(r.get("error") == "DUPLICATES_FOUND" for r in results)
    sc = status.HTTP_409_CONFLICT if has_dup else status.HTTP_201_CREATED

    # Explicitly clear memory after loop
    import gc
    gc.collect()

    if len(results) == 1:
        return Response(results[0], status=sc)
    return Response({"message": "Processing complete", "results": results}, status=sc)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def profit_summary(request):
    """GET /api/profit/summary/ — Top-level profit KPIs."""
    from .utils.profit_engine import get_profit_summary
    base_qs = ProfitRecord.objects.filter(user=request.user)
    
    if not base_qs.exists():
        return Response({"error": "No profit records available."})
        
    qs = _apply_profit_filters(base_qs, request.GET)
    return Response(get_profit_summary(qs))


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def profit_lanes(request):
    """GET /api/profit/lanes/ — Lane classification."""
    from .utils.profit_engine import get_lane_classification
    qs = ProfitRecord.objects.filter(user=request.user)
    qs = _apply_profit_filters(qs, request.GET)
    return Response(get_lane_classification(qs))


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def profit_trends(request):
    """GET /api/profit/trends/ — Cost-per-tonne trends by lane."""
    from .utils.profit_engine import get_lane_trends
    qs = ProfitRecord.objects.filter(user=request.user)
    qs = _apply_profit_filters(qs, request.GET)
    return Response(get_lane_trends(qs))


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def profit_alerts(request):
    """GET /api/profit/alerts/ — Smart profitability alerts."""
    from .utils.profit_engine import get_profit_alerts
    qs = ProfitRecord.objects.filter(user=request.user)
    qs = _apply_profit_filters(qs, request.GET)
    return Response(get_profit_alerts(qs))


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def profit_drilldown(request):
    """GET /api/profit/drilldown/?loading_city=X&delivery_city=Y — Lane waterfall."""
    from .utils.profit_engine import get_lane_drilldown
    lc = request.GET.get("loading_city", "")
    dc = request.GET.get("delivery_city", "")
    qs = ProfitRecord.objects.filter(user=request.user)
    qs = _apply_profit_filters(qs, request.GET)
    return Response(get_lane_drilldown(qs, loading_city=lc, delivery_city=dc))


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def profit_lane_shipments(request):
    """GET /api/profit/shipments/?loading_city=X&delivery_city=Y — Itemized shipments for a lane."""
    from .utils.profit_engine import get_lane_shipment_details
    lc = request.GET.get("loading_city", "")
    dc = request.GET.get("delivery_city", "")
    qs = ProfitRecord.objects.filter(user=request.user)
    qs = _apply_profit_filters(qs, request.GET)
    return Response(get_lane_shipment_details(qs, loading_city=lc, delivery_city=dc))


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def profit_insights(request):
    """GET /api/profit/insights/ — Human-readable profit insights."""
    from .utils.profit_engine import generate_profit_insights
    qs = ProfitRecord.objects.filter(user=request.user)
    qs = _apply_profit_filters(qs, request.GET)
    return Response(generate_profit_insights(qs))

