from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Counterparty",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=255, unique=True)),
                ("domain", models.CharField(blank=True, max_length=255)),
                ("bank_fingerprint", models.CharField(blank=True, max_length=255)),
                ("specter_company_id", models.CharField(blank=True, max_length=128)),
                ("specter_quality_score", models.PositiveIntegerField(default=50)),
                ("last_specter_sync_at", models.DateTimeField(blank=True, null=True)),
                ("is_known", models.BooleanField(default=False)),
            ],
        ),
        migrations.CreateModel(
            name="PolicyConfigEvent",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("key", models.CharField(max_length=128)),
                ("old_value", models.CharField(blank=True, max_length=255)),
                ("new_value", models.CharField(max_length=255)),
                ("signature", models.CharField(blank=True, max_length=255)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "changed_by",
                    models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL),
                ),
            ],
            options={"ordering": ("-created_at",)},
        ),
        migrations.CreateModel(
            name="PaymentIntent",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("external_id", models.CharField(max_length=128, unique=True)),
                ("provider", models.CharField(default="plaid", max_length=32)),
                ("amount_gbp", models.DecimalField(decimal_places=2, max_digits=12)),
                ("currency", models.CharField(default="GBP", max_length=10)),
                ("risk_score", models.PositiveIntegerField(default=0)),
                ("risk_reasons", models.JSONField(blank=True, default=list)),
                ("explainer_text", models.TextField(blank=True)),
                (
                    "tier",
                    models.CharField(
                        choices=[("tier0", "Tier 0"), ("tier1", "Tier 1"), ("tier2", "Tier 2")],
                        default="tier1",
                        max_length=8,
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("pending", "Pending"),
                            ("approved", "Approved"),
                            ("rejected", "Rejected"),
                            ("executed", "Executed"),
                            ("blocked", "Blocked"),
                            ("reversed", "Reversed"),
                        ],
                        default="pending",
                        max_length=16,
                    ),
                ),
                ("anomaly_score", models.PositiveIntegerField(default=0)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("executed_at", models.DateTimeField(blank=True, null=True)),
                (
                    "counterparty",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        to="activity.counterparty",
                    ),
                ),
            ],
            options={"ordering": ("-created_at",)},
        ),
        migrations.CreateModel(
            name="ApprovalSession",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("kind", models.CharField(choices=[("tier1", "Tier 1"), ("tier2", "Tier 2")], max_length=8)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("open", "Open"),
                            ("approved", "Approved"),
                            ("rejected", "Rejected"),
                            ("expired", "Expired"),
                            ("blocked", "Blocked"),
                        ],
                        default="open",
                        max_length=16,
                    ),
                ),
                ("required_approvers", models.PositiveIntegerField(default=1)),
                ("challenge_phrase", models.CharField(blank=True, max_length=255)),
                ("expires_at", models.DateTimeField()),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("payment_intent", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="approval_sessions", to="activity.paymentintent")),
            ],
        ),
        migrations.CreateModel(
            name="ApprovalAttestation",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("decision", models.CharField(choices=[("approve", "Approve"), ("reject", "Reject"), ("escalate", "Escalate")], max_length=16)),
                ("face_passed", models.BooleanField(default=False)),
                ("voice_passed", models.BooleanField(default=False)),
                ("emotion_label", models.CharField(blank=True, max_length=32)),
                ("coerced", models.BooleanField(default=False)),
                ("geo_country", models.CharField(blank=True, max_length=64)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("approver", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="attestations", to=settings.AUTH_USER_MODEL)),
                ("session", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="attestations", to="activity.approvalsession")),
            ],
            options={"unique_together": {("session", "approver")}},
        ),
        migrations.CreateModel(
            name="LedgerEntry",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("provider", models.CharField(max_length=32)),
                ("provider_txn_id", models.CharField(blank=True, max_length=128)),
                ("idempotency_key", models.CharField(max_length=128, unique=True)),
                ("success", models.BooleanField(default=False)),
                ("payload", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("payment_intent", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="ledger_entries", to="activity.paymentintent")),
            ],
            options={"ordering": ("-created_at",)},
        ),
        migrations.CreateModel(
            name="Receipt",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("can_reverse_until", models.DateTimeField()),
                ("reversal_requested_at", models.DateTimeField(blank=True, null=True)),
                ("reversed_at", models.DateTimeField(blank=True, null=True)),
                ("ledger_entry", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="receipts", to="activity.ledgerentry")),
                ("payment_intent", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="receipt", to="activity.paymentintent")),
            ],
        ),
    ]
