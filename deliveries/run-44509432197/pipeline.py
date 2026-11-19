"""Clean the sales export and aggregate exact revenue by region."""

from __future__ import annotations

import argparse
from decimal import Decimal, InvalidOperation
from pathlib import Path
import re
from typing import Any, Sequence

import pandas as pd

from solution import add_virtual_column

SOURCE_COLUMNS = [
    "Order ID",
    "Region",
    "Product",
    "Quantity ",
    "Unit Price",
    "Discount",
    "Order Date",
]
REGIONS = ("Central", "East", "North", "South", "West")
_INTEGER = re.compile(r"^-?\d+$")
_DECIMAL = re.compile(r"^-?\d+(?:\.\d+)?$")


class DataQualityError(ValueError):
    """Raised when input violates the approved fail-closed data policy."""


def _decimal(value: object, *, blank_zero: bool = False) -> Decimal:
    text = "" if value is None else str(value).strip()
    if not text:
        if blank_zero:
            return Decimal("0")
        raise DataQualityError("required numeric value is blank")
    text = text.replace(" ", "")
    if "," in text and "." in text:
        raise DataQualityError(f"ambiguous numeric separators: {value!r}")
    text = text.replace(",", ".")
    if _DECIMAL.fullmatch(text) is None:
        raise DataQualityError(f"malformed numeric value: {value!r}")
    try:
        return Decimal(text)
    except InvalidOperation as exc:
        raise DataQualityError(f"malformed numeric value: {value!r}") from exc


def _quantity(value: object) -> Decimal:
    text = "" if value is None else str(value).strip().replace(" ", "")
    if _INTEGER.fullmatch(text) is None:
        raise DataQualityError(f"quantity is not an integer: {value!r}")
    return Decimal(text)


def _header_mask(raw: pd.DataFrame) -> pd.Series:
    return raw.apply(
        lambda row: all(str(row[column]) == column for column in SOURCE_COLUMNS), axis=1
    )


def _profile(transactions: pd.DataFrame) -> dict[str, int]:
    original_regions = transactions["Region"].astype(str)
    normalized_regions = original_regions.str.strip().str.title()
    return {
        "missing_unit_price_rows": int(
            transactions["Unit Price"].astype(str).str.strip().eq("").sum()
        ),
        "blank_discount_rows": int(
            transactions["Discount"].astype(str).str.strip().eq("").sum()
        ),
        "negative_quantity_rows": sum(
            _quantity(value) < 0 for value in transactions["Quantity "]
        ),
        "noncanonical_region_rows": int((original_regions != normalized_regions).sum()),
        "comma_price_rows": int(
            transactions["Unit Price"].astype(str).str.contains(",", regex=False).sum()
        ),
        "spaced_quantity_rows": int(
            transactions["Quantity "].astype(str).str.contains(r"\s", regex=True).sum()
        ),
    }


