"""
accounts/urls.py
================
URL routing for authentication and notification endpoints.
"""

from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from . import views

app_name = "accounts"

urlpatterns = [
    # ── Standard auth ──────────────────────────────────────────────────────
    path("register/",           views.register,           name="register"),
    path("login/",              views.login_view,          name="login"),
    path("vehicle-login/",      views.vehicle_login,       name="vehicle-login"),
    path("cnno-login/",         views.cnno_login,          name="cnno-login"),
    path("token/refresh/",       TokenRefreshView.as_view(), name="token-refresh"),
    path("me/",                 views.me_view,             name="me"),

    # ── OTP auth ───────────────────────────────────────────────────────────
    path("otp/request/",        views.otp_request,         name="otp-request"),
    path("otp/verify/",         views.otp_verify,          name="otp-verify"),
]
