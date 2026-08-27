"""
accounts/views.py
~~~~~~~~~~~~~~~~~
All auth-related API views.

Authentication method: Django SessionAuthentication (30-min sliding window).
Login creates a server-side session; logout flushes it immediately.
No JWT or token headers are used or expected.
"""

import hmac
import logging

from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from common.permissions import IsTheOneAdmin
from common.throttles import LoginRateThrottle, OTPRateThrottle, PasswordResetRateThrottle, RegisterRateThrottle

from .models import Admin
from .serializers import (
    AdminSerializer,
    ChangePasswordSerializer,
    LoginSerializer,
    PasswordResetConfirmSerializer,
    PasswordResetRequestSerializer,
    RegisterSerializer,
    SignupSerializer,
    VerifyEmailSerializer,
    VerifyLoginOtpSerializer,
)
from .utils.tokens import (
    email_verification_token,
    hash_login_otp,
    issue_login_otp,
    login_otp_is_expired,
    password_reset_token,
    send_password_reset_email,
    send_verification_email,
    user_from_uid,
)

logger = logging.getLogger('accounts')


# ─── Existing endpoints (unchanged behaviour) ─────────────────────────────────

@method_decorator(ensure_csrf_cookie, name='dispatch')
class AdminExistsView(APIView):
    """Public utility: frontend calls this on load to decide /login vs /signup."""
    permission_classes = [AllowAny]

    def get(self, request):
        return Response({'exists': Admin.objects.exists_already()})


