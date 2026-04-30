import json
import uuid
from decimal import Decimal

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_GET, require_POST
from django.views.generic import TemplateView

from activity.models import ApprovalAttestation, ApprovalSession, PaymentIntent
from activity.services.ledger import execute_payment, reverse_payment
from activity.services.plaid import PlaidConfigError, fetch_transactions
from activity.services.risk import recommend_tier, upsert_counterparty
from activity.services.router import create_approval_session, enforce_daily_swipe_limit, update_session_status
from activity.services.specter import fetch_counterparty_signal


class ActivityDashboardView(LoginRequiredMixin, TemplateView):
    template_name = "activity/dashboard.html"

    def get(self, request: HttpRequest, *args, **kwargs) -> HttpResponse:
        if not settings.VOUCH_ACTIVITY_DASHBOARD_ENABLED:
            return render(request, "activity/dashboard_disabled.html")

        context = self.get_context_data(**kwargs)
        context["last_refreshed"] = request.GET.get("last_refreshed", "")
        try:
            transactions, total = fetch_transactions()
            context["transactions"] = transactions
            context["total_transactions"] = total
            context["dashboard_error"] = ""
            # Keep the exact rendered transaction set for reliable HTMX detail lookups.
            request.session["activity_dashboard_transactions"] = {
                str(txn.get("transaction_id")): txn for txn in transactions if txn.get("transaction_id")
            }
        except PlaidConfigError as exc:
            context["transactions"] = []
            context["total_transactions"] = 0
            context["dashboard_error"] = str(exc)
            request.session["activity_dashboard_transactions"] = {}
        except Exception as exc:  # pragma: no cover
            context["transactions"] = []
            context["total_transactions"] = 0
            context["dashboard_error"] = f"Unable to load transactions: {exc}"
            request.session["activity_dashboard_transactions"] = {}

        context["source_mode"] = "Mock" if settings.PLAID_USE_MOCK else "Plaid Sandbox"
        context["lookback_days"] = settings.VOUCH_PLAID_TRANSACTION_LOOKBACK_DAYS
        context["tier0_count"] = PaymentIntent.objects.filter(tier=PaymentIntent.Tier.TIER0).count()
        context["streaming_enabled"] = True
        return render(request, self.template_name, context)


@login_required
@require_GET
def transaction_detail_partial(request: HttpRequest, transaction_id: str = "") -> HttpResponse:
    transaction_id = transaction_id or request.GET.get("transaction_id", "")
    rendered_transactions = request.session.get("activity_dashboard_transactions", {})
    selected = rendered_transactions.get(str(transaction_id))
    if selected is None:
        transactions, _ = fetch_transactions(limit=settings.VOUCH_PLAID_TRANSACTION_PAGE_SIZE)
        selected = next((txn for txn in transactions if str(txn.get("transaction_id")) == transaction_id), None)
    return render(
        request,
        "activity/partials/transaction_detail.html",
        {"transaction": selected, "transaction_json": json.dumps(selected, indent=2, sort_keys=True) if selected else ""},
    )


@login_required
@require_POST
def payment_reverse_view(request: HttpRequest, payment_id: int) -> HttpResponse:
    intent = get_object_or_404(PaymentIntent, id=payment_id)
    if reverse_payment(intent):
        messages.success(request, "Payment reversal requested.")
    else:
        messages.error(request, "Payment cannot be reversed anymore.")
    return redirect("activity:dashboard")


@login_required
@require_POST
def create_payment_intent_api(request: HttpRequest) -> JsonResponse:
    payload = json.loads(request.body or "{}")
    counterparty = upsert_counterparty(payload.get("counterparty", "Unknown"), payload.get("metadata", {}))
    amount = Decimal(str(payload.get("amount_gbp", "0")))
    tier, reasons, risk_score = recommend_tier(amount, counterparty.name, int(payload.get("anomaly_score", 0)))
    intent = PaymentIntent.objects.create(
        external_id=payload.get("external_id", str(uuid.uuid4())),
        provider=payload.get("provider", "plaid"),
        counterparty=counterparty,
        amount_gbp=amount,
        currency=payload.get("currency", "GBP"),
        risk_score=risk_score,
        risk_reasons=reasons,
        tier=tier,
        anomaly_score=int(payload.get("anomaly_score", 0)),
        metadata=payload.get("metadata", {}),
    )
    if tier == PaymentIntent.Tier.TIER0:
        execute_payment(intent)
    else:
        create_approval_session(intent)
    return JsonResponse({"id": intent.id, "tier": intent.tier, "risk_score": intent.risk_score, "reasons": reasons}, status=201)


