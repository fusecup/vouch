from typing import Any

import requests
from django.conf import settings
from django.core.cache import cache

_BASE = "https://app.tryspecter.com/api/v1"
_TIMEOUT = 6


def _headers() -> dict:
    return {"X-API-Key": settings.SPECTER_API_KEY, "accept": "application/json"}


def _base_url() -> str:
    return getattr(settings, "SPECTER_BASE_URL", _BASE).rstrip("/")


def _parse_company(data: dict) -> dict[str, Any]:
    funding = data.get("funding") or {}
    hq = data.get("hq") or {}
    website = data.get("website") or {}
    founders = [
        {"name": f.get("full_name"), "title": f.get("title")}
        for f in (data.get("founder_info") or [])
        if isinstance(f, dict)
    ][:5]
    total_usd = funding.get("total_funding_usd")
    return {
        "specter_id": data.get("id"),
        "name": data.get("organization_name"),
        "tagline": data.get("tagline"),
        "description": data.get("description"),
        "website_url": website.get("url"),
        "domain": website.get("domain"),
        "founded_year": data.get("founded_year"),
        "operating_status": data.get("operating_status"),
        "employee_count": data.get("employee_count"),
        "employee_count_range": data.get("employee_count_range"),
        "hq_city": hq.get("city"),
        "hq_country": hq.get("country"),
        "industry": (data.get("industry") or [])[:3],
        "tech_verticals": [v[0] if v else "" for v in (data.get("tech_verticals") or [])][:3],
        "total_funding_usd": total_usd,
        "total_funding_display": _fmt_usd(total_usd),
        "last_funding_type": funding.get("last_funding_type"),
        "last_funding_date": funding.get("last_funding_date"),
        "round_count": funding.get("round_count"),
        "founders": founders,
        "traction": data.get("traction_highlights"),
        "tags": (data.get("tags") or [])[:8],
        "customer_focus": data.get("customer_focus"),
        "highlights": (data.get("highlights") or [])[:4],
    }


def _fmt_usd(amount) -> str:
    if not amount:
        return ""
    m = amount / 1_000_000
    if m >= 1000:
        return f"${m / 1000:.1f}B"
    return f"${m:.0f}M"


def fetch_company_profile(name: str, domain: str = "") -> dict[str, Any]:
    """Fetch rich company profile from Specter. Returns {} on any failure."""
    if not name and not domain:
        return {}

    key = f"specter:v2:{(domain or name).strip().lower()}"
    cached = cache.get(key)
    if cached is not None:
        return cached

    api_key = getattr(settings, "SPECTER_API_KEY", "")
    if not api_key:
        return {}

    base = _base_url()
    hdrs = _headers()

    try:
        if domain:
            resp = requests.post(
                f"{base}/companies",
                json={"domain": domain},
                headers=hdrs,
                timeout=_TIMEOUT,
            )
            resp.raise_for_status()
            companies = resp.json()
            if isinstance(companies, list) and companies:
                result = _parse_company(companies[0])
                cache.set(key, result, timeout=7200)
                return result
            cache.set(key, {}, timeout=3600)
            return {}

        # No domain — search by name first
        search_resp = requests.get(
            f"{base}/companies/search",
            params={"query": name, "limit": 1},
            headers=hdrs,
            timeout=_TIMEOUT,
        )
        search_resp.raise_for_status()
        results = search_resp.json()
        items = results if isinstance(results, list) else results.get("data", [])
        if not items:
            cache.set(key, {}, timeout=3600)
            return {}

        company_id = items[0].get("id")
        if not company_id:
            cache.set(key, {}, timeout=3600)
            return {}

        detail_resp = requests.get(
            f"{base}/companies/{company_id}",
            headers=hdrs,
            timeout=_TIMEOUT,
        )
        detail_resp.raise_for_status()
        result = _parse_company(detail_resp.json())
        cache.set(key, result, timeout=7200)
        return result

    except Exception:
        cache.set(key, {}, timeout=300)
        return {}


def fetch_counterparty_signal(name: str, domain: str = "") -> dict[str, Any]:
    """Legacy compatibility — returns quality-score dict for the risk engine."""
    profile = fetch_company_profile(name=name, domain=domain)
    if not profile:
        return {
            "company_id": "",
            "funding_stage": "unknown",
            "headcount_delta_3m": 0,
            "news_flags": [],
            "founded_year": None,
            "signals_matrix": {},
            "quality_score": 50,
            "source": "mock",
        }
    return {
        "company_id": profile.get("specter_id", ""),
        "funding_stage": profile.get("last_funding_type", "unknown"),
        "headcount_delta_3m": 0,
        "news_flags": profile.get("highlights", []),
        "founded_year": profile.get("founded_year"),
        "signals_matrix": {},
        "quality_score": 80 if profile.get("specter_id") else 50,
        "source": "specter",
    }
