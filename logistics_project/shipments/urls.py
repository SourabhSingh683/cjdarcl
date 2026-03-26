"""URL routing for the shipments API v2."""

from django.urls import path
from . import views

app_name = "shipments"

urlpatterns = [
    # File upload
    path("upload/", views.upload_file, name="upload-file"),

    # KPI endpoints
    path("kpis/summary/", views.kpi_summary, name="kpi-summary"),
    path("kpis/revenue-trends/", views.kpi_revenue_trends, name="kpi-revenue-trends"),
    path("kpis/top-routes/", views.kpi_top_routes, name="kpi-top-routes"),
    path("kpis/delayed-shipments/", views.kpi_delayed_shipments, name="kpi-delayed-shipments"),
    path("kpis/drilldown/", views.kpi_drilldown, name="kpi-drilldown"),
    path("kpis/comparison/", views.period_comparison, name="kpi-comparison"),

    # Analytics (NEW)
    path("analysis/root-cause/", views.analysis_root_cause, name="analysis-root-cause"),
    path("analysis/risk/", views.analysis_risk, name="analysis-risk"),
    path("analysis/shortage/", views.analysis_shortage, name="analysis-shortage"),

    # Data Quality (NEW)
    path("quality/", views.data_quality, name="data-quality"),

    # Insights
    path("insights/", views.insights, name="insights"),
    path("insights/smart/", views.smart_insights, name="smart-insights"),

    # Upload history & shipments
    path("uploads/", views.upload_history, name="upload-history"),
    path("shipments/", views.shipment_list, name="shipment-list"),

    # AI Analysis (Gemini)
    path("ai/analyze/", views.ai_analyze, name="ai-analyze"),
]
