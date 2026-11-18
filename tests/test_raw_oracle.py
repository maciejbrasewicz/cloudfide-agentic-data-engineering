"""Independent stdlib oracle: calculate totals straight from original CSV rows.

This independently checks arithmetic, not the validity of business assumptions.
No imports of production parsing, cleaning, or virtual-column functions.
"""
import csv
from collections import defaultdict
from decimal import Decimal

from pipeline import ROOT


def test_raw_csv_oracle_matches_committed_region_totals():
    with (ROOT / "sales.csv").open(newline="", encoding="utf-8") as stream:
        raw = list(csv.DictReader(stream))
    transactions = [line for line in raw if line["Order ID"].startswith("SO-")]

    # Independently validate the export's control row before any deduplication.
    control = next(line for line in raw if line["Order ID"] == "TOTAL")
    original_quantity = sum(int(line["Quantity "].replace(" ", "")) for line in transactions)
    original_discount = sum(
        (Decimal(line["Discount"].strip() or "0.00") for line in transactions),
        Decimal("0.00"),
    )
    assert original_quantity == int(control["Quantity "])
    assert original_discount == Decimal(control["Discount"])

    unique = []
    seen = set()
    for line in transactions:
        source_key = tuple(line.items())
        if source_key not in seen:
            unique.append(line)
            seen.add(source_key)
    assert len(unique) == 1500

    prices = defaultdict(set)
    for line in unique:
        value = line["Unit Price"].strip()
        if value:
            prices[line["Product"].strip()].add(Decimal(value.replace(",", ".")))

    totals = defaultdict(lambda: Decimal("0.00"))
    for line in unique:
        product = line["Product"].strip()
        price = line["Unit Price"].strip()
        if price:
            unit_price = Decimal(price.replace(",", "."))
        else:
            assert len(prices[product]) == 1
            unit_price = next(iter(prices[product]))
        quantity = int(line["Quantity "].replace(" ", ""))
        discount = Decimal(line["Discount"].strip() or "0.00")
        totals[line["Region"].strip().title()] += quantity * unit_price - discount

    with (ROOT / "revenue_by_region.csv").open(newline="", encoding="utf-8") as stream:
        committed = {line["region"]: Decimal(line["revenue"]) for line in csv.DictReader(stream)}

    assert dict(totals) == committed
    assert sum(totals.values()) == Decimal("2570247.03")
