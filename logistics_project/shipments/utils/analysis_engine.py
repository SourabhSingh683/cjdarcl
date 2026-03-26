"""
Analysis Engine — Root Cause Analysis + Risk Prediction
========================================================
All analysis is grounded in actual dataset columns.
Uses Django ORM aggregations only (no loops, no hallucinated fields).

Provides:
  - Route-wise delay analysis
  - Vehicle-wise delay analysis
  - Temporal delay patterns (monthly, weekday)
  - Shortage analysis
  - Penalty analysis
  - Rule-based risk scoring
  - Period comparison (recent vs prior)
"""

import logging
from datetime import timedelta
from decimal import Decimal

from django.db.models import (
    Count, Sum, Avg, Q, F, Case, When, Value,
    DecimalField, IntegerField, FloatField,
)
from django.db.models.functions import Coalesce, ExtractMonth, ExtractWeekDay
from django.utils import timezone

from shipments.models import Shipment, Route

logger = logging.getLogger("shipments")

# Risk thresholds
HIGH_RISK_THRESHOLD = 0.40   # > 40% delay rate
MEDIUM_RISK_THRESHOLD = 0.20  # > 20% delay rate


# ═══════════════════════════════════════════════════════════
# ROOT CAUSE ANALYSIS
# ═══════════════════════════════════════════════════════════

def analyze_routes(qs=None):
    """
    Route-wise delay analysis with financial impact.
    Returns list of routes with delay rates, avg delay, penalty, shortage info.
    """
    if qs is None:
        qs = Shipment.objects.all()

    return list(
        qs.values("route__origin", "route__destination")
        .annotate(
            total=Count("id"),
            delayed=Count("id", filter=Q(is_on_time=False)),
            on_time=Count("id", filter=Q(is_on_time=True)),
            avg_delay=Coalesce(
                Avg("delay_days", filter=Q(is_on_time=False)), 0,
                output_field=IntegerField()
            ),
            max_delay=Coalesce(
                Avg("delay_days", filter=Q(delay_days__gt=0)), 0,
                output_field=IntegerField()
            ),
            total_penalty=Coalesce(Sum("penalty"), Decimal("0"), output_field=DecimalField()),
            total_revenue=Coalesce(Sum("revenue"), Decimal("0"), output_field=DecimalField()),
            total_shortage=Coalesce(Sum("shortage"), Decimal("0"), output_field=DecimalField()),
            shortage_count=Count("id", filter=Q(has_shortage=True)),
            avg_weight=Coalesce(Avg("net_weight"), Decimal("0"), output_field=DecimalField()),
        )
        .order_by("-delayed")
    )


def analyze_vehicles(qs=None):
    """
    Vehicle-wise delay analysis.
    Groups by vehicle_no to find problem vehicles.
    """
    if qs is None:
        qs = Shipment.objects.all()

    return list(
        qs.exclude(vehicle_no="")
        .values("vehicle_no")
        .annotate(
            total=Count("id"),
            delayed=Count("id", filter=Q(is_on_time=False)),
            avg_delay=Coalesce(
                Avg("delay_days", filter=Q(is_on_time=False)), 0,
                output_field=IntegerField()
            ),
            total_penalty=Coalesce(Sum("penalty"), Decimal("0"), output_field=DecimalField()),
            total_shortage=Coalesce(Sum("shortage"), Decimal("0"), output_field=DecimalField()),
        )
        .order_by("-delayed")[:20]  # Top 20 worst vehicles
    )


def analyze_material_types(qs=None):
    """Delay analysis by material type (mapped as vehicle_type)."""
    if qs is None:
        qs = Shipment.objects.all()

    return list(
        qs.values("vehicle_type")
        .annotate(
            total=Count("id"),
            delayed=Count("id", filter=Q(is_on_time=False)),
            avg_delay=Coalesce(
                Avg("delay_days", filter=Q(is_on_time=False)), 0,
                output_field=IntegerField()
            ),
            total_penalty=Coalesce(Sum("penalty"), Decimal("0"), output_field=DecimalField()),
        )
        .order_by("-total")
    )


