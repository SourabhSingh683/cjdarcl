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
        # If the queryset is empty, we need to know if it's because of filters or because of no data.
        # But we don't have the unfiltered QS here easily. 
        # Better approach: the view should handle this, or we just return a clear flag.
        return {
            "total_records": 0,
            "no_results": True,
            "total_freight": 0,
            "total_cost": 0,
            "total_profit": 0,
            "final_profit_gm7": 0,
            "total_weight": 0,
            "overall_margin_pct": 0,
            "total_deductions": 0,
        }

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
    return {
        "total_records": total,
        "total_freight": round(freight, 2),
        "total_cost": round(cost, 2),
        "total_profit": round(profit_gm1, 2),
        "final_profit_gm7": round(_safe_float(agg["total_gm7"]), 2),
        "total_weight": round(weight, 2),
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

        # Classification logic (USER DEFINED Thresholds)
        if margin < 0:
            category = "bad"       # Loss Lane (<0%)
        elif margin < 3:
            category = "low_margin" # Low Margin (0-3%)
        elif margin <= 7:
            category = "average"    # Average Lane (3-7%)
        else:
            category = "good"       # Good Lane (>7%)

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
            "total_deductions": round(deductions, 2),
            "category": category,
        })

    # --- Compute cost-per-tonne change (first shipment → last shipment by date) per lane ---
    # For each lane, find the earliest and latest shipments by cn_date and compute
    # cost/tonne for each, then derive absolute change, percentage change, and trend label.

    # Get per-shipment cost/tonne ordered by date for each lane
    shipment_cpt_qs = (
        qs.filter(charge_weight__gt=0)
        .values("loading_city", "delivery_city", "cn_date")
        .annotate(
            s_cost=Coalesce(
                Sum("lorry_hire") + Sum("lorry_hire_topf") + Sum("fleet_freight") +
                Sum("own_fleet_exp") + Sum("rake_exp") + Sum("extra_lorry_hire") + Sum("transhipment_cost"),
                Decimal("0"), output_field=DecimalField()
            ),
            s_weight=Coalesce(Sum("charge_weight"), Decimal("0"), output_field=DecimalField()),
        )
        .order_by("loading_city", "delivery_city", "cn_date")
    )

    # Build ordered list of per-date CPT values per lane
    lane_cpt_data = {}  # key = (loading, delivery) -> list of (date, cpt)
    for s in shipment_cpt_qs:
        key = (s["loading_city"], s["delivery_city"])
        w = _safe_float(s["s_weight"])
        cpt = _safe_float(s["s_cost"]) / w if w > 0 else 0
        if cpt > 0:
            lane_cpt_data.setdefault(key, []).append((s["cn_date"], round(cpt, 2)))

    # Merge CPT insight fields into lanes
    for lane in lanes:
        key = (lane["loading_city"], lane["delivery_city"])
        cpt_entries = lane_cpt_data.get(key, [])
        if len(cpt_entries) >= 2 and cpt_entries[0][1] > 0:
            first_cpt = cpt_entries[0][1]
            last_cpt = cpt_entries[-1][1]
            abs_change = round(last_cpt - first_cpt, 2)
            pct_change = round((last_cpt - first_cpt) / first_cpt * 100, 2)
            abs_pct = abs(pct_change)
            trend_label = "Stable" if abs_pct <= 2 else ("Slight Change" if abs_pct <= 5 else "Significant Change")

            lane["first_cpt"] = first_cpt
            lane["last_cpt"] = last_cpt
            lane["cpt_abs_change"] = abs_change
            lane["cpt_pct_change"] = pct_change
            lane["cpt_trend_label"] = trend_label
        elif len(cpt_entries) == 1:
            lane["first_cpt"] = cpt_entries[0][1]
            lane["last_cpt"] = cpt_entries[0][1]
            lane["cpt_abs_change"] = 0
            lane["cpt_pct_change"] = 0
            lane["cpt_trend_label"] = "Stable"
        else:
            lane["first_cpt"] = 0
            lane["last_cpt"] = 0
            lane["cpt_abs_change"] = 0
            lane["cpt_pct_change"] = 0
            lane["cpt_trend_label"] = "Stable"

    return {
        "lanes": lanes,
        "summary": {
            "good": len([l for l in lanes if l["category"] == "good"]),
            "average": len([l for l in lanes if l["category"] == "average"]),
            "low_margin": len([l for l in lanes if l["category"] == "low_margin"]),
            "bad": len([l for l in lanes if l["category"] == "bad"]),
        }
    }


