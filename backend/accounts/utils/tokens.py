"""
accounts/utils/tokens.py
~~~~~~~~~~~~~~~~~~~~~~~~
Secure token generation and email delivery for:
  - Email address verification
  - Password reset

Both use Django's PasswordResetTokenGenerator mechanism so tokens are:
  - Cryptographically signed with SECRET_KEY
  - Single-use (hash includes mutable state that changes after use)
  - Time-limited (Django checks age via PASSWORD_RESET_TIMEOUT, default 3 days)
"""

import hashlib
import logging
import secrets
from datetime import timedelta
from urllib.parse import urlencode

from django.conf import settings
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.core.mail import send_mail
from django.utils import timezone
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode

logger = logging.getLogger('accounts')


# ─── Token generators ─────────────────────────────────────────────────────────

class _EmailVerificationTokenGenerator(PasswordResetTokenGenerator):
    """Token tied to the current is_verified state.

    Once the user is verified (is_verified=True), this token becomes
    invalid because the hash value changes — preventing replay attacks.
    """

    def _make_hash_value(self, user, timestamp):
        return (
            str(user.pk)
            + str(timestamp)
            + str(user.is_verified)
            + str(user.email)
        )


class _PasswordResetTokenGenerator(PasswordResetTokenGenerator):
    """Standard password-reset token.

    Invalidated as soon as password or last_login changes (Django default).
    """

    def _make_hash_value(self, user, timestamp):
        return (
            str(user.pk)
            + str(timestamp)
            + str(user.password)
            + str(user.last_login)
        )


email_verification_token = _EmailVerificationTokenGenerator()
password_reset_token = _PasswordResetTokenGenerator()


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _uid_for(user) -> str:
    return urlsafe_base64_encode(force_bytes(user.pk))


def user_from_uid(uid: str):
    """Decode a base64 uid back to a user, or return None on failure."""
    from accounts.models import Admin  # local import to avoid circular deps
    try:
        pk = force_str(urlsafe_base64_decode(uid))
        return Admin.objects.get(pk=pk)
    except (Admin.DoesNotExist, ValueError, TypeError, OverflowError):
        return None


def send_verification_email(user) -> None:
    """Send an email-verification link to *user*.

    The link points to FRONTEND_URL/auth/verify-email?uid=…&token=…
    The raw token is never logged.
    """
    uid = _uid_for(user)
    token = email_verification_token.make_token(user)
    params = urlencode({'uid': uid, 'token': token})
    frontend_url = getattr(settings, 'FRONTEND_URL', 'http://localhost:5173')
    verify_url = f'{frontend_url}/auth/verify-email?{params}'

    send_mail(
        subject='Verify your email — Bhavesh RTO CRM',
        message=(
            f'Hi {user.name},\n\n'
            f'Please verify your email address by clicking the link below:\n\n'
            f'{verify_url}\n\n'
            f'This link expires in 3 days. If you did not create this account, '
            f'you can safely ignore this email.\n\n'
            f'— Bhavesh RTO & Insurance Advisor'
        ),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
        fail_silently=False,
    )
    logger.info('Verification email queued for user pk=%s', user.pk)


def send_password_reset_email(user) -> None:
    """Send a password-reset link to *user*.

    The link points to FRONTEND_URL/auth/reset-password?uid=…&token=…
    Always called even when the address does not match a user account —
    the caller decides whether to actually invoke this function.
    """
    uid = _uid_for(user)
    token = password_reset_token.make_token(user)
    params = urlencode({'uid': uid, 'token': token})
    frontend_url = getattr(settings, 'FRONTEND_URL', 'http://localhost:5173')
    reset_url = f'{frontend_url}/auth/reset-password?{params}'

    send_mail(
        subject='Reset your password — Bhavesh RTO CRM',
        message=(
            f'Hi {user.name},\n\n'
            f'Click the link below to reset your password:\n\n'
            f'{reset_url}\n\n'
            f'This link expires in 3 days and can only be used once.\n'
            f'If you did not request a password reset, you can safely ignore '
            f'this email.\n\n'
            f'— Bhavesh RTO & Insurance Advisor'
        ),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
        fail_silently=False,
    )
    logger.info('Password-reset email queued for user pk=%s', user.pk)


# ─── Login OTP (two-step login) ───────────────────────────────────────────────

LOGIN_OTP_VALIDITY = timedelta(minutes=5)


def generate_login_otp() -> str:
    """Return a cryptographically random 6-digit code as a string."""
    return f'{secrets.randbelow(1_000_000):06d}'


def hash_login_otp(otp: str) -> str:
    """SHA-256 hex digest — the plain code is never persisted."""
    return hashlib.sha256(otp.encode('utf-8')).hexdigest()


def login_otp_is_expired(user) -> bool:
    if not user.login_otp_created_at:
        return True
    return timezone.now() - user.login_otp_created_at > LOGIN_OTP_VALIDITY


def issue_login_otp(user) -> str:
    """Create, store (hashed) and email a fresh login OTP for *user*.

    Returns the plain code only for the caller's convenience in tests;
    production callers should ignore it.
    """
    otp = generate_login_otp()
    user.login_otp_hash = hash_login_otp(otp)
    user.login_otp_created_at = timezone.now()
    user.save(update_fields=['login_otp_hash', 'login_otp_created_at'])

    send_mail(
        subject='Your login code — Bhavesh RTO CRM',
        message=(
            f'Hi {user.name},\n\n'
            f'Your one-time login code is:\n\n'
            f'    {otp}\n\n'
            f'It expires in 5 minutes and can be used only once.\n'
            f'If you did not try to log in, please ignore this email and '
            f'consider changing your password.\n\n'
            f'— Bhavesh RTO & Insurance Advisor'
        ),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
        fail_silently=False,
    )
    logger.info('Login OTP emailed to user pk=%s', user.pk)
    return otp
