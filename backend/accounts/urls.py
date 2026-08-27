from django.urls import path

from . import views

urlpatterns = [
    # ─── Existing endpoints (backward-compatible) ─────────────────────────────
    path('admin-exists', views.AdminExistsView.as_view(), name='admin-exists'),
    path('signup', views.SignupView.as_view(), name='signup'),
    path('login', views.LoginView.as_view(), name='login'),
    path('login/verify-otp', views.VerifyLoginOtpView.as_view(), name='login-verify-otp'),
    path('logout', views.LogoutView.as_view(), name='logout'),
    path('me', views.MeView.as_view(), name='me'),

    # ─── New auth endpoints ───────────────────────────────────────────────────
    path('register', views.RegisterView.as_view(), name='register'),
    path('verify-email', views.VerifyEmailView.as_view(), name='verify-email'),
    path('change-password', views.ChangePasswordView.as_view(), name='change-password'),
    path('password-reset/request', views.PasswordResetRequestView.as_view(), name='password-reset-request'),
    path('password-reset/confirm', views.PasswordResetConfirmView.as_view(), name='password-reset-confirm'),
]
