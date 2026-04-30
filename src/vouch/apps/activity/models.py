from django.conf import settings
from django.db import models
from django.utils import timezone


class Counterparty(models.Model):
    name = models.CharField(max_length=255, unique=True)
    domain = models.CharField(max_length=255, blank=True)
    bank_fingerprint = models.CharField(max_length=255, blank=True)
    specter_company_id = models.CharField(max_length=128, blank=True)
    specter_quality_score = models.PositiveIntegerField(default=50)
    last_specter_sync_at = models.DateTimeField(null=True, blank=True)
    is_known = models.BooleanField(default=False)

    def __str__(self) -> str:
        return self.name


class PolicyConfigEvent(models.Model):
    key = models.CharField(max_length=128)
    old_value = models.CharField(max_length=255, blank=True)
    new_value = models.CharField(max_length=255)
    changed_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    signature = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at",)


class PaymentIntent(models.Model):
    class Tier(models.TextChoices):
        TIER0 = "tier0", "Tier 0"
        TIER1 = "tier1", "Tier 1"
        TIER2 = "tier2", "Tier 2"

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"
        EXECUTED = "executed", "Executed"
        BLOCKED = "blocked", "Blocked"
        REVERSED = "reversed", "Reversed"

    external_id = models.CharField(max_length=128, unique=True)
    provider = models.CharField(max_length=32, default="plaid")
    counterparty = models.ForeignKey(Counterparty, null=True, blank=True, on_delete=models.SET_NULL)
    amount_gbp = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=10, default="GBP")
    risk_score = models.PositiveIntegerField(default=0)
    risk_reasons = models.JSONField(default=list, blank=True)
    explainer_text = models.TextField(blank=True)
    tier = models.CharField(max_length=8, choices=Tier.choices, default=Tier.TIER1)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.PENDING)
    anomaly_score = models.PositiveIntegerField(default=0)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    executed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ("-created_at",)

    def __str__(self) -> str:
        return f"{self.external_id} ({self.tier})"


class LedgerEntry(models.Model):
    payment_intent = models.ForeignKey(PaymentIntent, on_delete=models.CASCADE, related_name="ledger_entries")
    provider = models.CharField(max_length=32)
    provider_txn_id = models.CharField(max_length=128, blank=True)
    idempotency_key = models.CharField(max_length=128, unique=True)
    success = models.BooleanField(default=False)
    payload = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at",)


class Receipt(models.Model):
    payment_intent = models.OneToOneField(PaymentIntent, on_delete=models.CASCADE, related_name="receipt")
    ledger_entry = models.ForeignKey(LedgerEntry, on_delete=models.CASCADE, related_name="receipts")
    can_reverse_until = models.DateTimeField()
    reversal_requested_at = models.DateTimeField(null=True, blank=True)
    reversed_at = models.DateTimeField(null=True, blank=True)

    @classmethod
    def default_reversal_window(cls) -> timezone.datetime:
        return timezone.now() + timezone.timedelta(minutes=settings.VOUCH_TIER0_REVERSAL_MINUTES)


class ApprovalSession(models.Model):
    class Kind(models.TextChoices):
        TIER1 = "tier1", "Tier 1"
        TIER2 = "tier2", "Tier 2"

    class Status(models.TextChoices):
        OPEN = "open", "Open"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"
        EXPIRED = "expired", "Expired"
        BLOCKED = "blocked", "Blocked"

    payment_intent = models.ForeignKey(PaymentIntent, on_delete=models.CASCADE, related_name="approval_sessions")
    kind = models.CharField(max_length=8, choices=Kind.choices)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.OPEN)
    required_approvers = models.PositiveIntegerField(default=1)
    challenge_phrase = models.CharField(max_length=255, blank=True)
    expires_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)


class ApprovalAttestation(models.Model):
    class Decision(models.TextChoices):
        APPROVE = "approve", "Approve"
        REJECT = "reject", "Reject"
        ESCALATE = "escalate", "Escalate"

    session = models.ForeignKey(ApprovalSession, on_delete=models.CASCADE, related_name="attestations")
    approver = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="attestations")
    decision = models.CharField(max_length=16, choices=Decision.choices)
    face_passed = models.BooleanField(default=False)
    voice_passed = models.BooleanField(default=False)
    emotion_label = models.CharField(max_length=32, blank=True)
    coerced = models.BooleanField(default=False)
    geo_country = models.CharField(max_length=64, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("session", "approver")
