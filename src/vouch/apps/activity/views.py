import json
import uuid
from datetime import date, timedelta
from decimal import Decimal
from itertools import groupby

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.paginator import Paginator
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_GET, require_POST
from django.views.generic import TemplateView

from activity.models import ApprovalAttestation, ApprovalSession, Counterparty, PaymentIntent, PolicyConfigEvent, Receipt
from activity.services.ledger import execute_payment, reverse_payment
from activity.services.plaid import PlaidConfigError, fetch_transactions
from activity.services.risk import recommend_tier, upsert_counterparty
from activity.services.router import create_approval_session, enforce_daily_swipe_limit, update_session_status
from activity.services.simulator import PRESET_SCENARIOS, create_dynamic_transactions, create_scenario_intent
from activity.services.specter import fetch_company_profile, fetch_counterparty_signal


def _intent_to_transaction(intent: PaymentIntent) -> dict:
    return {
        "transaction_id": f"intent-{intent.id}",
        "date": intent.created_at.date().isoformat(),
        "name": intent.counterparty.name if intent.counterparty else "Unknown",
        "amount": str(intent.amount_gbp),
        "pending": intent.status == PaymentIntent.Status.PENDING,
        "account_id": intent.external_id,
        "category": [f"Tier {intent.tier}"],
        "source": intent.scenario_source or intent.provider,
        "payment_intent_id": intent.id,
        "status": intent.status,
        "risk_score": intent.risk_score,
        "risk_reasons": intent.risk_reasons,
        "anomaly_score": intent.anomaly_score,
        "metadata": intent.metadata,
    }


def _get_initials(name: str) -> str:
    words = name.split()
    if len(words) >= 2:
        return (words[0][0] + words[1][0]).upper()
    return words[0][0].upper() if words else "?"


def _get_settlement_status(intent: PaymentIntent) -> str:
    if intent.status in (PaymentIntent.Status.EXECUTED, PaymentIntent.Status.APPROVED, PaymentIntent.Status.REVERSED):
        return "Settled instantly"
    if intent.tier == PaymentIntent.Tier.TIER2:
        return "Holds until 3 vouchers"
    if intent.tier == PaymentIntent.Tier.TIER1:
        return "Clears in 2h"
    return "Clears T+1"


def _format_transaction_intent(intent: PaymentIntent) -> dict:
    txn = _intent_to_transaction(intent)
    txn_date = intent.created_at.date()
    today = date.today()
    yesterday = today - timedelta(days=1)
    if txn_date == today:
        txn["date_label"] = "Today"
    elif txn_date == yesterday:
        txn["date_label"] = "Yesterday"
    else:
        txn["date_label"] = f"{txn_date.day} {txn_date.strftime('%b %Y')}"
    txn["date_formatted"] = f"{txn_date.day} {txn_date.strftime('%b %Y')}"
    txn["payment_type"] = (intent.metadata or {}).get("payment_type", "Recurring")
    txn["settlement_status"] = _get_settlement_status(intent)
    tier_map = {
        PaymentIntent.Tier.TIER0: "1",
        PaymentIntent.Tier.TIER1: "2",
        PaymentIntent.Tier.TIER2: "3",
    }
    txn["tier_display"] = tier_map.get(intent.tier, "1")
    txn["initials"] = _get_initials(txn["name"])
    return txn


def _group_transaction_feed(transactions: list[dict]) -> list[dict]:
    groups = []
    for label, group_txns in groupby(transactions, key=lambda t: t["date_label"]):
        txn_list = list(group_txns)
        total = int(sum(Decimal(t["amount"]) for t in txn_list))
        pending_count = sum(1 for t in txn_list if t["pending"])
        settled_count = len(txn_list) - pending_count
        groups.append({
            "label": label,
            "transactions": txn_list,
            "total_gbp": total,
            "pending_count": pending_count,
            "settled_count": settled_count,
        })
    return groups


