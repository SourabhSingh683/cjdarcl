"""
accounts/views.py
=================
Auth + Notification API views for CJ Darcl LMS.

Endpoints:
  POST /api/auth/register/          — create user + profile
  POST /api/auth/login/             — username/password → JWT
  POST /api/auth/token/refresh/     — rotate access token
  GET  /api/auth/me/                — current user info
  POST /api/auth/otp/request/       — send OTP to phone (demo: returns OTP in response)
  POST /api/auth/otp/verify/        — verify OTP → JWT
  GET  /api/notifications/          — list notifications for current user
  PATCH /api/notifications/<id>/read/ — mark one notification as read
  POST /api/notifications/mark-all-read/ — mark all as read
"""

import logging

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework_simplejwt.views import TokenRefreshView as _BaseRefreshView

from .models import Notification, OTPRecord
from .serializers import (
    RegisterSerializer,
    LoginSerializer,
    VehicleLoginSerializer,
    CnnoLoginSerializer,
    OTPRequestSerializer,
    OTPVerifySerializer,
    MeSerializer,
    NotificationSerializer,
)
from .permissions import role_required

logger = logging.getLogger("accounts")


# ─── Registration ─────────────────────────────────────────────────────────────

@api_view(["POST"])
@permission_classes([AllowAny])
def register(request):
    """POST /api/auth/register/ — Register a new user with a role."""
    serializer = RegisterSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    user = serializer.save()
    logger.info(f"New user registered: {user.username} [{user.profile.role}]")
    return Response(
        {
            "message": f"User '{user.username}' registered successfully.",
            "username": user.username,
            "role": user.profile.role,
        },
        status=status.HTTP_201_CREATED,
    )


# ─── Username / Password Login ────────────────────────────────────────────────

@api_view(["POST"])
@permission_classes([AllowAny])
def login_view(request):
    """POST /api/auth/login/ — Authenticate with username + password."""
    serializer = LoginSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    user = serializer.validated_data["user"]
    from rest_framework_simplejwt.tokens import RefreshToken
    refresh = RefreshToken.for_user(user)

    profile = getattr(user, "profile", None)
    return Response(
        {
            "access": str(refresh.access_token),
            "refresh": str(refresh),
            "user": {
                "id": user.id,
                "username": user.username,
                "full_name": user.get_full_name() or user.username,
                "role": profile.role if profile else "unknown",
            },
        }
    )


@api_view(["POST"])
@permission_classes([AllowAny])
def vehicle_login(request):
    """POST /api/auth/vehicle-login/ — Driver login via gaadi number."""
    serializer = VehicleLoginSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    user = serializer.validated_data["user"]
    from rest_framework_simplejwt.tokens import RefreshToken
    refresh = RefreshToken.for_user(user)

    profile = getattr(user, "profile", None)
    return Response(
        {
            "access": str(refresh.access_token),
            "refresh": str(refresh),
            "user": {
                "id": user.id,
                "username": user.username,
                "full_name": user.get_full_name() or user.username,
                "role": profile.role if profile else "unknown",
            },
        }
    )


@api_view(["POST"])
@permission_classes([AllowAny])
def cnno_login(request):
    """POST /api/auth/cnno-login/ — Customer login via CN Number."""
    serializer = CnnoLoginSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    user = serializer.validated_data["user"]
    from rest_framework_simplejwt.tokens import RefreshToken
    refresh = RefreshToken.for_user(user)

    profile = getattr(user, "profile", None)
    return Response(
        {
            "access": str(refresh.access_token),
            "refresh": str(refresh),
            "user": {
                "id": user.id,
                "username": user.username,
                "full_name": user.get_full_name() or user.username,
                "role": profile.role if profile else "unknown",
            },
        }
    )


# ─── OTP Login — Step 1: Request ─────────────────────────────────────────────

@api_view(["POST"])
@permission_classes([AllowAny])
def otp_request(request):
    """
    POST /api/auth/otp/request/ — Generate and 'send' OTP.

    In production: integrate an SMS gateway (Twilio, MSG91, etc.).
    For demo: the OTP is returned directly in the response.
    """
    serializer = OTPRequestSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    phone = serializer.validated_data["phone"]
    otp_code, expires_at = serializer.create_otp(phone)

    logger.info(f"OTP requested for phone {phone}")

    # DEMO MODE: return OTP in response.
    # PRODUCTION: send via SMS and only return {"message": "OTP sent"}
    return Response(
        {
            "message": f"OTP sent to {phone}",
            "expires_at": expires_at.isoformat(),
            # ⚠️ Remove the line below in production!
            "_demo_otp": otp_code,
        }
    )


# ─── OTP Login — Step 2: Verify ──────────────────────────────────────────────

@api_view(["POST"])
@permission_classes([AllowAny])
def otp_verify(request):
    """POST /api/auth/otp/verify/ — Verify OTP, auto-create user, return JWT."""
    serializer = OTPVerifySerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    user, tokens = serializer.save()
    profile = getattr(user, "profile", None)

    logger.info(f"OTP login successful for phone {serializer.validated_data['phone']}")
    return Response(
        {
            **tokens,
            "user": {
                "id": user.id,
                "username": user.username,
                "full_name": user.get_full_name() or user.username,
                "role": profile.role if profile else "unknown",
            },
        }
    )


# ─── Me ───────────────────────────────────────────────────────────────────────

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def me_view(request):
    """GET /api/auth/me/ — Current user's info + role."""
    serializer = MeSerializer(request.user)
    return Response(serializer.data)


# ─── Notifications ────────────────────────────────────────────────────────────

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def notification_list(request):
    """GET /api/notifications/ — Paginated list for the current user."""
    qs = Notification.objects.filter(recipient=request.user)
    unread_count = qs.filter(is_read=False).count()

    # Simple manual pagination
    page = max(int(request.GET.get("page", 1)), 1)
    page_size = min(int(request.GET.get("page_size", 20)), 100)
    offset = (page - 1) * page_size
    total = qs.count()

    notifications = qs[offset: offset + page_size]
    serializer = NotificationSerializer(notifications, many=True)

    return Response(
        {
            "unread_count": unread_count,
            "total": total,
            "page": page,
            "page_size": page_size,
            "results": serializer.data,
        }
    )


@api_view(["PATCH"])
@permission_classes([IsAuthenticated])
def notification_mark_read(request, notif_id):
    """PATCH /api/notifications/<id>/read/ — Mark a specific notification as read."""
    try:
        notif = Notification.objects.get(id=notif_id, recipient=request.user)
    except Notification.DoesNotExist:
        return Response({"error": "Notification not found."}, status=status.HTTP_404_NOT_FOUND)

    notif.is_read = True
    notif.save(update_fields=["is_read"])
    return Response({"id": notif.id, "is_read": True})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def notification_mark_all_read(request):
    """POST /api/notifications/mark-all-read/ — Mark ALL as read."""
    count = Notification.objects.filter(
        recipient=request.user, is_read=False
    ).update(is_read=True)
    return Response({"marked_read": count})