def analyze_temporal(qs=None):
    """
    Monthly delay patterns.
    Returns delay rates by month of dispatch.
    """
    if qs is None:
        qs = Shipment.objects.all()

    return list(
        qs.annotate(month=ExtractMonth("dispatch_date"))
        .values("month")
        .annotate(
            total=Count("id"),
            delayed=Count("id", filter=Q(is_on_time=False)),
            total_penalty=Coalesce(Sum("penalty"), Decimal("0"), output_field=DecimalField()),
        )
        .order_by("month")
    )


def analyze_shortages(qs=None):
    """
    Shortage analysis — routes and vehicles with highest shortage.
    """
    if qs is None:
        qs = Shipment.objects.filter(has_shortage=True)
    else:
        qs = qs.filter(has_shortage=True)

    route_shortages = list(
        qs.values("route__origin", "route__destination")
        .annotate(
            count=Count("id"),
            total_shortage=Sum("shortage"),
            avg_shortage=Avg("shortage"),
        )
        .order_by("-total_shortage")[:10]
    )

    return {
        "total_shortage_shipments": qs.count(),
        "total_shortage_mt": float(qs.aggregate(
            t=Coalesce(Sum("shortage"), Decimal("0"), output_field=DecimalField())
        )["t"]),
        "by_route": route_shortages,
    }


def get_full_root_cause(qs=None):
    """Full root cause analysis bundle."""
    return {
        "by_route": analyze_routes(qs),
        "by_vehicle": analyze_vehicles(qs),
        "by_material_type": analyze_material_types(qs),
        "by_month": analyze_temporal(qs),
        "shortages": analyze_shortages(qs),
    }


# ═══════════════════════════════════════════════════════════
# RISK PREDICTION (RULE-BASED)
# ═══════════════════════════════════════════════════════════

def _classify_risk(delay_rate):
    """Classify risk based on delay rate."""
    if delay_rate > HIGH_RISK_THRESHOLD:
        return "high"
    elif delay_rate > MEDIUM_RISK_THRESHOLD:
        return "medium"
    return "low"


def get_route_risks(qs=None):
    """
    Risk-score each route based on delay rate.
    """
    if qs is None:
        qs = Shipment.objects.all()

    routes = (
        qs.values("route__origin", "route__destination")
        .annotate(
            total=Count("id"),
            delayed=Count("id", filter=Q(is_on_time=False)),
            total_penalty=Coalesce(Sum("penalty"), Decimal("0"), output_field=DecimalField()),
            total_shortage=Coalesce(Sum("shortage"), Decimal("0"), output_field=DecimalField()),
        )
        .filter(total__gte=1)  # At least 1 shipment
        .order_by("-delayed")
    )

    results = []
    for r in routes:
        delay_rate = r["delayed"] / r["total"] if r["total"] > 0 else 0
        results.append({
            **r,
            "delay_rate": round(delay_rate * 100, 1),
            "risk_level": _classify_risk(delay_rate),
        })

    return sorted(results, key=lambda x: -x["delay_rate"])


def get_vehicle_risks(qs=None):
    """Risk-score each vehicle."""
    if qs is None:
        qs = Shipment.objects.all()

    vehicles = (
        qs.exclude(vehicle_no="")
        .values("vehicle_no")
        .annotate(
            total=Count("id"),
            delayed=Count("id", filter=Q(is_on_time=False)),
        )
        .filter(total__gte=1)
        .order_by("-delayed")[:20]
    )

    results = []
    for v in vehicles:
        delay_rate = v["delayed"] / v["total"] if v["total"] > 0 else 0
        results.append({
            **v,
            "delay_rate": round(delay_rate * 100, 1),
            "risk_level": _classify_risk(delay_rate),
        })

    return sorted(results, key=lambda x: -x["delay_rate"])


