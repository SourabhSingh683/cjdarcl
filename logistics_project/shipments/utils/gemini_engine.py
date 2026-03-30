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
from dotenv import load_dotenv
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent

logger = logging.getLogger("shipments")

GEMINI_MODEL = "gemini-2.0-flash"

SYSTEM_PROMPT = """You are a senior logistics analyst AI for CJ DARCL.
You analyze shipment data based on a strict internal operations blueprint.
When analyzing data, understand these groupings (GOLD Insights):

A. Booking & Origin: Where shipments are booked (Booking Region) and loading station/state.
B. Destination: Delivery station/state.
C. Customer Info: Customer Name, Contract ID, Bill To Party.
D. Material Info: Material Type, Packages, Weights, Truck Type.
E. Transport: Vehicle No, Transporter Name, Distance. Check Transporter SLAs.
F. Time Metrics (CRITICAL): Dispatch Date, Delivery Date. Analyzes SLA delays and efficiency.
G. Financial Data: Billed Freight (Revenue) vs Penalties.
H. POD: Proof of Delivery status affects billing compliance.
I. Exceptions: Shortages or damages causing cargo loss.

Your responses must be:
- Data-driven and specific (reference actual numbers/transporters/regions)
- Actionable (suggest SLA reviews for bad transporters, rerouting, etc)
- Concise but comprehensive using bullet points
- Include risk levels (🔴 High, 🟡 Medium, 🟢 Low)

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
        avg_delay=Coalesce(Avg("delay_days", filter=Q(is_on_time=False)), 0.0),
        delayed=Count("id", filter=Q(is_on_time=False)),
        on_time=Count("id", filter=Q(is_on_time=True)),
        shortage_count=Count("id", filter=Q(has_shortage=True)),
        penalty_count=Count("id", filter=Q(has_penalty=True)),
        total_distance=Coalesce(Sum("total_distance"), 0.0, output_field=FloatField()),
        completed_pods=Count("id", filter=Q(pod_status__iexact="c")),
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

    # Worst 3 Transporters
    worst_transporters = list(
        qs.exclude(transporter_name='').values("transporter_name")
        .annotate(
            total=Count("id"),
            delayed=Count("id", filter=Q(is_on_time=False)),
            avg_delay=Coalesce(Avg("delay_days", filter=Q(is_on_time=False)), 0.0, output_field=FloatField()),
        )
        .order_by("-delayed", "-total")[:3]
    )

    # Top 3 Regions by Volume
    top_regions = list(
        qs.exclude(booking_region='').values("booking_region")
        .annotate(total=Count("id"), delayed=Count("id", filter=Q(is_on_time=False)))
        .order_by("-total")[:3]
    )

    summary = f"""
=== CJ DARCL LOGISTICS DATA SUMMARY ===
Total Shipments: {total}
Total Distance: {float(stats['total_distance']):,.2f} km
Completed PODs: {stats['completed_pods']} ({round((stats['completed_pods'] / total) * 100, 1) if total > 0 else 0}%)
On-Time: {stats['on_time']} ({on_time_pct}%)
Delayed: {stats['delayed']} ({round(100 - on_time_pct, 1)}%)
Average Delay (delayed only): {stats['avg_delay']} days
Total Billed Freight: ₹{float(stats['total_rev']):,.2f}
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

    summary += "\n=== TRANSPORTER PERFORMANCE ===\n"
    for t in worst_transporters:
        delay_pct = round((t["delayed"] / t["total"]) * 100, 1) if t["total"] > 0 else 0
        summary += f"- {t['transporter_name'][:20]}: {t['total']} shipments, {t['delayed']} delayed ({delay_pct}%), avg {t['avg_delay']:.1f} days late\n"

    summary += "\n=== REGION BREAKDOWN ===\n"
    for r in top_regions:
        summary += f"- {r['booking_region'][:20]}: {r['total']} shipments, {r['delayed']} delayed\n"

    return summary


