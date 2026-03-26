"""
Gemini AI Engine — Google Gemini-powered logistics analysis.
=============================================================
Aggregates shipment KPIs into a structured prompt and sends
to Gemini 2.0 Flash for actionable logistics insights.
"""

import json
import logging
import os
from decimal import Decimal

from django.db.models import Count, Sum, Avg, Q
from django.db.models.functions import Coalesce

logger = logging.getLogger("shipments")

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
GEMINI_MODEL = "gemini-2.0-flash"

SYSTEM_PROMPT = """You are a senior logistics analyst AI for CJ DARCL, one of India's largest logistics companies.
You analyze shipment data and provide actionable business intelligence.

Your responses must be:
- Data-driven and specific (reference actual numbers)
- Actionable (what should be done, not just what happened)
- Concise but comprehensive
- Use bullet points for clarity
- Include risk levels (🔴 High, 🟡 Medium, 🟢 Low) where appropriate
- Suggest concrete optimizations

Format your response with these sections:
## 📊 Key Findings
## ⚠️ Risk Alerts
## 💡 Recommendations
## 📈 Optimization Opportunities
"""


def _build_data_summary(qs):
    """Build a structured text summary of current shipment data for the AI."""
    from shipments.models import Shipment

    if qs is None:
        qs = Shipment.objects.all()

    total = qs.count()
    if total == 0:
        return "No shipment data available."

    # Core KPIs
    stats = qs.aggregate(
        total_rev=Coalesce(Sum("revenue"), Decimal("0")),
        total_penalty=Coalesce(Sum("penalty"), Decimal("0")),
        total_shortage=Coalesce(Sum("shortage"), Decimal("0")),
        avg_delay=Coalesce(Avg("delay_days", filter=Q(is_on_time=False)), 0),
        delayed=Count("id", filter=Q(is_on_time=False)),
        on_time=Count("id", filter=Q(is_on_time=True)),
        shortage_count=Count("id", filter=Q(has_shortage=True)),
        penalty_count=Count("id", filter=Q(has_penalty=True)),
    )

    on_time_pct = round((stats["on_time"] / total) * 100, 1) if total > 0 else 0

    # Top 5 routes by delay
    worst_routes = list(
        qs.filter(is_on_time=False)
        .values("route__origin", "route__destination")
        .annotate(
            count=Count("id"),
            avg_delay=Avg("delay_days"),
            penalty=Coalesce(Sum("penalty"), Decimal("0")),
        )
        .order_by("-count")[:5]
    )

    # Vehicle type breakdown
    vehicle_stats = list(
        qs.values("vehicle_type")
        .annotate(
            total=Count("id"),
            delayed=Count("id", filter=Q(is_on_time=False)),
        )
        .order_by("-total")[:5]
    )

    summary = f"""
=== CJ DARCL LOGISTICS DATA SUMMARY ===
Total Shipments: {total}
On-Time: {stats['on_time']} ({on_time_pct}%)
Delayed: {stats['delayed']} ({round(100 - on_time_pct, 1)}%)
Average Delay (delayed only): {stats['avg_delay']} days
Total Revenue: ₹{float(stats['total_rev']):,.2f}
Total Penalties: ₹{float(stats['total_penalty']):,.2f}
Shipments with Penalties: {stats['penalty_count']}
Shipments with Shortage: {stats['shortage_count']}
Total Shortage: {float(stats['total_shortage']):.3f} MT

=== TOP DELAYED ROUTES ===
"""
    for r in worst_routes:
        summary += (
            f"- {r['route__origin']} → {r['route__destination']}: "
            f"{r['count']} delayed, avg {r['avg_delay']:.1f} days, "
            f"₹{float(r['penalty']):,.2f} penalties\n"
        )

    summary += "\n=== VEHICLE TYPE BREAKDOWN ===\n"
    for v in vehicle_stats:
        delay_pct = round((v["delayed"] / v["total"]) * 100, 1) if v["total"] > 0 else 0
        summary += f"- {v['vehicle_type']}: {v['total']} shipments, {v['delayed']} delayed ({delay_pct}%)\n"

    return summary


def analyze_with_gemini(qs=None, user_question=None):
    """
    Send shipment data summary to Gemini and get AI-powered analysis.
    Falls back to rule-based analysis if API fails.
    """
    try:
        import google.generativeai as genai

        genai.configure(api_key=GEMINI_API_KEY)
        model = genai.GenerativeModel(GEMINI_MODEL)

        data_summary = _build_data_summary(qs)

        if user_question:
            prompt = f"{SYSTEM_PROMPT}\n\nHere is the current logistics data:\n{data_summary}\n\nUser Question: {user_question}\n\nProvide a detailed analysis answering the question based on the data above."
        else:
            prompt = f"{SYSTEM_PROMPT}\n\nHere is the current logistics data:\n{data_summary}\n\nProvide a comprehensive analysis of this logistics operation."

        response = model.generate_content(prompt)
        return {
            "analysis": response.text,
            "model": GEMINI_MODEL,
            "data_points": _get_data_points(qs),
            "status": "success",
        }

    except ImportError:
        logger.error("google-generativeai package not installed")
        return {
            "analysis": "⚠️ Google Generative AI package is not installed. Run: `pip install google-generativeai`",
            "model": "fallback",
            "data_points": _get_data_points(qs),
            "status": "error",
        }
    except Exception as e:
        logger.exception("Gemini API error")
        return {
            "analysis": f"⚠️ AI analysis temporarily unavailable: {str(e)}",
            "model": "fallback",
            "data_points": _get_data_points(qs),
            "status": "error",
        }


def _get_data_points(qs):
    """Return quick numeric summary for the frontend."""
    from shipments.models import Shipment

    if qs is None:
        qs = Shipment.objects.all()

    total = qs.count()
    if total == 0:
        return {}

    stats = qs.aggregate(
        delayed=Count("id", filter=Q(is_on_time=False)),
        on_time=Count("id", filter=Q(is_on_time=True)),
        total_rev=Coalesce(Sum("revenue"), Decimal("0")),
        total_penalty=Coalesce(Sum("penalty"), Decimal("0")),
    )

    return {
        "total_shipments": total,
        "on_time_rate": round((stats["on_time"] / total) * 100, 1) if total > 0 else 0,
        "delayed_count": stats["delayed"],
        "total_revenue": float(stats["total_rev"]),
        "total_penalties": float(stats["total_penalty"]),
    }
