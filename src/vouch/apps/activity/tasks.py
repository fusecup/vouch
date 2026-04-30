from celery import shared_task
from django.shortcuts import get_object_or_404

from activity.models import PaymentIntent
from activity.services.agent import explain_transaction, score_transaction
from activity.services.ledger import execute_payment


@shared_task
def score_payment_intent(intent_id: int) -> dict:
    intent = get_object_or_404(PaymentIntent, id=intent_id)
    payload = {"external_id": intent.external_id, "amount": float(intent.amount_gbp), "metadata": intent.metadata}
    result = score_transaction(payload)
    intent.risk_score = int(result.get("score", 0))
    intent.risk_reasons = result.get("reasons", [])
    intent.save(update_fields=["risk_score", "risk_reasons"])
    return result


@shared_task
def generate_tier_explanation(intent_id: int) -> str:
    intent = get_object_or_404(PaymentIntent, id=intent_id)
    text = explain_transaction(
        {"external_id": intent.external_id, "amount": float(intent.amount_gbp), "metadata": intent.metadata},
        intent.risk_reasons,
    )
    intent.explainer_text = text
    intent.save(update_fields=["explainer_text"])
    return text


@shared_task
def execute_payment_intent(intent_id: int) -> int:
    intent = get_object_or_404(PaymentIntent, id=intent_id)
    entry = execute_payment(intent)
    return entry.id
