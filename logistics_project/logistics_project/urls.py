"""
Project-level URL configuration.
Routes /api/ to the shipments app, and includes Django admin.
"""

from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include("shipments.urls")),
]