def clean_sales(raw: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Reconcile raw controls, then clean transaction rows under policy v1."""
    if list(raw.columns) != SOURCE_COLUMNS:
        raise DataQualityError(f"unexpected source schema: {list(raw.columns)!r}")
    if raw.isna().any(axis=None):
        raise DataQualityError("source must preserve empty fields as strings")

    header_mask = _header_mask(raw)
    total_mask = raw["Order ID"].astype(str).str.strip().eq("TOTAL")
    if int(header_mask.sum()) != 1 or int(total_mask.sum()) != 1:
        raise DataQualityError("expected one repeated header and one TOTAL control")
    if bool((header_mask & total_mask).any()):
        raise DataQualityError("control row classifications overlap")

    transactions_raw = raw.loc[~header_mask & ~total_mask].copy()
    control = raw.loc[total_mask].iloc[0]

    # The control describes the raw export. Reconcile it before deduplication.
    raw_quantity_total = sum(
        (_quantity(value) for value in transactions_raw["Quantity "]), Decimal("0")
    )
    raw_discount_total = sum(
        (
            _decimal(value, blank_zero=True)
            for value in transactions_raw["Discount"]
        ),
        Decimal("0"),
    )
    if raw_quantity_total != _quantity(control["Quantity "]):
        raise DataQualityError("raw quantity does not reconcile to TOTAL")
    if raw_discount_total != _decimal(control["Discount"]):
        raise DataQualityError("raw discount does not reconcile to TOTAL")

    issue_counts = _profile(transactions_raw)
    duplicate_count = int(transactions_raw.duplicated(keep="first").sum())
    transactions = transactions_raw.drop_duplicates(keep="first").copy()

    original_regions = transactions["Region"].astype(str)
    regions = original_regions.str.strip().str.title()
    unexpected_regions = set(regions) - set(REGIONS)
    if regions.eq("").any() or unexpected_regions:
        raise DataQualityError(
            f"unexpected normalized regions: {sorted(unexpected_regions)!r}"
        )

    products = transactions["Product"].astype(str).str.strip()
    order_ids = transactions["Order ID"].astype(str).str.strip()
    if products.eq("").any() or order_ids.eq("").any() or order_ids.duplicated().any():
        raise DataQualityError("blank product/order ID or duplicate order ID after dedup")

    quantities = [_quantity(value) for value in transactions["Quantity "]]
    discounts = [
        _decimal(value, blank_zero=True) for value in transactions["Discount"]
    ]
    prices: list[Decimal | None] = [
        None if str(value).strip() == "" else _decimal(value)
        for value in transactions["Unit Price"]
    ]

    observed_prices: dict[str, set[Decimal]] = {}
    for product, price in zip(products, prices):
        if price is not None:
            observed_prices.setdefault(product, set()).add(price)
    for index, (product, price) in enumerate(zip(products, prices)):
        if price is None:
            candidates = observed_prices.get(product, set())
            if len(candidates) != 1:
                raise DataQualityError(
                    f"missing price for {product!r} has {len(candidates)} candidates"
                )
            prices[index] = next(iter(candidates))

    dates = pd.to_datetime(
        transactions["Order Date"], format="%Y-%m-%d", errors="coerce"
    )
    if dates.isna().any():
        raise DataQualityError("invalid order date")

    cleaned = pd.DataFrame(
        {
            "order_id": order_ids.to_list(),
            "region": regions.to_list(),
            "product": products.to_list(),
            "quantity": quantities,
            "unit_price": prices,
            "discount": discounts,
            "order_date": dates.dt.strftime("%Y-%m-%d").to_list(),
        }
    )
    result = add_virtual_column(
        cleaned, "quantity * unit_price - discount", "revenue"
    )
    if not cleaned.empty and (result.empty or "revenue" not in result):
        raise DataQualityError("revenue expression could not be evaluated")

    stats: dict[str, Any] = {
        "source_rows": len(raw),
        "transaction_rows": len(transactions_raw),
        "repeated_header_rows": int(header_mask.sum()),
        "total_control_rows": int(total_mask.sum()),
        "exact_duplicate_extra_rows": duplicate_count,
        **issue_counts,
        "raw_quantity_total": raw_quantity_total,
        "raw_discount_total": raw_discount_total,
    }
    return result, stats


def aggregate_regions(cleaned: pd.DataFrame) -> pd.DataFrame:
    """Produce deterministic Decimal totals for exactly the five regions."""
    if cleaned.empty or "region" not in cleaned or "revenue" not in cleaned:
        raise DataQualityError("no cleaned revenue rows to aggregate")
    present = set(cleaned["region"])
    if present != set(REGIONS):
        raise DataQualityError(f"expected all five regions, got {sorted(present)!r}")
    totals = [
        sum(cleaned.loc[cleaned["region"] == region, "revenue"], Decimal("0"))
        for region in REGIONS
    ]
    return pd.DataFrame({"region": REGIONS, "revenue": totals})


def run_pipeline(
    source: str | Path = "sales.csv",
    destination: str | Path = "revenue_by_region.csv",
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Read, reconcile, clean, aggregate, and write the regional CSV."""
    raw = pd.read_csv(source, dtype=str, keep_default_na=False)
    cleaned, stats = clean_sales(raw)
    regional = aggregate_regions(cleaned)
    output = regional.copy()
    output["revenue"] = output["revenue"].map(lambda value: format(value, ".2f"))
    output.to_csv(destination, index=False, lineterminator="\n")
    return regional, stats


def _arguments(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", nargs="?", help="input CSV (positional form)")
    parser.add_argument("destination", nargs="?", help="output CSV (positional form)")
    parser.add_argument("--input", "-i", dest="input_path", help="input sales CSV")
    parser.add_argument("--output", "-o", dest="output_path", help="output regional CSV")
    args = parser.parse_args(argv)
    if args.source is not None and args.input_path is not None:
        parser.error("use either positional source or --input, not both")
    if args.destination is not None and args.output_path is not None:
        parser.error("use either positional destination or --output, not both")
    return args


def main(argv: Sequence[str] | None = None) -> None:
    """CLI supporting both documented flags and backward-compatible positionals."""
    args = _arguments(argv)
    source = args.input_path or args.source or "sales.csv"
    destination = args.output_path or args.destination or "revenue_by_region.csv"
    run_pipeline(source, destination)


if __name__ == "__main__":
    main()