@login_required
@require_GET
def tier1_queue_api(request: HttpRequest) -> JsonResponse:
    queue = (
        PaymentIntent.objects.filter(tier=PaymentIntent.Tier.TIER1, status=PaymentIntent.Status.PENDING)
        .select_related("counterparty")
        .order_by("created_at")[:50]
    )
    items = [
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
    return JsonResponse({"items": items})


@login_required
@require_POST
def tier1_swipe_action_api(request: HttpRequest) -> JsonResponse:
    if not enforce_daily_swipe_limit(request.user.id):
        return JsonResponse({"error": "Daily swipe limit reached. Escalate to tier2."}, status=429)

    payload = json.loads(request.body or "{}")
    intent = get_object_or_404(PaymentIntent, id=int(payload["payment_intent_id"]))
    session = intent.approval_sessions.filter(kind=ApprovalSession.Kind.TIER1).first() or create_approval_session(intent)
    decision = payload.get("decision", ApprovalAttestation.Decision.ESCALATE)
    attestation, _ = ApprovalAttestation.objects.update_or_create(
        session=session,
        approver=request.user,
        defaults={"decision": decision},
    )
    update_session_status(session)
    if decision == ApprovalAttestation.Decision.APPROVE:
        execute_payment(intent)
    elif decision == ApprovalAttestation.Decision.REJECT:
        intent.status = PaymentIntent.Status.REJECTED
        intent.save(update_fields=["status"])
    elif decision == ApprovalAttestation.Decision.ESCALATE:
        intent.tier = PaymentIntent.Tier.TIER2
        intent.save(update_fields=["tier"])
        create_approval_session(intent)
    return JsonResponse({"session_status": session.status, "decision": attestation.decision})


@login_required
@require_POST
def tier2_session_api(request: HttpRequest) -> JsonResponse:
    payload = json.loads(request.body or "{}")
    intent = get_object_or_404(PaymentIntent, id=int(payload["payment_intent_id"]))
    intent.tier = PaymentIntent.Tier.TIER2
    intent.save(update_fields=["tier"])
    session = create_approval_session(intent)
    return JsonResponse(
        {
            "session_id": session.id,
            "required_approvers": session.required_approvers,
            "challenge_phrase": session.challenge_phrase,
            "expires_at": session.expires_at.isoformat(),
        },
        status=201,
    )


@login_required
@require_POST
def tier2_attestation_api(request: HttpRequest) -> JsonResponse:
    payload = json.loads(request.body or "{}")
    session = get_object_or_404(ApprovalSession, id=int(payload["session_id"]), kind=ApprovalSession.Kind.TIER2)
    decision = payload.get("decision", ApprovalAttestation.Decision.APPROVE)
    attestation, _ = ApprovalAttestation.objects.update_or_create(
        session=session,
        approver=request.user,
        defaults={
            "decision": decision,
            "face_passed": bool(payload.get("face_passed", False)),
            "voice_passed": bool(payload.get("voice_passed", False)),
            "emotion_label": payload.get("emotion_label", ""),
            "coerced": bool(payload.get("coerced", False)),
            "geo_country": payload.get("geo_country", ""),
        },
    )
    update_session_status(session)
    if session.status == ApprovalSession.Status.APPROVED:
        execute_payment(session.payment_intent)
    if session.status in (ApprovalSession.Status.BLOCKED, ApprovalSession.Status.REJECTED):
        session.payment_intent.status = PaymentIntent.Status.BLOCKED
        session.payment_intent.save(update_fields=["status"])
    return JsonResponse({"session_status": session.status, "attestation_id": attestation.id})


@login_required
@require_GET
def specter_vendor_detail_api(request: HttpRequest) -> JsonResponse:
    name = request.GET.get("name", "")
    domain = request.GET.get("domain", "")
    return JsonResponse(fetch_counterparty_signal(name=name, domain=domain))
