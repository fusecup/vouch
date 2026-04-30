import uuid
from functools import lru_cache
from pathlib import Path
from decimal import Decimal
from random import choice, randint, random
import json

from activity.models import ApprovalAttestation, ApprovalSession, PaymentIntent
from activity.services.ledger import execute_payment
from activity.services.risk import recommend_tier, upsert_counterparty
from activity.services.router import create_approval_session


PRESET_SCENARIOS: dict[str, dict] = {
    "unknown_over_5k": {"label": "Unknown supplier over £5k", "counterparty": "Metro Catering Supplies Ltd", "amount_gbp": "6200", "anomaly_score": 65},
    "known_low_risk": {"label": "Typical coffee purchase (Tier 0)", "counterparty": "Pret A Manger", "amount_gbp": "4.20", "anomaly_score": 4},
    "high_over_25k": {"label": "High amount over £25k", "counterparty": "Square Wholesale Coffee UK", "amount_gbp": "62000", "anomaly_score": 55},
    "specter_poor": {"label": "Low-quality vendor profile", "counterparty": "Unverified Import Logistics Ltd", "amount_gbp": "4500", "anomaly_score": 70},
    "coerced_tier2": {"label": "Coerced Tier 2 case", "counterparty": "Crown Beverage Equipment Ltd", "amount_gbp": "31000", "anomaly_score": 80},
    "swipe_overload": {"label": "Swipe overload stress case", "counterparty": "Costa Coffee", "amount_gbp": "1200", "anomaly_score": 20},
    "random_thousands": {"label": "Random thousands supplier spend", "counterparty": "Random UK Business Vendor", "amount_gbp": "3800", "anomaly_score": 48},
}

UK_COFFEE_COMPANIES = [
    "Pret A Manger",
    "Costa Coffee",
    "Starbucks UK",
    "Caffe Nero",
    "GAIL's Bakery",
    "Black Sheep Coffee",
    "Camden Coffee Roasters Ltd",
    "Soho Espresso House Ltd",
    "Manchester Bean Collective Ltd",
    "Bristol Brew Bar Ltd",
    "Leeds Artisan Coffee Ltd",
    "Shoreditch Coffee Works Ltd",
    "Brighton Roast Studio Ltd",
    "York Street Coffee Co Ltd",
]


SIM_COUNTERPARTIES = [
    ("Coffee Beans UK", "coffeebeans.co.uk"),
    ("Northwind Logistics", "northwind-logistics.com"),
    ("Rapid Vendor", "rapidvendor.io"),
    ("Acme Treasury", "acme-treasury.net"),
    ("Shadow Supplies Ltd", "shadowsupplies.biz"),
]

UK_BUSINESS_VENDORS = [
    ("Bidfood UK", "bidfood.co.uk"),
    ("Nisbets Catering Equipment", "nisbets.co.uk"),
    ("Booker Wholesale", "booker.co.uk"),
    ("Brakes Foodservice", "brake.co.uk"),
    ("United Coffee UK", "unitedcoffee.com"),
    ("Pact Coffee Wholesale", "pactcoffee.com"),
]

PEAK_HOURS = [10, 10, 10, 11, 11, 9, 12, 8, 13]
MILK_OPTIONS = ["whole", "semi-skimmed", "oat", "almond", "soy"]
DRINK_OPTIONS = ["latte", "flat white", "americano", "cappuccino", "mocha", "cold brew"]
FOOD_OPTIONS = ["croissant", "banana bread", "pain au chocolat", "protein bar", "none"]


def _build_metadata(preset: str, actor_id: int | None, run_id: str) -> dict:
    drink = choice(DRINK_OPTIONS)
    milk = choice(MILK_OPTIONS if random() < 0.55 else ["whole", "semi-skimmed"])
    food = choice(FOOD_OPTIONS)
    visit_hour = choice(PEAK_HOURS) if random() < 0.6 else randint(7, 18)
    basket_type = "coffee_and_snack" if food != "none" else "drink_only"
    return {
        "preset": preset,
        "actor_id": actor_id,
        "merchant_category": choice(["Coffee Shop", "Cafe", "Bakery Cafe", "Quick Service Coffee"]),
        "geo_country": "GB",
        "geo_city": choice(["London", "Manchester", "Leeds", "Bristol", "Brighton", "Liverpool"]),
        "device_id": f"sim-device-{randint(1000, 9999)}",
        "velocity_per_hour": randint(1, 25),
        "run_id": run_id,
        "drink_type": drink,
        "milk_type": milk,
        "food_item": food,
        "basket_type": basket_type,
        "visit_hour_local": visit_hour,
        "market_profile": "uk_coffee_2024_2026",
    }


