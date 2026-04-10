"""
Profit Analytics Engine
=======================
Generates profit KPIs, lane classification, trend analysis,
smart alerts, comparison, drill-down, and decision support insights.
"""

from decimal import Decimal
from collections import defaultdict
from django.db.models import Count, Sum, Avg, Q, F, DecimalField, FloatField, Min, Max
from django.db.models.functions import Coalesce, TruncMonth
from shipments.models import ProfitRecord


def _safe_float(val):
    if val is None:
        return 0.0
    return float(val)


def get_profit_summary(qs=None):
    """Top-level KPIs for the profit dashboard."""
    if qs is None:
        qs = ProfitRecord.objects.all()

    total = qs.count()
    if total == 0:
        return {"error": "No profit records available."}

    agg = qs.aggregate(
        total_freight=Coalesce(Sum("freight"), Decimal("0"), output_field=DecimalField()),
        total_lorry_hire=Coalesce(Sum("lorry_hire"), Decimal("0"), output_field=DecimalField()),
        total_lorry_topf=Coalesce(Sum("lorry_hire_topf"), Decimal("0"), output_field=DecimalField()),
        total_fleet_freight=Coalesce(Sum("fleet_freight"), Decimal("0"), output_field=DecimalField()),
        total_own_fleet=Coalesce(Sum("own_fleet_exp"), Decimal("0"), output_field=DecimalField()),
        total_rake=Coalesce(Sum("rake_exp"), Decimal("0"), output_field=DecimalField()),
        total_extra_lorry=Coalesce(Sum("extra_lorry_hire"), Decimal("0"), output_field=DecimalField()),
        total_transhipment=Coalesce(Sum("transhipment_cost"), Decimal("0"), output_field=DecimalField()),
        total_gm1=Coalesce(Sum("gm1"), Decimal("0"), output_field=DecimalField()),
        total_gm7=Coalesce(Sum("gm7"), Decimal("0"), output_field=DecimalField()),
        total_weight=Coalesce(Sum("charge_weight"), Decimal("0"), output_field=DecimalField()),
        total_deductions=Coalesce(Sum("freight_deduction"), Decimal("0"), output_field=DecimalField()),
    )

    freight = _safe_float(agg["total_freight"])
    cost = (
        _safe_float(agg["total_lorry_hire"]) + _safe_float(agg["total_lorry_topf"]) +
        _safe_float(agg["total_fleet_freight"]) + _safe_float(agg["total_own_fleet"]) +
        _safe_float(agg["total_rake"]) + _safe_float(agg["total_extra_lorry"]) +
        _safe_float(agg["total_transhipment"])
    )
    profit_gm1 = _safe_float(agg["total_gm1"])
    weight = _safe_float(agg["total_weight"])
    margin_pct = (profit_gm1 / freight * 100) if freight > 0 else 0
    profit_per_tonne = (profit_gm1 / weight) if weight > 0 else 0

    return {
        "total_records": total,
        "total_freight": round(freight, 2),
        "total_cost": round(cost, 2),
        "total_profit": round(profit_gm1, 2),
        "final_profit_gm7": round(_safe_float(agg["total_gm7"]), 2),
        "total_weight": round(weight, 2),
        "avg_profit_per_tonne": round(profit_per_tonne, 2),
        "overall_margin_pct": round(margin_pct, 2),
        "total_deductions": round(_safe_float(agg["total_deductions"]), 2),
    }


