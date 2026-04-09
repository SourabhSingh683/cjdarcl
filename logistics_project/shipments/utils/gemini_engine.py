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

from django.db.models import Count, Sum, Avg, Q, FloatField
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
- Explain delays as 'X delayed shipments out of Y total' (e.g. 31 delayed out of 1093)
- For route-level analysis, provide a severity breakdown: '1 day delay: XX%, 2 days: YY%, more than 7 days: ZZ%'
- Actionable (suggest SLA reviews for bad transporters, rerouting, etc)
- Concise but comprehensive using bullet points
- Include risk levels (🔴 High, 🟡 Medium, 🟢 Low)
- DO NOT explain or mention penalty amounts in currency (₹) unless specifically asked. Focus on operational impact rather than money values.

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
    
    if delayed == 0:
        return base_insights

    if "trend" in q or "performance" in q:
        return (
            "### 📈 Performance Trends Analysis\n\n"
            f"- **Overall Volume**: {total} shipments processed.\n"
            f"- **Service Reliability**: Holding at **{on_time}%**. Consistent performance here protects your raw freight value.\n"
            f"- **Impact Tracking**: Currently, {delayed} shipments missed transit targets. This represents about **{round((delayed / total) * 100, 1) if total > 0 else 0}%** of your total operation.\n\n"
            "**Action:** Head to the visual `Analytics` tab to compare precise month-over-month performance trends.\n\n"
            "*(Note: AI analytical modeling is temporarily unavailable. Showing rule-based trends.)*"
        )
    elif "issue" in q or "risk" in q or "attention" in q:
        worst_r = data_points.get("worst_routes", [{}])[0]
        worst_t = data_points.get("worst_transporters", [{}])[0]
        
        issue_details = f"### 🚨 Top Issues Identified\n\n"
        if worst_r:
            issue_details += f"**1. High-Risk Route: {worst_r.get('route__origin')} → {worst_r.get('route__destination')}**\n"
            issue_details += f"   - **Impact**: {worst_r.get('delayed', 0)} delayed shipments (out of {worst_r.get('count', 0)} total).\n"
            issue_details += f"   - **Severity**: Over {round(((worst_r.get('d7plus', 0) / worst_r.get('delayed', 1)) * 100),1) if worst_r.get('delayed', 0) > 0 else 0}% of these show severe delay (>7 days).\n\n"
        
        if worst_t:
            issue_details += f"**2. Transporter Bottleneck: {worst_t.get('transporter_name', 'N/A')}**\n"
            issue_details += f"   - **Impact**: {worst_t.get('delayed', 0)} delays out of {worst_t.get('total', 0)} assignments.\n\n"
        
        issue_details += "### ⚠️ Risk Outlook\n"
        issue_details += f"Current reliability is **{on_time}%**. The {delayed} delays indicate systemic transit bottlenecks require attention.\n\n"
        
        return issue_details + "*(Note: Advanced AI analysis is temporarily unavailable. Showing rule-based issue matrix.)*"

    elif "recommendation" in q or "optimiz" in q:
        worst_t = data_points.get("worst_transporters", [{}])[0]
        
        rec_details = "### 💡 Strategic Optimization Recommendations\n\n"
        if worst_t:
            rec_details += f"**1. Vendor SLA Audit: {worst_t.get('transporter_name', 'N/A')}**\n"
            rec_details += f"   - **Action**: Immediately review transit performance. Vendor is failing on {round((worst_t.get('delayed', 0) / worst_t.get('total', 1)) * 100, 1) if worst_t.get('total', 0) > 0 else 0}% of shipments.\n\n"
        
        rec_details += "**2. Route Diversification**\n"
        rec_details += "   - **Action**: Identify alternative carriers for lanes where 1-2 day delays are recurring to prevent backlog buildup.\n\n"
        
        rec_details += f"**3. Target Stability Enhancement**\n"
        rec_details += f"   - **Target**: Pushing the on-time rate from **{on_time}%** back to **95%** will significantly reduce billing disputes.\n\n"
        
        return rec_details + "*(Note: Advanced AI analysis is temporarily unavailable. Showing rule-based strategy.)*"
    elif "delay" in q or "route" in q:
        routes_text = ""
        trans_text = ""
        if "worst_routes" in data_points and data_points["worst_routes"]:
            routes_text = "### 🚨 Routes Needing Immediate Attention:\n"
            for r in data_points["worst_routes"]:
                # Total shipments on this route
                total_on_route = r.get('count', 0)
                delayed_on_route = r.get('delayed', 0)
                
                # Percentages relative to delayed shipments
                p1 = round((r.get('d1', 0) / delayed_on_route) * 100, 1) if delayed_on_route > 0 else 0
                p2 = round((r.get('d2', 0) / delayed_on_route) * 100, 1) if delayed_on_route > 0 else 0
                p7 = round((r.get('d7plus', 0) / delayed_on_route) * 100, 1) if delayed_on_route > 0 else 0
                
                routes_text += f"- **{r['route__origin']} → {r['route__destination']}**: {delayed_on_route} delayed shipments out of {total_on_route}.\n"
                routes_text += f"  - Breakdown: 1 day delay: **{p1}%**, 2 days: **{p2}%**, >7 days: **{p7}%**\n"

        if "worst_transporters" in data_points and data_points["worst_transporters"]:
            trans_text = "\n### 🚛 Transporters Causing Delays:\n"
            for t in data_points["worst_transporters"]:
                trans_text += f"- **{t['transporter_name'][:20]}**: {t['delayed']} delays out of {t['total']} shipments.\n"

        return (
            routes_text + trans_text +
            f"\n### ⚠️ Overall Snapshot\n"
            f"- Out of {total} shipments, **{delayed} are currently delayed**.\n"
            "- **Action**: Prioritize resolving delays on the longest-running routes to limit operational impact.\n\n"
            "*(Note: Advanced AI route-level tracking is temporarily unavailable. Showing rule-based summary.)*"
        )
    elif "penalty" in q or "deduction" in q:
        total_p = data_points.get("total_penalties", 0)
        p_count = data_points.get("penalty_count", 0)
        
        return (
            "### 💰 Penalty & Deduction Analysis\n"
            f"- **Total Penalties**: ₹{total_p:,.2f} recorded.\n"
            f"- **Frequency**: {p_count} shipments incurred penalties.\n"
            f"- **Primary Driver**: Usually linked to transit delays exceeding permissible limits.\n\n"
            f"**Action**: Look at the `Analytics` tab and filter by **'Penalty'** to see specific vehicle numbers contributing to this leakage.\n\n"
            "*(Note: Advanced AI penalty modeling is temporarily unavailable. Showing rule-based financial summary.)*"
        )
    elif "shortage" in q or "loss" in q:
        shortage_mt = data_points.get("total_shortage", 0)
        s_count = data_points.get("shortage_count", 0)
        
        return (
            "### ⚖️ Shortage & Material Loss\n"
            f"- **Total Shortage**: {shortage_mt:.3f} MT (Metric Tons).\n"
            f"- **Incident Count**: {s_count} shipments with material variance.\n"
            f"- **Status**: { '🚨 Critical variance detected.' if shortage_mt > 1 else '✓ Within operational norms.' }\n\n"
            f"**Recommendation**: Audit the loading/unloading weighment records for routes showing consistent shortages.\n\n"
            "*(Note: AI shortage pattern analysis is temporarily unavailable. Showing rule-based logistics data.)*"
        )
    elif "revenue" in q or "cost" in q or "freight" in q:
        return (
            "### 💰 Financial Focus\n"
            f"- **Billed Freight**: ₹{rev:,.2f}\n"
            f"- **Total Penalties**: ₹{data_points.get('total_penalties', 0):,.2f}\n"
            f"- **Net Freight Expected**: ₹{(rev - data_points.get('total_penalties', 0)):,.2f}\n\n"
            "- **Action**: Investigate vendors executing routes with frequent delays to recover margin.\n"
            "*(Note: Advanced AI financial analysis is temporarily unavailable. Showing rule-based summary.)*"
        )
    else:
        return base_insights


