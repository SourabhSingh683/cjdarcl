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
            revenue_at_risk=Coalesce(Sum("revenue", filter=Q(is_on_time=False)), Decimal("0"), output_field=DecimalField()),
            avg_delay=Coalesce(Avg("delay_days", filter=Q(is_on_time=False)), 0, output_field=IntegerField()),
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
            "avg_delay_days": r["avg_delay"],
            "total_revenue": float(r["total_revenue"]),
            "revenue_at_risk": float(r["revenue_at_risk"]),
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

    # A. High Risk Routes & Grouping for 100% Delays
    # User requested: "alerts only if total shipments > 10 and delays > 80%"
    # AND grouping 100% delay routes into one card.
    
    valid_routes = [r for r in routes if r["total_shipments"] > 10]
    
    # 100% Delay Individually
    critical_routes = [r for r in valid_routes if r["delay_pct"] >= 100.0]
    for cr in critical_routes:
        alerts.append({
            "type": "absolute_risk_route",
            "level": "red",
            "title": f"Absolute Risk: {cr['route_name']}",
            "insight": f"🚨 Critical Failure: Every single shipment from {cr['origin']} to {cr['destination']} was delayed.",
            "metrics": {
                "Revenue at Risk": f"₹{cr['revenue_at_risk']:,.2f}",
                "Volume": f"{cr['total_shipments']} shipments",
                "Avg Delay": f"{cr['avg_delay_days']} days"
            },
            "recommendation": "👉 IMMEDIATE AUDIT REQUIRED. Analyze carrier assignments and corridor constraints immediately."
        })

    # High Risk Routes (other than 100%)
    high_risk_routes = [r for r in valid_routes if 80.0 < r["delay_pct"] < 100.0]
    high_risk_routes = sorted(high_risk_routes, key=lambda x: -x["delay_pct"])[:5]
    if high_risk_routes:
        for hr in high_risk_routes:
            alerts.append({
                "type": "high_risk_route",
                "level": "red",
                "title": f"Live Risk: {hr['route_name']}",
                "insight": f"{hr['route_name']} has {hr['delay_pct']}% delay rate across {hr['total_shipments']} shipments.",
                "metrics": {
                    "Revenue at Risk": f"₹{hr['revenue_at_risk']:,.2f}",
                    "Avg Delay": f"{hr['avg_delay_days']} days",
                    "Success Rate": f"{100 - hr['delay_pct']}%"
                },
                "recommendation": "👉 Check with driver to be punctual and analyze route conditions."
            })

    # B. Worst Transporter
    significant_transporters = [t for t in transporters if t["total_shipments"] > 10]
    if significant_transporters and significant_transporters[0]["delay_pct"] > 80:
        worst_t = significant_transporters[0]
        # Calculate revenue at risk for this transporter
        t_risk = qs.filter(transporter_name=worst_t["transporter_name"], is_on_time=False).aggregate(
            risk=Coalesce(Sum("revenue"), Decimal("0"), output_field=DecimalField())
        )["risk"]
        alerts.append({
            "type": "worst_transporter",
            "level": "red",
            "title": f"Transporter Alert: {worst_t['transporter_name']}",
            "insight": f"Transporter {worst_t['transporter_name']} has {worst_t['delay_pct']}% delay rate (highest this period).",
            "metrics": {
                "Revenue at Risk": f"₹{float(t_risk):,.2f}",
                "Avg Delay": f"{worst_t['avg_delay_days']} days",
                "Volume": f"{worst_t['total_shipments']} shipments"
            },
            "recommendation": "👉 Advise driver on punctuality and review transporter route management."
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
    repeated = [r for r in valid_routes if r["delay_pct"] > 80.0]
    for rr in repeated[:3]:
        if rr["delay_pct"] >= 100.0: continue
        
        alerts.append({
            "type": "repeated_failure",
            "level": "red",
            "title": f"Consistent Delay: {rr['route_name']}",
            "insight": f"🔁 {rr['route_name']} was delayed in {rr['delayed_shipments']} out of {rr['total_shipments']} recent trips ({rr['delay_pct']}%).",
            "metrics": {
                "Revenue at Risk": f"₹{rr['revenue_at_risk']:,.2f}",
                "Avg Delay": f"{rr['avg_delay_days']} days"
            },
            "recommendation": "👉 Brief drivers on punctuality and audit corridor for avoidable delays."
        })

    # 4. Section: Billing & SLA Impact
    total_delayed = qs.filter(is_on_time=False).count()
    sla_breach_pct = round((total_delayed / total_shipments) * 100, 1) if total_shipments else 0
    sla_stats = qs.aggregate(
        total_billed=Coalesce(Sum("revenue"), Decimal("0"), output_field=DecimalField()),
        revenue_at_risk=Coalesce(Sum("revenue", filter=Q(is_on_time=False)), Decimal("0"), output_field=DecimalField()),
    )

    # Risk Breakdown: Top 3 Routes by Revenue-at-Risk
    risk_routes_qs = (
        qs.filter(is_on_time=False)
        .values("route__origin", "route__destination")
        .annotate(risk_value=Sum("revenue"))
        .order_by("-risk_value")[:3]
    )
    risk_breakdown_routes = [
        {"name": f"{r['route__origin']} → {r['route__destination']}", "value": float(r["risk_value"] or 0)} 
        for r in risk_routes_qs
    ]

    # Risk Breakdown: Top 3 Transporters by Revenue-at-Risk
    risk_trans_qs = (
        qs.filter(is_on_time=False)
        .exclude(transporter_name="")
        .values("transporter_name")
        .annotate(risk_value=Sum("revenue"))
        .order_by("-risk_value")[:3]
    )
    risk_breakdown_transporters = [
        {"name": t["transporter_name"], "value": float(t["risk_value"] or 0)} 
        for t in risk_trans_qs
    ]

    billing_sla = {
        "total_billed_freight": float(sla_stats["total_billed"]),
        "revenue_at_risk": float(sla_stats["revenue_at_risk"]),
        "sla_breach_pct": sla_breach_pct,
        "risk_breakdown_routes": risk_breakdown_routes,
        "risk_breakdown_transporters": risk_breakdown_transporters,
    }

    return {
        "alerts": alerts,
        "transporters": transporters,
        "routes": routes,
        "best_route": best_route,
        "worst_route": worst_route,
        "billing_sla": billing_sla
    }