def get_lane_classification(qs=None):
    """Classify each route/lane into Good, Low Margin, Bad, Abnormal Loss, Abnormal Profit."""
    if qs is None:
        qs = ProfitRecord.objects.all()

    lanes_qs = (
        qs.values("loading_city", "delivery_city")
        .annotate(
            total_shipments=Count("id"),
            total_freight=Coalesce(Sum("freight"), Decimal("0"), output_field=DecimalField()),
            total_cost=Coalesce(
                Sum("lorry_hire") + Sum("lorry_hire_topf") + Sum("fleet_freight") +
                Sum("own_fleet_exp") + Sum("rake_exp") + Sum("extra_lorry_hire") +
                Sum("transhipment_cost"),
                Decimal("0"), output_field=DecimalField()
            ),
            total_gm1=Coalesce(Sum("gm1"), Decimal("0"), output_field=DecimalField()),
            total_gm7=Coalesce(Sum("gm7"), Decimal("0"), output_field=DecimalField()),
            total_weight=Coalesce(Sum("charge_weight"), Decimal("0"), output_field=DecimalField()),
            total_deductions=Coalesce(Sum("freight_deduction"), Decimal("0"), output_field=DecimalField()),
            avg_gm1_pct=Coalesce(Avg("gm1_pct"), 0, output_field=FloatField()),
        )
        .filter(total_shipments__gte=1)
        .order_by("-total_freight")
    )

    # Compute overall avg margin for anomaly detection
    all_margins = [_safe_float(l["avg_gm1_pct"]) for l in lanes_qs]
    avg_margin = sum(all_margins) / len(all_margins) if all_margins else 0
    margin_std = (sum((m - avg_margin) ** 2 for m in all_margins) / len(all_margins)) ** 0.5 if len(all_margins) > 1 else 5

    lanes = []
    for l in lanes_qs:
        freight = _safe_float(l["total_freight"])
        cost = _safe_float(l["total_cost"])
        gm1 = _safe_float(l["total_gm1"])
        weight = _safe_float(l["total_weight"])
        margin = _safe_float(l["avg_gm1_pct"])
        deductions = _safe_float(l["total_deductions"])
        cost_per_tonne = cost / weight if weight > 0 else 0
        profit_per_tonne = gm1 / weight if weight > 0 else 0

        # Classification logic
        if margin < 0 and abs(margin - avg_margin) > 2 * margin_std:
            category = "abnormal_loss"
        elif margin > 0 and (margin - avg_margin) > 2 * margin_std:
            category = "abnormal_profit"
        elif margin < 0 or gm1 < 0:
            category = "bad"
        elif margin < 3:
            category = "low_margin"
        else:
            category = "good"

        lanes.append({
            "lane_name": f"{l['loading_city']} → {l['delivery_city']}",
            "loading_city": l["loading_city"],
            "delivery_city": l["delivery_city"],
            "total_shipments": l["total_shipments"],
            "total_freight": round(freight, 2),
            "total_cost": round(cost, 2),
            "total_profit": round(gm1, 2),
            "total_weight": round(weight, 2),
            "margin_pct": round(margin, 2),
            "cost_per_tonne": round(cost_per_tonne, 2),
            "profit_per_tonne": round(profit_per_tonne, 2),
            "total_deductions": round(deductions, 2),
            "category": category,
        })

    return {
        "lanes": lanes,
        "summary": {
            "good": len([l for l in lanes if l["category"] == "good"]),
            "low_margin": len([l for l in lanes if l["category"] == "low_margin"]),
            "bad": len([l for l in lanes if l["category"] == "bad"]),
            "abnormal_loss": len([l for l in lanes if l["category"] == "abnormal_loss"]),
            "abnormal_profit": len([l for l in lanes if l["category"] == "abnormal_profit"]),
        }
    }