@lru_cache(maxsize=1)
def _realistic_coffee_merchants() -> tuple[str, ...]:
    """
    Build a realistic merchant pool from seeded transaction data when available,
    with safe fallbacks for local/demo environments.
    """
    merchants: set[str] = set(UK_COFFEE_COMPANIES)
    try:
        root = Path(__file__).resolve().parents[5]
        tx_path = root / "scripts" / "data" / "transactions.json"
        if tx_path.exists():
            raw = json.loads(tx_path.read_text())
            for row in raw[:5000]:
                name = str(row.get("name", "")).strip()
                lower = name.lower()
                if not name:
                    continue
                if any(token in lower for token in ("coffee", "cafe", "espresso", "pret", "starbucks", "costa", "nero")):
                    merchants.add(name)
    except Exception:
        # Keep simulator robust even when fixture data is unavailable.
        pass
    return tuple(sorted(merchants))


def _counterparty_for_preset(preset: str, fallback_name: str) -> tuple[str, str]:
    if preset == "known_low_risk":
        company = choice(_realistic_coffee_merchants())
        slug = (
            company.lower()
            .replace(" ltd", "")
            .replace(" ", "-")
            .replace(".", "")
            .replace("'", "")
            .replace("&", "and")
            .replace("/", "-")
        )
        return company, f"{slug}.co.uk"
    if preset == "random_thousands":
        return choice(UK_BUSINESS_VENDORS)
    return fallback_name, "example.com"


def create_scenario_intent(preset: str, actor_id: int | None = None) -> PaymentIntent:
    if preset not in PRESET_SCENARIOS:
        raise ValueError(f"Unknown preset '{preset}'")

    data = PRESET_SCENARIOS[preset]
    run_id = uuid.uuid4().hex[:12]
    counterparty_name, domain = _counterparty_for_preset(preset, data["counterparty"])
    counterparty = upsert_counterparty(counterparty_name, {"domain": domain})
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
        if preset == "random_thousands":
            # Add noisy companion transactions to mimic random supplier spend.
            for i in range(2):
                companion_amount = Decimal(str(randint(1200, 9500)))
                companion_tier, companion_reasons, companion_risk = recommend_tier(
                    companion_amount, counterparty.name, randint(20, 75)
                )
                PaymentIntent.objects.create(
                    external_id=f"sim-rand-{run_id}-{i}",
                    provider="simulator",
                    counterparty=counterparty,
                    amount_gbp=companion_amount,
                    currency="GBP",
                    risk_score=companion_risk,
                    risk_reasons=companion_reasons,
                    tier=companion_tier,
                    status=PaymentIntent.Status.PENDING,
                    anomaly_score=randint(20, 75),
                    scenario_source="simulator",
                    scenario_run_id=run_id,
                    scenario_tags=["random_thousands", "supplier_spend"],
                    metadata={**_build_metadata(preset="random_thousands", actor_id=actor_id, run_id=run_id), "companion": True},
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
        # Weighted to reflect typical UK coffee spend bands with occasional larger baskets.
        r = random()
        if r < 0.45:
            amount = Decimal(randint(300, 400)) / Decimal("100")  # £3-£4
        elif r < 0.88:
            amount = Decimal(randint(500, 700)) / Decimal("100")  # £5-£7
        elif r < 0.98:
            amount = Decimal(randint(800, 1500)) / Decimal("100")  # larger basket
        else:
            amount = Decimal(randint(2500, 12000)) / Decimal("100")  # catering/corporate anomaly
        amount = min(max(amount, min_amount), max_amount)
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
