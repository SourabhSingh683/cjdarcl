"""
Data Quality Engine
===================
Computes a 0–100 quality score for an uploaded dataset based on:
  - Missing critical values (shipment_id, dates, destination)
  - Invalid numeric/date entries
  - Duplicate shipment_ids
  - Shortage anomalies
  - Completeness of financial fields

Returns structured quality report with score and issues list.
"""

import logging
from django.db.models import Count, Q, Avg, Sum

from shipments.models import Shipment, UploadLog

logger = logging.getLogger("shipments")


def compute_upload_quality(upload_log: UploadLog) -> dict:
    """
    Compute data quality score for a specific upload batch.
    Returns: {"data_quality_score": int, "issues": [...], "summary": {...}}
    """
    shipments = Shipment.objects.filter(upload=upload_log)
    total = shipments.count()

    if total == 0:
        return {
            "data_quality_score": 0,
            "issues": ["No shipments found for this upload."],
            "summary": {},
        }

    issues = []
    penalties = 0  # Deductions from 100

    # --- 1. Missing delivery dates (weight: 15) ---
    missing_delivery = shipments.filter(delivery_date__isnull=True).count()
    if missing_delivery > 0:
        pct = round((missing_delivery / total) * 100, 1)
        penalties += min(15, int(pct * 0.15))
        issues.append(f"{missing_delivery} shipments ({pct}%) missing delivery date")

    # --- 2. Missing expected delivery date (weight: 10) ---
    missing_edd = shipments.filter(expected_delivery_date__isnull=True).count()
    if missing_edd > 0:
        pct = round((missing_edd / total) * 100, 1)
        penalties += min(10, int(pct * 0.10))
        issues.append(f"{missing_edd} shipments ({pct}%) missing expected delivery date")

    # --- 3. Zero revenue (weight: 15) ---
    zero_revenue = shipments.filter(revenue=0, total_amount=0).count()
    if zero_revenue > 0:
        pct = round((zero_revenue / total) * 100, 1)
        penalties += min(15, int(pct * 0.15))
        issues.append(f"{zero_revenue} shipments ({pct}%) have no revenue/amount data")

    # --- 4. Zero weight (weight: 10) ---
    zero_weight = shipments.filter(net_weight=0).count()
    if zero_weight > 0:
        pct = round((zero_weight / total) * 100, 1)
        penalties += min(10, int(pct * 0.10))
        issues.append(f"{zero_weight} shipments ({pct}%) have no weight data")

    # --- 5. Missing transit times (weight: 15) ---
    missing_transit = shipments.filter(
        transit_permissible=0, transit_taken=0
    ).count()
    if missing_transit > 0:
        pct = round((missing_transit / total) * 100, 1)
        penalties += min(15, int(pct * 0.15))
        issues.append(f"{missing_transit} shipments ({pct}%) missing transit time data")

    # --- 6. Shortages detected (informational, weight: 5) ---
    shortage_count = shipments.filter(has_shortage=True).count()
    if shortage_count > 0:
        pct = round((shortage_count / total) * 100, 1)
        penalties += min(5, int(pct * 0.05))
        issues.append(f"{shortage_count} shipments ({pct}%) have material shortages")

    # --- 7. Error rows from upload (weight: 15) ---
    if upload_log.error_rows > 0:
        error_pct = round(
            (upload_log.error_rows / max(upload_log.total_rows, 1)) * 100, 1
        )
        penalties += min(15, int(error_pct * 0.15))
        issues.append(
            f"{upload_log.error_rows} rows ({error_pct}%) had errors during processing"
        )

    # --- 8. Duplicate rows removed (weight: 10) ---
    if upload_log.duplicate_rows > 0:
        dup_pct = round(
            (upload_log.duplicate_rows / max(upload_log.total_rows, 1)) * 100, 1
        )
        penalties += min(10, int(dup_pct * 0.10))
        issues.append(
            f"{upload_log.duplicate_rows} duplicate rows ({dup_pct}%) were removed"
        )

    # --- 9. Unknown origin (weight: 5) ---
    unknown_origin = shipments.filter(route__origin="Unknown").count()
    if unknown_origin > 0:
        penalties += 5
        issues.append(f"{unknown_origin} shipments have unknown origin")

    score = max(0, 100 - penalties)

    if not issues:
        issues.append("No data quality issues detected — excellent data!")

    return {
        "data_quality_score": score,
        "issues": issues,
        "summary": {
            "total_shipments": total,
            "missing_delivery_dates": missing_delivery,
            "missing_expected_dates": missing_edd,
            "zero_revenue_count": zero_revenue,
            "zero_weight_count": zero_weight,
            "shortage_count": shortage_count,
            "error_rows": upload_log.error_rows,
            "duplicate_rows": upload_log.duplicate_rows,
        },
    }


def compute_overall_quality(qs=None) -> dict:
    """
    Compute overall data quality across filtered shipments.
    """
    if qs is None:
        qs = Shipment.objects.all()
        
    total = qs.count()
    if total == 0:
        return {"data_quality_score": 0, "issues": ["No data in database."], "summary": {}}

    issues = []
    penalties = 0

    checks = [
        ("delivery_date__isnull", True, "missing delivery date", 15),
        ("expected_delivery_date__isnull", True, "missing expected delivery date", 10),
        ("net_weight", 0, "no weight data", 10),
        ("has_shortage", True, "material shortages", 5),
        ("has_penalty", True, "late delivery penalties", 5),
    ]

    summary = {"total_shipments": total}

    for field, value, label, max_penalty in checks:
        count = qs.filter(**{field: value}).count()
        if count > 0:
            pct = round((count / total) * 100, 1)
            penalties += min(max_penalty, int(pct * max_penalty / 100))
            issues.append(f"{count} shipments ({pct}%) have {label}")
            summary[f"{label.replace(' ', '_')}_count"] = count

    # Revenue check
    zero_rev = qs.filter(revenue=0, total_amount=0).count()
    if zero_rev > 0:
        pct = round((zero_rev / total) * 100, 1)
        penalties += min(15, int(pct * 0.15))
        issues.append(f"{zero_rev} shipments ({pct}%) have no revenue data")

    score = max(0, 100 - penalties)
    if not issues:
        issues.append("Excellent data quality!")

    return {"data_quality_score": score, "issues": issues, "summary": summary}
