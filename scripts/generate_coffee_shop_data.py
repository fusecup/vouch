"""
Generate 2 years of realistic coffee shop bank transaction data.

Outputs transactions in Plaid's transaction format (GBP).

Business profile:
  Morning Grounds Coffee — a small UK coffee shop with 5 employees,
  two coffee bean suppliers, a dairy supplier, a pastry supplier, and
  fixed monthly expenses (rent, utilities, insurance, payroll).

Usage:
  python scripts/generate_coffee_shop_data.py
  python scripts/generate_coffee_shop_data.py --format csv --output transactions.csv
  python scripts/generate_coffee_shop_data.py --format json --output transactions.json
"""

import argparse
import csv
import json
import random
import sys
import uuid
from datetime import date, timedelta


# ── Seed for reproducibility ──────────────────────────────────────────────────
SEED = 42
random.seed(SEED)

CHECKING_ACCOUNT_ID = "acc_checking_morning_grounds"
SAVINGS_ACCOUNT_ID = "acc_savings_morning_grounds"

START_DATE = date(2024, 4, 30)
END_DATE = date(2026, 4, 30)


# ── Helpers ───────────────────────────────────────────────────────────────────

def date_range(start: date, end: date):
    d = start
    while d <= end:
        yield d
        d += timedelta(days=1)


def jitter(base: float, pct: float = 0.12) -> float:
    """Return base ± pct%, rounded to 2dp."""
    delta = base * pct * (random.random() * 2 - 1)
    return round(base + delta, 2)


def make_txn(
    txn_date: date,
    amount: float,
    name: str,
    merchant_name: str | None,
    category: list[str],
    account_id: str = CHECKING_ACCOUNT_ID,
    payment_channel: str = "other",
    pending: bool = False,
) -> dict:
    """
    Plaid transaction format.
    Positive amount = money OUT of account (debit/expense).
    Negative amount = money IN (credit/income).
    """
    return {
        "transaction_id": str(uuid.uuid4()),
        "account_id": account_id,
        "amount": amount,
        "iso_currency_code": "GBP",
        "date": txn_date.isoformat(),
        "name": name,
        "merchant_name": merchant_name,
        "category": category,
        "payment_channel": payment_channel,
        "pending": pending,
        "transaction_type": "place" if payment_channel == "in store" else "digital",
    }


# ── Transaction generators ────────────────────────────────────────────────────

def daily_sales(d: date) -> list[dict]:
    """Card machine settlement — one batched deposit per trading day."""
    if d.weekday() == 6:  # closed Sundays
        return []

    if d.weekday() == 5:  # lighter on Saturdays
        base = random.uniform(420, 780)
    else:
        base = random.uniform(680, 1_400)

    # seasonal lift: Dec/Jan/Feb mornings are busier for hot drinks
    if d.month in (12, 1, 2):
        base *= 1.15
    elif d.month in (7, 8):
        base *= 0.90

    amount = round(base, 2)
    return [
        make_txn(
            d,
            -amount,  # credit — money coming in
            "SQUARE PAYMENTS CARD SETTLEMENT",
            "Square",
            ["Transfer", "Credit"],
            payment_channel="in store",
        )
    ]


def rent(d: date) -> list[dict]:
    """£3,800/month on the 1st."""
    if d.day != 1:
        return []
    return [
        make_txn(
            d, 3_800.00,
            "LANDLORD BUILDING RENT",
            None,
            ["Payment", "Rent"],
            payment_channel="other",
        )
    ]


