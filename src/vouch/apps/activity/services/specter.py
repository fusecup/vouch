from typing import Any

import requests
from django.conf import settings
from django.core.cache import cache


def _cache_key(name: str) -> str:
    return f"specter:{name.strip().lower()}"


def fetch_counterparty_signal(name: str, domain: str = "") -> dict[str, Any]:
    fallback = {
        "company_id": "",
        "funding_stage": "unknown",
        "headcount_delta_3m": 0,
        "news_flags": [],
        "founded_year": None,
        "signals_matrix": {},
        "quality_score": 50,
        "source": "mock",
    }
    if not name:
        return fallback

    cached = cache.get(_cache_key(name))
    if cached:
        return cached

    if not (settings.SPECTER_LIVE and settings.SPECTER_BASE_URL and settings.SPECTER_API_KEY):
        cache.set(_cache_key(name), fallback, timeout=3600)
        return fallback

    try:
        response = requests.get(
            f"{settings.SPECTER_BASE_URL.rstrip('/')}/v1/companies/resolve",
            params={"name": name, "domain": domain},
            headers={"Authorization": f"Bearer {settings.SPECTER_API_KEY}"},
            timeout=5,
        )
        response.raise_for_status()
        payload = response.json()
    except Exception:
        payload = fallback

    cache.set(_cache_key(name), payload, timeout=3600)
    return payload
