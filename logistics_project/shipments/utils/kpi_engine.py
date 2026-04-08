"""
KPI Engine
==========
Aggregation queries using Django ORM to generate KPIs and insights.
All functions accept a base queryset so filters can be pre-applied by the view layer.
"""

import logging
from datetime import timedelta
from decimal import Decimal

from django.db.models import (
    Count, Sum, Avg, Q, F, Value, CharField,
    DecimalField, IntegerField, FloatField
)
from django.db.models.functions import (
    TruncDate, TruncWeek, TruncMonth, Coalesce,
)
from django.utils import timezone

from shipments.models import Shipment, Route

logger = logging.getLogger("shipments")


def get_summary_kpis(qs=None):
    """
    Returns a dict with high-level KPIs:
      - total_shipments
      - on_time_count / on_time_percentage
      - delayed_count / delayed_percentage
      - total_revenue / average_revenue
    """
    if qs is None:
        qs = Shipment.objects.all()

    stats = qs.aggregate(
        total=Count("id"),
        on_time=Count("id", filter=Q(is_on_time=True)),
        delayed=Count("id", filter=Q(is_on_time=False)),
        total_revenue=Coalesce(Sum("revenue"), Decimal("0"), output_field=DecimalField()),
        avg_revenue=Coalesce(Avg("revenue"), Decimal("0"), output_field=DecimalField()),
        avg_delay=Coalesce(Avg("delay_days", filter=Q(is_on_time=False)), 0, output_field=IntegerField()),
        total_distance=Coalesce(Sum("total_distance"), 0.0, output_field=FloatField()),
        completed_pods=Count("id", filter=Q(pod_status__iexact="c")),
    )

    total = stats["total"] or 0
    on_time = stats["on_time"] or 0
    delayed = stats["delayed"] or 0
    completed_pods = stats["completed_pods"] or 0

    # Advanced Data Science Metrics
    revenue_at_risk = qs.filter(is_on_time=False).aggregate(rev=Sum("revenue"))["rev"] or Decimal("0")
    
    delays_list = list(qs.filter(is_on_time=False).values_list("delay_days", flat=True))
    if delays_list and len(delays_list) > 1:
        avg_d = sum(delays_list) / len(delays_list)
        variance = sum((x - avg_d) ** 2 for x in delays_list) / len(delays_list)
        volatility = round(variance ** 0.5, 2)
    else:
        volatility = 0.0

    return {
        "total_shipments": total,
        "on_time_count": on_time,
        "on_time_percentage": round((on_time / total) * 100, 2) if total > 0 else 0.0,
        "delayed_count": delayed,
        "delayed_percentage": round((delayed / total) * 100, 2) if total > 0 else 0.0,
        "total_revenue": float(stats["total_revenue"]),
        "average_revenue": round(float(stats["avg_revenue"]), 2),
        "average_delay_days": round(float(stats["avg_delay"]), 1),
        "total_distance": round(float(stats["total_distance"]), 1),
        "pod_compliance": round((completed_pods / total) * 100, 1) if total > 0 else 0.0,
        "revenue_at_risk": float(revenue_at_risk),
        "delay_volatility": volatility,
        "delay_distribution": get_delay_distribution(qs),
    }


def get_delay_distribution(qs=None):
    """
    Returns delay counts grouped by ranges: 1-2, 3-4, 5-7, 8+ days.
    """
    if qs is None:
        qs = Shipment.objects.all()

    stats = qs.filter(is_on_time=False).aggregate(
        range_1_2=Count("id", filter=Q(delay_days__gte=1, delay_days__lte=2)),
        range_3_4=Count("id", filter=Q(delay_days__gte=3, delay_days__lte=4)),
        range_5_7=Count("id", filter=Q(delay_days__gte=5, delay_days__lte=7)),
        range_8_plus=Count("id", filter=Q(delay_days__gt=7)),
    )

    return [
        {"range": "1-2 Days", "count": stats["range_1_2"] or 0, "filter": "delayed_1_2"},
        {"range": "3-4 Days", "count": stats["range_3_4"] or 0, "filter": "delayed_3_4"},
        {"range": "5-7 Days", "count": stats["range_5_7"] or 0, "filter": "delayed_5_7"},
        {"range": "7+ Days", "count": stats["range_8_plus"] or 0, "filter": "delayed_8_plus"},
    ]


