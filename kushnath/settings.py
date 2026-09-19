"""
Merged Django settings: Kushnath Live (ecommerce) + Billvice (billing/POS).
"""

from pathlib import Path
from datetime import timedelta
import os

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.environ.get(
    "DJANGO_SECRET_KEY",
    "django-insecure-merged-kushnath-change-me-in-production",
)

# Production: export DJANGO_DEBUG=false
DEBUG = os.environ.get("DJANGO_DEBUG", "true").lower() in ("1", "true", "yes")

ALLOWED_HOSTS = [
    "localhost",
    "127.0.0.1",
    "0.0.0.0",
    "192.168.29.206",
    "192.168.1.51",
    "192.168.29.121",
    "www.kushnathayurveda.com",
    "kushnathayurveda.com",
]
# Extra hosts: DJANGO_ALLOWED_HOSTS=example.com,www.example.com
_extra_hosts = os.environ.get("DJANGO_ALLOWED_HOSTS", "")
if _extra_hosts.strip():
    ALLOWED_HOSTS.extend(h.strip() for h in _extra_hosts.split(",") if h.strip())
if DEBUG:
    ALLOWED_HOSTS = ["*"]

CSRF_TRUSTED_ORIGINS = [
    "http://127.0.0.1:8000",
    "https://127.0.0.1:8000",
    "http://localhost:8000",
    "https://localhost:8000",
    "http://localhost:1001",
    "http://127.0.0.1:1001",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:5174",
    "http://127.0.0.1:5174",
    "http://192.168.29.206:8000",
    "https://192.168.29.206:8000",
    "http://192.168.1.51:8000",
    "https://192.168.1.51:8000",
    "http://192.168.29.206:1001",
    "http://192.168.1.51:1001",
    "https://www.kushnathayurveda.com",
    "https://kushnathayurveda.com",
]
_extra_csrf = os.environ.get("DJANGO_CSRF_TRUSTED_ORIGINS", "")
if _extra_csrf.strip():
    CSRF_TRUSTED_ORIGINS.extend(o.strip() for o in _extra_csrf.split(",") if o.strip())

# Trust nginx/Apache HTTPS headers (required for session cookies behind proxy)
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
USE_X_FORWARDED_HOST = True

INSTALLED_APPS = [
    "daphne",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "channels",
    "rest_framework",
    "corsheaders",
    # Billvice (POS / inventory / invoices)
    "billing",
    # Kushnath Live (ecommerce storefront)
    "dashboard",
    "coupon",
    "customer",
    "cart",
    "orders",
    "advertisement",
    "authentication",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "kushnath.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        # Do NOT put frontend/dist or build/ here — Billvice SPA is served by
        # kushnath.billvice_views.serve_billvice from BILLVICE_DIST_DIR only.
        # Putting dist/build in DIRS caused wrong index.html on deploy.
        "DIRS": [
            BASE_DIR / "templates",
            BASE_DIR / "billing" / "templates",
        ],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "kushnath_dashboard.context_processors.storefront",
            ],
        },
    },
]

WSGI_APPLICATION = "kushnath.wsgi.application"
ASGI_APPLICATION = "kushnath.asgi.application"

CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels.layers.InMemoryChannelLayer",
    },
}

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        # Keep this file OUTSIDE the zip you re-upload, or set DJANGO_DB_PATH.
        # Overwriting db.sqlite3 on deploy deletes all Billvice data.
        "NAME": Path(
            os.environ.get("DJANGO_DB_PATH", str(BASE_DIR / "db.sqlite3"))
        ),
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "Asia/Kolkata"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATICFILES_DIRS = [
    BASE_DIR / "billing" / "static",
]
STATIC_ROOT = BASE_DIR / "staticfiles"

# Kushnath Live legacy React build (catch-all assets only; not Billvice)
FRONTEND_BUILD_DIR = BASE_DIR / "build"

# Billvice React SPA — produced by: cd frontend && npm run build
# Must contain index.html with asset URLs under /billvice/
BILLVICE_DIST_DIR = BASE_DIR / "frontend" / "dist"

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Combined auth: JWT for ecommerce + Session for Billvice POS.
# Views that need auth set permission_classes explicitly (billing ViewSets
# inherit IsAuthenticated below via DEFAULT; public catalog uses AllowAny).
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(days=5),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
}

CORS_ALLOW_CREDENTIALS = True
CORS_ALLOWED_ORIGINS = [
    "http://localhost:1001",
    "http://127.0.0.1:1001",
    "http://localhost:8000",
    "http://127.0.0.1:8000",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:5174",
    "http://127.0.0.1:5174",
    "http://192.168.29.206:1001",
    "http://192.168.1.51:1001",
    "http://192.168.29.206:8000",
    "http://192.168.1.51:8000",
    "https://www.kushnathayurveda.com",
    "https://kushnathayurveda.com",
]

CORS_ALLOW_METHODS = ["DELETE", "GET", "OPTIONS", "PATCH", "POST", "PUT"]
CORS_ALLOW_HEADERS = [
    "accept",
    "accept-encoding",
    "authorization",
    "content-type",
    "dnt",
    "origin",
    "user-agent",
    "x-csrftoken",
    "x-requested-with",
]

CSRF_COOKIE_HTTPONLY = False
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SAMESITE = "Lax"
SESSION_COOKIE_AGE = 60 * 60 * 24 * 14  # 14 days
SESSION_SAVE_EVERY_REQUEST = True  # keep session alive while using the app
SESSION_EXPIRE_AT_BROWSER_CLOSE = False

# Behind HTTPS nginx, secure cookies when DEBUG is off
CSRF_COOKIE_SECURE = not DEBUG
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_NAME = "csrftoken"
SESSION_COOKIE_NAME = "sessionid"
SESSION_COOKIE_PATH = "/"
CSRF_COOKIE_PATH = "/"

LOGIN_REDIRECT_URL = "/billvice/"
LOGIN_URL = "login"

# Delhivery courier (from Kushnath Live)
DELHIVERY_API_TOKEN = os.environ.get(
    "DELHIVERY_API_TOKEN", "8c14830cadfdb3c4f169b053020659593d3baecc"
)
DELHIVERY_BASE_URL = "https://track.delhivery.com"
DELHIVERY_PICKUP_NAME = "Quirckart"

# Razorpay (from Kushnath Live)
RAZORPAY_KEY_ID = os.environ.get("RAZORPAY_KEY_ID", "rzp_live_RFVSx4eax0xMjW")
RAZORPAY_KEY_SECRET = os.environ.get("RAZORPAY_KEY_SECRET", "aMrwajwB1bKan4upU3ukXT24")
RAZORPAY_MODE = os.environ.get("RAZORPAY_MODE", "live")

# Firebase phone OTP (from Kushnath Live)
FIREBASE_CONFIG = {
    "apiKey": "AIzaSyAvRobkSXCsNFOdogIFwKuN95nLOQIkXoI",
    "authDomain": "kushnath-19401.firebaseapp.com",
    "projectId": "kushnath-19401",
    "storageBucket": "kushnath-19401.firebasestorage.app",
    "messagingSenderId": "704991416939",
    "appId": "1:704991416939:web:ccf9033058042dadf4d72e",
    "measurementId": "G-VYRLCTDEKM",
}
