from decimal import Decimal
from typing import Any

from django.conf import settings

from activity.models import Counterparty, PaymentIntent
from activity.services.specter import fetch_counterparty_signal


def recommend_tier(amount_gbp: Decimal, counterparty_name: str, anomaly_score: int = 0) -> tuple[str, list[str], int]:
    reasons: list[str] = []
    risk_score = min(100, max(0, anomaly_score))

    known_counterparties = set(settings.VOUCH_KNOWN_COUNTERPARTIES)
    is_known = counterparty_name in known_counterparties
    if is_known:
        reasons.append("Known counterparty")
        risk_score = max(0, risk_score - 10)
    else:
        reasons.append("Unknown counterparty")
        risk_score += 15

    signal = fetch_counterparty_signal(counterparty_name)
    quality_score = int(signal.get("quality_score", 50))
    if quality_score < 35:
        reasons.append("Poor Specter quality signal")
        risk_score += 25
    elif quality_score > 70:
        reasons.append("Strong Specter quality signal")
        risk_score = max(0, risk_score - 10)

    tier = PaymentIntent.Tier.TIER1
    if amount_gbp <= Decimal(str(settings.VOUCH_TIER0_MAX_AMOUNT_GBP)) and is_known and quality_score >= 60:
        tier = PaymentIntent.Tier.TIER0
    if amount_gbp > Decimal(str(settings.VOUCH_TIER1_MAX_AMOUNT_GBP)) or risk_score >= 75:
        tier = PaymentIntent.Tier.TIER2
    if (not is_known) and amount_gbp >= Decimal(str(settings.VOUCH_HARD_BLOCK_UNKNOWN_OVER_GBP)):
        tier = PaymentIntent.Tier.TIER2
        reasons.append("Unknown counterparty over hard threshold")
    if amount_gbp >= Decimal(str(settings.VOUCH_ALWAYS_TIER2_OVER_GBP)):
        tier = PaymentIntent.Tier.TIER2
        reasons.append("Amount exceeds always-tier2 threshold")

    return tier, reasons[:3], min(100, risk_score)


def upsert_counterparty(name: str, metadata: dict[str, Any] | None = None) -> Counterparty:
    metadata = metadata or {}
    signal = fetch_counterparty_signal(name=name, domain=metadata.get("domain", ""))
    known = name in set(settings.VOUCH_KNOWN_COUNTERPARTIES)
    counterparty, _ = Counterparty.objects.update_or_create(
        name=name,
        defaults={
            "domain": metadata.get("domain", ""),
            "bank_fingerprint": metadata.get("bank_fingerprint", ""),
            "specter_company_id": signal.get("company_id", ""),
            "specter_quality_score": int(signal.get("quality_score", 50)),
            "is_known": known,
        },
    )
    return counterparty
