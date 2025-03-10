"""
Django settings for cfehome project using Django 5.1.5.
"""

from pathlib import Path

from decouple import Csv
from django.core.management.utils import get_random_secret_key

# uses python-decouple
# loads environment variables from .env.local and .env
from helpers import config

from .installed import INSTALLED_APPS

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/5.1/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = config("DJANGO_SECRET_KEY", cast=str, default=get_random_secret_key())

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = config("DJANGO_DEBUG", cast=bool, default=False)
PORT = config("PORT", cast=int, default=8000)


DJANGO_ALLOWED_HOSTS = config("DJANGO_ALLOWED_HOSTS", cast=Csv(), default="")
CSRF_TRUSTED_ORIGINS = config("DJANGO_CSRF_TRUSTED_ORIGINS", cast=Csv(), default="")
APPEND_SLASH = config("DJANGO_APPEND_SLASH", cast=bool, default=True)

ALLOWED_HOSTS = DJANGO_ALLOWED_HOSTS
CSRF_TRUSTED_ORIGINS = CSRF_TRUSTED_ORIGINS

if DEBUG:
    ALLOWED_HOSTS += ["localhost", "127.0.0.1", "[::]"]
    CSRF_TRUSTED_ORIGINS += [
        f"http://localhost:{PORT}",
        f"http://127.0.0.1:{PORT}",
        f"http://[::]:{PORT}",
    ]

RAILWAY_HOSTS = [
    "healthcheck.railway.app",
    ".railway.internal",
    ".up.railway.app",
    "plutopicom.railway.internal",
]

for host in RAILWAY_HOSTS:
    ALLOWED_HOSTS.append(host)
    for protocol in ["http", "https"]:
        if host.startswith("."):
            CSRF_TRUSTED_ORIGINS.append(f"{protocol}://*{host}")
        else:
            CSRF_TRUSTED_ORIGINS.append(f"{protocol}://{host}")


# Application definition
SITE_ID = 1
INSTALLED_APPS = INSTALLED_APPS


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
# https://docs.djangoproject.com/en/5.1/ref/settings/#databases

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

DATABASE_URL = config("DATABASE_URL", cast=str, default="")
if DATABASE_URL:
    if DATABASE_URL.startswith("postgres://") or DATABASE_URL.startswith(
        "postgresql://"
    ):
        import dj_database_url

        DATABASES = {
            "default": dj_database_url.config(
                default=DATABASE_URL,
                conn_max_age=60,
                conn_health_checks=True,
            )
        }
    else:
        raise Exception("DATABASE_URL only supports PostgreSQL at this time")

# Password validation
# https://docs.djangoproject.com/en/5.1/ref/settings/#auth-password-validators

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
# https://docs.djangoproject.com/en/5.1/topics/i18n/

LANGUAGE_CODE = "en-us"

TIME_ZONE = "UTC"

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.1/howto/static-files/

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "static_root"
STATICFILES_DIRS = [BASE_DIR / "staticfiles"]
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

# Default primary key field type
# https://docs.djangoproject.com/en/5.1/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