def get_lane_trends(qs=None):
    """Monthly cost-per-tonne trend for each lane.

    Implements full data validation, cleaning, anomaly detection,
    data quality scoring, and intelligent insight generation before
    producing chart-ready data.
    """
    if qs is None:
        qs = ProfitRecord.objects.all()

    total_records = qs.count()
    if total_records == 0:
        return {
            "trends": [],
            "data_quality": {"score": 0, "label": "critical", "total_rows": 0,
                             "valid_rows": 0, "excluded_rows": 0, "messages": []},
        }

    # ── Step 1: Data Validation — count how many rows have bad data ──
    invalid_weight = qs.filter(charge_weight__lte=0).count()
    zero_cost_and_freight = qs.filter(
        freight__lte=0,
        lorry_hire__lte=0, lorry_hire_topf__lte=0, fleet_freight__lte=0,
        own_fleet_exp__lte=0, rake_exp__lte=0, extra_lorry_hire__lte=0,
        transhipment_cost__lte=0,
    ).count()

    # Build a clean queryset — exclude rows where charge_weight is 0/null
    # and rows where BOTH cost and freight are zero
    clean_qs = qs.filter(charge_weight__gt=0).exclude(
        freight__lte=0,
        lorry_hire__lte=0, lorry_hire_topf__lte=0, fleet_freight__lte=0,
        own_fleet_exp__lte=0, rake_exp__lte=0, extra_lorry_hire__lte=0,
        transhipment_cost__lte=0,
    )
    valid_count = clean_qs.count()
    excluded_count = total_records - valid_count

    # ── Step 2: Data Quality Score ──
    quality_pct = round(valid_count / total_records * 100, 1) if total_records > 0 else 0
    if quality_pct > 90:
        q_label = "good"
    elif quality_pct >= 60:
        q_label = "warning"
    else:
        q_label = "critical"

    quality_messages = []
    if invalid_weight > 0:
        quality_messages.append(
            f"{invalid_weight} rows excluded — charge weight is zero or missing (would cause division errors)."
        )
    if zero_cost_and_freight > 0:
        quality_messages.append(
            f"{zero_cost_and_freight} rows excluded — both cost and freight are zero (no meaningful data)."
        )
    if excluded_count > 0:
        quality_messages.append(
            f"Using {valid_count} of {total_records} rows for trend analysis ({excluded_count} excluded)."
        )
    else:
        quality_messages.append(f"All {total_records} rows are valid and used for analysis.")

    data_quality = {
        "score": quality_pct,
        "label": q_label,
        "total_rows": total_records,
        "valid_rows": valid_count,
        "excluded_rows": excluded_count,
        "messages": quality_messages,
    }

    if valid_count == 0:
        return {
            "trends": [],
            "data_quality": data_quality,
        }

    # ── Step 3: Aggregate monthly data from clean rows ──
    trends_qs = (
        clean_qs.annotate(month=TruncMonth("cn_date"))
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
            total_deductions=Coalesce(Sum("freight_deduction"), Decimal("0"), output_field=DecimalField()),
            shipments=Count("id"),
            # Count rows per month that had zero cost (for per-month quality checks)
            zero_cost_rows=Count("id", filter=Q(
                lorry_hire__lte=0, lorry_hire_topf__lte=0, fleet_freight__lte=0,
                own_fleet_exp__lte=0, rake_exp__lte=0, extra_lorry_hire__lte=0,
                transhipment_cost__lte=0,
            )),
        )
        .order_by("loading_city", "delivery_city", "month")
    )

    lane_trends = defaultdict(list)
    lane_total_shipments = defaultdict(int)
    lane_valid_shipments = defaultdict(int)

    for t in trends_qs:
        lane = f"{t['loading_city']} → {t['delivery_city']}"
        weight = _safe_float(t["total_weight"])
        cost = _safe_float(t["total_cost"])
        freight = _safe_float(t["total_freight"])
        profit = _safe_float(t["total_gm1"])
        shipments = t["shipments"]

        # Recalculate — cost_per_tonne only if weight > 0 (already guaranteed by clean_qs)
        cost_per_tonne = cost / weight if weight > 0 else None
        margin_pct = (profit / freight * 100) if freight > 0 else None

        lane_total_shipments[lane] += shipments
        lane_valid_shipments[lane] += shipments

        point = {
            "month": t["month"].strftime("%Y-%m") if t["month"] else "",
            "cost_per_tonne": round(cost_per_tonne, 2) if cost_per_tonne is not None else None,
            "freight": round(freight, 2),
            "profit": round(profit, 2),
            "margin_pct": round(margin_pct, 2) if margin_pct is not None else None,
            "total_cost": round(cost, 2),
            "total_weight": round(weight, 2),
            "shipments": shipments,
        }
        lane_trends[lane].append(point)

    # ── Step 4: Trend analysis, classification, priority scoring ──
    all_lanes = []
    for lane, data in lane_trends.items():
        valid_points = [d for d in data if d["cost_per_tonne"] is not None and d["cost_per_tonne"] > 0]

        anomalies = []
        lane_insights = []

        # Aggregate totals for this lane
        total_profit = sum(d["profit"] for d in data)
        total_freight = sum(d["freight"] for d in data)
        total_shipments = sum(d["shipments"] for d in data)
        total_cost = sum(d["total_cost"] for d in data)

        if len(valid_points) < 2:
            trend_dir = "insufficient"
            pct_change = 0
            profit_pct_change = 0
            avg_cpt = valid_points[0]["cost_per_tonne"] if valid_points else 0
        else:
            first_cpt = valid_points[0]["cost_per_tonne"]
            last_cpt = valid_points[-1]["cost_per_tonne"]
            pct_change = ((last_cpt - first_cpt) / first_cpt * 100) if first_cpt > 0 else 0

            # Profit trend
            first_profit = valid_points[0]["profit"]
            last_profit = valid_points[-1]["profit"]
            profit_pct_change = ((last_profit - first_profit) / abs(first_profit) * 100) if first_profit != 0 else 0

            # Anomaly detection
            cpt_values = [d["cost_per_tonne"] for d in valid_points]
            avg_cpt = sum(cpt_values) / len(cpt_values)
            std_cpt = (sum((v - avg_cpt) ** 2 for v in cpt_values) / len(cpt_values)) ** 0.5 if len(cpt_values) > 1 else 0

            for idx, d in enumerate(valid_points):
                cpt = d["cost_per_tonne"]
                if std_cpt > 0 and abs(cpt - avg_cpt) > 2.5 * std_cpt:
                    anomalies.append({
                        "month": d["month"],
                        "type": "spike" if cpt > avg_cpt else "drop",
                        "value": cpt, "avg": round(avg_cpt, 2),
                    })
                if idx > 0 and cpt < 1 and valid_points[idx - 1]["cost_per_tonne"] > 100:
                    anomalies.append({
                        "month": d["month"], "type": "zero_drop",
                        "value": cpt, "prev_value": valid_points[idx - 1]["cost_per_tonne"],
                    })

            if std_cpt > 0 and avg_cpt > 0 and (std_cpt / avg_cpt * 100) < 1 and len(cpt_values) >= 3:
                anomalies.append({"type": "flat_line", "avg": round(avg_cpt, 2)})

            # Trend direction
            increasing = all(valid_points[i]["cost_per_tonne"] <= valid_points[i + 1]["cost_per_tonne"] for i in range(len(valid_points) - 1))
            decreasing = all(valid_points[i]["cost_per_tonne"] >= valid_points[i + 1]["cost_per_tonne"] for i in range(len(valid_points) - 1))
            if increasing and pct_change > 5:
                trend_dir = "increasing"
            elif decreasing and pct_change < -5:
                trend_dir = "decreasing"
            else:
                trend_dir = "stable"

        # ── Step 5: Business Category Classification ──
        margin_pct = (total_profit / total_freight * 100) if total_freight > 0 else 0
        categories = []      # a lane can belong to multiple categories
        priority_score = 0   # higher = more urgent

        # 1. Loss Making (profit < 0)
        if total_profit < 0:
            categories.append("loss_making")
            priority_score += min(abs(total_profit) / max(total_freight, 1) * 100, 100)  # loss severity

        # 2. High Cost Increase (cost/tonne increased > 5%)
        if trend_dir == "increasing" and pct_change > 5:
            categories.append("high_cost_increase")
            priority_score += min(abs(pct_change), 100)

        # 3. Declining Profit (profit trend going down)
        if len(valid_points) >= 2 and profit_pct_change < -5:
            categories.append("declining_profit")
            priority_score += min(abs(profit_pct_change), 100)

        # 4. Abnormal (has anomalies)
        if len(anomalies) > 0:
            categories.append("abnormal")
            priority_score += len(anomalies) * 15

        # 5. Top Performing (profit > 0, margin > 7%, 5+ shipments)
        if total_profit > 0 and margin_pct > 7 and total_shipments >= 3:
            categories.append("top_performing")

        # Default: if no category assigned, mark as stable
        if not categories:
            categories.append("stable")

        # ── Insight text (decision-focused) ──
        if "loss_making" in categories and "high_cost_increase" in categories:
            lane_insights.append({
                "type": "danger",
                "text": f"Cost increased by {round(pct_change, 1)}% while lane is running at a loss "
                        f"(margin: {round(margin_pct, 1)}%). Immediate action required — renegotiate rates or suspend.",
            })
        elif "loss_making" in categories:
            lane_insights.append({
                "type": "danger",
                "text": f"This lane is loss-making with {round(margin_pct, 1)}% margin across {total_shipments} shipments. "
                        f"Total loss: ₹{abs(total_profit):,.0f}.",
            })
        elif "high_cost_increase" in categories and "declining_profit" in categories:
            lane_insights.append({
                "type": "warning",
                "text": f"Cost increased by {round(pct_change, 1)}% while profit declined by {round(abs(profit_pct_change), 1)}%, "
                        f"indicating margin pressure. Review transporter pricing.",
            })
        elif "high_cost_increase" in categories:
            first_cpt_val = valid_points[0]["cost_per_tonne"] if valid_points else 0
            last_cpt_val = valid_points[-1]["cost_per_tonne"] if valid_points else 0
            lane_insights.append({
                "type": "warning",
                "text": f"Cost per tonne rose by {round(pct_change, 1)}% "
                        f"(₹{round(first_cpt_val, 0):,.0f} → ₹{round(last_cpt_val, 0):,.0f}). "
                        f"Investigate fuel costs or explore alternate carriers.",
            })
        elif "declining_profit" in categories:
            lane_insights.append({
                "type": "warning",
                "text": f"Profit has declined by {round(abs(profit_pct_change), 1)}% over {len(valid_points)} months "
                        f"despite stable costs. Check deductions or freight rate erosion.",
            })
        elif "top_performing" in categories:
            lane_insights.append({
                "type": "success",
                "text": f"Consistently profitable lane with {round(margin_pct, 1)}% margin and ₹{total_profit:,.0f} profit "
                        f"across {total_shipments} shipments. Consider increasing volume.",
            })
        elif "abnormal" in categories:
            lane_insights.append({
                "type": "warning",
                "text": f"Detected {len(anomalies)} anomal{'y' if len(anomalies) == 1 else 'ies'} in cost/tonne data. "
                        f"Review for data entry errors or unusual operational costs.",
            })
        else:
            lane_insights.append({
                "type": "info",
                "text": f"Stable performance with ₹{round(avg_cpt, 0):,.0f}/tonne avg cost and {round(margin_pct, 1)}% margin.",
            })

        # Anomaly insights
        for a in anomalies:
            if a["type"] == "spike":
                lane_insights.append({
                    "type": "warning",
                    "text": f"Anomaly in {a['month']}: cost/tonne spiked to ₹{a['value']:,.0f} (avg: ₹{a['avg']:,.0f}).",
                })
            elif a["type"] == "zero_drop":
                lane_insights.append({
                    "type": "danger",
                    "text": f"In {a['month']}, cost/tonne dropped from ₹{a['prev_value']:,.0f} to ₹{a['value']:,.0f} — likely missing data.",
                })

        # Per-lane quality
        total_for_lane = lane_total_shipments[lane]
        valid_for_lane = lane_valid_shipments[lane]
        lane_quality_pct = round(valid_for_lane / total_for_lane * 100, 1) if total_for_lane > 0 else 0
        lane_q_label = "good" if lane_quality_pct > 90 else ("warning" if lane_quality_pct >= 60 else "critical")

        all_lanes.append({
            "lane_name": lane,
            "data": data,
            "trend": trend_dir,
            "pct_change": round(pct_change, 2),
            "profit_pct_change": round(profit_pct_change, 2) if len(valid_points) >= 2 else 0,
            "total_profit": round(total_profit, 2),
            "total_freight": round(total_freight, 2),
            "total_shipments": total_shipments,
            "margin_pct": round(margin_pct, 2),
            "categories": categories,
            "priority_score": round(priority_score, 2),
            "anomalies": anomalies,
            "insights": lane_insights,
            "quality": {
                "score": lane_quality_pct,
                "label": lane_q_label,
                "valid_points": len(valid_points),
                "total_points": len(data),
            },
        })

    # ── Step 6: Smart filtering — only show high-impact lanes ──
    # Separate into tabs, sorted by priority, max 10 per category
    def _top(lanes, cat, limit=10):
        matching = [l for l in lanes if cat in l["categories"]]
        matching.sort(key=lambda x: x["priority_score"], reverse=True)
        return matching[:limit]

    critical_lanes = []
    # Loss-making: top 10 by priority
    for l in _top(all_lanes, "loss_making", 10):
        if l not in critical_lanes:
            l["tab"] = "critical"
            l["tab_reason"] = "Loss Making"
            critical_lanes.append(l)
    # Abnormal: top 5 that aren't already in critical
    for l in _top(all_lanes, "abnormal", 5):
        if l not in critical_lanes:
            l["tab"] = "critical"
            l["tab_reason"] = "Abnormal"
            critical_lanes.append(l)

    warning_lanes = []
    for l in _top(all_lanes, "high_cost_increase", 10):
        if l not in critical_lanes:
            l["tab"] = "warning"
            l["tab_reason"] = "High Cost Increase"
            warning_lanes.append(l)
    for l in _top(all_lanes, "declining_profit", 10):
        if l not in critical_lanes and l not in warning_lanes:
            l["tab"] = "warning"
            l["tab_reason"] = "Declining Profit"
            warning_lanes.append(l)

    good_lanes = _top(all_lanes, "top_performing", 10)
    for l in good_lanes:
        l["tab"] = "good"
        l["tab_reason"] = "Top Performing"

    # Cap total at 30
    selected = critical_lanes[:10] + warning_lanes[:10] + good_lanes[:10]

    # Build category counts for the summary
    tab_summary = {
        "critical": len(critical_lanes),
        "warning": len(warning_lanes),
        "good": len(good_lanes),
        "total_analyzed": len(all_lanes),
        "total_displayed": len(selected),
    }

    return {
        "trends": selected,
        "data_quality": data_quality,
        "tab_summary": tab_summary,
    }


