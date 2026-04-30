import uuid
from decimal import Decimal

from activity.models import ApprovalAttestation, ApprovalSession, PaymentIntent
from activity.services.ledger import execute_payment
from activity.services.risk import recommend_tier, upsert_counterparty
from activity.services.router import create_approval_session


PRESET_SCENARIOS: dict[str, dict] = {
    "unknown_over_5k": {"counterparty": "Shadow Supplies Ltd", "amount_gbp": "6200", "anomaly_score": 65},
    "known_low_risk": {"counterparty": "Coffee Beans UK", "amount_gbp": "180", "anomaly_score": 5},
    "high_over_25k": {"counterparty": "Acme Treasury", "amount_gbp": "62000", "anomaly_score": 55},
    "specter_poor": {"counterparty": "Dormant Shell Co", "amount_gbp": "4500", "anomaly_score": 70},
    "coerced_tier2": {"counterparty": "Acme Treasury", "amount_gbp": "31000", "anomaly_score": 80},
    "swipe_overload": {"counterparty": "Rapid Vendor", "amount_gbp": "1200", "anomaly_score": 20},
}


def create_scenario_intent(preset: str, actor_id: int | None = None) -> PaymentIntent:
    if preset not in PRESET_SCENARIOS:
        raise ValueError(f"Unknown preset '{preset}'")

    data = PRESET_SCENARIOS[preset]
    run_id = uuid.uuid4().hex[:12]
    counterparty = upsert_counterparty(data["counterparty"], {"domain": "example.com"})
    amount = Decimal(str(data["amount_gbp"]))
    tier, reasons, risk_score = recommend_tier(amount, counterparty.name, int(data.get("anomaly_score", 0)))

    intent = PaymentIntent.objects.create(
        external_id=f"sim-{run_id}",
        provider="simulator",
        counterparty=counterparty,
        amount_gbp=amount,
        currency="GBP",
        risk_score=risk_score,
        risk_reasons=reasons,
        tier=tier,
        anomaly_score=int(data.get("anomaly_score", 0)),
        scenario_source="simulator",
        scenario_run_id=run_id,
        scenario_tags=[preset],
        metadata={"preset": preset, "actor_id": actor_id},
    )

    if preset == "known_low_risk" or tier == PaymentIntent.Tier.TIER0:
        execute_payment(intent, provider="simulator-ledger")
    else:
        session = create_approval_session(intent)
        if preset == "coerced_tier2":
            session.kind = ApprovalSession.Kind.TIER2
            session.save(update_fields=["kind"])
            ApprovalAttestation.objects.create(
                session=session,
                approver_id=actor_id if actor_id else 1,
                decision=ApprovalAttestation.Decision.APPROVE,
                face_passed=True,
                voice_passed=True,
                emotion_label="stressed",
                coerced=True,
            )
        if preset == "swipe_overload":
            for i in range(3):
                PaymentIntent.objects.create(
                    external_id=f"sim-over-{run_id}-{i}",
                    provider="simulator",
                    counterparty=counterparty,
                    amount_gbp=Decimal("1100"),
                    currency="GBP",
                    risk_score=40,
                    risk_reasons=["Simulator swipe overload"],
                    tier=PaymentIntent.Tier.TIER1,
                    status=PaymentIntent.Status.PENDING,
                    scenario_source="simulator",
                    scenario_run_id=run_id,
                    scenario_tags=["swipe_overload"],
                )

    return intent
