import uuid
from decimal import Decimal
from typing import Any

from django.conf import settings
from django.shortcuts import get_object_or_404
from ninja import Field, NinjaAPI, Schema, Status
from ninja.security import django_auth

from activity.models import (
    ApprovalAttestation,
    ApprovalSession,
    Counterparty,
    PaymentIntent,
    PolicyConfigEvent,
    Receipt,
)
from activity.services.ledger import execute_payment
from activity.services.plaid import fetch_transactions
from activity.services.risk import recommend_tier, upsert_counterparty
from activity.services.router import create_approval_session, enforce_daily_swipe_limit, update_session_status
from activity.services.simulator import PRESET_SCENARIOS, create_dynamic_transactions, create_scenario_intent
from activity.services.specter import fetch_counterparty_signal
from activity.views import _intent_to_transaction

api = NinjaAPI(
    title="Vouch Activity API",
    version="1.0.0",
    auth=django_auth,
    urls_namespace="activity_api",
)


class PaymentIntentCreateIn(Schema):
    counterparty: str = "Unknown"
    amount_gbp: Decimal = Decimal("0")
    external_id: str | None = None
    provider: str = "plaid"
    currency: str = "GBP"
    anomaly_score: int = 0
    metadata: dict[str, Any] = Field(default_factory=dict)


class ThresholdUpdateIn(Schema):
    tier0_max: Decimal
    tier1_max: Decimal
    hard_block_unknown_over: Decimal
    always_tier2_over: Decimal


class SimulatorPresetRunIn(Schema):
    preset: str


class SimulatorBatchRunIn(Schema):
    counts: dict[str, int] = Field(default_factory=dict)


class SimulatorDynamicGenerateIn(Schema):
    count: int = 25
    min_amount: Decimal = Decimal("20")
    max_amount: Decimal = Decimal("50000")
    require_all_tiers: bool = True


class Tier1SwipeActionIn(Schema):
    payment_intent_id: int
    decision: str = ApprovalAttestation.Decision.ESCALATE


class Tier2SessionCreateIn(Schema):
    payment_intent_id: int


class Tier2AttestationIn(Schema):
    session_id: int
    decision: str = ApprovalAttestation.Decision.APPROVE
    face_passed: bool = False
    voice_passed: bool = False
    emotion_label: str = ""
    coerced: bool = False
    geo_country: str = ""


@api.get("/overview/stats/")
def overview_stats(request):
    return {
        "tier0_executed": PaymentIntent.objects.filter(tier=PaymentIntent.Tier.TIER0).count(),
        "tier1_pending": PaymentIntent.objects.filter(
            tier=PaymentIntent.Tier.TIER1, status=PaymentIntent.Status.PENDING
        ).count(),
        "tier2_pending": PaymentIntent.objects.filter(
            tier=PaymentIntent.Tier.TIER2, status=PaymentIntent.Status.PENDING
        ).count(),
        "receipts_count": Receipt.objects.count(),
    }


@api.get("/transactions/")
def transactions(request, limit: int = settings.VOUCH_PLAID_TRANSACTION_PAGE_SIZE, offset: int = 0):
    source_mode = getattr(settings, "VOUCH_ACTIVITY_TRANSACTIONS_SOURCE", "internal")
    if source_mode == "plaid":
        txns, total = fetch_transactions(limit=limit, offset=offset)
    else:
        bounded_limit = max(1, min(limit, 500))
        bounded_offset = max(0, offset)
        intents = PaymentIntent.objects.select_related("counterparty").order_by("-created_at")[
            bounded_offset : bounded_offset + bounded_limit
        ]
        txns = [_intent_to_transaction(intent) for intent in intents]
        total = PaymentIntent.objects.count()
    return {"total": total, "items": txns}


@api.post("/payments/create/", response={201: dict[str, Any]})
def create_payment_intent(request, payload: PaymentIntentCreateIn):
    counterparty = upsert_counterparty(payload.counterparty, payload.metadata)
    tier, reasons, risk_score = recommend_tier(payload.amount_gbp, counterparty.name, payload.anomaly_score)
    intent = PaymentIntent.objects.create(
        external_id=payload.external_id or str(uuid.uuid4()),
        provider=payload.provider,
        counterparty=counterparty,
        amount_gbp=payload.amount_gbp,
        currency=payload.currency,
        risk_score=risk_score,
        risk_reasons=reasons,
        tier=tier,
        anomaly_score=payload.anomaly_score,
        metadata=payload.metadata,
    )
    if tier == PaymentIntent.Tier.TIER0:
        execute_payment(intent)
    else:
        create_approval_session(intent)
    return Status(201, {"id": intent.id, "tier": intent.tier, "risk_score": intent.risk_score, "reasons": reasons})


