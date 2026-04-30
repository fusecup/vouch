import json
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from datetime import date, timedelta
from pathlib import Path
from typing import Any

from django.conf import settings


class PlaidConfigError(Exception):
    pass


@dataclass
class MockAccount:
    account_id: str
    balances: dict
    name: str
    official_name: str
    type: str
    subtype: str
    mask: str = "0000"


@dataclass
class MockTransactionsGetResponse:
    accounts: list[MockAccount]
    transactions: list[dict]
    total_transactions: int
    item: dict = field(default_factory=lambda: {"item_id": "mock_item_id"})


def _default_mock_path() -> Path:
    return Path(settings.BASE_DIR).parent / "scripts" / "data" / "transactions.json"


def _load_transactions() -> list[dict]:
    explicit = settings.PLAID_MOCK_DATA
    candidate = Path(explicit) if explicit else _default_mock_path()
    if candidate.exists():
        return json.loads(candidate.read_text())

    generator = Path(settings.BASE_DIR).parent / "scripts" / "generate_coffee_shop_data.py"
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tmp:
        subprocess.run(
            [sys.executable, str(generator), "--format", "json", "--output", tmp.name],
            check=True,
        )
        return json.loads(Path(tmp.name).read_text())


class MockPlaidClient:
    def __init__(self, transactions: list[dict]) -> None:
        self._transactions = transactions

    def transactions_get(self, request: Any) -> MockTransactionsGetResponse:
        if isinstance(request, dict):
            start = request.get("start_date")
            end = request.get("end_date")
            options = request.get("options", {})
        else:
            start = getattr(request, "start_date")
            end = getattr(request, "end_date")
            options = getattr(request, "options", {})

        start_date = date.fromisoformat(str(start))
        end_date = date.fromisoformat(str(end))
        count = int(getattr(options, "count", options.get("count", 100)))
        offset = int(getattr(options, "offset", options.get("offset", 0)))

        in_range = [txn for txn in self._transactions if start_date <= date.fromisoformat(txn["date"]) <= end_date]
        return MockTransactionsGetResponse(
            accounts=[],
            transactions=in_range[offset : offset + count],
            total_transactions=len(in_range),
        )


def get_plaid_client() -> Any:
    if settings.PLAID_USE_MOCK:
        return MockPlaidClient(_load_transactions())

    if not settings.PLAID_ACCESS_TOKEN:
        raise PlaidConfigError("PLAID_ACCESS_TOKEN is required when PLAID_USE_MOCK is false.")
    if not settings.PLAID_CLIENT_ID or not settings.PLAID_SECRET:
        raise PlaidConfigError("PLAID_CLIENT_ID and PLAID_SECRET are required for live Plaid mode.")

    import plaid
    from plaid.api import plaid_api

    env_map = {
        "sandbox": plaid.Environment.Sandbox,
        "development": plaid.Environment.Development,
        "production": plaid.Environment.Production,
    }
    env_key = settings.PLAID_ENV.lower()
    config = plaid.Configuration(
        host=env_map[env_key],
        api_key={"clientId": settings.PLAID_CLIENT_ID, "secret": settings.PLAID_SECRET},
    )
    return plaid_api.PlaidApi(plaid.ApiClient(config))


def serialize_transaction(txn: Any) -> dict:
    if isinstance(txn, dict):
        return txn
    if hasattr(txn, "to_dict"):
        return txn.to_dict()
    if hasattr(txn, "__dict__"):
        return dict(txn.__dict__)
    return {"raw": str(txn)}


def fetch_transactions(limit: int | None = None, offset: int = 0) -> tuple[list[dict], int]:
    page_size = limit or settings.VOUCH_PLAID_TRANSACTION_PAGE_SIZE
    end_date = date.today()
    start_date = end_date - timedelta(days=settings.VOUCH_PLAID_TRANSACTION_LOOKBACK_DAYS)
    request = {
        "access_token": settings.PLAID_ACCESS_TOKEN,
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "options": {"count": page_size, "offset": offset},
    }
    client = get_plaid_client()
    response = client.transactions_get(request)
    transactions = [serialize_transaction(txn) for txn in response.transactions]
    return transactions, int(response.total_transactions)
