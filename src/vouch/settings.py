import os
import sys

import sentry_sdk
from django.utils.translation import gettext_lazy as _
from sentry_sdk.integrations.celery import CeleryIntegration
from sentry_sdk.integrations.django import DjangoIntegration

from .helpers import strtobool

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
# <root-file>/src/vouch/
sys.path.append(os.path.join(PROJECT_DIR, "apps/"))
# <root-file>/src/vouch/apps/
BASE_DIR = os.path.dirname(PROJECT_DIR)
# <root-file>/src

TAG = os.getenv("DOCKER_IMAGE_TAG", "latest")

# ENVIRONMENT
DEBUG: bool = bool(strtobool(os.getenv("DEBUG", "false")))
IS_STAGE: bool = bool(strtobool(os.getenv("IS_STAGE", "false")))
IS_PROD: bool = bool(strtobool(os.getenv("IS_PROD", "True")))
IS_TEST: bool = bool(strtobool(os.getenv("IS_TEST", "false")))
ENVIRONMENT_NAME: str = os.environ.get("ENVIRONMENT_NAME", "Production")
ENVIRONMENT_COLOR: str = os.environ.get("ENVIRONMENT_COLOR", "#FF0000")

SECRET_KEY = os.environ.get("SECRET_KEY", None)

SITE_URL = os.environ.get("SITE_URL", "http://127.0.0.1:8000")

# AXES
AXES_ENABLED = False

# HOSTS
allowed_hosts = os.getenv("ALLOWED_HOSTS", ".localhost,127.0.0.1,[::1]")
ALLOWED_HOSTS = list(map(str.strip, allowed_hosts.split(",")))

ADMINS = [
    ("Girish", "girish@fuscup.co"),
]
MANAGERS = [
    ("Girish", "girish@fuscup.co"),
]
SYSTEM_EMAIL_RECIPIENT = [
    "girish@fuscup.co",
]

INSTALLED_APPS = [
    # Base Local Apps
    "common.apps.CommonConfig",
    "accounts.apps.AccountsConfig",
    "fc_uikit.apps.FcUikitConfig",
    "activity.apps.ActivityConfig",
    # Local Apps
    # Django Core
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.sites",
    "django.contrib.humanize",
    "django.contrib.postgres",
    # 3rd Party Apps
    "django_cotton.apps.SimpleAppConfig",
    "tz_detect",
    "django_countries",
    "multiselectfield",
    "django_extensions",
    "allauth",
    "allauth.account",
    "allauth.socialaccount",
    "allauth.socialaccount.providers.google",
    # 'allauth.socialaccount.providers.windowslive',
    "compressor",
    "widget_tweaks",
    "prettyjson",
    "import_export",
    "nested_admin",
]

if DEBUG:
    INSTALLED_APPS.extend(
        [
            "debug_toolbar",
        ]
    )

    DEBUG_TOOLBAR_PANELS = [
        "debug_toolbar.panels.history.HistoryPanel",
        "debug_toolbar.panels.versions.VersionsPanel",
        "debug_toolbar.panels.timer.TimerPanel",
        "debug_toolbar.panels.settings.SettingsPanel",
        "debug_toolbar.panels.headers.HeadersPanel",
        "debug_toolbar.panels.request.RequestPanel",
        "debug_toolbar.panels.sql.SQLPanel",
        "debug_toolbar.panels.staticfiles.StaticFilesPanel",
        "debug_toolbar.panels.templates.TemplatesPanel",
        "debug_toolbar.panels.cache.CachePanel",  # commenting this line allows DDT to continue to work
        "debug_toolbar.panels.signals.SignalsPanel",
        "debug_toolbar.panels.logging.LoggingPanel",
        "debug_toolbar.panels.redirects.RedirectsPanel",
        "debug_toolbar.panels.profiling.ProfilingPanel",
    ]

SITE_ID = 1

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "allauth.account.middleware.AccountMiddleware",
    "tz_detect.middleware.TimezoneMiddleware",
]

if DEBUG:
    MIDDLEWARE.extend(
        [
            "debug_toolbar.middleware.DebugToolbarMiddleware",
        ]
    )

ROOT_URLCONF = "vouch.urls"

default_loaders = [
    "django_cotton.cotton_loader.Loader",
    "django.template.loaders.filesystem.Loader",
    "django.template.loaders.app_directories.Loader",
]