def get_lane_trends(qs=None):
    """Monthly cost-per-tonne trend for each lane."""
    if qs is None:
        qs = ProfitRecord.objects.all()

    trends_qs = (
        qs.annotate(month=TruncMonth("cn_date"))
        .values("loading_city", "delivery_city", "month")
        .annotate(
            total_cost=Coalesce(
                Sum("lorry_hire") + Sum("lorry_hire_topf") + Sum("fleet_freight") +
                Sum("own_fleet_exp") + Sum("rake_exp") + Sum("extra_lorry_hire") + Sum("transhipment_cost"),
                Decimal("0"), output_field=DecimalField()
            ),
            total_weight=Coalesce(Sum("charge_weight"), Decimal("0"), output_field=DecimalField()),
            total_freight=Coalesce(Sum("freight"), Decimal("0"), output_field=DecimalField()),
            total_gm1=Coalesce(Sum("gm1"), Decimal("0"), output_field=DecimalField()),
            shipments=Count("id"),
        )
        .order_by("loading_city", "delivery_city", "month")
    )

    lane_trends = defaultdict(list)
    for t in trends_qs:
        lane = f"{t['loading_city']} → {t['delivery_city']}"
        weight = _safe_float(t["total_weight"])
        cost_per_tonne = _safe_float(t["total_cost"]) / weight if weight > 0 else 0
        lane_trends[lane].append({
            "month": t["month"].strftime("%Y-%m") if t["month"] else "",
            "cost_per_tonne": round(cost_per_tonne, 2),
            "freight": round(_safe_float(t["total_freight"]), 2),
            "profit": round(_safe_float(t["total_gm1"]), 2),
            "shipments": t["shipments"],
        })

    # Add trend insights
    result = []
    for lane, data in lane_trends.items():
        if len(data) < 2:
            trend_dir = "stable"
            pct_change = 0
        else:
            first_cpt = data[0]["cost_per_tonne"]
            last_cpt = data[-1]["cost_per_tonne"]
            pct_change = ((last_cpt - first_cpt) / first_cpt * 100) if first_cpt > 0 else 0

            # Check for consistent increase
            increasing = all(data[i]["cost_per_tonne"] <= data[i + 1]["cost_per_tonne"] for i in range(len(data) - 1))
            decreasing = all(data[i]["cost_per_tonne"] >= data[i + 1]["cost_per_tonne"] for i in range(len(data) - 1))

            if increasing and pct_change > 5:
                trend_dir = "increasing"
            elif decreasing and pct_change < -5:
                trend_dir = "decreasing"
            else:
                trend_dir = "stable"

        result.append({
            "lane_name": lane,
            "data": data,
            "trend": trend_dir,
            "pct_change": round(pct_change, 2),
        })

    return result


def get_profit_alerts(qs=None):
    """Generate smart profitability alerts."""
    if qs is None:
        qs = ProfitRecord.objects.all()

    alerts = []
    classification = get_lane_classification(qs)
    trends = get_lane_trends(qs)

    # 1. Cost increase alerts
    for t in trends:
        if t["trend"] == "increasing" and t["pct_change"] > 8:
            alerts.append({
                "type": "cost_increase",
                "level": "red",
                "title": f"🔴 High Cost Increase: {t['lane_name']}",
                "insight": f"Cost per tonne has increased by {t['pct_change']}% over the period with a consistent upward trend.",
                "recommendation": "👉 Investigate fuel costs, renegotiate transporter rates, or explore alternate carriers."
            })

    # 2. Loss alerts
    for lane in classification["lanes"]:
        if lane["category"] == "bad":
            alerts.append({
                "type": "loss",
                "level": "red",
                "title": f"🚨 Loss Alert: {lane['lane_name']}",
                "insight": f"This lane has a negative margin of {lane['margin_pct']}% across {lane['total_shipments']} shipments.",
                "recommendation": "👉 Consider suspending operations or renegotiating freight rates for this corridor."
            })
        elif lane["category"] == "abnormal_loss":
            alerts.append({
                "type": "abnormal_loss",
                "level": "red",
                "title": f"🚨 Abnormal Loss: {lane['lane_name']}",
                "insight": f"This lane shows unusually high losses (margin: {lane['margin_pct']}%). Possible issue: unexpected cost spike or high deductions.",
                "recommendation": "👉 Immediate audit required. Check for pricing anomalies or vendor overcharging."
            })

    # 3. High deduction alerts
    for lane in classification["lanes"]:
        if lane["total_freight"] > 0:
            ded_ratio = abs(lane["total_deductions"]) / lane["total_freight"] * 100
            if ded_ratio > 10:
                alerts.append({
                    "type": "high_deduction",
                    "level": "yellow",
                    "title": f"⚠️ High Deduction: {lane['lane_name']}",
                    "insight": f"Freight deductions represent {ded_ratio:.1f}% of total freight on this lane.",
                    "recommendation": "👉 Review deduction reasons — late delivery penalties, weight discrepancies, or compliance issues."
                })

    # 4. High performance lanes
    for lane in classification["lanes"]:
        if lane["category"] == "good" and lane["margin_pct"] > 5 and lane["total_shipments"] >= 5:
            alerts.append({
                "type": "high_performance",
                "level": "green",
                "title": f"🟢 High Performance: {lane['lane_name']}",
                "insight": f"Consistently profitable lane with {lane['margin_pct']}% margin across {lane['total_shipments']} shipments.",
                "recommendation": "👉 Consider increasing volume on this corridor. This is a model lane."
            })

    # 5. Abnormal profit alerts
    for lane in classification["lanes"]:
        if lane["category"] == "abnormal_profit":
            alerts.append({
                "type": "abnormal_profit",
                "level": "purple",
                "title": f"🟣 Abnormal Profit: {lane['lane_name']}",
                "insight": f"This lane shows unusually high margins ({lane['margin_pct']}%). Could indicate a pricing anomaly or data issue.",
                "recommendation": "👉 Verify data accuracy and ensure pricing is sustainable."
            })

    return alerts


