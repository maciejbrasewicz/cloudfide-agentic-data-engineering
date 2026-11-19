"""Clean the sales export and produce exact regional revenue totals."""

from __future__ import annotations

import argparse
import re
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Iterable

import pandas as pd

from solution import add_virtual_column


SOURCE_COLUMNS = {
    "Order ID": "order_id",
    "Region": "region",
    "Product": "product",
    "Quantity ": "quantity",
    "Unit Price": "unit_price",
    "Discount": "discount",
    "Order Date": "order_date",
}
EXPECTED_REGIONS = {"Central", "East", "North", "South", "West"}
_INTEGER = re.compile(r"^[+-]?\d+$")
_DECIMAL = re.compile(r"^[+-]?(?:\d+(?:\.\d*)?|\.\d+)$")


class DataQualityError(ValueError):
    """Raised when a source control fails or a repair is ambiguous."""


def _decimal(value: object, *, blank_zero: bool = False) -> Decimal:
    text = str(value).strip()
    if not text:
        if blank_zero:
            return Decimal("0")
        raise DataQualityError("unexpected blank numeric value")
    if "," in text and "." in text:
        raise DataQualityError(f"ambiguous decimal value: {text!r}")
    normalized = text.replace(",", ".")
    if not _DECIMAL.fullmatch(normalized):
        raise DataQualityError(f"invalid decimal value: {text!r}")
    try:
        return Decimal(normalized)
    except InvalidOperation as exc:
        raise DataQualityError(f"invalid decimal value: {text!r}") from exc


def _quantity(value: object) -> Decimal:
    text = str(value).strip().replace(" ", "")
    if not _INTEGER.fullmatch(text):
        raise DataQualityError(f"invalid integral quantity: {value!r}")
    return Decimal(text)


def _sum(values: Iterable[Decimal]) -> Decimal:
    return sum(values, Decimal("0"))


def load_and_clean_sales(path: str | Path) -> pd.DataFrame:
    """Read, reconcile, repair, and calculate the transaction population."""
    raw = pd.read_csv(path, dtype=str, keep_default_na=False)
    if list(raw.columns) != list(SOURCE_COLUMNS):
        raise DataQualityError("unexpected source columns")

    order_ids = raw["Order ID"].str.strip()
    transaction_mask = order_ids.str.fullmatch(r"SO-\d+")
    total_mask = order_ids.eq("TOTAL")
    repeated_header_mask = order_ids.eq("Order ID")
    if int(total_mask.sum()) != 1:
        raise DataQualityError("source must contain exactly one TOTAL control row")
    if (~(transaction_mask | total_mask | repeated_header_mask)).any():
        raise DataQualityError("unrecognized non-transaction source row")

    # Reconcile the untouched transaction population, including exact
    # duplicates, before excluding metadata or deduplicating anything.
    raw_transactions = raw.loc[transaction_mask].copy()
    raw_quantity = _sum(_quantity(v) for v in raw_transactions["Quantity "])
    raw_discount = _sum(
        _decimal(v, blank_zero=True) for v in raw_transactions["Discount"]
    )
    control = raw.loc[total_mask].iloc[0]
    if raw_quantity != _quantity(control["Quantity "]):
        raise DataQualityError("raw quantity does not reconcile to TOTAL")
    if raw_discount != _decimal(control["Discount"]):
        raise DataQualityError("raw discount does not reconcile to TOTAL")

    cleaned = (
        raw_transactions.drop_duplicates(keep="first")
        .rename(columns=SOURCE_COLUMNS)
        .reset_index(drop=True)
    )

    for field in ("order_id", "product", "order_date"):
        cleaned[field] = cleaned[field].str.strip()
        if cleaned[field].eq("").any():
            raise DataQualityError(f"blank {field}")
    dates = pd.to_datetime(
        cleaned["order_date"], format="%Y-%m-%d", errors="coerce"
    )
    if dates.isna().any():
        raise DataQualityError("invalid order_date")

    cleaned["region"] = cleaned["region"].str.strip().str.title()
    if set(cleaned["region"]) != EXPECTED_REGIONS:
        raise DataQualityError("regions do not match the expected five-region set")
    cleaned["quantity"] = cleaned["quantity"].map(_quantity)
    cleaned["discount"] = cleaned["discount"].map(
        lambda value: _decimal(value, blank_zero=True)
    )

    price_text = cleaned["unit_price"].str.strip()
    has_price = price_text.ne("")
    parsed_prices = cleaned.loc[has_price, "unit_price"].map(_decimal)
    for index, price in parsed_prices.items():
        cleaned.at[index, "unit_price"] = price

    prices_by_product: dict[str, set[Decimal]] = {}
    for index in cleaned.index[has_price]:
        product = cleaned.at[index, "product"]
        price = cleaned.at[index, "unit_price"]
        prices_by_product.setdefault(product, set()).add(price)
    for index in cleaned.index[~has_price]:
        product = cleaned.at[index, "product"]
        candidates = prices_by_product.get(product, set())
        if len(candidates) != 1:
            raise DataQualityError(
                f"missing unit price is ambiguous for {product!r}"
            )
        cleaned.at[index, "unit_price"] = next(iter(candidates))

    result = add_virtual_column(
        cleaned, "quantity * unit_price - discount", "revenue"
    )
    if result.empty and not cleaned.empty:
        raise DataQualityError("revenue expression could not be calculated")
    return result


def revenue_by_region(cleaned: pd.DataFrame) -> pd.DataFrame:
    """Return exact regional totals with schema ``region,revenue``."""
    if not {"region", "revenue"}.issubset(cleaned.columns):
        raise DataQualityError("cleaned data lacks region or revenue")
    rows = [
        {"region": region, "revenue": _sum(group["revenue"])}
        for region, group in cleaned.groupby("region", sort=True)
    ]
    result = pd.DataFrame(rows, columns=["region", "revenue"])
    if set(result["region"]) != EXPECTED_REGIONS:
        raise DataQualityError("aggregation did not produce all five regions")
    return result


def run_pipeline(
    input_path: str | Path = "sales.csv",
    output_path: str | Path = "revenue_by_region.csv",
) -> pd.DataFrame:
    """Run the ETL, write the regional CSV, and return its DataFrame."""
    totals = revenue_by_region(load_and_clean_sales(input_path))
    totals.to_csv(output_path, index=False)
    return totals


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", default="sales.csv")
    parser.add_argument("--output", default="revenue_by_region.csv")
    args = parser.parse_args()
    run_pipeline(args.input, args.output)


if __name__ == "__main__":
    main()