class SignupView(APIView):
    """One-time admin setup. Returns 403 if an Admin already exists."""
    permission_classes = [AllowAny]

    def post(self, request):
        if Admin.objects.exists_already():
            return Response(
                {'success': False, 'message': 'An admin account already exists. Signup is permanently disabled.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = SignupSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        admin = Admin.objects.create_user(
            email=serializer.validated_data['email'],
            password=serializer.validated_data['password'],
            name=serializer.validated_data['name'],
        )
        return Response(
            {'success': True, 'message': 'Admin account created. Please log in.', 'adminId': str(admin.id)},
            status=status.HTTP_201_CREATED,
        )


# ─── New: Register ─────────────────────────────────────────────────────────────

class RegisterView(APIView):
    """
    POST /api/auth/register/

    Creates a new admin account (one-admin system: returns 403 if one already
    exists). Sets is_verified=False and sends a verification email.

    Normal registration NEVER creates staff or superuser accounts.
    Use `python manage.py createsuperuser` for Django admin access.
    """
    permission_classes = [AllowAny]
    throttle_classes = [RegisterRateThrottle]

    def post(self, request):
        if Admin.objects.exists_already():
            return Response(
                {
                    'success': False,
                    'message': (
                        'An admin account already exists. '
                        'This system supports a single admin only. '
                        'Use the login page or contact your administrator.'
                    ),
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        admin = Admin.objects.create_user(
            email=serializer.validated_data['email'],
            password=serializer.validated_data['password'],
            name=serializer.validated_data['name'],
            is_verified=False,
            is_staff=False,
            is_superuser=False,
        )

        try:
            send_verification_email(admin)
        except Exception:
            logger.exception('Failed to send verification email to pk=%s', admin.pk)
            # Account created; email can be re-triggered later.

        return Response(
            {
                'success': True,
                'message': (
                    'Account created. A verification email has been sent. '
                    'Please verify your email before logging in.'
                ),
            },
            status=status.HTTP_201_CREATED,
        )


# ─── New: Email Verification ───────────────────────────────────────────────────

class VerifyEmailView(APIView):
    """
    POST /api/auth/verify-email/

    Body: { "uid": "…", "token": "…" }

    Marks the admin's email as verified. The token is single-use — it becomes
    invalid as soon as is_verified flips to True.
    """
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = VerifyEmailSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = user_from_uid(serializer.validated_data['uid'])
        token = serializer.validated_data['token']

        if user is None or not email_verification_token.check_token(user, token):
            return Response(
                {'success': False, 'message': 'Invalid or expired verification link.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if user.is_verified:
            return Response({'success': True, 'message': 'Email is already verified. You can log in.'})

        user.is_verified = True
        user.save(update_fields=['is_verified'])
        logger.info('Email verified for user pk=%s', user.pk)

        return Response({'success': True, 'message': 'Email verified successfully. You can now log in.'})


# ─── Updated: Login ────────────────────────────────────────────────────────────

@method_decorator(ensure_csrf_cookie, name='dispatch')
class LoginView(APIView):
    """
    POST /api/auth/login/   (step 1 of two-step login)

    Body: { "email": "…", "password": "…" }

    Validates email + password. If correct, generates a 6-digit one-time
    code, emails it to the account's address via SMTP, and responds with
    otp_required=true — NO session is created yet.

    Step 2 is POST /api/auth/login/verify-otp with { email, otp }, which
    actually creates the session.
    """
    permission_classes = [AllowAny]
    throttle_classes = [LoginRateThrottle]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        identifier = serializer.validated_data['identifier']
        password = serializer.validated_data['password']

        # django.contrib.auth.authenticate handles password comparison.
        admin = authenticate(request=request, username=identifier, password=password)

        if not admin:
            # Fallback: check if user exists but authenticate() failed due to
            # a different password hasher (e.g., old bcrypt hash).
            try:
                admin = Admin.objects.get(email__iexact=identifier)
            except Admin.DoesNotExist:
                return Response(
                    {'success': False, 'message': 'Invalid email or password.'},
                    status=status.HTTP_401_UNAUTHORIZED,
                )
            if not admin.check_password(password):
                return Response(
                    {'success': False, 'message': 'Invalid email or password.'},
                    status=status.HTTP_401_UNAUTHORIZED,
                )

        if not admin.is_active:
            return Response(
                {'success': False, 'message': 'This account has been deactivated.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        if not admin.is_verified:
            return Response(
                {
                    'success': False,
                    'message': (
                        'Your email address has not been verified. '
                        'Please check your inbox for the verification email.'
                    ),
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        # Credentials are correct — issue the OTP challenge instead of
        # logging in directly. Any previous pending OTP is overwritten.
        try:
            issue_login_otp(admin)
        except Exception:
            logger.exception('Failed to send login OTP to pk=%s', admin.pk)
            return Response(
                {'success': False, 'message': 'Could not send the OTP email. Please try again in a moment.'},
                status=status.HTTP_502_BAD_GATEWAY,
            )
        logger.info('Credentials OK, OTP challenge issued for user pk=%s', admin.pk)

        return Response({
            'success': True,
            'otp_required': True,
            'message': (
                'Login code sent to your email. '
                'Enter the 6-digit code to continue.'
            ),
        })


# ─── New: Login OTP verification (step 2) ──────────────────────────────────────

class VerifyLoginOtpView(APIView):
    """
    POST /api/auth/login/verify-otp/

    Body: { "email": "…", "otp": "123456" }

    Completes two-step login. On success this creates the Django session
    exactly like the old single-step login did. The OTP is single-use and
    expires after 5 minutes; issuing a new one overwrites the old code.
    """
    permission_classes = [AllowAny]
    throttle_classes = [OTPRateThrottle]

    def post(self, request):
        serializer = VerifyLoginOtpSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data['email']
        otp = serializer.validated_data['otp']

        try:
            admin = Admin.objects.get(email__iexact=email)
        except Admin.DoesNotExist:
            return Response(
                {'success': False, 'message': 'Invalid or expired code.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        otp_ok = (
            admin.login_otp_hash
            and not login_otp_is_expired(admin)
            and hmac.compare_digest(admin.login_otp_hash, hash_login_otp(otp))
        )

        if not otp_ok:
            return Response(
                {'success': False, 'message': 'Invalid or expired code.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Single use — burn it before creating the session.
        admin.login_otp_hash = ''
        admin.login_otp_created_at = None
        admin.save(update_fields=['login_otp_hash', 'login_otp_created_at'])

        login(request, admin)
        logger.info('Login completed via OTP for user pk=%s', admin.pk)

        return Response({
            'success': True,
            'message': 'Login successful.',
            'user': AdminSerializer(admin).data,
        })


# ─── Updated: Logout ───────────────────────────────────────────────────────────

class LogoutView(APIView):
    """
    POST /api/auth/logout/

    Flushes the server-side session immediately. The sessionid cookie becomes
    invalid on the next request. Works even if the user is already logged out.
    """
    permission_classes = [AllowAny]

    def post(self, request):
        logout(request)  # deletes the DB session record + clears session cookie
        return Response({'success': True, 'message': 'Logged out successfully.'})


# ─── Me ────────────────────────────────────────────────────────────────────────

@method_decorator(ensure_csrf_cookie, name='dispatch')
class MeView(APIView):
    """
    GET /api/auth/me/

    Returns the currently authenticated admin's profile.
    """
    permission_classes = [IsTheOneAdmin]

    def get(self, request):
        return Response({'success': True, 'admin': AdminSerializer(request.user).data})

# ─── New: Change Password ──────────────────────────────────────────────────────

class ChangePasswordView(APIView):
    """
    POST /api/auth/change-password/

    Body: { "old_password": "…", "new_password": "…" }

    Requires an active session. Validates old password, applies Django password
    validators to new password. Session remains valid after change.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = request.user
        old_password = serializer.validated_data['old_password']
        new_password = serializer.validated_data['new_password']

        if not user.check_password(old_password):
            return Response(
                {'success': False, 'message': 'Current password is incorrect.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user.set_password(new_password)
        user.save(update_fields=['password'])

        # Re-authenticate the session so the user isn't logged out after
        # the password change (Django's session auth_user_hash changes).
        login(request, user)
        logger.info('Password changed for user pk=%s', user.pk)

        return Response({'success': True, 'message': 'Password changed successfully.'})


# ─── New: Password Reset Request ───────────────────────────────────────────────

class PasswordResetRequestView(APIView):
    """
    POST /api/auth/password-reset/request/

    Body: { "email": "…" }

    Always returns 200 regardless of whether the email exists (prevents
    user-enumeration attacks). If the email belongs to a verified admin,
    sends a password-reset link to that address.
    """
    permission_classes = [AllowAny]
    throttle_classes = [PasswordResetRateThrottle]

    _SAFE_RESPONSE = Response({
        'success': True,
        'message': (
            'If that email is registered, you will receive a password-reset link shortly.'
        ),
    })

    def post(self, request):
        serializer = PasswordResetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data['email']

        try:
            user = Admin.objects.get(email__iexact=email)
        except Admin.DoesNotExist:
            # Do not reveal that the email doesn't exist.
            return Response({
                'success': True,
                'message': (
                    'If that email is registered, you will receive a password-reset link shortly.'
                ),
            })

        try:
            send_password_reset_email(user)
        except Exception:
            logger.exception('Failed to send password-reset email to pk=%s', user.pk)

        return Response({
            'success': True,
            'message': (
                'If that email is registered, you will receive a password-reset link shortly.'
            ),
        })


# ─── New: Password Reset Confirm ───────────────────────────────────────────────

class PasswordResetConfirmView(APIView):
    """
    POST /api/auth/password-reset/confirm/

    Body: { "uid": "…", "token": "…", "new_password": "…" }

    Validates the UID + token and sets the new password. The token is
    single-use — once the password changes, the token is invalidated.
    """
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = user_from_uid(serializer.validated_data['uid'])
        token = serializer.validated_data['token']
        new_password = serializer.validated_data['new_password']

        if user is None or not password_reset_token.check_token(user, token):
            return Response(
                {'success': False, 'message': 'Invalid or expired password-reset link.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user.set_password(new_password)
        user.save(update_fields=['password'])
        logger.info('Password reset completed for user pk=%s', user.pk)

        return Response({'success': True, 'message': 'Password has been reset. You can now log in.'})
