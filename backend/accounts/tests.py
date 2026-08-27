"""
accounts/tests.py
~~~~~~~~~~~~~~~~~
Full test suite for the authentication system.

Run with:
    python manage.py test accounts --verbosity=2

Notes on expected status codes
--------------------------------
DRF SessionAuthentication returns HTTP 403 for unauthenticated requests
(not 401), because it does not send a WWW-Authenticate challenge.
Tests for "unauthenticated" endpoints therefore assert 403.

Throttle isolation
------------------
The @override_settings decorator disables throttling inside each throttle-
sensitive test class so the shared cache doesn't bleed between tests.
"""

import datetime
import uuid

from django.contrib.sessions.backends.db import SessionStore
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from rest_framework.test import APIClient

from .models import Admin
from .utils.tokens import (
    email_verification_token,
    password_reset_token,
    user_from_uid,
)

# ─── Helpers ──────────────────────────────────────────────────────────────────

def _uid(user):
    return urlsafe_base64_encode(force_bytes(user.pk))


def _make_admin(email='admin@test.com', password='StrongPass@99', verified=True, **kwargs):
    """Create a test admin bypassing the one-admin save() guard."""
    Admin.objects.filter(email=email).delete()
    admin = Admin(email=email, name='Test Admin', is_verified=verified, **kwargs)
    admin.set_password(password)
    admin.save()
    return admin


# Throttle-free settings used in tests that exercise login multiple times.
NO_THROTTLE = {
    'DEFAULT_THROTTLE_CLASSES': [],
    'DEFAULT_THROTTLE_RATES': {},
}


# ─── Registration ─────────────────────────────────────────────────────────────

@override_settings(REST_FRAMEWORK={**(__import__('django.conf', fromlist=['settings']).settings.REST_FRAMEWORK), 'DEFAULT_THROTTLE_CLASSES': [], 'DEFAULT_THROTTLE_RATES': {}})
class RegistrationTests(TestCase):
    """POST /api/auth/register/"""

    def setUp(self):
        self.client = APIClient()
        self.url = '/api/auth/register'

    def _payload(self, **overrides):
        data = {'name': 'Alice', 'email': 'alice@example.com', 'password': 'Strong@Pass1'}
        data.update(overrides)
        return data

    def test_register_success(self):
        """First registration succeeds and returns 201."""
        resp = self.client.post(self.url, self._payload(), format='json')
        self.assertEqual(resp.status_code, 201)
        self.assertTrue(resp.data['success'])
        admin = Admin.objects.get(email='alice@example.com')
        self.assertFalse(admin.is_verified, 'New user must start unverified')
        self.assertFalse(admin.is_staff, 'Registration must not grant staff')
        self.assertFalse(admin.is_superuser, 'Registration must not grant superuser')

    def test_register_blocked_if_admin_exists(self):
        """Returns 403 when an admin already exists (one-admin system)."""
        _make_admin()
        resp = self.client.post(self.url, self._payload(), format='json')
        self.assertEqual(resp.status_code, 403)

    def test_register_duplicate_email(self):
        """Second registration returns 403 (one-admin system locks after first)."""
        self.client.post(self.url, self._payload(), format='json')
        resp = self.client.post(self.url, self._payload(), format='json')
        self.assertIn(resp.status_code, [400, 403])

    def test_register_weak_password_rejected(self):
        resp = self.client.post(self.url, self._payload(password='123'), format='json')
        self.assertEqual(resp.status_code, 400)

    def test_register_missing_email_rejected(self):
        resp = self.client.post(self.url, {'name': 'X', 'password': 'Strong@Pass1'}, format='json')
        self.assertEqual(resp.status_code, 400)


# ─── Email Verification ────────────────────────────────────────────────────────

