"""
Project-level URL configuration.
Routes:
  /api/auth/          → accounts.urls  (register, login, OTP, me, token refresh)
  /api/notifications/ → accounts notification views
  /api/              → shipments.urls  (all analytics, POD upload, invoice)
  /admin/            → Django admin
"""

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

# Notification views are part of accounts app
from accounts import views as accounts_views

urlpatterns = [
    path("admin/", admin.site.urls),

    # Auth endpoints
    path("api/auth/", include("accounts.urls")),

    # Notification endpoints
    path("api/notifications/",
         accounts_views.notification_list,          name="notification-list"),
    path("api/notifications/<int:notif_id>/read/",
         accounts_views.notification_mark_read,     name="notification-mark-read"),
    path("api/notifications/mark-all-read/",
         accounts_views.notification_mark_all_read, name="notification-mark-all-read"),

    # All shipments / analytics / upload / AI endpoints
    path("api/", include("shipments.urls")),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
