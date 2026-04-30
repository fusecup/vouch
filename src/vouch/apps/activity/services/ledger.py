import uuid
from datetime import timedelta

from django.conf import settings
from django.utils import timezone

from activity.models import LedgerEntry, PaymentIntent, Receipt
from activity.services.slack import send_tier0_receipt_notification


def execute_payment(intent: PaymentIntent, provider: str = "mock-ledger") -> LedgerEntry:
    entry = LedgerEntry.objects.create(
        payment_intent=intent,
        provider=provider,
        provider_txn_id=f"{provider}-{intent.external_id}",
        idempotency_key=str(uuid.uuid4()),
        success=True,
        payload={"status": "executed", "provider": provider},
    )
    intent.status = PaymentIntent.Status.EXECUTED
    intent.executed_at = timezone.now()
    intent.save(update_fields=["status", "executed_at"])

    if intent.tier == PaymentIntent.Tier.TIER0:
        Receipt.objects.update_or_create(
            payment_intent=intent,
            defaults={
                "ledger_entry": entry,
                "can_reverse_until": timezone.now() + timedelta(minutes=settings.VOUCH_TIER0_REVERSAL_MINUTES),
            },
        )
        send_tier0_receipt_notification(intent)

    return entry


def reverse_payment(intent: PaymentIntent) -> bool:
    if not hasattr(intent, "receipt"):
        return False
    receipt = intent.receipt
    if timezone.now() > receipt.can_reverse_until:
        return False

    intent.status = PaymentIntent.Status.REVERSED
    intent.save(update_fields=["status"])
    receipt.reversal_requested_at = timezone.now()
    receipt.reversed_at = timezone.now()
    receipt.save(update_fields=["reversal_requested_at", "reversed_at"])
    return True
