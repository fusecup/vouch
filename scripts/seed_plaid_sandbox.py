"""
Create a Plaid sandbox item for Morning Grounds Coffee and advance a test clock
through 2 years so Plaid generates its own transactions.

Plaid sandbox does NOT allow uploading arbitrary custom transactions via API.
What IS possible:
  1. Test Clock — create a fake item at a past date, advance the clock through
     2 years.  Plaid generates transactions automatically.  This is the closest
     you get to "2 years of history" in a genuine Plaid sandbox item.

  2. Mock client (see mock_plaid_client.py) — for a demo that needs specific
     merchant names / amounts, skip the real Plaid client and return your
     generated data instead.

Requirements:
  pip install plaid-python python-dotenv

Usage:
  export PLAID_CLIENT_ID=...
  export PLAID_SECRET=...   # Sandbox secret from dashboard.plaid.com
  python scripts/seed_plaid_sandbox.py
"""

import os
import time
from datetime import date, timedelta

try:
    import plaid
    from plaid.api import plaid_api
    from plaid.model.country_code import CountryCode
    from plaid.model.products import Products
    from plaid.model.sandbox_item_fire_webhook_request import SandboxItemFireWebhookRequest
    from plaid.model.sandbox_public_token_create_request import SandboxPublicTokenCreateRequest
    from plaid.model.sandbox_public_token_create_request_options import SandboxPublicTokenCreateRequestOptions
    from plaid.model.sandbox_test_clock_advance_request import SandboxTestClockAdvanceRequest
    from plaid.model.sandbox_test_clock_create_request import SandboxTestClockCreateRequest
    from plaid.model.item_public_token_exchange_request import ItemPublicTokenExchangeRequest
    from plaid.model.transactions_get_request import TransactionsGetRequest
    from plaid.model.transactions_get_request_options import TransactionsGetRequestOptions
except ImportError:
    print("Install plaid-python first:  pip install plaid-python")
    raise


def build_client() -> plaid_api.PlaidApi:
    client_id = os.environ["PLAID_CLIENT_ID"]
    secret = os.environ["PLAID_SECRET"]

    configuration = plaid.Configuration(
        host=plaid.Environment.Sandbox,
        api_key={"clientId": client_id, "secret": secret},
    )
    api_client = plaid.ApiClient(configuration)
    return plaid_api.PlaidApi(api_client)


def create_test_clock(client: plaid_api.PlaidApi, start: date) -> str:
    """Create a test clock anchored at `start`. Returns test_clock_id."""
    import datetime
    start_dt = datetime.datetime(start.year, start.month, start.day, 0, 0, 0)

    req = SandboxTestClockCreateRequest(virtual_time=start_dt)
    resp = client.sandbox_test_clock_create(req)
    clock_id = resp["test_clock"]["test_clock_id"]
    print(f"  Created test clock {clock_id} at {start}")
    return clock_id


def create_sandbox_item(client: plaid_api.PlaidApi, test_clock_id: str) -> tuple[str, str]:
    """
    Create a sandbox item attached to the test clock.
    Returns (public_token, access_token).
    """
    options = SandboxPublicTokenCreateRequestOptions(
        test_clock_id=test_clock_id,
    )
    req = SandboxPublicTokenCreateRequest(
        institution_id="ins_109508",  # 'First Platypus Bank' — sandbox test bank
        initial_products=[Products("transactions")],
        country_codes=[CountryCode("GB")],
        options=options,
    )
    resp = client.sandbox_public_token_create(req)
    public_token = resp["public_token"]
    print(f"  Got public token: {public_token[:20]}…")

    exchange_req = ItemPublicTokenExchangeRequest(public_token=public_token)
    exchange_resp = client.item_public_token_exchange(exchange_req)
    access_token = exchange_resp["access_token"]
    item_id = exchange_resp["item_id"]
    print(f"  Exchanged → item_id: {item_id}")
    print(f"  Access token: {access_token[:20]}…")
    return public_token, access_token


def advance_clock_through_two_years(client: plaid_api.PlaidApi, test_clock_id: str, start: date, end: date):
    """
    Advance the test clock in monthly increments from start→end.
    Each advance triggers Plaid to generate transactions for that period.
    """
    import datetime

    current = start
    step_months = 1

    while current < end:
        # Advance by one month
        month = current.month + step_months
        year = current.year + (month - 1) // 12
        month = ((month - 1) % 12) + 1
        next_date = date(year, month, min(current.day, 28))

        if next_date > end:
            next_date = end

        target_dt = datetime.datetime(next_date.year, next_date.month, next_date.day, 23, 59, 59)
        req = SandboxTestClockAdvanceRequest(
            test_clock_id=test_clock_id,
            new_virtual_time=target_dt,
        )
        client.sandbox_test_clock_advance(req)
        print(f"  Advanced clock → {next_date}")

        # Give Plaid a moment to process
        time.sleep(1)
        current = next_date


def fetch_transactions(client: plaid_api.PlaidApi, access_token: str, start: date, end: date) -> list[dict]:
    """Pull all transactions for the item."""
    options = TransactionsGetRequestOptions(count=500, offset=0)
    req = TransactionsGetRequest(
        access_token=access_token,
        start_date=start,
        end_date=end,
        options=options,
    )
    resp = client.transactions_get(req)
    total = resp["total_transactions"]
    transactions = list(resp["transactions"])
    print(f"  Fetched {len(transactions)} / {total} transactions")

    # Paginate if needed
    while len(transactions) < total:
        options = TransactionsGetRequestOptions(count=500, offset=len(transactions))
        req = TransactionsGetRequest(
            access_token=access_token,
            start_date=start,
            end_date=end,
            options=options,
        )
        resp = client.transactions_get(req)
        transactions.extend(resp["transactions"])
        print(f"  Fetched {len(transactions)} / {total} transactions")

    return [t.to_dict() for t in transactions]


def main():
    print("Plaid Sandbox — 2-year test clock item")
    print("=" * 45)

    client = build_client()

    start = date(2024, 4, 30)
    end = date(2026, 4, 30)

    print("\n1. Creating test clock…")
    clock_id = create_test_clock(client, start)

    print("\n2. Creating sandbox item…")
    _, access_token = create_sandbox_item(client, clock_id)

    print("\n3. Advancing clock through 2 years (this takes ~2 min)…")
    advance_clock_through_two_years(client, clock_id, start, end)

    print("\n4. Fetching generated transactions…")
    txns = fetch_transactions(client, access_token, start, end)
    print(f"\n✓ Done. {len(txns)} transactions generated by Plaid.")
    print(f"  Access token (save this): {access_token}")
    print(
        "\nNote: Plaid generates its own transaction data — merchant names and"
        "\namounts will be Plaid's generic test data, not the coffee shop data."
        "\nFor specific coffee shop transactions, use mock_plaid_client.py instead."
    )


if __name__ == "__main__":
    main()