class BaseActivityPageView(LoginRequiredMixin, TemplateView):
    page_title = "Activity"
    template_name = "activity/overview.html"

    def base_context(self, request: HttpRequest) -> dict:
        return {
            "page_title": self.page_title,
            "tier0_count": PaymentIntent.objects.filter(tier=PaymentIntent.Tier.TIER0).count(),
            "tier1_pending_count": PaymentIntent.objects.filter(
                tier=PaymentIntent.Tier.TIER1, status=PaymentIntent.Status.PENDING
            ).count(),
            "tier2_pending_count": PaymentIntent.objects.filter(
                tier=PaymentIntent.Tier.TIER2, status=PaymentIntent.Status.PENDING
            ).count(),
        }

    def get(self, request: HttpRequest, *args, **kwargs) -> HttpResponse:
        if not settings.VOUCH_ACTIVITY_DASHBOARD_ENABLED:
            return render(request, "activity/dashboard_disabled.html")
        context = self.get_context_data(**kwargs)
        context.update(self.base_context(request))
        return render(request, self.template_name, context)


class ActivityOverviewView(BaseActivityPageView):
    template_name = "activity/overview.html"
    page_title = "Overview"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        recent_intents = PaymentIntent.objects.select_related("counterparty").order_by("-created_at")[:10]
        context["recent_intents"] = recent_intents
        context["recent_receipts"] = Receipt.objects.select_related("payment_intent").order_by("-id")[:5]
        return context


class ActivityTransactionsView(BaseActivityPageView):
    template_name = "activity/transactions.html"
    page_title = "Transactions"

    def get(self, request: HttpRequest, *args, **kwargs) -> HttpResponse:
        if not settings.VOUCH_ACTIVITY_DASHBOARD_ENABLED:
            return render(request, "activity/dashboard_disabled.html")
        context = self.get_context_data(**kwargs)
        context.update(self.base_context(request))
        context["last_refreshed"] = request.GET.get("last_refreshed", "")
        source_mode = getattr(settings, "VOUCH_ACTIVITY_TRANSACTIONS_SOURCE", "internal")
        context["source_mode"] = source_mode.title()
        context["lookback_days"] = settings.VOUCH_PLAID_TRANSACTION_LOOKBACK_DAYS
        if source_mode == "plaid":
            try:
                transactions, total = fetch_transactions()
                context["transactions"] = transactions
                context["total_transactions"] = total
                context["dashboard_error"] = ""
            except PlaidConfigError as exc:
                context["transactions"] = []
                context["total_transactions"] = 0
                context["dashboard_error"] = str(exc)
            except Exception as exc:  # pragma: no cover
                context["transactions"] = []
                context["total_transactions"] = 0
                context["dashboard_error"] = f"Unable to load transactions: {exc}"
        else:
            intents = PaymentIntent.objects.select_related("counterparty").order_by("-created_at")[:200]
            transactions = [_format_transaction_intent(intent) for intent in intents]
            context["transactions"] = transactions
            context["total_transactions"] = len(transactions)
            context["dashboard_error"] = ""
            context["transaction_groups"] = _group_transaction_feed(transactions)
        request.session["activity_dashboard_transactions"] = {
            str(txn.get("transaction_id")): txn for txn in context["transactions"] if txn.get("transaction_id")
        }
        return render(request, self.template_name, context)


class ActivityTier1ReviewView(BaseActivityPageView):
    template_name = "activity/tier1_review.html"
    page_title = "Tier 1 Review"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["queue"] = (
            PaymentIntent.objects.filter(tier=PaymentIntent.Tier.TIER1, status=PaymentIntent.Status.PENDING)
            .select_related("counterparty")
            .order_by("created_at")[:100]
        )
        return context


class ActivityTier2SessionsView(BaseActivityPageView):
    template_name = "activity/tier2_sessions.html"
    page_title = "Tier 2 Sessions"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        sessions = ApprovalSession.objects.filter(kind=ApprovalSession.Kind.TIER2).select_related("payment_intent")[:100]
        context["sessions"] = sessions
        return context


class ActivityCounterpartiesView(BaseActivityPageView):
    template_name = "activity/counterparties.html"
    page_title = "Counterparties"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        counterparties = Counterparty.objects.order_by("name")
        paginator = Paginator(counterparties, 50)
        page_obj = paginator.get_page(1)
        context["counterparties"] = page_obj
        return context


