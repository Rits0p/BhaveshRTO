import sys
from pathlib import Path

import environ

BASE_DIR = Path(__file__).resolve().parent.parent

env = environ.Env(DEBUG=(bool, True))
environ.Env.read_env(BASE_DIR / '.env')

SECRET_KEY = env('SECRET_KEY', default='django-insecure-bhavesh-rto-crm-super-secret-key-2026')
DEBUG = env.bool('DEBUG', default=True)
ALLOWED_HOSTS = env.list('ALLOWED_HOSTS', default=['*'])

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # Third party
    'corsheaders',
    'rest_framework',
    'rest_framework_simplejwt',
    'django_filters',
    'drf_spectacular',
    'django_crontab',
    # Local apps
    'common',
    'accounts',
    'customers',
    'payments',
    'reminders',
    'remarks',
    'dashboard',
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': env('DB_NAME', default='rto'),
        'USER': env('DB_USER', default='pritesh'),
        'PASSWORD': env('DB_PASSWORD', default='Pritesh@2026'),
        'HOST': env('DB_HOST', default='localhost'),
        'PORT': env('DB_PORT', default='3306'),
        'OPTIONS': {'charset': 'utf8mb4'},
    }
}

AUTH_USER_MODEL = 'accounts.Admin'

# BCryptSHA256PasswordHasher is listed first purely for continuity with the
# bcrypt-hashed passwords used by this project's earlier iterations; Django's
# own PBKDF2 hasher (which follows) is equally secure and used for anything
# not already bcrypt-hashed.
PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.BCryptSHA256PasswordHasher',
    'django.contrib.auth.hashers.PBKDF2PasswordHasher',
    'django.contrib.auth.hashers.PBKDF2SHA1PasswordHasher',
    'django.contrib.auth.hashers.Argon2PasswordHasher',
]

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator', 'OPTIONS': {'min_length': 6}},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
]

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Asia/Kolkata'
USE_I18N = True
USE_TZ = True

STATIC_URL = 'static/'
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# The existing React frontend calls endpoints without a trailing slash
# (e.g. `/customers/${id}`); disabling APPEND_SLASH avoids Django issuing a
# 301 redirect that would silently downgrade POST/PUT/DELETE requests to GET.
APPEND_SLASH = False

# ─── CORS ──────────────────────────────────────────────────────────────────
FRONTEND_ORIGIN = env('FRONTEND_ORIGIN', default=env('FRONTEND_URL', default='http://localhost:5173'))
CORS_ALLOW_ALL_ORIGINS = DEBUG
CORS_ALLOWED_ORIGINS = [] if DEBUG else [FRONTEND_ORIGIN]
CORS_ALLOW_CREDENTIALS = True

# Django's CSRF middleware compares the request Origin against this list when
# the API is served from a different host than the SPA (Vite dev server).
CSRF_TRUSTED_ORIGINS = env.list(
    'CSRF_TRUSTED_ORIGINS',
    default=[FRONTEND_ORIGIN, 'http://127.0.0.1:5173'],
)

# ─── Session (30-minute authenticated sessions) ───────────────────────────
# Sessions are stored in the database (Django's default django_session table).
# SESSION_SAVE_EVERY_REQUEST gives a sliding window: each API call resets the
# 30-minute idle timer so an active user is never unexpectedly logged out.
SESSION_COOKIE_AGE = 1800              # seconds — 30 minutes
SESSION_EXPIRE_AT_BROWSER_CLOSE = True # also expire when tab/browser closes
SESSION_SAVE_EVERY_REQUEST = True      # sliding window
SESSION_COOKIE_HTTPONLY = True         # JS cannot read the cookie
SESSION_COOKIE_SAMESITE = 'Lax'       # CSRF protection
SESSION_COOKIE_SECURE = not DEBUG      # HTTPS-only in production
FRONTEND_URL = env('FRONTEND_URL', default=env('FRONTEND_ORIGIN', default='http://localhost:5173'))

# ─── Email delivery ───────────────────────────────────────────────────────
# Defaults to the console backend so the app works out of the box. Set
# EMAIL_HOST_USER / EMAIL_HOST_PASSWORD in .env to send real emails.
EMAIL_HOST_USER = env('EMAIL_HOST_USER', default='')
EMAIL_HOST_PASSWORD = env('EMAIL_HOST_PASSWORD', default='')