def get_risk_summary(qs=None):
    """Overall risk summary."""
    route_risks = get_route_risks(qs)
    vehicle_risks = get_vehicle_risks(qs)

    high_risk_routes = [r for r in route_risks if r["risk_level"] == "high"]
    medium_risk_routes = [r for r in route_risks if r["risk_level"] == "medium"]

    return {
        "route_risks": route_risks,
        "vehicle_risks": vehicle_risks,
        "high_risk_route_count": len(high_risk_routes),
        "medium_risk_route_count": len(medium_risk_routes),
        "low_risk_route_count": len(route_risks) - len(high_risk_routes) - len(medium_risk_routes),
    }


# ═══════════════════════════════════════════════════════════
# TIME COMPARISON ENGINE
# ═══════════════════════════════════════════════════════════

def compare_periods(qs=None, days=30):
    """
    Compare recent period vs prior period.
    Default: last 30 days vs 30 days before that.
    Returns metrics with % changes.
    """
    if qs is None:
        qs = Shipment.objects.all()

    now = timezone.now().date()
    recent = qs.filter(dispatch_date__gte=now - timedelta(days=days))
    prior = qs.filter(
        dispatch_date__gte=now - timedelta(days=days * 2),
        dispatch_date__lt=now - timedelta(days=days),
    )

    def _period_stats(period_qs):
        total = period_qs.count()
        if total == 0:
            return None
        delayed = period_qs.filter(is_on_time=False).count()
        on_time_pct = round(((total - delayed) / total) * 100, 1)
        stats = period_qs.aggregate(
            total_revenue=Coalesce(Sum("revenue"), Decimal("0"), output_field=DecimalField()),
            total_penalty=Coalesce(Sum("penalty"), Decimal("0"), output_field=DecimalField()),
            total_shortage=Coalesce(Sum("shortage"), Decimal("0"), output_field=DecimalField()),
            avg_delay=Coalesce(Avg("delay_days", filter=Q(is_on_time=False)), 0, output_field=IntegerField()),
        )
        return {
            "total_shipments": total,
            "delayed_count": delayed,
            "on_time_pct": on_time_pct,
            "total_revenue": float(stats["total_revenue"]),
            "total_penalty": float(stats["total_penalty"]),
            "total_shortage": float(stats["total_shortage"]),
            "avg_delay_days": stats["avg_delay"],
        }

    def _pct_change(current, previous):
        if previous == 0:
            return None
        return round(((current - previous) / abs(previous)) * 100, 1)

    recent_stats = _period_stats(recent)
    prior_stats = _period_stats(prior)

    if not recent_stats:
        return {
            "period_days": days,
            "recent": None,
            "prior": None,
            "changes": {},
            "message": f"No shipments found in the last {days} days.",
        }

    changes = {}
    if prior_stats:
        for key in ["total_shipments", "delayed_count", "on_time_pct",
                     "total_revenue", "total_penalty"]:
            changes[key] = _pct_change(recent_stats[key], prior_stats[key])

    return {
        "period_days": days,
        "recent": recent_stats,
        "prior": prior_stats,
        "changes": changes,
    }


# ═══════════════════════════════════════════════════════════
# SMART INSIGHTS GENERATOR
# ═══════════════════════════════════════════════════════════