def get_profit_alerts(qs=None):
    """Generate smart profitability alerts grouped by category.

    Instead of one alert per route, produces one consolidated alert per
    alert type (cost_increase, loss, high_deduction, high_performance,
    abnormal_loss, abnormal_profit) with a ``routes`` list inside.
    """
    if qs is None:
        qs = ProfitRecord.objects.all()

    alerts = []
    classification = get_lane_classification(qs)
    trends_data = get_lane_trends(qs)
    trends = trends_data.get("trends", []) if isinstance(trends_data, dict) else trends_data

    # ── 1. High Cost Increase ──────────────────────────────────────
    cost_increase_routes = []
    for t in trends:
        if t["trend"] == "increasing" and t["pct_change"] > 8:
            first_cpt = t["data"][0]["cost_per_tonne"] if t["data"] else 0
            last_cpt = t["data"][-1]["cost_per_tonne"] if t["data"] else 0
            cost_increase_routes.append({
                "lane_name": t["lane_name"],
                "pct_change": t["pct_change"],
                "from_cpt": round(first_cpt, 2),
                "to_cpt": round(last_cpt, 2),
                "months": len(t["data"]),
            })
    if cost_increase_routes:
        cost_increase_routes.sort(key=lambda r: r["pct_change"], reverse=True)
        alerts.append({
            "type": "cost_increase",
            "level": "red",
            "title": f"🔴 High Cost Increase ({len(cost_increase_routes)} routes)",
            "insight": "The following routes show a consistent upward trend in cost per tonne.",
            "recommendation": "👉 Investigate fuel costs, renegotiate transporter rates, or explore alternate carriers.",
            "routes": cost_increase_routes,
        })

    # ── 2. Loss Alerts (bad lanes) ─────────────────────────────────
    loss_routes = []
    for lane in classification["lanes"]:
        if lane["category"] == "bad":
            loss_routes.append({
                "lane_name": lane["lane_name"],
                "margin_pct": lane["margin_pct"],
                "total_shipments": lane["total_shipments"],
                "total_freight": lane["total_freight"],
                "total_profit": lane["total_profit"],
            })
    if loss_routes:
        loss_routes.sort(key=lambda r: r["margin_pct"])
        alerts.append({
            "type": "loss",
            "level": "red",
            "title": f"🚨 Loss Alert ({len(loss_routes)} routes)",
            "insight": "These routes are operating at a negative margin.",
            "recommendation": "👉 Consider suspending operations or renegotiating freight rates for these corridors.",
            "routes": loss_routes,
        })

    # ── 3. Abnormal Loss ───────────────────────────────────────────
    abnormal_loss_routes = []
    for lane in classification["lanes"]:
        if lane["category"] == "abnormal_loss":
            abnormal_loss_routes.append({
                "lane_name": lane["lane_name"],
                "margin_pct": lane["margin_pct"],
                "total_shipments": lane["total_shipments"],
                "total_freight": lane["total_freight"],
                "total_profit": lane["total_profit"],
            })
    if abnormal_loss_routes:
        abnormal_loss_routes.sort(key=lambda r: r["margin_pct"])
        alerts.append({
            "type": "abnormal_loss",
            "level": "red",
            "title": f"🚨 Abnormal Loss ({len(abnormal_loss_routes)} routes)",
            "insight": "These routes show unusually high losses — possible unexpected cost spikes or data issues.",
            "recommendation": "👉 Immediate audit required. Check for pricing anomalies or vendor overcharging.",
            "routes": abnormal_loss_routes,
        })

    # ── 4. High Deduction ──────────────────────────────────────────
    high_deduction_routes = []
    for lane in classification["lanes"]:
        if lane["total_freight"] > 0:
            ded_ratio = abs(lane["total_deductions"]) / lane["total_freight"] * 100
            if ded_ratio > 10:
                high_deduction_routes.append({
                    "lane_name": lane["lane_name"],
                    "deduction_pct": round(ded_ratio, 1),
                    "total_deductions": round(abs(lane["total_deductions"]), 2),
                    "total_freight": lane["total_freight"],
                    "total_shipments": lane["total_shipments"],
                })
    if high_deduction_routes:
        high_deduction_routes.sort(key=lambda r: r["deduction_pct"], reverse=True)
        alerts.append({
            "type": "high_deduction",
            "level": "yellow",
            "title": f"⚠️ High Deduction ({len(high_deduction_routes)} routes)",
            "insight": "These routes have freight deductions exceeding 10% of total freight.",
            "recommendation": "👉 Review deduction reasons — late delivery penalties, weight discrepancies, or compliance issues.",
            "routes": high_deduction_routes,
        })

    # ── 5. High Performance ────────────────────────────────────────
    high_perf_routes = []
    for lane in classification["lanes"]:
        if lane["category"] == "good" and lane["margin_pct"] > 7 and lane["total_shipments"] >= 5:
            high_perf_routes.append({
                "lane_name": lane["lane_name"],
                "margin_pct": lane["margin_pct"],
                "total_shipments": lane["total_shipments"],
                "total_freight": lane["total_freight"],
                "total_profit": lane["total_profit"],
            })
    if high_perf_routes:
        high_perf_routes.sort(key=lambda r: r["margin_pct"], reverse=True)
        alerts.append({
            "type": "high_performance",
            "level": "green",
            "title": f"🟢 High Performance ({len(high_perf_routes)} routes)",
            "insight": "These routes are consistently profitable with healthy margins.",
            "recommendation": "👉 Consider increasing volume on these corridors. These are model lanes.",
            "routes": high_perf_routes,
        })

    # ── 6. Abnormal Profit ─────────────────────────────────────────
    abnormal_profit_routes = []
    for lane in classification["lanes"]:
        if lane["category"] == "abnormal_profit":
            abnormal_profit_routes.append({
                "lane_name": lane["lane_name"],
                "margin_pct": lane["margin_pct"],
                "total_shipments": lane["total_shipments"],
                "total_freight": lane["total_freight"],
                "total_profit": lane["total_profit"],
            })
    if abnormal_profit_routes:
        abnormal_profit_routes.sort(key=lambda r: r["margin_pct"], reverse=True)
        alerts.append({
            "type": "abnormal_profit",
            "level": "purple",
            "title": f"🟣 Abnormal Profit ({len(abnormal_profit_routes)} routes)",
            "insight": "These routes show unusually high margins. Could indicate pricing anomalies or data issues.",
            "recommendation": "👉 Verify data accuracy and ensure pricing is sustainable.",
            "routes": abnormal_profit_routes,
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
        operational_other_income=Coalesce(Sum("operational_other_income"), Decimal("0"), output_field=DecimalField()),
        lrp=Coalesce(Sum("lrp"), Decimal("0"), output_field=DecimalField()),
        reimb_exp=Coalesce(Sum("reimb_exp"), Decimal("0"), output_field=DecimalField()),
        ldp=Coalesce(Sum("ldp"), Decimal("0"), output_field=DecimalField()),
        other_operation_ded=Coalesce(Sum("other_operation_ded"), Decimal("0"), output_field=DecimalField()),
        cash_discount=Coalesce(Sum("cash_discount"), Decimal("0"), output_field=DecimalField()),
        transaction_charges=Coalesce(Sum("transaction_charges"), Decimal("0"), output_field=DecimalField()),
        pli=Coalesce(Sum("pli"), Decimal("0"), output_field=DecimalField()),
        broker_discount=Coalesce(Sum("broker_discount"), Decimal("0"), output_field=DecimalField()),
        petro_incentive=Coalesce(Sum("petro_incentive"), Decimal("0"), output_field=DecimalField()),
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
            
            # --- Tier 1 Components (Direct Transport Cost) ---
            {"label": "Lorry Hire", "value": -r(agg["lorry_hire"]), "type": "cost"},
            {"label": "Lorry Hire TOPF", "value": -r(agg["lorry_hire_topf"]), "type": "cost"},
            {"label": "Fleet Freight", "value": -r(agg["fleet_freight"]), "type": "cost"},
            {"label": "Own Fleet Exp", "value": -r(agg["own_fleet_exp"]), "type": "cost"},
            {"label": "Rake Exp", "value": -r(agg["rake_exp"]), "type": "cost"},
            {"label": "Extra Lorry Hire", "value": -r(agg["extra_lorry_hire"]), "type": "cost"},
            {"label": "Transhipment Cost", "value": -r(agg["transhipment_cost"]), "type": "cost"},
            {"label": "Freight Deduction", "value": -r(agg["freight_deduction"]), "type": "deduction"}, # Negative value in Excel = Positive addition here
            {"label": "GM1 (Gross Margin)", "value": r(agg["gm1"]), "type": "margin"},

            # --- Tier 2 Components (Direct Operating Cost) ---
            {"label": "Freight Incentive", "value": r(agg["freight_incentive"]), "type": "revenue"},
            {"label": "Other Op. Income", "value": r(agg["operational_other_income"]), "type": "revenue"},
            {"label": "Labour + Wages", "value": -(r(agg["labour"]) + r(agg["wages"])), "type": "cost"},
            {"label": "Insurance", "value": -r(agg["insurance"]), "type": "cost"},
            {"label": "Other Direct Exp", "value": -r(agg["other_direct_exp"]), "type": "cost"},
            {"label": "LRP", "value": -r(agg["lrp"]), "type": "cost"},
            {"label": "GM2", "value": r(agg["gm2"]), "type": "margin"},

            # --- Tier 3 Components (Reimbursements) ---
            {"label": "Reimb Exp", "value": r(agg["reimb_exp"]), "type": "revenue"},
            {"label": "GM3", "value": r(agg["gm3"]), "type": "margin"},

            # --- Tier 4 Components (Claims & Penalties) ---
            {"label": "Claims + Detention", "value": -(r(agg["claim"]) + r(agg["detention"])), "type": "deduction"},
            {"label": "LDP", "value": -r(agg["ldp"]), "type": "deduction"},
            {"label": "Other Op. Ded.", "value": -r(agg["other_operation_ded"]), "type": "deduction"},
            {"label": "GM4", "value": r(agg["gm4"]), "type": "margin"},

            # --- Tier 5 Components (Finance) ---
            {"label": "Interest", "value": -r(agg["interest"]), "type": "cost"},
            {"label": "GM5", "value": r(agg["gm5"]), "type": "margin"},

            # --- Tier 6 Components (Discounts & Charges) ---
            {"label": "PLI / CLI", "value": -r(agg["pli"]), "type": "deduction"},
            {"label": "Transaction Charges", "value": -r(agg["transaction_charges"]), "type": "cost"},
            {"label": "Cash / Broker Disc.", "value": -(r(agg["cash_discount"]) + r(agg["broker_discount"])), "type": "deduction"},
            {"label": "Petro Incentive", "value": r(agg["petro_incentive"]), "type": "revenue"},
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
    trends_data = get_lane_trends(qs)
    trends = trends_data.get("trends", []) if isinstance(trends_data, dict) else trends_data

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


def get_lane_shipment_details(qs, loading_city, delivery_city):
    """Returns individual shipment records, optionally filtered by lane."""
    records = qs
    if loading_city:
        records = records.filter(loading_city=loading_city)
    if delivery_city:
        records = records.filter(delivery_city=delivery_city)
        
    records = records.order_by("-cn_date")
    
    shipments = []
    for r in records:
        cust = r.customer_name
        # Shortening removed as per new standard
        
        shipments.append({
            "sap_delivery_no": r.sap_delivery_no,
            "sap_external_no": r.sap_external_no or r.sap_delivery_no,
            "cn_date": r.cn_date.strftime("%Y-%m-%d") if r.cn_date else None,
            "loading_city": r.loading_city,
            "delivery_city": r.delivery_city,
            "customer": cust,
            "vehicle": r.vehicle_type,
            "material_name": r.material_name,
            "weight": int(round(float(r.charge_weight))),
            "freight": round(float(r.freight), 2),
            "cost": round(r.total_cost, 2),
            "profit": round(float(r.gm1), 2),
            "cpt": int(round(r.cost_per_tonne)),
        })
    return shipments