_explicit_backend = env('EMAIL_BACKEND', default='')
if _explicit_backend:
    EMAIL_BACKEND = _explicit_backend
elif EMAIL_HOST_USER and EMAIL_HOST_PASSWORD:
    EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
else:
    EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

EMAIL_HOST = env('EMAIL_HOST', default='smtp.gmail.com')
EMAIL_PORT = env.int('EMAIL_PORT', default=587)
EMAIL_USE_TLS = env.bool('EMAIL_USE_TLS', default=True)
DEFAULT_FROM_EMAIL = env('DEFAULT_FROM_EMAIL', default=EMAIL_HOST_USER or 'no-reply@bhaveshrto.local')

# ─── WhatsApp (Meta Cloud API & OpenWA Integration) ─────────────────────────
WHATSAPP_PROVIDER = env('WHATSAPP_PROVIDER', default='auto')  # 'auto', 'openwa', 'meta', 'stub'
WHATSAPP_API_TOKEN = env('WHATSAPP_API_TOKEN', default='')
WHATSAPP_PHONE_NUMBER_ID = env('WHATSAPP_PHONE_NUMBER_ID', default='')

OPENWA_SERVER_URL = env('OPENWA_SERVER_URL', default='http://localhost:2785')
OPENWA_SESSION_ID = env('OPENWA_SESSION_ID', default='default')
OPENWA_API_KEY = env('OPENWA_API_KEY', default='')

# ─── DRF ─────────────────────────────────────────────────────────────────
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.SessionAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.AllowAny',
    ],
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
        'rest_framework.renderers.BrowsableAPIRenderer',
    ],
    'DEFAULT_PARSER_CLASSES': [
        'rest_framework.parsers.JSONParser',
        'rest_framework.parsers.FormParser',
        'rest_framework.parsers.MultiPartParser',
    ],
    'DEFAULT_PAGINATION_CLASS': 'common.pagination.StandardResultsSetPagination',
    'DEFAULT_FILTER_BACKENDS': ['django_filters.rest_framework.DjangoFilterBackend'],
    'EXCEPTION_HANDLER': 'common.exceptions.api_exception_handler',
    'DEFAULT_THROTTLE_RATES': {
        'login': env('LOGIN_THROTTLE_RATE', default='5/hour'),
        'otp': env('OTP_THROTTLE_RATE', default='10/hour'),
        'register': env('REGISTER_THROTTLE_RATE', default='10/hour'),
        'password_reset': env('PASSWORD_RESET_THROTTLE_RATE', default='5/hour'),
    },
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
}

SPECTACULAR_SETTINGS = {
    'TITLE': 'Bhavesh RTO & Insurance Advisor CRM API',
    'DESCRIPTION': 'Single-admin CRM API for RTO & Insurance advisory operations.',
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
    'SCHEMA_PATH_PREFIX': '/api/',
}

# ─── Cron (daily expiry scan) ───────────────────────────────────────────────
# django-crontab shells out to the `crontab` binary, which doesn't exist on
# Windows — see DECISIONS.md. On Linux/prod, run:
#   python manage.py crontab add
# On Windows, schedule the same command via Task Scheduler instead:
#   python manage.py scan_expiring_customers
CRONJOBS = [
    ('0 7 * * *', 'django.core.management.call_command', ['scan_expiring_customers']),
]

# ─── Logging ────────────────────────────────────────────────────────────────
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'simple': {'format': '[{asctime}] {levelname} {name}: {message}', 'style': '{'},
    },
    'handlers': {
        'console': {'class': 'logging.StreamHandler', 'formatter': 'simple'},
    },
    'loggers': {
        'reminders': {'handlers': ['console'], 'level': 'INFO', 'propagate': False},
        'accounts': {'handlers': ['console'], 'level': 'INFO', 'propagate': False},
        'django': {'handlers': ['console'], 'level': 'WARNING', 'propagate': False},
    },
}

# Ensure emoji/unicode log messages never crash on Windows consoles that
# default to a non-UTF-8 codepage.
for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, 'reconfigure'):
        _stream.reconfigure(encoding='utf-8', errors='replace')