def get_lane_drilldown(qs=None, loading_city="", delivery_city=""):
    """Detailed margin waterfall for a specific lane."""
    if qs is None:
        qs = ProfitRecord.objects.all()

    lane_qs = qs.filter(loading_city=loading_city, delivery_city=delivery_city)
    count = lane_qs.count()
    if count == 0:
        return {"error": "No records for this lane."}

    agg = lane_qs.aggregate(
        freight=Coalesce(Sum("freight"), Decimal("0"), output_field=DecimalField()),
        lorry_hire=Coalesce(Sum("lorry_hire"), Decimal("0"), output_field=DecimalField()),
        lorry_hire_topf=Coalesce(Sum("lorry_hire_topf"), Decimal("0"), output_field=DecimalField()),
        fleet_freight=Coalesce(Sum("fleet_freight"), Decimal("0"), output_field=DecimalField()),
        own_fleet_exp=Coalesce(Sum("own_fleet_exp"), Decimal("0"), output_field=DecimalField()),
        rake_exp=Coalesce(Sum("rake_exp"), Decimal("0"), output_field=DecimalField()),
        freight_deduction=Coalesce(Sum("freight_deduction"), Decimal("0"), output_field=DecimalField()),
        extra_lorry_hire=Coalesce(Sum("extra_lorry_hire"), Decimal("0"), output_field=DecimalField()),
        transhipment_cost=Coalesce(Sum("transhipment_cost"), Decimal("0"), output_field=DecimalField()),
        gm1=Coalesce(Sum("gm1"), Decimal("0"), output_field=DecimalField()),
        freight_incentive=Coalesce(Sum("freight_incentive"), Decimal("0"), output_field=DecimalField()),
        labour=Coalesce(Sum("labour"), Decimal("0"), output_field=DecimalField()),
        wages=Coalesce(Sum("wages"), Decimal("0"), output_field=DecimalField()),
        insurance=Coalesce(Sum("insurance"), Decimal("0"), output_field=DecimalField()),
        other_direct_exp=Coalesce(Sum("other_direct_exp"), Decimal("0"), output_field=DecimalField()),
        gm2=Coalesce(Sum("gm2"), Decimal("0"), output_field=DecimalField()),
        gm3=Coalesce(Sum("gm3"), Decimal("0"), output_field=DecimalField()),
        claim=Coalesce(Sum("claim"), Decimal("0"), output_field=DecimalField()),
        detention=Coalesce(Sum("detention"), Decimal("0"), output_field=DecimalField()),
        gm4=Coalesce(Sum("gm4"), Decimal("0"), output_field=DecimalField()),
        interest=Coalesce(Sum("interest"), Decimal("0"), output_field=DecimalField()),
        gm5=Coalesce(Sum("gm5"), Decimal("0"), output_field=DecimalField()),
        gm6=Coalesce(Sum("gm6"), Decimal("0"), output_field=DecimalField()),
        gm7=Coalesce(Sum("gm7"), Decimal("0"), output_field=DecimalField()),
        weight=Coalesce(Sum("charge_weight"), Decimal("0"), output_field=DecimalField()),
    )

    def r(val):
        return round(_safe_float(val), 2)

    freight = r(agg["freight"])
    return {
        "lane_name": f"{loading_city} → {delivery_city}",
        "total_shipments": count,
        "total_weight": r(agg["weight"]),
        "waterfall": [
            {"label": "Freight (Revenue)", "value": freight, "type": "revenue"},
            {"label": "Lorry Hire", "value": -r(agg["lorry_hire"]), "type": "cost"},
            {"label": "Lorry Hire TOPF", "value": -r(agg["lorry_hire_topf"]), "type": "cost"},
            {"label": "Fleet Freight", "value": -r(agg["fleet_freight"]), "type": "cost"},
            {"label": "Own Fleet Exp", "value": -r(agg["own_fleet_exp"]), "type": "cost"},
            {"label": "Rake Exp", "value": -r(agg["rake_exp"]), "type": "cost"},
            {"label": "Extra Lorry Hire", "value": -r(agg["extra_lorry_hire"]), "type": "cost"},
            {"label": "Transhipment", "value": -r(agg["transhipment_cost"]), "type": "cost"},
            {"label": "GM1 (Gross Margin)", "value": r(agg["gm1"]), "type": "margin"},
            {"label": "Freight Deduction", "value": -r(agg["freight_deduction"]), "type": "deduction"},
            {"label": "Labour + Wages", "value": -(r(agg["labour"]) + r(agg["wages"])), "type": "cost"},
            {"label": "Insurance", "value": -r(agg["insurance"]), "type": "cost"},
            {"label": "GM2", "value": r(agg["gm2"]), "type": "margin"},
            {"label": "GM3", "value": r(agg["gm3"]), "type": "margin"},
            {"label": "Claims + Detention", "value": -(r(agg["claim"]) + r(agg["detention"])), "type": "deduction"},
            {"label": "GM4", "value": r(agg["gm4"]), "type": "margin"},
            {"label": "Interest", "value": -r(agg["interest"]), "type": "cost"},
            {"label": "GM5", "value": r(agg["gm5"]), "type": "margin"},
            {"label": "GM6", "value": r(agg["gm6"]), "type": "margin"},
            {"label": "GM7 (Final)", "value": r(agg["gm7"]), "type": "final"},
        ],
        "margin_pct": round((_safe_float(agg["gm1"]) / freight * 100) if freight > 0 else 0, 2),
    }


