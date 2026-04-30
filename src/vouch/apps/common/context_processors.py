from django.conf import settings
from django.contrib.sites.models import Site

EU_GDPR_COUNTRIES = {
    "AT",
    "BE",
    "BG",
    "HR",
    "CY",
    "CZ",
    "DK",
    "EE",
    "FI",
    "FR",
    "DE",
    "GR",
    "HU",
    "IE",
    "IT",
    "LV",
    "LT",
    "LU",
    "MT",
    "NL",
    "PL",
    "PT",
    "RO",
    "SK",
    "SI",
    "ES",
    "SE",
    "IS",
    "LI",
    "NO",
    "GB",
    "CH",
}


def app_settings(request):
    return {
        "debug": settings.DEBUG,
        "is_stage": settings.IS_STAGE,
        "is_prod": settings.IS_PROD,
        "current_site": Site.objects.get_current(),
        "ENVIRONMENT_NAME": settings.ENVIRONMENT_NAME,
        "ENVIRONMENT_COLOR": settings.ENVIRONMENT_COLOR,
        "POSTHOG_API_KEY": settings.POSTHOG_API_KEY,
        "POSTHOG_HOST": settings.POSTHOG_HOST,
        "TAG": settings.TAG,
        "SITE_URL": settings.SITE_URL,
        "LOGIN_URL": settings.LOGIN_URL,
    }


def cookie_consent_settings(request):
    """Enable cookie banner for GDPR regions when feature flag is on."""
    if not settings.ENABLE_GDPR_COOKIE_BANNER:
        return {"show_cookie_banner": False}

    cf_country = (request.META.get("HTTP_CF_IPCOUNTRY") or "").upper()
    return {"show_cookie_banner": cf_country in EU_GDPR_COUNTRIES}
