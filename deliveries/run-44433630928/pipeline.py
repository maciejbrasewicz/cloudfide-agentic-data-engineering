"""Deterministic cleaning and regional aggregation for the sales export."""

from __future__ import annotations

import argparse
import re
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Final, Sequence

import pandas as pd

from solution import add_virtual_column


EXPECTED_COLUMNS: Final = (
    "order_id",
    "region",
    "product",
    "quantity",
    "unit_price",
    "discount",
    "order_date",
)
REGIONS: Final = ("Central", "East", "North", "South", "West")
_INTEGER: Final = re.compile(r"^[+-]?\d+$")
_DECIMAL: Final = re.compile(r"^[+-]?\d+(?:[.,]\d+)?$")
_ORDER_ID: Final = re.compile(r"^SO-\d+$")
_CENT: Final = Decimal("0.01")


class DataQualityError(ValueError):
    """Raised when source data cannot be repaired unambiguously."""


def _to_decimal(value: object, *, integer: bool = False) -> Decimal:
    text = str(value).strip()
    if integer:
        text = text.replace(" ", "")
        pattern = _INTEGER
    else:
        pattern = _DECIMAL
    if not text or not pattern.fullmatch(text):
        raise DataQualityError(f"invalid numeric value: {value!r}")
    try:
        number = Decimal(text.replace(",", "."))
    except InvalidOperation as exc:
        raise DataQualityError(f"invalid numeric value: {value!r}") from exc
    if not number.is_finite():
        raise DataQualityError(f"non-finite numeric value: {value!r}")
    return number


def _normalise_headers(raw: pd.DataFrame) -> pd.DataFrame:
    labels = tuple(
        re.sub(r"\s+", "_", str(label).strip().lower())
        for label in raw.columns
    )
    if labels != EXPECTED_COLUMNS:
        raise DataQualityError(f"unexpected CSV columns: {tuple(raw.columns)!r}")
    result = raw.copy()
    result.columns = list(EXPECTED_COLUMNS)
    return result


def _reconcile_raw_controls(raw: pd.DataFrame) -> pd.DataFrame:
    """Verify controls against untouched transactions before deduplication."""
    ids = raw["order_id"].str.strip()
    repeated_header = ids.str.lower().eq("order id")
    total_row = ids.str.upper().eq("TOTAL")
    if int(repeated_header.sum()) != 1:
        raise DataQualityError("exactly one repeated header row is required")
    if int(total_row.sum()) != 1:
        raise DataQualityError("exactly one TOTAL control row is required")

    transactions = raw.loc[~repeated_header & ~total_row].copy()
    if transactions.empty:
        raise DataQualityError("source contains no transactions")

    raw_quantity = sum(
        (_to_decimal(value, integer=True) for value in transactions["quantity"]),
        Decimal(0),
    )
    raw_discount = sum(
        (
            Decimal(0) if not str(value).strip() else _to_decimal(value)
            for value in transactions["discount"]
        ),
        Decimal(0),
    )
    control = raw.loc[total_row].iloc[0]
    control_quantity = _to_decimal(control["quantity"], integer=True)
    control_discount = _to_decimal(control["discount"])
    if raw_quantity != control_quantity or raw_discount != control_discount:
        raise DataQualityError(
            "raw controls do not reconcile: "
            f"quantity {raw_quantity}/{control_quantity}, "
            f"discount {raw_discount}/{control_discount}"
        )
    return transactions


