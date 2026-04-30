import requests
from django.conf import settings

from activity.models import PaymentIntent


def send_tier0_receipt_notification(intent: PaymentIntent) -> None:
    if not settings.SLACK_WEBHOOK_URL:
        return

    reverse_url = f"{settings.SITE_URL.rstrip('/')}/d/payments/{intent.id}/reverse/"
    text = (
        f"Tier 0 auto-approved: {intent.counterparty} £{intent.amount_gbp} "
        f"(risk={intent.risk_score}). Reverse: {reverse_url}"
    )
    requests.post(settings.SLACK_WEBHOOK_URL, json={"text": text}, timeout=3)
