"""
Django settings for cfehome project using Django 6.0.
"""

from pathlib import Path

from decouple import Csv
from django.core.exceptions import ImproperlyConfigured
from django.core.management.utils import get_random_secret_key

from helpers import config

from .installed import INSTALLED_APPS as PROJECT_INSTALLED_APPS

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/6.0/howto/deployment/checklist/

DEBUG = config("DJANGO_DEBUG", cast=bool, default=False)
SECRET_KEY = config("DJANGO_SECRET_KEY", default="")
if not SECRET_KEY.strip():
    if not DEBUG:
        raise ImproperlyConfigured("Set DJANGO_SECRET_KEY when DJANGO_DEBUG is false.")
    SECRET_KEY = get_random_secret_key()

PORT = config("PORT", cast=int, default=8000)

ALLOWED_HOSTS = config("DJANGO_ALLOWED_HOSTS", cast=Csv(), default="")
CSRF_TRUSTED_ORIGINS = config("DJANGO_CSRF_TRUSTED_ORIGINS", cast=Csv(), default="")
APPEND_SLASH = config("DJANGO_APPEND_SLASH", cast=bool, default=True)

# Allow the container and Railway probes and the domains assigned to this service.
railway_public_domain = config("RAILWAY_PUBLIC_DOMAIN", default="")
for host in (
    "localhost",
    "127.0.0.1",
    "[::1]",
    "healthcheck.railway.app",
    railway_public_domain,
    config("RAILWAY_PRIVATE_DOMAIN", default=""),
):
    if host and host not in ALLOWED_HOSTS:
        ALLOWED_HOSTS.append(host)

if railway_public_domain:
    CSRF_TRUSTED_ORIGINS.append(f"https://{railway_public_domain}")

if DEBUG:
    ALLOWED_HOSTS += ["[::]"]
    CSRF_TRUSTED_ORIGINS += [
        f"http://localhost:{PORT}",
        f"http://127.0.0.1:{PORT}",
        f"http://[::]:{PORT}",
    ]

# Application definition
SITE_ID = config("DJANGO_SITE_ID", cast=int, default=1)
INSTALLED_APPS = PROJECT_INSTALLED_APPS


MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "cfehome.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "cfehome.wsgi.application"


# Database
# https://docs.djangoproject.com/en/6.0/ref/settings/#databases

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

# A single DATABASE_URL drives every container variant. dj-database-url
# understands postgres://, mysql://, sqlite:// and more, so the engine is
# decided by the URL (and the driver baked into the chosen Dockerfile).
DATABASE_URL = config("DATABASE_URL", cast=str, default="")
if DATABASE_URL:
    import dj_database_url

    DATABASES = {
        "default": dj_database_url.parse(
            DATABASE_URL,
            conn_max_age=60,
            conn_health_checks=True,
        )
    }

# Password validation
# https://docs.djangoproject.com/en/6.0/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]


# Internationalization
# https://docs.djangoproject.com/en/6.0/topics/i18n/

LANGUAGE_CODE = "en-us"

TIME_ZONE = "UTC"

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/6.0/howto/static-files/

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "static_root"
STATICFILES_DIRS = [BASE_DIR / "staticfiles"]

# Django 5.1+ removed STATICFILES_STORAGE/DEFAULT_FILE_STORAGE in favor of
# the unified STORAGES setting. WhiteNoise's compressed+hashed manifest
# storage serves static files straight from the app, no CDN required.
STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}

# Default primary key field type
# https://docs.djangoproject.com/en/6.0/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