class ActivityRulesThresholdsView(BaseActivityPageView):
    template_name = "activity/rules_thresholds.html"
    page_title = "Rules and Thresholds"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["thresholds"] = {
            "tier0_max": settings.VOUCH_TIER0_MAX_AMOUNT_GBP,
            "tier1_max": settings.VOUCH_TIER1_MAX_AMOUNT_GBP,
            "hard_block_unknown_over": settings.VOUCH_HARD_BLOCK_UNKNOWN_OVER_GBP,
            "always_tier2_over": settings.VOUCH_ALWAYS_TIER2_OVER_GBP,
        }
        context["config_events"] = PolicyConfigEvent.objects.select_related("changed_by").order_by("-created_at")[:50]
        return context


class ActivityReceiptsReversalsView(BaseActivityPageView):
    template_name = "activity/receipts_reversals.html"
    page_title = "Receipts and Reversals"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["receipts"] = Receipt.objects.select_related("payment_intent", "ledger_entry").order_by("-id")[:100]
        return context


class ActivitySimulatorView(BaseActivityPageView):
    template_name = "activity/simulator.html"
    page_title = "Simulator"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["presets"] = PRESET_SCENARIOS
        context["simulated"] = (
            PaymentIntent.objects.filter(scenario_source="simulator")
            .select_related("counterparty")
            .order_by("-created_at")[:100]
        )
        return context


class ActivitySimulationSettingsView(BaseActivityPageView):
    template_name = "activity/simulation_settings.html"
    page_title = "Simulation Settings"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["presets"] = PRESET_SCENARIOS
        context["default_batch_size"] = 5
        return context


class ActivityDashboardView(BaseActivityPageView):
    template_name = "activity/dashboard.html"

    def get(self, request: HttpRequest, *args, **kwargs) -> HttpResponse:
        if not settings.VOUCH_ACTIVITY_DASHBOARD_ENABLED:
            return render(request, "activity/dashboard_disabled.html")
        context = self.get_context_data(**kwargs)
        context.update(self.base_context(request))

        intents = PaymentIntent.objects.select_related("counterparty").order_by("-created_at")[:50]
        transactions = [_format_transaction_intent(intent) for intent in intents]
        groups = _group_transaction_feed(transactions)

        context["transaction_groups"] = groups
        source_mode = getattr(settings, "VOUCH_ACTIVITY_TRANSACTIONS_SOURCE", "internal")
        context["source_mode"] = "PLAID SANDBOX" if source_mode == "plaid" else "INTERNAL"

        request.session["activity_dashboard_transactions"] = {
            str(txn.get("transaction_id")): txn for txn in transactions if txn.get("transaction_id")
        }
        return render(request, self.template_name, context)


class ActivityProfileView(BaseActivityPageView):
    template_name = "activity/profile.html"
    page_title = "Profile"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["user_email"] = self.request.user.email
        context["user_name"] = self.request.user.get_full_name() or self.request.user.email
        return context


@login_required
@require_GET
def transactions_api(request: HttpRequest) -> JsonResponse:
    limit = int(request.GET.get("limit", settings.VOUCH_PLAID_TRANSACTION_PAGE_SIZE))
    offset = int(request.GET.get("offset", 0))
    source_mode = getattr(settings, "VOUCH_ACTIVITY_TRANSACTIONS_SOURCE", "internal")
    if source_mode == "plaid":
        txns, total = fetch_transactions(limit=limit, offset=offset)
    else:
        intents = PaymentIntent.objects.select_related("counterparty").order_by("-created_at")[offset : offset + limit]
        txns = [_intent_to_transaction(intent) for intent in intents]
        total = PaymentIntent.objects.count()
    return JsonResponse({"total": total, "items": txns})


@login_required
@require_GET
def overview_stats_api(request: HttpRequest) -> JsonResponse:
    return JsonResponse(
        {
            "tier0_executed": PaymentIntent.objects.filter(tier=PaymentIntent.Tier.TIER0).count(),
            "tier1_pending": PaymentIntent.objects.filter(
                tier=PaymentIntent.Tier.TIER1, status=PaymentIntent.Status.PENDING
            ).count(),
            "tier2_pending": PaymentIntent.objects.filter(
                tier=PaymentIntent.Tier.TIER2, status=PaymentIntent.Status.PENDING
            ).count(),
            "receipts_count": Receipt.objects.count(),
        }
    )