def get_full_root_cause(qs=None):
    """
    Returns detailed breakdown of delays and issues by various dimensions.
    """
    if qs is None:
        qs = Shipment.objects.all()

    # 1. By Route
    by_route = list(
        qs.values("route__origin", "route__destination")
        .annotate(
            delayed_count=Count("id", filter=Q(is_on_time=False)),
            avg_delay=Avg("delay_days", filter=Q(is_on_time=False))
        )
        .order_by("-delayed_count")[:10]
    )

    # 2. By Vehicle
    by_vehicle = list(
        qs.values("vehicle_type")
        .annotate(
            delayed_count=Count("id", filter=Q(is_on_time=False)),
            avg_delay=Avg("delay_days", filter=Q(is_on_time=False))
        )
        .order_by("-delayed_count")[:10]
    )

    # 3. By Month
    by_month = list(
        qs.annotate(month=TruncMonth("dispatch_date"))
        .values("month")
        .annotate(
            delayed_count=Count("id", filter=Q(is_on_time=False)),
            total_shipments=Count("id")
        )
        .order_by("month")
    )

    # 4. By Transporter / Contractor
    by_contractor = list(
        qs.exclude(transporter_name='').values("transporter_name")
        .annotate(
            total_shipments=Count("id"),
            delayed_count=Count("id", filter=Q(is_on_time=False)),
            avg_delay=Avg("delay_days", filter=Q(is_on_time=False)),
            shortage_count=Count("id", filter=Q(has_shortage=True)),
            penalty_count=Count("id", filter=Q(has_penalty=True))
        )
        .order_by("-delayed_count")[:10]
    )

    # Aggregates for shortages/penalties
    shortage_stats = qs.aggregate(
        total_shortage=Sum("shortage_mt"),
        shortage_count=Count("id", filter=Q(has_shortage=True))
    )
    penalty_stats = qs.aggregate(
        total_penalty=Sum("penalty_amount"),
        penalty_count=Count("id", filter=Q(has_penalty=True))
    )

    return {
        "by_route": by_route,
        "by_vehicle": by_vehicle,
        "by_month": by_month,
        "by_contractor": by_contractor,
        "shortages": {
            "total_shortage_mt": float(shortage_stats["total_shortage"] or 0),
            "total_incidents": shortage_stats["shortage_count"] or 0
        },
        "penalties": {
            "total_penalty_amount": float(penalty_stats["total_penalty"] or 0),
            "total_incidents": penalty_stats["penalty_count"] or 0
        }
    }


def get_revenue_trends(qs=None, group_by="day"):
    """
    Revenue aggregated by time period.
    group_by: 'day', 'week', or 'month'
    Uses dispatch_date directly for 'day' (SQLite-compatible).
    """
    if qs is None:
        qs = Shipment.objects.all()

    if group_by == "day":
        # dispatch_date is already a DateField — just group by it directly
        results = list(
            qs.values("dispatch_date")
            .annotate(
                total_revenue=Sum("revenue"),
                shipment_count=Count("id"),
            )
            .order_by("dispatch_date")
        )
        # Rename key to 'period' for consistent API response
        for r in results:
            r["period"] = r.pop("dispatch_date")
        return results
    elif group_by == "month":
        # Use TruncMonth for month grouping (works on DateField)
        return list(
            qs.annotate(period=TruncMonth("dispatch_date"))
            .values("period")
            .annotate(
                total_revenue=Sum("revenue"),
                shipment_count=Count("id"),
            )
            .order_by("period")
        )
    else:
        # For week, fall back to day-level grouping (safest for SQLite)
        results = list(
            qs.values("dispatch_date")
            .annotate(
                total_revenue=Sum("revenue"),
                shipment_count=Count("id"),
            )
            .order_by("dispatch_date")
        )
        for r in results:
            r["period"] = r.pop("dispatch_date")
        return results


def get_top_routes(qs=None, limit=10):
    """
    Top N routes by shipment count.
    Returns route info with shipment count, on-time %, and total revenue.
    """
    if qs is None:
        qs = Shipment.objects.all()

    return list(
        qs.values(
            "route__id",
            "route__origin",
            "route__destination",
        )
        .annotate(
            shipment_count=Count("id"),
            on_time_count=Count("id", filter=Q(is_on_time=True)),
            delayed_count=Count("id", filter=Q(is_on_time=False)),
            total_revenue=Sum("revenue"),
        )
        .order_by("-shipment_count")[:limit]
    )