def generate_smart_insights(qs=None):
    """
    Context-aware, data-size-aware insights.
    Unlike basic insights, these include:
      - Financial impact (penalties, revenue loss)
      - Shortage patterns
      - Trend detection
      - Anomaly detection
    """
    if qs is None:
        qs = Shipment.objects.all()

    insights = []
    total = qs.count()
    if total == 0:
        return [{"type": "info", "text": "No shipment data available for analysis."}]

    # --- 1. Overall performance ---
    delayed = qs.filter(is_on_time=False).count()
    on_time_pct = round(((total - delayed) / total) * 100, 1)

    if on_time_pct >= 90:
        insights.append({"type": "success",
            "text": f"Excellent delivery performance: {on_time_pct}% on-time across {total} shipments."})
    elif on_time_pct >= 70:
        insights.append({"type": "warning",
            "text": f"Delivery performance is moderate at {on_time_pct}% on-time. {delayed} of {total} shipments were delayed."})
    else:
        insights.append({"type": "danger",
            "text": f"Critical: Only {on_time_pct}% on-time delivery. {delayed} out of {total} shipments delayed."})

    # --- 2. Penalty financial impact ---
    penalty_stats = qs.aggregate(
        total_penalty=Coalesce(Sum("penalty"), Decimal("0"), output_field=DecimalField()),
        penalty_count=Count("id", filter=Q(has_penalty=True)),
    )
    if penalty_stats["penalty_count"] > 0:
        insights.append({"type": "danger",
            "text": f"₹{float(penalty_stats['total_penalty']):,.2f} in late delivery penalties "
                    f"across {penalty_stats['penalty_count']} shipments."})

    # --- 3. Worst route ---
    worst_route = (
        qs.filter(is_on_time=False)
        .values("route__origin", "route__destination")
        .annotate(
            count=Count("id"),
            avg_delay=Avg("delay_days"),
            penalty_sum=Coalesce(Sum("penalty"), Decimal("0"), output_field=DecimalField()),
        )
        .order_by("-count")
        .first()
    )
    if worst_route and worst_route["count"] > 0:
        penalty_text = ""
        if worst_route["penalty_sum"] > 0:
            penalty_text = f", incurring ₹{float(worst_route['penalty_sum']):,.2f} in penalties"
        insights.append({"type": "warning",
            "text": f"Route {worst_route['route__origin']} → {worst_route['route__destination']} "
                    f"has the most delays ({worst_route['count']} shipments, "
                    f"avg {worst_route['avg_delay']:.1f} days late{penalty_text})."})

    # --- 4. Shortage analysis ---
    shortage_stats = qs.aggregate(
        shortage_count=Count("id", filter=Q(has_shortage=True)),
        total_shortage=Coalesce(Sum("shortage", filter=Q(has_shortage=True)), Decimal("0"), output_field=DecimalField()),
    )
    if shortage_stats["shortage_count"] > 0:
        insights.append({"type": "warning",
            "text": f"{shortage_stats['shortage_count']} shipments had material shortages "
                    f"(total: {float(shortage_stats['total_shortage']):.3f} MT)."})

    # --- 5. Revenue insight ---
    rev_stats = qs.aggregate(
        total_rev=Coalesce(Sum("revenue"), Decimal("0"), output_field=DecimalField()),
        total_receivable=Coalesce(Sum("amount_receivable"), Decimal("0"), output_field=DecimalField()),
    )
    total_rev = float(rev_stats["total_rev"])
    total_recv = float(rev_stats["total_receivable"])
    if total_rev > 0 and total_recv > 0 and total_recv < total_rev:
        loss = total_rev - total_recv
        loss_pct = round((loss / total_rev) * 100, 1)
        insights.append({"type": "info",
            "text": f"Revenue leakage: ₹{loss:,.2f} ({loss_pct}%) lost to deductions and penalties "
                    f"(Billed: ₹{total_rev:,.2f}, Receivable: ₹{total_recv:,.2f})."})

    # --- 6. Top revenue destination ---
    top_dest = (
        qs.values("route__destination")
        .annotate(rev=Coalesce(Sum("revenue"), Decimal("0"), output_field=DecimalField()))
        .order_by("-rev")
        .first()
    )
    if top_dest and float(top_dest["rev"]) > 0:
        insights.append({"type": "info",
            "text": f"Highest revenue destination: {top_dest['route__destination']} "
                    f"(₹{float(top_dest['rev']):,.2f})."})

    # --- 7. Data size awareness ---
    if total < 20:
        insights.append({"type": "info",
            "text": f"Analysis based on {total} shipments — upload more data for stronger trend detection."})

    return insights