cached_loaders = [("django.template.loaders.cached.Loader", default_loaders)]

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [
            os.path.join(PROJECT_DIR, "templates"),
            os.path.join(PROJECT_DIR, "templates_htmx"),
        ],
        "OPTIONS": {
            "debug": DEBUG,  # to allow live reload of templates
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "common.context_processors.app_settings",
                "common.context_processors.cookie_consent_settings",
            ],
            "loaders": default_loaders if DEBUG else cached_loaders,
            "builtins": [
                "django_cotton.templatetags.cotton",
            ],
        },
    },
]

WSGI_APPLICATION = "vouch.wsgi.application"

# Django User Model Stuff
AUTHENTICATION_BACKENDS = (
    # Needed to login by username in Django admin, regardless of `allauth`
    "django.contrib.auth.backends.ModelBackend",
    # `allauth` specific authentication methods, such as login by email
    "allauth.account.auth_backends.AuthenticationBackend",
)

AUTH_USER_MODEL = "accounts.User"

ACCOUNT_PRESERVE_USERNAME_CASING = False

UPDATE_ON_DUPLICATE_REG_ID = True

# Django Emails
EMAIL_SUBJECT_PREFIX = ""

# django-allauth Configuration
# http://django-allauth.readthedocs.io/en/latest/configuration.html
LOGIN_URL = "/a/login/"
# LOGIN_REDIRECT_URL = '/a/signup/profile/'
LOGIN_REDIRECT_URL = "/d/"
ACCOUNT_ADAPTER = "accounts.adapter.SignupAccountAdapter"
# ACCOUNT_ADAPTER = 'allauth_2fa.adapter.OTPAdapter'
# (="username" | "email" | "username_email")
# ACCOUNT_AUTHENTICATION_METHOD = "email"  # deprecated
ACCOUNT_LOGIN_METHODS = {"email"}
# ACCOUNT_CONFIRM_EMAIL_ON_GET = False
# ACCOUNT_EMAIL_CONFIRMATION_ANONYMOUS_REDIRECT_URL = settings.LOGIN_URL
# ACCOUNT_EMAIL_CONFIRMATION_AUTHENTICATED_REDIRECT_URL = None
# ACCOUNT_EMAIL_CONFIRMATION_EXPIRE_DAYS = 3
# ACCOUNT_EMAIL_CONFIRMATION_HMAC =True
# ACCOUNT_EMAIL_REQUIRED = True  # deprecated
ACCOUNT_SIGNUP_FIELDS = ["email*", "password1*", "password2*"]
ACCOUNT_EMAIL_VERIFICATION = "optional"  # (="mandatory" | "optional" | "none")
# ACCOUNT_EMAIL_VERIFICATION_BY_CODE_ENABLED = False
ACCOUNT_EMAIL_SUBJECT_PREFIX = ""
# ACCOUNT_FORMS = {
#     "login": "accounts.forms.LoginForm",
#     "signup": "accounts.forms.SignupForm",
# }
ACCOUNT_LOGIN_BY_CODE_ENABLED = True
# Used to override forms, for example: {'login': 'myapp.forms.LoginForm'}
# ACCOUNT_LOGIN_ATTEMPTS_LIMIT = 5
# ACCOUNT_LOGIN_ATTEMPTS_TIMEOUT = 300
# ACCOUNT_LOGOUT_ON_GET = False
# ACCOUNT_LOGOUT_ON_PASSWORD_CHANGE = False
# ACCOUNT_LOGOUT_REDIRECT_URL = '/'
# ACCOUNT_SIGNUP_FORM_CLASS = 'accounts.forms.SignupForm'
# A string pointing to a custom form class (e.g. 'myapp.forms.SignupForm') that
# is used during signup to ask the user for additional input (e.g. newsletter signup, birth date).
# This class should implement a def signup(self, request, user) method, where user represents the newly signed up user.
# ACCOUNT_SIGNUP_PASSWORD_VERIFICATION = True
ACCOUNT_UNIQUE_EMAIL = True
ACCOUNT_USER_MODEL_USERNAME_FIELD = None
# ACCOUNT_USER_MODEL_EMAIL_FIELD = 'email'
# ACCOUNT_USER_DISPLAY = 'user.first_name'
# A callable (or string of the form 'some.module.callable_name') that takes a user as its only
# argument and returns the display name of the user. The default
# implementation returns user.username.
# ACCOUNT_USERNAME_MIN_LENGTH = 5
# ACCOUNT_USERNAME_BLACKLIST = []
# ACCOUNT_USERNAME_REQUIRED = False  # deprecated
# SOCIALACCOUNT_QUERY_EMAIL = True
# LOGIN_REDIRECT_URL = "/"