def get_delayed_shipments(qs=None):
    """Return queryset of delayed shipments, ordered by worst delay first."""
    if qs is None:
        qs = Shipment.objects.all()

    return (
        qs.filter(is_on_time=False)
        .select_related("route")
        .order_by("-delay_days")
    )


def generate_insights(qs=None):
    """
    Auto-generate human-readable insights from the data.
    Returns a list of insight strings.
    """
    if qs is None:
        qs = Shipment.objects.all()

    insights = []
    total = qs.count()
    if total == 0:
        return ["No shipment data available for analysis."]

    # --- Insight 1: Route with highest delays ---
    worst_route = (
        qs.filter(is_on_time=False)
        .values("route__origin", "route__destination")
        .annotate(
            delay_count=Count("id"),
            avg_delay=Avg("delay_days"),
        )
        .order_by("-delay_count")
        .first()
    )
    if worst_route:
        insights.append(
            f"Route {worst_route['route__origin']} → {worst_route['route__destination']} "
            f"has the highest delays ({worst_route['delay_count']} delayed shipments, "
            f"avg {worst_route['avg_delay']:.1f} days late)."
        )

    # --- Insight 2: Overall delivery performance ---
    summary = get_summary_kpis(qs)
    if summary["on_time_percentage"] >= 90:
        insights.append(
            f"Excellent delivery performance: {summary['on_time_percentage']}% of shipments delivered on time."
        )
    elif summary["on_time_percentage"] >= 70:
        insights.append(
            f"Delivery performance is moderate: {summary['on_time_percentage']}% on-time. "
            f"Consider investigating routes with recurring delays."
        )
    else:
        insights.append(
            f"⚠️ Delivery performance needs attention: only {summary['on_time_percentage']}% on-time. "
            f"{summary['delayed_count']} shipments were delayed."
        )

    # --- Insight 3: Last 7 days vs previous 7 days ---
    now = timezone.now().date()
    last_7 = qs.filter(dispatch_date__gte=now - timedelta(days=7))
    prev_7 = qs.filter(
        dispatch_date__gte=now - timedelta(days=14),
        dispatch_date__lt=now - timedelta(days=7),
    )
    last_7_count = last_7.count()
    prev_7_count = prev_7.count()

    if prev_7_count > 0 and last_7_count > 0:
        last_7_ontime = last_7.filter(is_on_time=True).count()
        prev_7_ontime = prev_7.filter(is_on_time=True).count()
        last_pct = round((last_7_ontime / last_7_count) * 100, 1)
        prev_pct = round((prev_7_ontime / prev_7_count) * 100, 1)
        diff = last_pct - prev_pct

        if diff < -5:
            insights.append(
                f"📉 Delivery performance dropped in the last 7 days: "
                f"{last_pct}% on-time vs {prev_pct}% in the prior week ({diff:+.1f}%)."
            )
        elif diff > 5:
            insights.append(
                f"📈 Delivery performance improved in the last 7 days: "
                f"{last_pct}% on-time vs {prev_pct}% in the prior week ({diff:+.1f}%)."
            )

    # --- Insight 4: Top revenue route ---
    top_revenue = (
        qs.values("route__origin", "route__destination")
        .annotate(total_revenue=Sum("revenue"))
        .order_by("-total_revenue")
        .first()
    )
    if top_revenue and top_revenue["total_revenue"]:
        insights.append(
            f"Highest revenue route: {top_revenue['route__origin']} → {top_revenue['route__destination']} "
            f"(₹{top_revenue['total_revenue']:,.2f})."
        )

    # --- Insight 5: Vehicle type with most delays ---
    worst_vehicle = (
        qs.filter(is_on_time=False)
        .values("vehicle_type")
        .annotate(delay_count=Count("id"))
        .order_by("-delay_count")
        .first()
    )
    if worst_vehicle:
        insights.append(
            f"Vehicle type '{worst_vehicle['vehicle_type']}' has the most delays "
            f"({worst_vehicle['delay_count']} delayed shipments)."
        )

    return insights

def get_transporter_performance(qs=None, limit=5):
    """
    Top N transporters by shipment count.
    Used for a simple bar chart.
    """
    if qs is None:
        qs = Shipment.objects.all()

    return list(
        qs.exclude(transporter_name='')
        .values("transporter_name")
        .annotate(shipment_count=Count("id"))
        .order_by("-shipment_count")[:limit]
    )
