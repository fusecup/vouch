from typing import Any

from django.conf import settings

try:
    from anthropic import Anthropic
except ImportError:  # pragma: no cover - handled at runtime by graceful fallback
    Anthropic = None  # type: ignore[assignment]


def _client() -> Any | None:
    if not settings.ANTHROPIC_API_KEY or Anthropic is None:
        return None
    return Anthropic(api_key=settings.ANTHROPIC_API_KEY)


def score_transaction(transaction: dict[str, Any]) -> dict[str, Any]:
    if not _client():
        return {
            "score": min(100, int(abs(float(transaction.get("amount", 0))) // 100)),
            "reasons": ["Fallback scorer (no Anthropic key configured)"],
            "recommended_tier": "tier1",
        }

    prompt = (
        "Score this transaction from 0-100 for payment risk and return JSON with keys "
        "score, reasons (max 3), recommended_tier (tier0/tier1/tier2).\n"
        f"Transaction: {transaction}"
    )
    response = _client().messages.create(
        model=settings.VOUCH_ANTHROPIC_HAIKU_MODEL,
        max_tokens=300,
        messages=[{"role": "user", "content": prompt}],
    )
    text = response.content[0].text if response.content else ""
    return {"raw": text, "score": 50, "reasons": ["Model response captured"], "recommended_tier": "tier1"}


def explain_transaction(transaction: dict[str, Any], reasons: list[str]) -> str:
    if not _client():
        return "Requested because this payment is outside normal confidence bounds."

    prompt = (
        "Write one concise line explaining why human review is requested for this transaction.\n"
        f"Transaction: {transaction}\nReasons: {reasons}"
    )
    response = _client().messages.create(
        model=settings.VOUCH_ANTHROPIC_OPUS_MODEL,
        max_tokens=80,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.content[0].text.strip() if response.content else "Manual review recommended."