@api.get("/tier1/queue/")
def tier1_queue(request):
    queue = (
        PaymentIntent.objects.filter(tier=PaymentIntent.Tier.TIER1, status=PaymentIntent.Status.PENDING)
        .select_related("counterparty")
        .order_by("created_at")[:50]
    )
    return {
        "items": [
            {
                "id": item.id,
                "external_id": item.external_id,
                "counterparty": item.counterparty.name if item.counterparty else "Unknown",
                "amount_gbp": str(item.amount_gbp),
                "risk_score": item.risk_score,
                "reasons": item.risk_reasons,
                "explainer": item.explainer_text,
            }
            for item in queue
        ]
    }


@api.post("/tier1/swipe/", response={200: dict[str, Any], 429: dict[str, str]})
def tier1_swipe_action(request, payload: Tier1SwipeActionIn):
    if not enforce_daily_swipe_limit(request.user.id):
        return Status(429, {"error": "Daily swipe limit reached. Escalate to tier2."})

    intent = get_object_or_404(PaymentIntent, id=payload.payment_intent_id)
    session = intent.approval_sessions.filter(kind=ApprovalSession.Kind.TIER1).first() or create_approval_session(intent)
    attestation, _ = ApprovalAttestation.objects.update_or_create(
        session=session,
        approver=request.user,
        defaults={"decision": payload.decision},
    )
    update_session_status(session)
    if payload.decision == ApprovalAttestation.Decision.APPROVE:
        execute_payment(intent)
    elif payload.decision == ApprovalAttestation.Decision.REJECT:
        intent.status = PaymentIntent.Status.REJECTED
        intent.save(update_fields=["status"])
    elif payload.decision == ApprovalAttestation.Decision.ESCALATE:
        intent.tier = PaymentIntent.Tier.TIER2
        intent.save(update_fields=["tier"])
        create_approval_session(intent)
    return {"session_status": session.status, "decision": attestation.decision}


@api.post("/tier2/session/", response={201: dict[str, Any]})
def tier2_session(request, payload: Tier2SessionCreateIn):
    intent = get_object_or_404(PaymentIntent, id=payload.payment_intent_id)
    intent.tier = PaymentIntent.Tier.TIER2
    intent.save(update_fields=["tier"])
    session = create_approval_session(intent)
    return Status(
        201,
        {
            "session_id": session.id,
            "required_approvers": session.required_approvers,
            "challenge_phrase": session.challenge_phrase,
            "expires_at": session.expires_at.isoformat(),
        },
    )


@api.get("/tier2/sessions/")
def tier2_sessions(request):
    sessions = ApprovalSession.objects.filter(kind=ApprovalSession.Kind.TIER2).select_related("payment_intent")[:100]
    return {
        "items": [
            {
                "id": session.id,
                "payment_intent_id": session.payment_intent_id,
                "status": session.status,
                "required_approvers": session.required_approvers,
                "expires_at": session.expires_at.isoformat(),
                "attestation_count": session.attestations.count(),
            }
            for session in sessions
        ]
    }


@api.post("/tier2/attestation/")
def tier2_attestation(request, payload: Tier2AttestationIn):
    session = get_object_or_404(ApprovalSession, id=payload.session_id, kind=ApprovalSession.Kind.TIER2)
    attestation, _ = ApprovalAttestation.objects.update_or_create(
        session=session,
        approver=request.user,
        defaults={
            "decision": payload.decision,
            "face_passed": payload.face_passed,
            "voice_passed": payload.voice_passed,
            "emotion_label": payload.emotion_label,
            "coerced": payload.coerced,
            "geo_country": payload.geo_country,
        },
    )
    update_session_status(session)
    if session.status == ApprovalSession.Status.APPROVED:
        execute_payment(session.payment_intent)
    if session.status in (ApprovalSession.Status.BLOCKED, ApprovalSession.Status.REJECTED):
        session.payment_intent.status = PaymentIntent.Status.BLOCKED
        session.payment_intent.save(update_fields=["status"])
    return {"session_status": session.status, "attestation_id": attestation.id}


@api.get("/counterparties/")
def counterparties(request):
    return {
        "items": [
            {
                "id": counterparty.id,
                "name": counterparty.name,
                "is_known": counterparty.is_known,
                "specter_quality_score": counterparty.specter_quality_score,
                "domain": counterparty.domain,
            }
            for counterparty in Counterparty.objects.order_by("name")[:200]
        ]
    }