def _generate_fallback_response(user_question, data_points):
    """Rule-based fallback when AI fails."""
    if not data_points:
        return "No logistics data available to analyze."
    
    total = data_points.get("total_shipments", 0)
    delayed = data_points.get("delayed_count", 0)
    rev = data_points.get("total_revenue", 0)
    on_time = data_points.get("on_time_rate", 0)

    if delayed == 0 and data_points.get("total_penalties", 0) == 0:
        base_insights = (
            "### ✨ Logistics Health Status: Excellent\n"
            f"- **Volume Tracking**: Successfully tracked **{total}** shipments over **{data_points.get('total_distance', 0):,.2f} km**.\n"
            "- **Status**: 🟢 **Currently NO ISSUES detected!** There are **0 delayed** shipments and no penalty records affecting your operations.\n"
            f"- **Compliance**: Current POD tracking compliance is **{data_points.get('pod_compliance', 0)}%**.\n"
            f"- **Financials**: Billed Freight is stable at **₹{rev:,.2f}**.\n\n"
            "*(Note: Advanced AI analysis is temporarily unavailable. Showing automated logic instead.)*"
        )
    else:
        base_insights = (
            "### 📊 Automated Insights (Rule-Based Fallback)\n"
            f"- **Volume & Scope**: **{total}** total shipments tracked covering **{data_points.get('total_distance', 0):,.2f} km**.\n"
            f"- **Performance**: On-time rate is **{on_time}%** with POD compliance at **{data_points.get('pod_compliance', 0)}%**.\n"
            f"- **Delays**: There are **{delayed}** delayed shipments currently affecting operations.\n"
            f"- **Financials**: Total billed freight stands at **₹{rev:,.2f}**.\n\n"
            "*(Note: Advanced AI analysis is temporarily unavailable. Showing rule-based summary instead.)*"
        )
    
    if not user_question:
        return base_insights
    
    q = user_question.lower()
    
    if delayed == 0 and data_points.get("total_penalties", 0) == 0:
        return base_insights

    if "trend" in q or "performance" in q:
        return (
            "### 📈 Performance Trends Analysis\n\n"
            f"- **Overall Volume**: {total} shipments processed.\n"
            f"- **On-Time Reliability**: Holding at **{on_time}%**. Consistency here protects your raw freight value (₹{rev:,.2f}).\n"
            f"- **Impact Tracking**: Currently, {delayed} shipments missed targets. If this trend is seasonal, expect higher capacity crunches next quarter.\n\n"
            "**Action:** Head to the visual `Analytics` tab to compare precise month-over-month performance trends.\n\n"
            "*(Note: AI analytical modeling is temporarily unavailable. Showing rule-based trends.)*"
        )
    elif "issue" in q or "recommendation" in q or "optimiz" in q:
        return (
            "### 💡 Optimization Recommendations\n\n"
            f"**1. Address Delays ({delayed} Shipments)**\n"
            "   - **Root Cause**: High delay volumes typically originate from severe weather or vendor mismanagement on core routes.\n"
            "   - **Action**: Check the Analytics tab for the `Route Risk Matrix` to identify the specific worst-performing lanes.\n\n"
            f"**2. Mitigate Financial Penalties (₹{data_points.get('total_penalties', 0):,.2f})**\n"
            "   - **Action**: Renegotiate SLAs with vendors who repeatedly fail transit times, and hold strict compliance checks on loading to prevent shortages.\n\n"
            "**3. Improve On-Time Rate**\n"
            f"   - **Current Rate**: {on_time}%\n"
            "   - **Target**: Pushing this above 95% will drastically cut penalty overhead and improve client satisfaction.\n\n"
            "*(Note: Advanced AI insights are temporarily unavailable. Showing rule-based strategy.)*"
        )
    elif "delay" in q or "attention" in q or "risk" in q or "route" in q:
        routes_text = ""
        trans_text = ""
        if "worst_routes" in data_points and data_points["worst_routes"]:
            routes_text = "### 🚨 Routes Needing Immediate Attention:\n"
            for r in data_points["worst_routes"]:
                routes_text += f"- **{r['route__origin']} → {r['route__destination']}**: {r['count']} delayed shipments, incurring ₹{float(r['penalty']):,.0f} penalty.\n"
        if "worst_transporters" in data_points and data_points["worst_transporters"]:
            trans_text = "\n### 🚛 Transporters Causing Delays:\n"
            for t in data_points["worst_transporters"]:
                trans_text += f"- **{t['transporter_name'][:20]}**: {t['delayed']} delays out of {t['total']} shipments.\n"

        return (
            routes_text + trans_text +
            f"\n### ⚠️ Overall Snapshot\n"
            f"- Out of {total} shipments, **{delayed} are currently delayed**.\n"
            "- **Action**: Prioritize resolving delays on the longest-running routes to limit penalty exposure.\n\n"
            "*(Note: Advanced AI route-level tracking is temporarily unavailable. Showing rule-based summary.)*"
        )
    elif "revenue" in q or "penalty" in q or "cost" in q or "freight" in q:
        penalty_text = ""
        if "worst_routes" in data_points and data_points["worst_routes"]:
            penalty_text = "### 🛑 Highest Penalty Routes:\n"
            sorted_routes = sorted(data_points["worst_routes"], key=lambda x: x['penalty'], reverse=True)
            for r in sorted_routes:
                if r['penalty'] > 0:
                    penalty_text += f"- **{r['route__origin']} → {r['route__destination']}**: ₹{float(r['penalty']):,.0f}\n"

        return (
            "### 💰 Financial Focus\n"
            f"- **Billed Freight**: ₹{rev:,.2f}\n"
            f"- **Penalties**: ₹{data_points.get('total_penalties', 0):,.2f}\n\n" +
            penalty_text +
            "\n- **Action**: Investigate vendors executing routes with high shortage deductibles to recover margin.\n\n"
            "*(Note: Advanced AI financial analysis is temporarily unavailable. Showing rule-based summary.)*"
        )
    else:
        return base_insights