def generate_profit_insights(qs=None):
    """Generate human-readable insight strings with decision support."""
    if qs is None:
        qs = ProfitRecord.objects.all()

    insights = []
    classification = get_lane_classification(qs)
    trends = get_lane_trends(qs)

    # Cost trend insights
    for t in trends:
        if t["trend"] == "increasing" and t["pct_change"] > 5:
            insights.append({
                "type": "warning",
                "text": f"{t['lane_name']}: Cost per tonne has increased by ~{t['pct_change']}% over the period. Consistent upward trend observed.",
                "suggestion": "Consider renegotiating transporter rates or investigating fuel cost changes."
            })
        elif t["trend"] == "decreasing" and t["pct_change"] < -5:
            insights.append({
                "type": "success",
                "text": f"{t['lane_name']}: Cost per tonne has decreased by ~{abs(t['pct_change'])}%. Efficiency improving.",
                "suggestion": "Maintain current operations. This lane is optimizing well."
            })

    # Profitability insights
    bad_lanes = [l for l in classification["lanes"] if l["category"] in ("bad", "abnormal_loss")]
    if bad_lanes:
        total_loss = sum(l["total_profit"] for l in bad_lanes)
        insights.append({
            "type": "danger",
            "text": f"{len(bad_lanes)} lanes are operating at a loss, with total losses of ₹{abs(total_loss):,.2f}.",
            "suggestion": "Investigate reasons for increasing transport cost on these corridors. Check for inefficiencies in route planning."
        })

    good_lanes = [l for l in classification["lanes"] if l["category"] == "good"]
    if good_lanes:
        total_profit = sum(l["total_profit"] for l in good_lanes)
        insights.append({
            "type": "success",
            "text": f"{len(good_lanes)} lanes are performing well, generating ₹{total_profit:,.2f} in profit.",
            "suggestion": "Consider increasing volume allocation to these high-performing corridors."
        })

    # Deduction insights
    high_ded = [l for l in classification["lanes"] if l["total_freight"] > 0 and abs(l["total_deductions"]) / l["total_freight"] > 0.08]
    if high_ded:
        insights.append({
            "type": "warning",
            "text": f"{len(high_ded)} lanes have high freight deductions impacting profitability.",
            "suggestion": "High deductions are impacting profitability. Review SLA compliance and penalty clauses."
        })

    return insights