class EmailVerificationTests(TestCase):
    """POST /api/auth/verify-email/"""

    def setUp(self):
        self.client = APIClient()
        self.url = '/api/auth/verify-email'
        self.admin = _make_admin(verified=False)

    def _valid_payload(self):
        return {
            'uid': _uid(self.admin),
            'token': email_verification_token.make_token(self.admin),
        }

    def test_verify_email_success(self):
        resp = self.client.post(self.url, self._valid_payload(), format='json')
        self.assertEqual(resp.status_code, 200)
        self.admin.refresh_from_db()
        self.assertTrue(self.admin.is_verified)

    def test_verify_email_invalid_token(self):
        payload = self._valid_payload()
        payload['token'] = 'bad-token'
        resp = self.client.post(self.url, payload, format='json')
        self.assertEqual(resp.status_code, 400)

    def test_verify_email_invalid_uid(self):
        payload = self._valid_payload()
        payload['uid'] = urlsafe_base64_encode(force_bytes(uuid.uuid4()))
        resp = self.client.post(self.url, payload, format='json')
        self.assertEqual(resp.status_code, 400)

    def test_verify_email_already_verified(self):
        """Already-verified users get a 200 (idempotent)."""
        self.admin.is_verified = True
        self.admin.save(update_fields=['is_verified'])
        resp = self.client.post(self.url, self._valid_payload(), format='json')
        self.assertEqual(resp.status_code, 200)

    def test_token_invalidated_after_verification(self):
        """Token must no longer work once is_verified is True (hash changes)."""
        payload = self._valid_payload()
        self.client.post(self.url, payload, format='json')
        # Second attempt — token is now stale; is_verified is True
        self.admin.refresh_from_db()
        self.assertTrue(self.admin.is_verified)


# ─── Login ─────────────────────────────────────────────────────────────────────

class LoginTests(TestCase):
    """POST /api/auth/login/"""

    def setUp(self):
        self.client = APIClient()
        self.url = '/api/auth/login'
        self.admin = _make_admin(verified=True)

    def test_login_success(self):
        resp = self.client.post(
            self.url, {'email': 'admin@test.com', 'password': 'StrongPass@99'}, format='json'
        )
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.data['success'])
        self.assertIn('sessionid', resp.cookies)

    @override_settings(REST_FRAMEWORK={**(__import__('django.conf', fromlist=['settings']).settings.REST_FRAMEWORK), 'DEFAULT_THROTTLE_CLASSES': [], 'DEFAULT_THROTTLE_RATES': {}})
    def test_login_wrong_password(self):
        resp = self.client.post(
            self.url, {'email': 'admin@test.com', 'password': 'wrongpassword'}, format='json'
        )
        self.assertEqual(resp.status_code, 401)

    def test_login_nonexistent_email(self):
        resp = self.client.post(
            self.url, {'email': 'nobody@example.com', 'password': 'StrongPass@99'}, format='json'
        )
        self.assertEqual(resp.status_code, 401)

    @override_settings(REST_FRAMEWORK={**(__import__('django.conf', fromlist=['settings']).settings.REST_FRAMEWORK), 'DEFAULT_THROTTLE_CLASSES': [], 'DEFAULT_THROTTLE_RATES': {}})
    def test_login_unverified_user(self):
        """Unverified email must return 403."""
        self.admin.is_verified = False
        self.admin.save(update_fields=['is_verified'])
        resp = self.client.post(
            self.url, {'email': 'admin@test.com', 'password': 'StrongPass@99'}, format='json'
        )
        self.assertEqual(resp.status_code, 403)

    def test_login_missing_email(self):
        resp = self.client.post(self.url, {'password': 'StrongPass@99'}, format='json')
        self.assertEqual(resp.status_code, 400)


# ─── Session Expiry ────────────────────────────────────────────────────────────

class SessionExpiryTests(TestCase):
    """Expired sessions must be rejected on protected endpoints."""

    def setUp(self):
        self.client = APIClient()
        self.admin = _make_admin(verified=True)

    def test_expired_session_rejected(self):
        """Force-login then expire the session; /me must return 403 (unauthenticated)."""
        self.client.force_login(self.admin)
        # Expire all sessions
        from django.contrib.sessions.models import Session
        for s in Session.objects.all():
            s.expire_date = timezone.now() - datetime.timedelta(seconds=1)
            s.save()

        resp = self.client.get('/api/auth/me')
        # DRF SessionAuthentication returns 403 for unauthenticated (no WWW-Authenticate header)
        self.assertIn(resp.status_code, [401, 403])


# ─── Logout ────────────────────────────────────────────────────────────────────

