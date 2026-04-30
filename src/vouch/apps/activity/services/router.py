from decimal import Decimal

from django.conf import settings
from django.utils import timezone

from activity.models import ApprovalAttestation, ApprovalSession, PaymentIntent


def create_approval_session(intent: PaymentIntent) -> ApprovalSession:
    required = 1
    kind = ApprovalSession.Kind.TIER1
    phrase = ""
    if intent.tier == PaymentIntent.Tier.TIER2:
        required = min(settings.VOUCH_TIER2_MAX_APPROVERS, settings.VOUCH_TIER2_MIN_APPROVERS)
        kind = ApprovalSession.Kind.TIER2
        phrase = f"Authorize {intent.amount_gbp} GBP to {intent.counterparty.name if intent.counterparty else 'recipient'}"

    expires = timezone.now() + timezone.timedelta(
        minutes=settings.VOUCH_TIER2_WINDOW_MINUTES if kind == ApprovalSession.Kind.TIER2 else settings.VOUCH_TIER1_FALLBACK_MINUTES
    )
    return ApprovalSession.objects.create(
        payment_intent=intent,
        kind=kind,
        required_approvers=required,
        challenge_phrase=phrase,
        expires_at=expires,
    )


def enforce_daily_swipe_limit(user_id: int) -> bool:
    day_start = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
    count = ApprovalAttestation.objects.filter(
        approver_id=user_id,
        session__kind=ApprovalSession.Kind.TIER1,
        created_at__gte=day_start,
    ).count()
    return count < settings.VOUCH_MAX_TIER1_CARDS_PER_DAY


def should_hard_block(intent: PaymentIntent) -> bool:
    if intent.amount_gbp >= Decimal(str(settings.VOUCH_ALWAYS_TIER2_OVER_GBP)):
        return False
    if intent.counterparty and not intent.counterparty.is_known:
        return intent.amount_gbp >= Decimal(str(settings.VOUCH_HARD_BLOCK_UNKNOWN_OVER_GBP))
    return False


def update_session_status(session: ApprovalSession) -> None:
    attestations = session.attestations.all()
    if any(att.coerced for att in attestations):
        session.status = ApprovalSession.Status.BLOCKED
    elif any(att.decision == ApprovalAttestation.Decision.REJECT for att in attestations):
        session.status = ApprovalSession.Status.REJECTED
    elif attestations.filter(decision=ApprovalAttestation.Decision.APPROVE).count() >= session.required_approvers:
        session.status = ApprovalSession.Status.APPROVED
    elif timezone.now() > session.expires_at:
        session.status = ApprovalSession.Status.EXPIRED
    else:
        session.status = ApprovalSession.Status.OPEN
    session.save(update_fields=["status"])
