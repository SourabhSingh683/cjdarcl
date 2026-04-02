"""
accounts/serializers.py
=======================
DRF serializers for auth, OTP, user profile, and notifications.
"""

import random
import string
from datetime import timedelta

from django.contrib.auth.models import User
from django.utils import timezone
from rest_framework import serializers
from rest_framework_simplejwt.tokens import RefreshToken

from .models import UserProfile, OTPRecord, Notification


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _generate_otp(length=6):
    """Generate a random numeric OTP."""
    return "".join(random.choices(string.digits, k=length))


def _get_tokens_for_user(user):
    """Return JWT access + refresh tokens as strings."""
    refresh = RefreshToken.for_user(user)
    return {
        "access": str(refresh.access_token),
        "refresh": str(refresh),
    }


# ─── Registration ─────────────────────────────────────────────────────────────

class RegisterSerializer(serializers.Serializer):
    """
    Register a new user with a role.
    For drivers: supply vehicle_no.
    For customers: supply customer_id.
    """

    username = serializers.CharField(max_length=150)
    password = serializers.CharField(write_only=True, min_length=6)
    email = serializers.EmailField(required=False, allow_blank=True)
    first_name = serializers.CharField(required=False, allow_blank=True)
    last_name = serializers.CharField(required=False, allow_blank=True)
    role = serializers.ChoiceField(choices=["manager", "driver", "customer"])
    phone = serializers.CharField(required=False, allow_blank=True)
    vehicle_no = serializers.CharField(required=False, allow_blank=True)
    customer_id = serializers.CharField(required=False, allow_blank=True)

    def validate_username(self, value):
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError("Username already exists.")
        return value

    def create(self, validated_data):
        user = User.objects.create_user(
            username=validated_data["username"],
            password=validated_data["password"],
            email=validated_data.get("email", ""),
            first_name=validated_data.get("first_name", ""),
            last_name=validated_data.get("last_name", ""),
        )
        UserProfile.objects.create(
            user=user,
            role=validated_data["role"],
            phone=validated_data.get("phone") or None,
            vehicle_no=validated_data.get("vehicle_no", ""),
            customer_id=validated_data.get("customer_id", ""),
        )
        return user


# ─── Standard Login ──────────────────────────────────────────────────────────

class LoginSerializer(serializers.Serializer):
    """Username + password login — returns JWT tokens."""

    username = serializers.CharField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        from django.contrib.auth import authenticate
        user = authenticate(username=attrs["username"], password=attrs["password"])
        if not user:
            raise serializers.ValidationError("Invalid username or password.")
        if not user.is_active:
            raise serializers.ValidationError("User account is disabled.")
        attrs["user"] = user
        return attrs


# ─── OTP Flow ────────────────────────────────────────────────────────────────

class OTPRequestSerializer(serializers.Serializer):
    """Step 1: request an OTP for a phone number."""

    phone = serializers.CharField(max_length=15)

    def validate_phone(self, value):
        # Normalize: strip spaces
        return value.strip().replace(" ", "")

    def create_otp(self, phone):
        """
        Invalidate old OTPs for this phone, generate a new one.
        Returns (otp_code, expires_at).
        In production, send via SMS gateway. Here we return it directly for demo.
        """
        # Mark all existing OTPs for this phone as used
        OTPRecord.objects.filter(phone=phone, is_used=False).update(is_used=True)

        code = _generate_otp()
        expires_at = timezone.now() + timedelta(minutes=10)
        OTPRecord.objects.create(phone=phone, otp=code, expires_at=expires_at)
        return code, expires_at


class OTPVerifySerializer(serializers.Serializer):
    """Step 2: verify OTP + return JWT tokens. Auto-creates user if phone is new."""

    phone = serializers.CharField(max_length=15)
    otp = serializers.CharField(max_length=6)
    # Optional fields for first-time registration
    role = serializers.ChoiceField(
        choices=["manager", "driver", "customer"], required=False, default="customer"
    )
    vehicle_no = serializers.CharField(required=False, allow_blank=True, default="")
    customer_id = serializers.CharField(required=False, allow_blank=True, default="")

    def validate(self, attrs):
        phone = attrs["phone"].strip().replace(" ", "")
        otp_code = attrs["otp"]

        record = (
            OTPRecord.objects
            .filter(phone=phone, is_used=False)
            .order_by("-created_at")
            .first()
        )
        if not record:
            raise serializers.ValidationError({"otp": "No active OTP found. Please request a new one."})
        if not record.is_valid:
            raise serializers.ValidationError({"otp": "OTP has expired. Please request a new one."})
        if record.otp != otp_code:
            raise serializers.ValidationError({"otp": "Invalid OTP."})

        attrs["_otp_record"] = record
        attrs["phone"] = phone
        return attrs

    def save(self):
        """Mark OTP used, get-or-create user, return tokens."""
        attrs = self.validated_data
        phone = attrs["phone"]
        record = attrs["_otp_record"]
        record.is_used = True
        record.save(update_fields=["is_used"])

        # Try to find existing profile with this phone
        profile = UserProfile.objects.filter(phone=phone).first()
        if profile:
            user = profile.user
        else:
            # Auto-create user from phone number
            username = f"user_{phone.lstrip('+')}"
            user, created = User.objects.get_or_create(username=username)
            if created:
                user.set_unusable_password()
                user.save()
            profile, _ = UserProfile.objects.get_or_create(user=user)
            profile.phone = phone
            profile.role = attrs.get("role", "customer")
            profile.vehicle_no = attrs.get("vehicle_no", "")
            profile.customer_id = attrs.get("customer_id", "")
            profile.is_phone_verified = True
            profile.save()

        return user, _get_tokens_for_user(user)


# ─── User Profile ────────────────────────────────────────────────────────────

class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserProfile
        fields = ["role", "phone", "vehicle_no", "customer_id", "is_phone_verified"]


class MeSerializer(serializers.ModelSerializer):
    """Full current-user serializer used by /api/auth/me/."""

    profile = UserProfileSerializer(read_only=True)
    full_name = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ["id", "username", "email", "first_name", "last_name", "full_name", "profile"]

    def get_full_name(self, obj):
        return obj.get_full_name() or obj.username


# ─── Notifications ───────────────────────────────────────────────────────────

class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = [
            "id", "notif_type", "title", "message",
            "shipment_ref", "is_read", "created_at",
        ]
        read_only_fields = fields
