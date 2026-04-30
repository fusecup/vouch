import json
from pathlib import Path

import pytest
from django.contrib.auth import get_user_model
from django.test import Client
from django.urls import reverse

from activity.models import PaymentIntent, PolicyConfigEvent


@pytest.mark.django_db
def test_dashboard_renders_with_mock_mode(settings):
    fixture = Path(settings.BASE_DIR).parent / "scripts" / "data" / "transactions.json"
    settings.PLAID_USE_MOCK = True
    settings.PLAID_MOCK_DATA = str(fixture)
    settings.VOUCH_ACTIVITY_DASHBOARD_ENABLED = True

    user = get_user_model().objects.create_user(email="dashboard@example.com", password="password")
    client = Client()
    client.force_login(user)

    response = client.get(reverse("activity:overview"))
    assert response.status_code == 200
    assert "Activity Overview" in response.content.decode()


@pytest.mark.django_db
def test_transaction_partial_renders(settings):
    fixture = Path(settings.BASE_DIR).parent / "scripts" / "data" / "transactions.json"
    settings.PLAID_USE_MOCK = True
    settings.PLAID_MOCK_DATA = str(fixture)

    first_id = json.loads(fixture.read_text())[0]["transaction_id"]
    user = get_user_model().objects.create_user(email="partial@example.com", password="password")
    client = Client()
    client.force_login(user)
    response = client.get(f"{reverse('activity:transaction_detail')}?transaction_id={first_id}")
    assert response.status_code == 200
    assert first_id in response.content.decode()


@pytest.mark.django_db
def test_create_payment_intent_api(settings):
    user = get_user_model().objects.create_user(email="api@example.com", password="password")
    client = Client()
    client.force_login(user)
    payload = {"counterparty": "Acme Ltd", "amount_gbp": "62000", "external_id": "txn-123"}
    response = client.post(
        reverse("activity:create_payment"),
        data=json.dumps(payload),
        content_type="application/json",
    )
    assert response.status_code == 201
    body = response.json()
    assert body["tier"] == PaymentIntent.Tier.TIER2
    assert PaymentIntent.objects.filter(external_id="txn-123").exists()


@pytest.mark.django_db
def test_all_dashboard_pages_render(settings):
    user = get_user_model().objects.create_user(email="pages@example.com", password="password")
    client = Client()
    client.force_login(user)
    routes = [
        "activity:overview",
        "activity:transactions",
        "activity:tier1_review",
        "activity:tier2_sessions",
        "activity:counterparties",
        "activity:rules_thresholds",
        "activity:receipts_reversals",
        "activity:simulator",
        "activity:simulation_settings",
        "activity:profile",
    ]
    for name in routes:
        response = client.get(reverse(name))
        assert response.status_code == 200


@pytest.mark.django_db
def test_rules_threshold_update_validation(settings):
    user = get_user_model().objects.create_user(email="rules@example.com", password="password")
    client = Client()
    client.force_login(user)
    bad_payload = {"tier0_max": "5000", "tier1_max": "1000", "always_tier2_over": "20000", "hard_block_unknown_over": "100"}
    response = client.post(
        reverse("activity:rules_thresholds_update_api"),
        data=json.dumps(bad_payload),
        content_type="application/json",
    )
    assert response.status_code == 400

    good_payload = {"tier0_max": "500", "tier1_max": "2000", "always_tier2_over": "20000", "hard_block_unknown_over": "1500"}
    response = client.post(
        reverse("activity:rules_thresholds_update_api"),
        data=json.dumps(good_payload),
        content_type="application/json",
    )
    assert response.status_code == 200
    assert PolicyConfigEvent.objects.count() >= 1


@pytest.mark.django_db
def test_simulator_preset_creates_payment_intent(settings):
    user = get_user_model().objects.create_user(email="sim@example.com", password="password")
    client = Client()
    client.force_login(user)

    response = client.post(
        reverse("activity:simulator_run_api"),
        data=json.dumps({"preset": "high_over_25k"}),
        content_type="application/json",
    )
    assert response.status_code == 201
    body = response.json()
    intent = PaymentIntent.objects.get(id=body["id"])
    assert intent.scenario_source == "simulator"
    assert "high_over_25k" in intent.scenario_tags


@pytest.mark.django_db
def test_page_apis_respond(settings):
    user = get_user_model().objects.create_user(email="apis@example.com", password="password")
    client = Client()
    client.force_login(user)

    urls = [
        "activity:overview_stats",
        "activity:transactions_api",
        "activity:tier1_queue",
        "activity:tier2_sessions_api",
        "activity:counterparties_api",
        "activity:rules_thresholds_api",
        "activity:receipts_api",
        "activity:simulator_presets_api",
    ]
    for name in urls:
        response = client.get(reverse(name))
        assert response.status_code == 200


@pytest.mark.django_db
def test_simulation_settings_batch_creation():
    user = get_user_model().objects.create_user(email="sim-batch@example.com", password="password")
    client = Client()
    client.force_login(user)

    page = client.get(reverse("activity:simulation_settings"))
    assert page.status_code == 200
    assert "Batch Scenario Generator" in page.content.decode()

    response = client.post(
        reverse("activity:simulator_batch_run_api"),
        data=json.dumps({"counts": {"known_low_risk": 2, "high_over_25k": 1}}),
        content_type="application/json",
    )
    assert response.status_code == 201
    body = response.json()
    assert body["created_count"] == 3
    assert PaymentIntent.objects.filter(scenario_source="simulator").count() >= 3


@pytest.mark.django_db
def test_dynamic_simulation_generation_creates_rich_transaction_data():
    user = get_user_model().objects.create_user(email="sim-dyn@example.com", password="password")
    client = Client()
    client.force_login(user)

    response = client.post(
        reverse("activity:simulator_dynamic_generate_api"),
        data=json.dumps({"count": 30, "min_amount": "50", "max_amount": "30000", "require_all_tiers": True}),
        content_type="application/json",
    )
    assert response.status_code == 201
    body = response.json()
    assert body["created_count"] == 30
    assert body["tiers"]["tier0"] >= 1
    assert body["tiers"]["tier1"] >= 1
    assert body["tiers"]["tier2"] >= 1

    intent = PaymentIntent.objects.filter(scenario_source="simulator", scenario_run_id=body["run_id"]).first()
    assert intent is not None
    assert intent.risk_reasons
    assert intent.metadata.get("merchant_category")
    assert intent.metadata.get("geo_country")