def payroll(d: date) -> list[dict]:
    """
    5 employees paid on the 15th and last day of each month.
    - 3 baristas: £1,050–£1,150 per pay period
    - 1 manager:  £1,600 per pay period
    - 1 part-timer: £480 per pay period
    """
    if d.day not in (15, 28):
        return []

    employees = [
        ("Alex Turner", jitter(1_100)),
        ("Sam Patel", jitter(1_075)),
        ("Chloe Davies", jitter(1_050)),
        ("Jordan Kim", 1_600.00),   # manager — fixed
        ("Lily Booth", jitter(480)),
    ]
    txns = []
    for name, gross in employees:
        txns.append(
            make_txn(
                d,
                round(gross, 2),
                f"PAYROLL {name.upper()}",
                "Payroll",
                ["Payment", "Payroll"],
                payment_channel="other",
            )
        )
    return txns


def coffee_supplier_1(d: date) -> list[dict]:
    """Highland Roasters — bi-weekly on Mondays."""
    if d.weekday() != 0:
        return []
    week_number = (d - START_DATE).days // 7
    if week_number % 2 != 0:
        return []
    return [
        make_txn(
            d, jitter(1_380),
            "HIGHLAND ROASTERS LTD",
            "Highland Roasters",
            ["Food and Drink", "Coffee Shop"],
            payment_channel="online",
        )
    ]


def coffee_supplier_2(d: date) -> list[dict]:
    """Pacific Beans Co — monthly on the 10th."""
    if d.day != 10:
        return []
    return [
        make_txn(
            d, jitter(720),
            "PACIFIC BEANS CO",
            "Pacific Beans Co",
            ["Food and Drink", "Coffee Shop"],
            payment_channel="online",
        )
    ]


def dairy_supplier(d: date) -> list[dict]:
    """Valley Dairy — bi-weekly on Wednesdays."""
    if d.weekday() != 2:
        return []
    week_number = (d - START_DATE).days // 7
    if week_number % 2 != 0:
        return []
    return [
        make_txn(
            d, jitter(490),
            "VALLEY DAIRY SUPPLIES",
            "Valley Dairy",
            ["Food and Drink", "Dairy"],
            payment_channel="online",
        )
    ]


def pastry_supplier(d: date) -> list[dict]:
    """Golden Bakery — every Friday."""
    if d.weekday() != 4:
        return []
    return [
        make_txn(
            d, jitter(410),
            "GOLDEN BAKERY WHOLESALE",
            "Golden Bakery",
            ["Food and Drink", "Bakeries"],
            payment_channel="online",
        )
    ]


def utilities(d: date) -> list[dict]:
    """Electric, water, broadband — all on the 5th."""
    if d.day != 5:
        return []
    txns = [
        make_txn(d, jitter(370), "BRITISH GAS BUSINESS", "British Gas", ["Service", "Utilities"], payment_channel="online"),
        make_txn(d, jitter(115), "THAMES WATER", "Thames Water", ["Service", "Utilities"], payment_channel="online"),
        make_txn(d, 89.99, "BT BUSINESS BROADBAND", "BT", ["Service", "Telecommunications"], payment_channel="online"),
    ]
    return txns


def insurance(d: date) -> list[dict]:
    """Monthly on the 3rd."""
    if d.day != 3:
        return []
    return [
        make_txn(
            d, 340.00,
            "SIMPLY BUSINESS INSURANCE",
            "Simply Business",
            ["Payment", "Insurance"],
            payment_channel="online",
        )
    ]


def pos_fees(d: date) -> list[dict]:
    """Square monthly subscription on the 20th."""
    if d.day != 20:
        return []
    return [
        make_txn(
            d, 49.00,
            "SQUARE INC MONTHLY",
            "Square",
            ["Service", "Financial"],
            payment_channel="online",
        )
    ]


def marketing(d: date) -> list[dict]:
    """Meta/Google ads on the 22nd."""
    if d.day != 22:
        return []
    txns = []
    if random.random() > 0.3:
        txns.append(make_txn(d, jitter(180), "META ADS BILLING", "Meta", ["Service", "Advertising"], payment_channel="online"))
    if random.random() > 0.5:
        txns.append(make_txn(d, jitter(120), "GOOGLE ADS", "Google", ["Service", "Advertising"], payment_channel="online"))
    return txns