@login_required
@require_GET
def tier2_sessions_api(request: HttpRequest) -> JsonResponse:
    sessions = ApprovalSession.objects.filter(kind=ApprovalSession.Kind.TIER2).select_related("payment_intent")[:100]
    data = [
        {
            "id": s.id,
            "payment_intent_id": s.payment_intent_id,
            "status": s.status,
            "required_approvers": s.required_approvers,
            "expires_at": s.expires_at.isoformat(),
            "attestation_count": s.attestations.count(),
        }
        for s in sessions
    ]
    return JsonResponse({"items": data})


@login_required
@require_GET
def counterparties_api(request: HttpRequest) -> JsonResponse:
    data = [
        {
            "id": c.id,
            "name": c.name,
            "is_known": c.is_known,
            "specter_quality_score": c.specter_quality_score,
            "domain": c.domain,
        }
        for c in Counterparty.objects.order_by("name")[:200]
    ]
    return JsonResponse({"items": data})


@login_required
@require_GET
def receipts_api(request: HttpRequest) -> JsonResponse:
    data = [
        {
            "id": r.id,
            "payment_intent_id": r.payment_intent_id,
            "can_reverse_until": r.can_reverse_until.isoformat(),
            "reversed_at": r.reversed_at.isoformat() if r.reversed_at else None,
        }
        for r in Receipt.objects.select_related("payment_intent").order_by("-id")[:200]
    ]
    return JsonResponse({"items": data})


@login_required
@require_GET
def rules_thresholds_api(request: HttpRequest) -> JsonResponse:
    data = {
        "tier0_max": settings.VOUCH_TIER0_MAX_AMOUNT_GBP,
        "tier1_max": settings.VOUCH_TIER1_MAX_AMOUNT_GBP,
        "hard_block_unknown_over": settings.VOUCH_HARD_BLOCK_UNKNOWN_OVER_GBP,
        "always_tier2_over": settings.VOUCH_ALWAYS_TIER2_OVER_GBP,
    }
    return JsonResponse(data)


@login_required
@require_POST
def rules_thresholds_update_api(request: HttpRequest) -> JsonResponse:
    payload = json.loads(request.body or "{}")
    tier0 = Decimal(str(payload.get("tier0_max", settings.VOUCH_TIER0_MAX_AMOUNT_GBP)))
    tier1 = Decimal(str(payload.get("tier1_max", settings.VOUCH_TIER1_MAX_AMOUNT_GBP)))
    hard = Decimal(str(payload.get("hard_block_unknown_over", settings.VOUCH_HARD_BLOCK_UNKNOWN_OVER_GBP)))
    always2 = Decimal(str(payload.get("always_tier2_over", settings.VOUCH_ALWAYS_TIER2_OVER_GBP)))
    if not (tier0 < tier1 < always2):
        return JsonResponse({"error": "Threshold order must satisfy tier0 < tier1 < always_tier2"}, status=400)
    if hard > always2:
        return JsonResponse({"error": "Hard block threshold cannot exceed always_tier2 threshold"}, status=400)

    old_values = {
        "tier0_max": settings.VOUCH_TIER0_MAX_AMOUNT_GBP,
        "tier1_max": settings.VOUCH_TIER1_MAX_AMOUNT_GBP,
        "hard_block_unknown_over": settings.VOUCH_HARD_BLOCK_UNKNOWN_OVER_GBP,
        "always_tier2_over": settings.VOUCH_ALWAYS_TIER2_OVER_GBP,
    }
    new_values = {
        "tier0_max": str(tier0),
        "tier1_max": str(tier1),
        "hard_block_unknown_over": str(hard),
        "always_tier2_over": str(always2),
    }
    for key, value in new_values.items():
        PolicyConfigEvent.objects.create(
            key=key,
            old_value=str(old_values.get(key, "")),
            new_value=value,
            changed_by=request.user,
            signature=f"local-{request.user.id}-{uuid.uuid4().hex[:8]}",
        )
    return JsonResponse({"ok": True, "new_values": new_values})