def clean_sales(source: str | Path) -> pd.DataFrame:
    """Read, reconcile, deduplicate, repair, and calculate transaction rows."""
    raw = pd.read_csv(source, dtype=str, keep_default_na=False, na_filter=False)
    raw = _normalise_headers(raw)
    transactions = _reconcile_raw_controls(raw)

    # The supplied controls describe the raw export, including duplicate rows.
    transactions = transactions.drop_duplicates(keep="first").reset_index(drop=True)

    text_columns = ("order_id", "region", "product", "order_date")
    for column in text_columns:
        transactions[column] = transactions[column].str.strip()
    if transactions[list(text_columns)].eq("").any().any():
        raise DataQualityError("blank required text field")
    if not transactions["order_id"].map(
        lambda value: bool(_ORDER_ID.fullmatch(value))
    ).all():
        raise DataQualityError("invalid order ID")
    if transactions["order_id"].duplicated().any():
        raise DataQualityError("non-identical rows share an order ID")

    transactions["region"] = transactions["region"].str.title()
    unknown_regions = sorted(set(transactions["region"]) - set(REGIONS))
    if unknown_regions:
        raise DataQualityError(f"unknown regions: {unknown_regions!r}")

    transactions["quantity"] = transactions["quantity"].map(
        lambda value: _to_decimal(value, integer=True)
    )
    transactions["discount"] = transactions["discount"].map(
        lambda value: Decimal(0) if not str(value).strip() else _to_decimal(value)
    )
    if (transactions["discount"] < Decimal(0)).any():
        raise DataQualityError("discount cannot be negative")

    parsed_prices: list[Decimal | None] = [
        None if not str(value).strip() else _to_decimal(value)
        for value in transactions["unit_price"]
    ]
    transactions["unit_price"] = parsed_prices
    prices_by_product: dict[str, set[Decimal]] = {}
    for product, price in zip(transactions["product"], parsed_prices):
        if price is not None:
            prices_by_product.setdefault(product, set()).add(price)

    for index, row in transactions.loc[transactions["unit_price"].isna()].iterrows():
        candidates = prices_by_product.get(row["product"], set())
        if len(candidates) != 1:
            raise DataQualityError(
                f"unit price for product {row['product']!r} is not uniquely recoverable"
            )
        transactions.at[index, "unit_price"] = next(iter(candidates))
    if any(
        price is None or price <= Decimal(0)
        for price in transactions["unit_price"]
    ):
        raise DataQualityError("unit prices must be positive")

    dates = pd.to_datetime(
        transactions["order_date"], format="%Y-%m-%d", errors="coerce"
    )
    if dates.isna().any():
        raise DataQualityError("invalid order date")
    transactions["order_date"] = dates.dt.strftime("%Y-%m-%d")

    result = add_virtual_column(
        transactions, "quantity * unit_price - discount", "revenue"
    )
    if "revenue" not in result.columns:
        raise DataQualityError("revenue expression could not be calculated")
    return result


def revenue_by_region(cleaned: pd.DataFrame) -> pd.DataFrame:
    """Return Decimal totals in stable five-region order."""
    if not {"region", "revenue"}.issubset(cleaned.columns):
        raise DataQualityError("cleaned data lacks region or revenue")
    totals = {region: Decimal(0) for region in REGIONS}
    for region, revenue in zip(cleaned["region"], cleaned["revenue"]):
        if region not in totals or not isinstance(revenue, Decimal):
            raise DataQualityError("invalid cleaned regional revenue")
        totals[region] += revenue
    return pd.DataFrame(
        {
            "region": list(REGIONS),
            "revenue": [totals[region].quantize(_CENT) for region in REGIONS],
        }
    )


def run_pipeline(
    source: str | Path = "sales.csv",
    destination: str | Path = "revenue_by_region.csv",
) -> pd.DataFrame:
    """Run the ETL, write the aggregate CSV, and return the Decimal totals."""
    aggregate = revenue_by_region(clean_sales(source))
    serialised = aggregate.copy()
    serialised["revenue"] = serialised["revenue"].map(
        lambda amount: f"{amount:.2f}"
    )
    output_path = Path(destination)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    serialised.to_csv(output_path, index=False, lineterminator="\n")
    return aggregate


def main(argv: Sequence[str] | None = None) -> int:
    """CLI supporting defaults, positional paths, and --input/--output paths."""
    parser = argparse.ArgumentParser(description="Clean and aggregate sales CSV data")
    parser.add_argument("source", nargs="?", help="input CSV (default: sales.csv)")
    parser.add_argument("destination", nargs="?", help="output aggregate CSV")
    parser.add_argument("--input", dest="input_path", help="input sales CSV")
    parser.add_argument("--output", dest="output_path", help="output aggregate CSV")
    args = parser.parse_args(argv)

    source = args.input_path or args.source or "sales.csv"
    destination = args.output_path or args.destination or "revenue_by_region.csv"
    run_pipeline(source, destination)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