def cleaning_supplies(d: date) -> list[dict]:
    """Amazon/B&Q monthly, around the 12th."""
    if d.day != 12:
        return []
    return [
        make_txn(
            d, jitter(140),
            "AMAZON BUSINESS",
            "Amazon",
            ["Shops", "Supermarkets"],
            payment_channel="online",
        )
    ]


def equipment_maintenance(d: date) -> list[dict]:
    """Occasional — ~1.5x per month, random day."""
    # Roughly every 20 days on average
    if random.random() > (1 / 20):
        return []
    vendors = [
        ("ESPRESSO TECH SERVICES", "Espresso Tech"),
        ("COMMERCIAL KITCHEN REPAIRS", None),
        ("FILTERTECH LTD", "Filtertech"),
    ]
    name, merchant = random.choice(vendors)
    amount = round(random.uniform(180, 620), 2)
    return [
        make_txn(d, amount, name, merchant, ["Service", "Equipment Maintenance"], payment_channel="online")
    ]


def bank_charges(d: date) -> list[dict]:
    """Monthly bank fee on the 28th."""
    if d.day != 28:
        return []
    return [
        make_txn(d, 12.50, "BARCLAYS BUSINESS BANKING FEE", "Barclays", ["Payment", "Bank Fee"], payment_channel="other")
    ]


def savings_transfer(d: date) -> list[dict]:
    """Transfer £500 to savings on the 25th when it's a good month."""
    if d.day != 25 or random.random() > 0.65:
        return []
    return [
        make_txn(d, 500.00, "TRANSFER TO SAVINGS", None, ["Transfer", "Internal Account Transfer"],
                 account_id=CHECKING_ACCOUNT_ID, payment_channel="other"),
        make_txn(d, -500.00, "TRANSFER FROM CURRENT", None, ["Transfer", "Internal Account Transfer"],
                 account_id=SAVINGS_ACCOUNT_ID, payment_channel="other"),
    ]


# ── Main generator ────────────────────────────────────────────────────────────

GENERATORS = [
    daily_sales,
    rent,
    payroll,
    coffee_supplier_1,
    coffee_supplier_2,
    dairy_supplier,
    pastry_supplier,
    utilities,
    insurance,
    pos_fees,
    marketing,
    cleaning_supplies,
    equipment_maintenance,
    bank_charges,
    savings_transfer,
]


def generate() -> list[dict]:
    transactions: list[dict] = []
    for d in date_range(START_DATE, END_DATE):
        for gen in GENERATORS:
            transactions.extend(gen(d))
    # Chronological, newest first (Plaid default)
    transactions.sort(key=lambda t: t["date"], reverse=True)
    return transactions


# ── Output formats ────────────────────────────────────────────────────────────

def to_csv(transactions: list[dict], out) -> None:
    if not transactions:
        return
    writer = csv.DictWriter(out, fieldnames=list(transactions[0].keys()))
    writer.writeheader()
    for t in transactions:
        row = dict(t)
        row["category"] = " > ".join(t["category"])
        writer.writerow(row)


def to_json(transactions: list[dict], out) -> None:
    json.dump(transactions, out, indent=2)


# ── CLI ───────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Generate coffee shop demo transactions")
    parser.add_argument("--format", choices=["json", "csv"], default="json")
    parser.add_argument("--output", default="-", help="Output file path (default: stdout)")
    args = parser.parse_args()

    transactions = generate()

    if args.output == "-":
        out = sys.stdout
        if args.format == "json":
            to_json(transactions, out)
        else:
            to_csv(transactions, out)
    else:
        mode = "w"
        with open(args.output, mode, newline="" if args.format == "csv" else "\n") as f:
            if args.format == "json":
                to_json(transactions, f)
            else:
                to_csv(transactions, f)

    print(f"\n✓ Generated {len(transactions)} transactions "
          f"({START_DATE} → {END_DATE})", file=sys.stderr)


if __name__ == "__main__":
    main()