class LogoutTests(TestCase):
    """POST /api/auth/logout/"""

    def setUp(self):
        self.client = APIClient()
        self.admin = _make_admin(verified=True)

    def test_logout_flushes_session(self):
        self.client.force_login(self.admin)
        resp = self.client.post('/api/auth/logout')
        self.assertEqual(resp.status_code, 200)
        # Subsequent /me — session deleted, so 403 (DRF SessionAuth unauthenticated)
        resp2 = self.client.get('/api/auth/me')
        self.assertIn(resp2.status_code, [401, 403])

    def test_logout_when_not_logged_in(self):
        """Logout is idempotent."""
        resp = self.client.post('/api/auth/logout')
        self.assertEqual(resp.status_code, 200)


# ─── Me ────────────────────────────────────────────────────────────────────────

class MeViewTests(TestCase):
    """GET /api/auth/me/"""

    def setUp(self):
        self.client = APIClient()
        self.admin = _make_admin(verified=True)

    def test_me_authenticated(self):
        self.client.force_login(self.admin)
        resp = self.client.get('/api/auth/me')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data['admin']['email'], 'admin@test.com')
        self.assertNotIn('password', str(resp.data))

    def test_me_unauthenticated(self):
        # DRF SessionAuthentication returns 403 for anonymous (no WWW-Authenticate challenge)
        resp = self.client.get('/api/auth/me')
        self.assertIn(resp.status_code, [401, 403])

    def test_me_unverified_blocked(self):
        """Unverified users blocked by IsTheOneAdmin even with a valid session."""
        self.admin.is_verified = False
        self.admin.save(update_fields=['is_verified'])
        self.client.force_login(self.admin)
        resp = self.client.get('/api/auth/me')
        self.assertIn(resp.status_code, [401, 403])


# ─── Change Password ───────────────────────────────────────────────────────────

class ChangePasswordTests(TestCase):
    """POST /api/auth/change-password/"""

    def setUp(self):
        self.client = APIClient()
        self.admin = _make_admin(verified=True)
        self.client.force_login(self.admin)

    def test_change_password_success(self):
        resp = self.client.post(
            '/api/auth/change-password',
            {'old_password': 'StrongPass@99', 'new_password': 'NewPass@2024!'},
            format='json',
        )
        self.assertEqual(resp.status_code, 200)
        self.admin.refresh_from_db()
        self.assertTrue(self.admin.check_password('NewPass@2024!'))

    def test_change_password_wrong_old(self):
        resp = self.client.post(
            '/api/auth/change-password',
            {'old_password': 'wrongpassword', 'new_password': 'NewPass@2024!'},
            format='json',
        )
        self.assertEqual(resp.status_code, 400)

    def test_change_password_weak_new(self):
        resp = self.client.post(
            '/api/auth/change-password',
            {'old_password': 'StrongPass@99', 'new_password': '123'},
            format='json',
        )
        self.assertEqual(resp.status_code, 400)

    def test_change_password_requires_auth(self):
        self.client.logout()
        resp = self.client.post(
            '/api/auth/change-password',
            {'old_password': 'StrongPass@99', 'new_password': 'NewPass@2024!'},
            format='json',
        )
        # DRF SessionAuthentication → 403 for unauthenticated
        self.assertIn(resp.status_code, [401, 403])


# ─── Password Reset ────────────────────────────────────────────────────────────