def analyze_with_gemini(qs=None, user_question=None):
    """
    Send shipment data summary to Gemini and get AI-powered analysis.
    Falls back to rule-based analysis if API fails.
    """
    # ─── 0. Data Gathering (Safe) ───
    try:
        d_points = _get_data_points(qs)
    except Exception as e:
        logger.exception("Error gathering data points for AI")
        d_points = {}

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
        # Handle cases where response might be empty or blocked
        try:
            txt = response.text
        except:
            txt = "⚠️ AI was unable to generate a text response for this query (it may have been blocked or the content is unavailable)."

        return {
            "analysis": txt,
            "model": GEMINI_MODEL,
            "data_points": d_points,
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
        error_msg = str(e).lower()
        if any(w in error_msg for w in ["quota", "429", "limit", "exhausted"]):
            clean_msg = "⚠️ Google AI API quota exceeded. Please try again later or check your API usage limits."
        elif any(w in error_msg for w in ["api_key", "invalid", "400"]):
            clean_msg = "⚠️ Invalid Gemini API key. Please check your .env configuration."
        else:
            clean_msg = "⚠️ AI analysis temporarily unavailable. The service may be experiencing issues."
            
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
        total_shortage=Coalesce(Sum("shortage"), 0.0, output_field=FloatField()),
        shortage_count=Count("id", filter=Q(has_shortage=True)),
        penalty_count=Count("id", filter=Q(has_penalty=True)),
    )

    worst_routes = list(
        qs.values("route__origin", "route__destination")
        .annotate(
            count=Count("id"),
            delayed=Count("id", filter=Q(is_on_time=False)),
            d1=Count("id", filter=Q(delay_days=1)),
            d2=Count("id", filter=Q(delay_days=2)),
            d7plus=Count("id", filter=Q(delay_days__gt=7)),
        )
        .filter(delayed__gt=0)
        .order_by("-delayed")[:3]
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
        "total_shortage": float(stats["total_shortage"]),
        "shortage_count": stats["shortage_count"],
        "penalty_count": stats["penalty_count"],
        "worst_routes": worst_routes,
        "worst_transporters": worst_transporters,
    }