# ACCOUNT_PASSWORD_INPUT_RENDER_VALUE = False
# render_value parameter as passed to PasswordInput fields.
# ACCOUNT_PASSWORD_MIN_LENGTH = 6
# ACCOUNT_LOGIN_ON_EMAIL_CONFIRMATION = False

# ACCOUNT_LOGIN_ON_PASSWORD_RESET = False
ACCOUNT_SESSION_REMEMBER = None
# Controls the life time of the session. Set to None to ask the user ("Remember me?"),
# False to not remember, and True to always remember.
ACCOUNT_AUTHENTICATED_LOGIN_REDIRECTS = True
ACCOUNT_LOGIN_REDIRECT_URL = "/d/"
ACCOUNT_SIGNUP_REDIRECT_URL = "/d/"

# Django Hijack Configuration
HIJACK_LOGIN_REDIRECT_URL = "/d/"  # Where to redirect after hijacking a user
HIJACK_LOGOUT_REDIRECT_URL = "/d/profile/resume-admin/"  # Where to redirect after releasing hijack

# ACCOUNT_TEMPLATE_EXTENSION = "html"
# SOCIALACCOUNT_ADAPTER = "accounts.adapter.SignupSocialAccountAdapter"
# SOCIALACCOUNT_ADAPTER = 'allauth.socialaccount.adapter.DefaultSocialAccountAdapter'
# SOCIALACCOUNT_QUERY_EMAIL = ACCOUNT_EMAIL_REQUIRED
# SOCIALACCOUNT_AUTO_SIGNUP = True
# SOCIALACCOUNT_EMAIL_REQUIRED = ACCOUNT_EMAIL_REQUIRED
# SOCIALACCOUNT_EMAIL_VERIFICATION = ACCOUNT_EMAIL_VERIFICATION
# SOCIALACCOUNT_FORMS ={}
# Used to override forms, for example: {'signup': 'myapp.forms.SignupForm'}
# SOCIALACCOUNT_PROVIDERS = dict
# Dictionary containing provider specific settings.
# SOCIALACCOUNT_STORE_TOKENS = True
# Indicates whether or not the access tokens are stored in the database.
SOCIALACCOUNT_EMAIL_AUTHENTICATION_AUTO_CONNECT = True
ACCOUNT_EMAIL_UNKNOWN_ACCOUNTS = False
# SOCIALACCOUNT_LOGIN_ON_GET = True

SOCIALACCOUNT_PROVIDERS = {
    "google": {
        "EMAIL_AUTHENTICATION": True,
        "SCOPE": [
            "profile",
            "email",
        ],
        "AUTH_PARAMS": {
            "access_type": "online",
        },
    },
}


# Password validation
# https://docs.djangoproject.com/en/4.0/ref/settings/#auth-password-validators

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

# Default primary key field type
# https://docs.djangoproject.com/en/4.0/ref/settings/#default-auto-field
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Internationalization
# https://docs.djangoproject.com/en/4.0/topics/i18n/

LANGUAGES = [
    ("en-gb", _("English (United Kingdom)")),
    # ("en-us", _("English (United States)")),
]

LANGUAGE_CODE = LANGUAGES[0][0]

LOCALE_PATHS = (os.path.join(BASE_DIR, "locale"),)

TIME_ZONE = os.environ.get("TIME_ZONE", "America/New_York")

USE_I18N = True

USE_L10N = True

USE_TZ = True

# INTERNAL IP
if DEBUG:
    import socket  # only if you haven't already imported this

    hostname, _, ips = socket.gethostbyname_ex(socket.gethostname())
    INTERNAL_IPS = [ip[: ip.rfind(".")] + ".1" for ip in ips] + ["127.0.0.1", "0.0.0.0"]

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql_psycopg2",
        "NAME": os.environ.get("POSTGRES_DB", ""),
        "USER": os.environ.get("POSTGRES_USER", ""),
        "PASSWORD": os.environ.get("POSTGRES_PASSWORD", ""),
        "HOST": os.environ.get("POSTGRES_HOST", ""),
        "PORT": os.environ.get("POSTGRES_PORT", "5432"),
        "CONN_MAX_AGE": 600,
    }
}

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/4.0/howto/static-files/

