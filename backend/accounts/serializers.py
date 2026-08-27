from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from .models import Admin


class AdminSerializer(serializers.ModelSerializer):
    class Meta:
        model = Admin
        fields = ['id', 'name', 'email', 'is_verified', 'created_at']


class SignupSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=100)
    email = serializers.EmailField()
    password = serializers.CharField(min_length=6, write_only=True)

    def validate_email(self, value):
        return value.lower()

    def validate_password(self, value):
        try:
            validate_password(value)
        except DjangoValidationError as exc:
            raise serializers.ValidationError(list(exc.messages))
        return value


class LoginSerializer(serializers.Serializer):
    email = serializers.CharField(required=False, allow_blank=False, write_only=True)
    username = serializers.CharField(required=False, allow_blank=False, write_only=True)
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        email = attrs.get('email')
        username = attrs.get('username')

        if email and username:
            raise serializers.ValidationError({'username': 'Provide either email or username, not both.'})

        if not email and not username:
            raise serializers.ValidationError({'email': 'Email or username is required.'})

        if email:
            attrs['identifier'] = email.strip().lower()
        else:
            attrs['identifier'] = username.strip()

        return attrs


# ─── New auth serializers ─────────────────────────────────────────────────

class RegisterSerializer(serializers.Serializer):
    """Used by the new /api/auth/register/ endpoint."""
    name = serializers.CharField(max_length=100)
    email = serializers.EmailField()
    password = serializers.CharField(min_length=6, write_only=True)

    def validate_email(self, value):
        value = value.strip().lower()
        if Admin.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError('An account with this email already exists.')
        return value

    def validate_password(self, value):
        try:
            validate_password(value)
        except DjangoValidationError as exc:
            raise serializers.ValidationError(list(exc.messages))
        return value


class VerifyEmailSerializer(serializers.Serializer):
    uid = serializers.CharField()
    token = serializers.CharField()


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(min_length=6, write_only=True)

    def validate_new_password(self, value):
        try:
            validate_password(value)
        except DjangoValidationError as exc:
            raise serializers.ValidationError(list(exc.messages))
        return value


class VerifyLoginOtpSerializer(serializers.Serializer):
    """Step 2 of two-step login: { email, otp }."""
    email = serializers.EmailField(write_only=True)
    otp = serializers.RegexField(regex=r'^\d{6}$', write_only=True)

    def validate_email(self, value):
        return value.strip().lower()


class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()

    def validate_email(self, value):
        # Normalise but never hint whether the address exists.
        return value.strip().lower()


class PasswordResetConfirmSerializer(serializers.Serializer):
    uid = serializers.CharField()
    token = serializers.CharField()
    new_password = serializers.CharField(min_length=6, write_only=True)

    def validate_new_password(self, value):
        try:
            validate_password(value)
        except DjangoValidationError as exc:
            raise serializers.ValidationError(list(exc.messages))
        return value
