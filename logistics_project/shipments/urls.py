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
    path("uploads/<int:upload_id>/", views.delete_upload, name="delete-upload"),
    path("shipments/", views.shipment_list, name="shipment-list"),

    # POD upload & Invoice generation
    path("shipments/<str:shipment_id>/pod/", views.pod_upload, name="pod-upload"),
    path("shipments/<str:shipment_id>/invoice/", views.generate_invoice_view, name="invoice"),

    # AI Analysis (Gemini)
    path("ai/analyze/", views.ai_analyze, name="ai-analyze"),

    # ── Driver Panel ──────────────────────────────────────────
    path("driver/shipments/", views.DriverShipmentListView.as_view(), name="driver-shipments"),
    path("driver/upload-pod/<int:shipment_id>/", views.UploadPodImagesView.as_view(), name="driver-upload-pod"),

    # ── POD Download + View (Driver + Manager) ──────────────────
    path("download-pod/<str:shipment_id>/", views.DownloadPodView.as_view(), name="download-pod"),
    path("view-pod/<str:shipment_id>/", views.ViewPodView.as_view(), name="view-pod"),
    path("driver/delete-pod/<str:shipment_id>/", views.DeletePodView.as_view(), name="delete-pod"),
]
