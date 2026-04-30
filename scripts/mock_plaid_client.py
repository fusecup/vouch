"""Compatibility wrapper for the canonical app Plaid service."""

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = ROOT / "src" / "vouch" / "apps"
if str(SRC_PATH) not in sys.path:
    sys.path.append(str(SRC_PATH))

from activity.services.plaid import MockPlaidClient, get_plaid_client  # noqa: E402,F401


if __name__ == "__main__":
    os.environ.setdefault("PLAID_USE_MOCK", "true")
    client = get_plaid_client()
    response = client.transactions_get(
        {"start_date": "2024-04-30", "end_date": "2026-04-30", "options": {"count": 3, "offset": 0}}
    )
    print(f"Loaded {response.total_transactions} transactions; preview {len(response.transactions)} rows.")
