"""
Operational Intelligence Engine
===============================
Generates actionable management alerts, transporter performance, route intelligence,
and SLA impact metrics based on historical shipment data.
"""

from decimal import Decimal
from django.db.models import Count, Sum, Avg, Q, F, DecimalField, IntegerField
from django.db.models.functions import Coalesce
from shipments.models import Shipment

def get_operational_intelligence(qs=None):
    if qs is None:
        qs = Shipment.objects.all()

    total_shipments = qs.count()
    if total_shipments == 0:
        return {"error": "No shipments available for analysis."}

    # 1. Section: Transporter Performance
    transporters_qs = (
        qs.exclude(transporter_name="")
        .values("transporter_name")
        .annotate(
            total_shipments=Count("id"),
            delayed=Count("id", filter=Q(is_on_time=False)),
            avg_delay=Coalesce(Avg("delay_days", filter=Q(is_on_time=False)), 0, output_field=IntegerField())
        )
        .filter(total_shipments__gt=0)
    )

    transporters = []
    for t in transporters_qs:
        delay_pct = round((t["delayed"] / t["total_shipments"]) * 100, 1)
        transporters.append({
            "transporter_name": t["transporter_name"],
            "total_shipments": t["total_shipments"],
            "delayed_shipments": t["delayed"],
            "delay_pct": delay_pct,
            "avg_delay_days": t["avg_delay"],
        })
    transporters = sorted(transporters, key=lambda x: -x["delay_pct"])

    # 2. Section: Route Intelligence
    routes_qs = (
        qs.values("route__origin", "route__destination")
        .annotate(
            total_shipments=Count("id"),
            delayed=Count("id", filter=Q(is_on_time=False)),
            total_revenue=Coalesce(Sum("revenue"), Decimal("0"), output_field=DecimalField()),
            avg_transit=Coalesce(Avg("transit_taken"), 0, output_field=IntegerField())
        )
        .filter(total_shipments__gt=0)
    )
    
    routes = []
    for r in routes_qs:
        delay_pct = round((r["delayed"] / r["total_shipments"]) * 100, 1)
        name = f"{r['route__origin']} → {r['route__destination']}"
        routes.append({
            "route_name": name,
            "origin": r["route__origin"],
            "destination": r["route__destination"],
            "total_shipments": r["total_shipments"],
            "delayed_shipments": r["delayed"],
            "delay_pct": delay_pct,
            "avg_transit_days": r["avg_transit"],
            "total_revenue": float(r["total_revenue"]),
        })
    
    # Best and Worst routes
    # Worst: highest delay among routes with at least 3 shipments
    # Best: lowest delay among routes with at least 3 shipments
    freq_routes = [r for r in routes if r["total_shipments"] >= 3]
    if not freq_routes:
        freq_routes = routes # fallback
    
    worst_route = max(freq_routes, key=lambda x: x["delay_pct"]) if freq_routes else None
    best_route = min(freq_routes, key=lambda x: x["delay_pct"]) if freq_routes else None

    # 3. Section: Management Alerts
    alerts = []

    # A. High Risk Routes
    high_risk_routes = [r for r in routes if r["delay_pct"] >= 40 and r["total_shipments"] >= 2]
    high_risk_routes = sorted(high_risk_routes, key=lambda x: -x["delay_pct"])[:5]
    if high_risk_routes:
        for hr in high_risk_routes:
            alerts.append({
                "type": "high_risk_route",
                "level": "red",
                "title": f"Live Risk: {hr['route_name']}",
                "insight": f"{hr['route_name']} has {hr['delay_pct']}% delay rate across {hr['total_shipments']} shipments.",
                "recommendation": "👉 Consider re-allocating to a different transporter or route line."
            })

    # B. Worst Transporter
    if transporters and transporters[0]["delay_pct"] > 0:
        worst_t = transporters[0]
        alerts.append({
            "type": "worst_transporter",
            "level": "red" if worst_t["delay_pct"] > 30 else "yellow",
            "title": f"Transporter Alert: {worst_t['transporter_name']}",
            "insight": f"Transporter {worst_t['transporter_name']} has {worst_t['delay_pct']}% delay rate (highest this period).",
            "recommendation": "👉 Review contracts or issue performance warning."
        })

    # C. Revenue Leakage
    leakage_qs = qs.exclude(billing_status__icontains="billed").filter(has_penalty=True).aggregate(
        total=Coalesce(Sum("penalty"), Decimal("0"), output_field=DecimalField()),
        count=Count("id")
    )
    # Another metric: Total outstanding or deduced
    short_rev = qs.aggregate(
        deducted=Coalesce(Sum(F("total_amount") - F("revenue")), Decimal("0"), output_field=DecimalField())
    )
    leakage_val = float(short_rev["deducted"])
    if leakage_val > 0:
        alerts.append({
            "type": "revenue_leakage",
            "level": "yellow",
            "title": "Revenue Leakage Alert",
            "insight": f"💸 ₹{leakage_val:,.2f} lost to deductions and SLA penalties this period.",
            "recommendation": "👉 Streamline delivery handover to minimize penalty deductions."
        })

    # D. POD Compliance Issues
    # Check for shipments that should have POD but pod_status is empty or 'not uploaded'
    # For actual historical data, we check shipments where delivery_date is not null but pod_status is missing.
    pod_missing = qs.filter(delivery_date__isnull=False).filter(Q(pod_status="") | Q(pod_status__isnull=True)).count()
    if pod_missing > 0:
        alerts.append({
            "type": "pod_compliance",
            "level": "yellow",
            "title": "POD Compliance Missing",
            "insight": f"📄 {pod_missing} shipments are marked delivered but missing POD document.",
            "recommendation": "👉 Follow up with branch managers/drivers to upload POD immediately."
        })

    # E. Repeated Failure Routes
    repeated = [r for r in routes if r["delayed_shipments"] >= 4 and r["total_shipments"] >= 5]
    for rr in repeated[:3]:
        alerts.append({
            "type": "repeated_failure",
            "level": "red",
            "title": f"Consistent Delay: {rr['route_name']}",
            "insight": f"🔁 {rr['route_name']} was delayed in {rr['delayed_shipments']} out of {rr['total_shipments']} recent trips.",
            "recommendation": "👉 Operational intervention required on this corridor."
        })

    # 4. Section: Billing & SLA Impact
    total_delayed = qs.filter(is_on_time=False).count()
    sla_breach_pct = round((total_delayed / total_shipments) * 100, 1) if total_shipments else 0
    sla_stats = qs.aggregate(
        total_billed=Coalesce(Sum("revenue"), Decimal("0"), output_field=DecimalField()),
        revenue_at_risk=Coalesce(Sum("revenue", filter=Q(is_on_time=False)), Decimal("0"), output_field=DecimalField()),
    )

    billing_sla = {
        "total_billed_freight": float(sla_stats["total_billed"]),
        "revenue_at_risk": float(sla_stats["revenue_at_risk"]),
        "sla_breach_pct": sla_breach_pct
    }

    return {
        "alerts": alerts,
        "transporters": transporters,
        "routes": routes,
        "best_route": best_route,
        "worst_route": worst_route,
        "billing_sla": billing_sla
    }
