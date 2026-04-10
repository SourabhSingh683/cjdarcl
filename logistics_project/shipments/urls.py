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
    path("kpis/transporter-performance/", views.kpi_transporter_performance, name="kpi-transporter-performance"),

    # Analytics (NEW)
    path("analysis/operational-intelligence/", views.operational_intelligence, name="analysis-operational-intelligence"),
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
    path("uploads/bulk-delete/", views.bulk_delete_uploads, name="bulk-delete-uploads"),
    path("uploads/<int:upload_id>/", views.delete_upload, name="delete-upload"),
    path("uploads/<int:upload_id>/reprocess/", views.reprocess_upload, name="reprocess-upload"),
    path("shipments/", views.shipment_list, name="shipment-list"),
    path("clear-data/", views.clear_all_data, name="clear-all-data"),

    # AI Analysis (Gemini)
    path("ai/analyze/", views.ai_analyze, name="ai-analyze"),

    # Profit Analysis
    path("profit/upload/", views.profit_upload, name="profit-upload"),
    path("profit/summary/", views.profit_summary, name="profit-summary"),
    path("profit/lanes/", views.profit_lanes, name="profit-lanes"),
    path("profit/trends/", views.profit_trends, name="profit-trends"),
    path("profit/alerts/", views.profit_alerts, name="profit-alerts"),
    path("profit/drilldown/", views.profit_drilldown, name="profit-drilldown"),
    path("profit/insights/", views.profit_insights, name="profit-insights"),
]