@login_required
@require_POST
def simulator_run_api(request: HttpRequest) -> JsonResponse:
    payload = json.loads(request.body or "{}")
    preset = payload.get("preset", "")
    try:
        intent = create_scenario_intent(preset=preset, actor_id=request.user.id)
    except ValueError as exc:
        return JsonResponse({"error": str(exc)}, status=400)
    return JsonResponse({"id": intent.id, "external_id": intent.external_id, "tier": intent.tier}, status=201)


@login_required
@require_POST
def simulator_batch_run_api(request: HttpRequest) -> JsonResponse:
    payload = json.loads(request.body or "{}")
    counts = payload.get("counts", {})
    created = []
    for preset, count in counts.items():
        if preset not in PRESET_SCENARIOS:
            return JsonResponse({"error": f"Unknown preset '{preset}'"}, status=400)
        qty = max(0, min(int(count), 100))
        for _ in range(qty):
            intent = create_scenario_intent(preset=preset, actor_id=request.user.id)
            created.append({"id": intent.id, "tier": intent.tier, "preset": preset})
    return JsonResponse({"created_count": len(created), "items": created}, status=201)


@login_required
@require_POST
def simulator_dynamic_generate_api(request: HttpRequest) -> JsonResponse:
    payload = json.loads(request.body or "{}")
    try:
        count = int(payload.get("count", 25))
        min_amount = Decimal(str(payload.get("min_amount", "20")))
        max_amount = Decimal(str(payload.get("max_amount", "50000")))
        require_all_tiers = bool(payload.get("require_all_tiers", True))
    except Exception:
        return JsonResponse({"error": "Invalid payload values for dynamic simulation"}, status=400)

    count = max(1, min(count, 1000))
    try:
        intents = create_dynamic_transactions(
            count=count,
            min_amount=min_amount,
            max_amount=max_amount,
            actor_id=request.user.id,
            require_all_tiers=require_all_tiers,
        )
    except ValueError as exc:
        return JsonResponse({"error": str(exc)}, status=400)

    tiers = {"tier0": 0, "tier1": 0, "tier2": 0}
    for intent in intents:
        tiers[intent.tier] = tiers.get(intent.tier, 0) + 1
    return JsonResponse(
        {
            "created_count": len(intents),
            "tiers": tiers,
            "run_id": intents[0].scenario_run_id if intents else "",
        },
        status=201,
    )


@login_required
@require_GET
def simulator_presets_api(request: HttpRequest) -> JsonResponse:
    return JsonResponse({"presets": PRESET_SCENARIOS})


@login_required
@require_GET
def transaction_detail_partial(request: HttpRequest, transaction_id: str = "") -> HttpResponse:
    transaction_id = transaction_id or request.GET.get("transaction_id", "")
    rendered_transactions = request.session.get("activity_dashboard_transactions", {})
    selected = rendered_transactions.get(str(transaction_id))
    if selected is None:
        if str(transaction_id).startswith("intent-"):
            try:
                intent_id = int(str(transaction_id).replace("intent-", ""))
                intent = PaymentIntent.objects.select_related("counterparty").get(id=intent_id)
                selected = _intent_to_transaction(intent)
            except (ValueError, PaymentIntent.DoesNotExist):
                selected = None
        else:
            transactions, _ = fetch_transactions(limit=settings.VOUCH_PLAID_TRANSACTION_PAGE_SIZE)
            selected = next((txn for txn in transactions if str(txn.get("transaction_id")) == transaction_id), None)
    specter = {}
    if selected:
        cp_name = selected.get("name", "")
        cp_domain = ""
        if str(transaction_id).startswith("intent-"):
            try:
                intent_id = int(str(transaction_id).replace("intent-", ""))
                cp = PaymentIntent.objects.select_related("counterparty").get(id=intent_id).counterparty
                if cp:
                    cp_domain = cp.domain
            except (ValueError, PaymentIntent.DoesNotExist):
                pass
        specter = fetch_company_profile(name=cp_name, domain=cp_domain)

    return render(
        request,
        "activity/partials/transaction_detail.html",
        {
            "transaction": selected,
            "transaction_json": json.dumps(selected, indent=2, sort_keys=True) if selected else "",
            "specter": specter,
        },
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
