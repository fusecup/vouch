import uuid
from decimal import Decimal
from random import choice, randint, random

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


SIM_COUNTERPARTIES = [
    ("Coffee Beans UK", "coffeebeans.co.uk"),
    ("Northwind Logistics", "northwind-logistics.com"),
    ("Rapid Vendor", "rapidvendor.io"),
    ("Acme Treasury", "acme-treasury.net"),
    ("Shadow Supplies Ltd", "shadowsupplies.biz"),
]


def _build_metadata(preset: str, actor_id: int | None, run_id: str) -> dict:
    return {
        "preset": preset,
        "actor_id": actor_id,
        "merchant_category": choice(["Hospitality", "Payroll", "SaaS", "Logistics", "Consulting"]),
        "geo_country": choice(["GB", "US", "DE", "FR", "NL"]),
        "device_id": f"sim-device-{randint(1000, 9999)}",
        "velocity_per_hour": randint(1, 25),
        "run_id": run_id,
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
        metadata=_build_metadata(preset=preset, actor_id=actor_id, run_id=run_id),
    )

    if preset == "known_low_risk" or tier == PaymentIntent.Tier.TIER0:
        execute_payment(intent, provider="simulator-ledger")
    else:
        session = create_approval_session(intent)
        if preset == "coerced_tier2":
            session.kind = ApprovalSession.Kind.TIER2
            session.save(update_fields=["kind"])
            if actor_id:
                ApprovalAttestation.objects.create(
                    session=session,
                    approver_id=actor_id,
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


def create_dynamic_transactions(
    *,
    count: int,
    min_amount: Decimal,
    max_amount: Decimal,
    actor_id: int | None = None,
    require_all_tiers: bool = True,
) -> list[PaymentIntent]:
    if count <= 0:
        return []
    if min_amount <= 0 or max_amount <= 0 or min_amount > max_amount:
        raise ValueError("Invalid amount range")

    created: list[PaymentIntent] = []
    run_id = uuid.uuid4().hex[:12]
    tier_seed = [PaymentIntent.Tier.TIER0, PaymentIntent.Tier.TIER1, PaymentIntent.Tier.TIER2] if require_all_tiers else []

    for i in range(count):
        counterparty_name, domain = choice(SIM_COUNTERPARTIES)
        counterparty = upsert_counterparty(counterparty_name, {"domain": domain})
        amount_pennies = randint(int(min_amount * 100), int(max_amount * 100))
        amount = Decimal(amount_pennies) / Decimal("100")
        anomaly = randint(0, 95)
        tier, reasons, risk_score = recommend_tier(amount, counterparty.name, anomaly)
        if tier_seed and i < len(tier_seed):
            tier = tier_seed[i]
            reasons = [*reasons, "Forced tier coverage for simulator"]

        intent = PaymentIntent.objects.create(
            external_id=f"sim-dyn-{run_id}-{i}",
            provider="simulator",
            counterparty=counterparty,
            amount_gbp=amount,
            currency="GBP",
            risk_score=risk_score,
            risk_reasons=reasons,
            tier=tier,
            anomaly_score=anomaly,
            scenario_source="simulator",
            scenario_run_id=run_id,
            scenario_tags=["dynamic", "auto-generated"],
            metadata={
                **_build_metadata(preset="dynamic", actor_id=actor_id, run_id=run_id),
                "index": i,
                "randomized": True,
                "edge_case": random() > 0.7,
            },
        )
        if tier == PaymentIntent.Tier.TIER0:
            execute_payment(intent, provider="simulator-ledger")
        else:
            create_approval_session(intent)
        created.append(intent)
    return created