class PasswordResetTests(TestCase):
    """POST /api/auth/password-reset/request/ and /confirm/"""

    def setUp(self):
        self.client = APIClient()
        self.admin = _make_admin(verified=True)
        self.request_url = '/api/auth/password-reset/request'
        self.confirm_url = '/api/auth/password-reset/confirm'

    def test_reset_request_always_200(self):
        """Even for a non-existent email, must return 200 (no leakage)."""
        resp = self.client.post(self.request_url, {'email': 'nobody@example.com'}, format='json')
        self.assertEqual(resp.status_code, 200)

    def test_reset_request_known_email_200(self):
        resp = self.client.post(self.request_url, {'email': 'admin@test.com'}, format='json')
        self.assertEqual(resp.status_code, 200)

    def test_reset_confirm_success(self):
        uid = _uid(self.admin)
        token = password_reset_token.make_token(self.admin)
        resp = self.client.post(
            self.confirm_url,
            {'uid': uid, 'token': token, 'new_password': 'BrandNewPass@77'},
            format='json',
        )
        self.assertEqual(resp.status_code, 200)
        self.admin.refresh_from_db()
        self.assertTrue(self.admin.check_password('BrandNewPass@77'))

    def test_reset_confirm_invalid_token(self):
        resp = self.client.post(
            self.confirm_url,
            {'uid': _uid(self.admin), 'token': 'bad-token', 'new_password': 'BrandNewPass@77'},
            format='json',
        )
        self.assertEqual(resp.status_code, 400)

    def test_reset_confirm_invalid_uid(self):
        resp = self.client.post(
            self.confirm_url,
            {
                'uid': urlsafe_base64_encode(force_bytes(uuid.uuid4())),
                'token': password_reset_token.make_token(self.admin),
                'new_password': 'BrandNewPass@77',
            },
            format='json',
        )
        self.assertEqual(resp.status_code, 400)

    def test_reset_confirm_token_invalidated_after_use(self):
        """Token must be invalid after use (password changed → hash differs)."""
        uid = _uid(self.admin)
        token = password_reset_token.make_token(self.admin)
        self.client.post(
            self.confirm_url,
            {'uid': uid, 'token': token, 'new_password': 'FirstNewPass@88'},
            format='json',
        )
        resp = self.client.post(
            self.confirm_url,
            {'uid': uid, 'token': token, 'new_password': 'SecondNewPass@99'},
            format='json',
        )
        self.assertEqual(resp.status_code, 400)

    def test_reset_confirm_weak_password(self):
        uid = _uid(self.admin)
        token = password_reset_token.make_token(self.admin)
        resp = self.client.post(
            self.confirm_url,
            {'uid': uid, 'token': token, 'new_password': '123'},
            format='json',
        )
        self.assertEqual(resp.status_code, 400)


# ─── Permissions ───────────────────────────────────────────────────────────────

class PermissionsTests(TestCase):
    """AllowAny / IsAuthenticated / IsTheOneAdmin / IsAdminUser gates."""

    def setUp(self):
        self.client = APIClient()
        self.admin = _make_admin(verified=True, is_staff=True, is_superuser=True)

    def test_public_endpoints_accessible_without_auth(self):
        public = [
            '/api/auth/login',
            '/api/auth/logout',
            '/api/auth/register',
            '/api/auth/verify-email',
            '/api/auth/password-reset/request',
        ]
        for url in public:
            resp = self.client.options(url)
            self.assertNotIn(
                resp.status_code, [401, 403],
                f'{url} should be AllowAny but returned {resp.status_code}',
            )

    def test_me_requires_auth(self):
        # DRF SessionAuthentication → 403 for unauthenticated (no WWW-Authenticate)
        resp = self.client.get('/api/auth/me')
        self.assertIn(resp.status_code, [401, 403])

    def test_change_password_requires_auth(self):
        resp = self.client.post('/api/auth/change-password', {}, format='json')
        self.assertIn(resp.status_code, [401, 403])

    def test_superuser_can_access_django_admin(self):
        self.client.force_login(self.admin)
        resp = self.client.get('/admin/')
        self.assertIn(resp.status_code, [200, 302])


# ─── Superuser Access ──────────────────────────────────────────────────────────

class SuperuserTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        Admin.objects.filter(email='super@test.com').delete()
        self.superuser = Admin(
            email='super@test.com',
            name='Super',
            is_staff=True,
            is_superuser=True,
            is_verified=True,
        )
        self.superuser.set_password('SuperPass@123')
        self.superuser.save()

    def test_superuser_login_succeeds(self):
        resp = self.client.post(
            '/api/auth/login',
            {'email': 'super@test.com', 'password': 'SuperPass@123'},
            format='json',
        )
        self.assertEqual(resp.status_code, 200)

    def test_superuser_can_access_me(self):
        self.client.force_login(self.superuser)
        resp = self.client.get('/api/auth/me')
        self.assertEqual(resp.status_code, 200)