def analyze_with_gemini(qs=None, user_question=None):
    """
    Send shipment data summary to Gemini and get AI-powered analysis.
    Falls back to rule-based analysis if API fails.
    """
    d_points = _get_data_points(qs)
    
    # Dynamically reload environment in case the .env file was modified while server is running
    load_dotenv(BASE_DIR / ".env", override=True)
    
    try:
        import google.generativeai as genai

        api_key = os.environ.get("GEMINI_API_KEY", "")
        if not api_key:
            fallback = _generate_fallback_response(user_question, d_points)
            return {
                "analysis": f"⚠️ AI analysis temporarily unavailable: API key not found in environment.\n\n---\n\n{fallback}",
                "model": "fallback",
                "data_points": d_points,
                "status": "error",
            }

        genai.configure(api_key=api_key)
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
        fallback = _generate_fallback_response(user_question, d_points)
        return {
            "analysis": f"⚠️ Google Generative AI package is not installed.\n\n---\n\n{fallback}",
            "model": "fallback",
            "data_points": d_points,
            "status": "error",
        }
    except Exception as e:
        logger.exception("Gemini API error")
        error_msg = str(e)
        if "quota" in error_msg.lower() or "429" in error_msg:
            clean_msg = "⚠️ Google AI API daily free-tier quota exceeded for this API key. Please try again tomorrow or generate a new key."
        elif "api_key_invalid" in error_msg.lower() or "400" in error_msg:
            clean_msg = "⚠️ Invalid Gemini API key. Please check your .env configuration."
        else:
            clean_msg = "⚠️ AI analysis temporarily unavailable. The service may be down or experiencing issues."
            
        fallback = _generate_fallback_response(user_question, d_points)
        return {
            "analysis": f"{clean_msg}\n\n---\n\n{fallback}",
            "model": "fallback",
            "data_points": d_points,
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

    worst_routes = list(
        qs.filter(is_on_time=False)
        .values("route__origin", "route__destination")
        .annotate(
            count=Count("id"),
            penalty=Coalesce(Sum("penalty"), Decimal("0"))
        )
        .order_by("-count")[:3]
    )

    worst_transporters = list(
        qs.exclude(transporter_name='').values("transporter_name")
        .annotate(
            total=Count("id"),
            delayed=Count("id", filter=Q(is_on_time=False)),
        )
        .order_by("-delayed", "-total")[:3]
    )

    return {
        "total_shipments": total,
        "on_time_rate": round((stats["on_time"] / total) * 100, 1) if total > 0 else 0,
        "delayed_count": stats["delayed"],
        "total_revenue": float(stats["total_rev"]),
        "total_penalties": float(stats["total_penalty"]),
        "worst_routes": worst_routes,
        "worst_transporters": worst_transporters,
    }