COMPRESS_ENABLED = bool(strtobool(os.getenv("COMPRESS_ENABLED", "true")))

COMPRESS_OFFLINE = bool(strtobool(os.getenv("COMPRESS_OFFLINE", "false")))

# if DEBUG:
#     DEFAULT_FILE_STORAGE = "django.core.files.storage.FileSystemStorage"
#     STATICFILES_STORAGE = "django.contrib.staticfiles.storage.StaticFilesStorage"

# STATIC URL & ROOT
STATIC_URL = "static/"

# STATIC FILES STORAGE LOCATION
STATICFILES_DIRS = [
    os.path.join(PROJECT_DIR, "static"),
]
STATIC_ROOT = os.path.join(BASE_DIR, "public", "static")

# MEDIA URL & ROOT
MEDIA_URL = "media/"
MEDIA_ROOT = os.path.join(BASE_DIR, "public", "media")

STATICFILES_FINDERS = [
    "django.contrib.staticfiles.finders.FileSystemFinder",
    "django.contrib.staticfiles.finders.AppDirectoriesFinder",
    "compressor.finders.CompressorFinder",
]
COMPRESS_STORAGE = "compressor.storage.BrotliCompressorFileStorage"

STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedStaticFilesStorage",
    },
}


_ = sentry_sdk.init(
    dsn=os.getenv("SENTRY_DSN", ""),
    integrations=[DjangoIntegration(), CeleryIntegration(monitor_beat_tasks=True)],
    environment=ENVIRONMENT_NAME,
    send_default_pii=True,  # This needs to be false for data privacy reasons
    release=TAG,
    enable_tracing=True,
)

# CELERY STUFF
CELERY_BROKER_URL = os.environ.get("CELERY_BROKER_URL", "redis://redis:6379/0")
CELERY_RESULT_BACKEND = CELERY_BROKER_URL
CELERY_ACCEPT_CONTENT = ["application/json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = TIME_ZONE
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = 30 * 60

# Send emails to smtp-server
EMAIL_BACKEND = os.getenv("EMAIL_BACKEND", "django.core.mail.backends.smtp.EmailBackend")
EMAIL_HOST = os.getenv("EMAIL_HOST", "")
EMAIL_PORT = os.getenv("EMAIL_PORT", "")
EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD", "")
EMAIL_USE_TLS = bool(strtobool(os.getenv("EMAIL_USE_TLS", "false")))
EMAIL_USE_SSL = bool(strtobool(os.getenv("EMAIL_USE_SSL", "false")))


# SES AWS
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID", "")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY", "")
AWS_SES_REGION_NAME = os.getenv("AWS_SES_REGION_NAME", "us-east-1")
AWS_SES_REGION_ENDPOINT = os.getenv("AWS_SES_REGION_ENDPOINT", "email.us-east-1.amazonaws.com")


DEFAULT_FROM_EMAIL = os.getenv("DEFAULT_FROM_EMAIL", "vouch<no-reply@mail.vouch.co>")
SERVER_EMAIL = os.getenv("SERVER_EMAIL", "vouch Server<no-reply-server@mail.vouch.co>")

ACCOUNT_DEFAULT_HTTP_PROTOCOL = "http" if DEBUG else "https"

# When running behind a reverse proxy, ensure generated absolute URLs are https in production.
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
USE_X_FORWARDED_HOST = True

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": os.environ.get("CACHES", "redis://redis:6379"),
    }
}

DATA_UPLOAD_MAX_NUMBER_FIELDS = 50000

CSRF_TRUSTED_ORIGINS = [
    SITE_URL,
]

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "WARNING",
    },
    "loggers": {
        "django": {
            "handlers": ["console"],
            "level": os.getenv("DJANGO_LOG_LEVEL", "INFO"),
            "propagate": False,
        },
    },
}

SHELL_PLUS = "ipython"

SHELL_PLUS_PRINT_SQL = True

NOTEBOOK_ARGUMENTS = [
    "--ip",
    "0.0.0.0",
    "--port",
    "2222",
    "--allow-root",
    "--no-browser",
]

IPYTHON_ARGUMENTS = [
    "--ext",
    "django_extensions.management.notebook_extension",
    "--debug",
]

