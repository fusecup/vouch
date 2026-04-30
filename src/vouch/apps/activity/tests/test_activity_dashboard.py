import json
from pathlib import Path

import pytest
from django.contrib.auth import get_user_model
from django.test import Client
from django.urls import reverse

from activity.models import PaymentIntent


@pytest.mark.django_db
def test_dashboard_renders_with_mock_mode(settings):
    fixture = Path(settings.BASE_DIR).parent / "scripts" / "data" / "transactions.json"
    settings.PLAID_USE_MOCK = True
    settings.PLAID_MOCK_DATA = str(fixture)
    settings.VOUCH_ACTIVITY_DASHBOARD_ENABLED = True

    user = get_user_model().objects.create_user(email="dashboard@example.com", password="password")
    client = Client()
    client.force_login(user)

    response = client.get(reverse("activity:dashboard"))
    assert response.status_code == 200
    assert "Vouch Activity Dashboard" in response.content.decode()


@pytest.mark.django_db
def test_transaction_partial_renders(settings):
    fixture = Path(settings.BASE_DIR).parent / "scripts" / "data" / "transactions.json"
    settings.PLAID_USE_MOCK = True
    settings.PLAID_MOCK_DATA = str(fixture)

    first_id = json.loads(fixture.read_text())[0]["transaction_id"]
    user = get_user_model().objects.create_user(email="partial@example.com", password="password")
    client = Client()
    client.force_login(user)
    response = client.get(reverse("activity:transaction_detail", kwargs={"transaction_id": first_id}))
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