@api.get("/rules-thresholds/")
def rules_thresholds(request):
    return {
        "tier0_max": settings.VOUCH_TIER0_MAX_AMOUNT_GBP,
        "tier1_max": settings.VOUCH_TIER1_MAX_AMOUNT_GBP,
        "hard_block_unknown_over": settings.VOUCH_HARD_BLOCK_UNKNOWN_OVER_GBP,
        "always_tier2_over": settings.VOUCH_ALWAYS_TIER2_OVER_GBP,
    }


@api.post("/rules-thresholds/update/", response={200: dict[str, Any], 400: dict[str, str]})
def rules_thresholds_update(request, payload: ThresholdUpdateIn):
    if not (payload.tier0_max < payload.tier1_max < payload.always_tier2_over):
        return Status(400, {"error": "Threshold order must satisfy tier0 < tier1 < always_tier2"})
    if payload.hard_block_unknown_over > payload.always_tier2_over:
        return Status(400, {"error": "Hard block threshold cannot exceed always_tier2 threshold"})

    old_values = {
        "tier0_max": settings.VOUCH_TIER0_MAX_AMOUNT_GBP,
        "tier1_max": settings.VOUCH_TIER1_MAX_AMOUNT_GBP,
        "hard_block_unknown_over": settings.VOUCH_HARD_BLOCK_UNKNOWN_OVER_GBP,
        "always_tier2_over": settings.VOUCH_ALWAYS_TIER2_OVER_GBP,
    }
    new_values = {
        "tier0_max": str(payload.tier0_max),
        "tier1_max": str(payload.tier1_max),
        "hard_block_unknown_over": str(payload.hard_block_unknown_over),
        "always_tier2_over": str(payload.always_tier2_over),
    }
    for key, value in new_values.items():
        PolicyConfigEvent.objects.create(
            key=key,
            old_value=str(old_values.get(key, "")),
            new_value=value,
            changed_by=request.user,
            signature=f"local-{request.user.id}-{uuid.uuid4().hex[:8]}",
        )
    return {"ok": True, "new_values": new_values}


@api.get("/receipts/")
def receipts(request):
    return {
        "items": [
            {
                "id": receipt.id,
                "payment_intent_id": receipt.payment_intent_id,
                "can_reverse_until": receipt.can_reverse_until.isoformat(),
                "reversed_at": receipt.reversed_at.isoformat() if receipt.reversed_at else None,
            }
            for receipt in Receipt.objects.select_related("payment_intent").order_by("-id")[:200]
        ]
    }


@api.get("/simulator/presets/")
def simulator_presets(request):
    return {"presets": PRESET_SCENARIOS}


@api.post("/simulator/run/", response={201: dict[str, Any], 400: dict[str, str]})
def simulator_run(request, payload: SimulatorPresetRunIn):
    try:
        intent = create_scenario_intent(preset=payload.preset, actor_id=request.user.id)
    except ValueError as exc:
        return Status(400, {"error": str(exc)})
    return Status(201, {"id": intent.id, "external_id": intent.external_id, "tier": intent.tier})


@api.post("/simulator/run-batch/", response={201: dict[str, Any], 400: dict[str, str]})
def simulator_batch_run(request, payload: SimulatorBatchRunIn):
    created = []
    for preset, count in payload.counts.items():
        if preset not in PRESET_SCENARIOS:
            return Status(400, {"error": f"Unknown preset '{preset}'"})
        qty = max(0, min(int(count), 100))
        for _ in range(qty):
            intent = create_scenario_intent(preset=preset, actor_id=request.user.id)
            created.append({"id": intent.id, "tier": intent.tier, "preset": preset})
    return Status(201, {"created_count": len(created), "items": created})


@api.post("/simulator/generate-dynamic/", response={201: dict[str, Any], 400: dict[str, str]})
def simulator_dynamic_generate(request, payload: SimulatorDynamicGenerateIn):
    count = max(1, min(payload.count, 1000))
    try:
        intents = create_dynamic_transactions(
            count=count,
            min_amount=payload.min_amount,
            max_amount=payload.max_amount,
            actor_id=request.user.id,
            require_all_tiers=payload.require_all_tiers,
        )
    except ValueError as exc:
        return Status(400, {"error": str(exc)})

    tiers = {"tier0": 0, "tier1": 0, "tier2": 0}
    for intent in intents:
        tiers[intent.tier] = tiers.get(intent.tier, 0) + 1
    return Status(
        201,
        {
            "created_count": len(intents),
            "tiers": tiers,
            "run_id": intents[0].scenario_run_id if intents else "",
        },
    )


@api.get("/vendors/specter/")
def specter_vendor_detail(request, name: str = "", domain: str = ""):
    return fetch_counterparty_signal(name=name, domain=domain)