IPYTHON_KERNEL_DISPLAY_NAME = "Django Shell-Plus"

POSTHOG_API_KEY = os.getenv("POSTHOG_API_KEY", "")
POSTHOG_HOST = os.getenv("POSTHOG_HOST", "")
ENABLE_GDPR_COOKIE_BANNER = bool(strtobool(os.getenv("ENABLE_GDPR_COOKIE_BANNER", "false")))

X_FRAME_OPTIONS = "SAMEORIGIN"
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "strict-origin-when-cross-origin"

# Plaid and dashboard settings
PLAID_CLIENT_ID = os.getenv("PLAID_CLIENT_ID", "")
PLAID_SECRET = os.getenv("PLAID_SECRET", "")
PLAID_ENV = os.getenv("PLAID_ENV", "sandbox")
PLAID_ACCESS_TOKEN = os.getenv("PLAID_ACCESS_TOKEN", "")
PLAID_USE_MOCK = bool(strtobool(os.getenv("PLAID_USE_MOCK", "true")))
PLAID_MOCK_DATA = os.getenv("PLAID_MOCK_DATA", "")

VOUCH_ACTIVITY_DASHBOARD_ENABLED = bool(strtobool(os.getenv("VOUCH_ACTIVITY_DASHBOARD_ENABLED", "true")))
VOUCH_ACTIVITY_TRANSACTIONS_SOURCE = os.getenv("VOUCH_ACTIVITY_TRANSACTIONS_SOURCE", "internal").lower()
VOUCH_PLAID_TRANSACTION_LOOKBACK_DAYS = int(os.getenv("VOUCH_PLAID_TRANSACTION_LOOKBACK_DAYS", "90"))
VOUCH_PLAID_TRANSACTION_PAGE_SIZE = int(os.getenv("VOUCH_PLAID_TRANSACTION_PAGE_SIZE", "100"))

# PRD phases 2-7 settings
VOUCH_KNOWN_COUNTERPARTIES = [value for value in os.getenv("VOUCH_KNOWN_COUNTERPARTIES", "").split(",") if value]
VOUCH_TIER0_MAX_AMOUNT_GBP = float(os.getenv("VOUCH_TIER0_MAX_AMOUNT_GBP", "1000"))
VOUCH_TIER1_MAX_AMOUNT_GBP = float(os.getenv("VOUCH_TIER1_MAX_AMOUNT_GBP", "10000"))
VOUCH_HARD_BLOCK_UNKNOWN_OVER_GBP = float(os.getenv("VOUCH_HARD_BLOCK_UNKNOWN_OVER_GBP", "5000"))
VOUCH_ALWAYS_TIER2_OVER_GBP = float(os.getenv("VOUCH_ALWAYS_TIER2_OVER_GBP", "25000"))
VOUCH_MAX_TIER1_CARDS_PER_DAY = int(os.getenv("VOUCH_MAX_TIER1_CARDS_PER_DAY", "20"))
VOUCH_TIER1_FALLBACK_MINUTES = int(os.getenv("VOUCH_TIER1_FALLBACK_MINUTES", "10"))
VOUCH_TIER2_WINDOW_MINUTES = int(os.getenv("VOUCH_TIER2_WINDOW_MINUTES", "30"))
VOUCH_TIER2_MIN_APPROVERS = int(os.getenv("VOUCH_TIER2_MIN_APPROVERS", "3"))
VOUCH_TIER2_MAX_APPROVERS = int(os.getenv("VOUCH_TIER2_MAX_APPROVERS", "4"))
VOUCH_TIER0_REVERSAL_MINUTES = int(os.getenv("VOUCH_TIER0_REVERSAL_MINUTES", "60"))

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
VOUCH_ANTHROPIC_HAIKU_MODEL = os.getenv("VOUCH_ANTHROPIC_HAIKU_MODEL", "claude-3-5-haiku-latest")
VOUCH_ANTHROPIC_OPUS_MODEL = os.getenv("VOUCH_ANTHROPIC_OPUS_MODEL", "claude-3-opus-latest")

SPECTER_API_KEY = os.getenv("SPECTER_API_KEY", "")
SPECTER_BASE_URL = os.getenv("SPECTER_BASE_URL", "")
SPECTER_LIVE = bool(strtobool(os.getenv("SPECTER_LIVE", "false")))

SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL", "")
