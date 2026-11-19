"""Clean the sales export and write exact revenue totals by region."""

from __future__ import annotations

import argparse
import re
from dataclasses import asdict, dataclass
from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Iterable

import pandas as pd

from solution import add_virtual_column

EXPECTED_COLUMNS = [
    "Order ID",
    "Region",
    "Product",
    "Quantity",
    "Unit Price",
    "Discount",
    "Order Date",
]
REGIONS = ("Central", "East", "North", "South", "West")
INTEGER = re.compile(r"[+-]?\d+\Z")
NUMBER = re.compile(r"[+-]?(?:\d+(?:[.,]\d*)?|[.,]\d+)\Z")
CENT = Decimal("0.01")


class DataQualityError(ValueError):
    """Raised when source data cannot be repaired unambiguously by policy."""


@dataclass(frozen=True)
class CleaningAudit:
    transaction_rows: int
    repeated_header_rows: int
    control_rows: int
    exact_duplicate_extra_rows: int
    missing_unit_price_rows: int
    blank_discount_rows: int
    negative_quantity_rows: int
    noncanonical_region_rows: int
    comma_price_rows: int
    spaced_quantity_rows: int
    raw_quantity_total: int
    raw_discount_total: Decimal

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def _integer(value: object, field: str) -> int:
    text = "".join(str(value).split())
    if not text or INTEGER.fullmatch(text) is None:
        raise DataQualityError(f"invalid {field}: {value!r}")
    return int(text)


def _decimal(value: object, field: str, *, blank_zero: bool = False) -> Decimal:
    text = str(value).strip()
    if not text:
        if blank_zero:
            return Decimal("0")
        raise DataQualityError(f"missing {field}")
    if NUMBER.fullmatch(text) is None:
        raise DataQualityError(f"invalid {field}: {value!r}")
    try:
        result = Decimal(text.replace(",", "."))
    except InvalidOperation as exc:
        raise DataQualityError(f"invalid {field}: {value!r}") from exc
    if not result.is_finite():
        raise DataQualityError(f"non-finite {field}")
    return result


def _read_raw(path: str | Path) -> pd.DataFrame:
    try:
        frame = pd.read_csv(path, dtype=str, keep_default_na=False)
    except Exception as exc:
        raise DataQualityError(f"could not read sales source: {exc}") from exc

    frame.columns = [str(column).strip() for column in frame.columns]
    if list(frame.columns) != EXPECTED_COLUMNS:
        raise DataQualityError(
            f"unexpected columns: expected {EXPECTED_COLUMNS!r}, "
            f"got {list(frame.columns)!r}"
        )
    return frame


def clean_sales(path: str | Path) -> tuple[pd.DataFrame, CleaningAudit]:
    """Reconcile raw transactions, then clean them under policy version 1."""
    raw = _read_raw(path)
    identifiers = raw["Order ID"].str.strip()
    header_mask = identifiers.eq("Order ID")
    control_mask = identifiers.eq("TOTAL")
    if int(control_mask.sum()) != 1:
        raise DataQualityError("source must contain exactly one TOTAL control row")

    transaction_mask = ~(header_mask | control_mask)
    source = raw.loc[transaction_mask].copy()
    if source.empty:
        raise DataQualityError("source contains no transaction rows")

    # Reconcile the untouched transaction population before duplicate removal.
    raw_quantities = source["Quantity"].map(
        lambda value: _integer(value, "Quantity")
    )
    raw_discounts = source["Discount"].map(
        lambda value: _decimal(value, "Discount", blank_zero=True)
    )
    raw_quantity_total = int(raw_quantities.sum())
    raw_discount_total = sum(raw_discounts, Decimal("0"))
    control = raw.loc[control_mask].iloc[0]
    if (
        raw_quantity_total != _integer(control["Quantity"], "control Quantity")
        or raw_discount_total
        != _decimal(control["Discount"], "control Discount")
    ):
        raise DataQualityError(
            "raw transaction totals do not match the TOTAL control row"
        )

    raw_regions = source["Region"].astype(str)
    canonical_regions = raw_regions.str.strip().str.title()
    raw_prices = source["Unit Price"].astype(str)
    audit_values = {
        "transaction_rows": int(len(source)),
        "repeated_header_rows": int(header_mask.sum()),
        "control_rows": 1,
        "exact_duplicate_extra_rows": int(source.duplicated(keep="first").sum()),
        "missing_unit_price_rows": int(raw_prices.str.strip().eq("").sum()),
        "blank_discount_rows": int(
            source["Discount"].astype(str).str.strip().eq("").sum()
        ),
        "negative_quantity_rows": int((raw_quantities < 0).sum()),
        "noncanonical_region_rows": int((raw_regions != canonical_regions).sum()),
        "comma_price_rows": int(raw_prices.str.contains(",", regex=False).sum()),
        "spaced_quantity_rows": int(
            source["Quantity"]
            .astype(str)
            .map(lambda value: any(character.isspace() for character in value))
            .sum()
        ),
        "raw_quantity_total": raw_quantity_total,
        "raw_discount_total": raw_discount_total,
    }

    # The approved policy removes only byte-equivalent field rows, and only
    # after the preceding source-control reconciliation succeeds.
    rows = source.drop_duplicates(keep="first").copy()
    regions = rows["Region"].astype(str).str.strip().str.title()
    unknown_regions = sorted(set(regions) - set(REGIONS))
    if regions.eq("").any() or unknown_regions:
        raise DataQualityError(
            f"unknown or blank regions: {unknown_regions!r}"
        )

    quantities = rows["Quantity"].map(
        lambda value: _integer(value, "Quantity")
    )
    discounts = rows["Discount"].map(
        lambda value: _decimal(value, "Discount", blank_zero=True)
    )

    observed_prices: dict[str, set[Decimal]] = {}
    parsed_prices: dict[object, Decimal] = {}
    for index, row in rows.iterrows():
        product = str(row["Product"]).strip()
        if not product:
            raise DataQualityError("blank Product")
        price_text = str(row["Unit Price"]).strip()
        if price_text:
            price = _decimal(price_text, "Unit Price")
            parsed_prices[index] = price
            observed_prices.setdefault(product, set()).add(price)

    prices: list[Decimal] = []
    for index, row in rows.iterrows():
        product = str(row["Product"]).strip()
        if index in parsed_prices:
            prices.append(parsed_prices[index])
        else:
            candidates = observed_prices.get(product, set())
            if len(candidates) != 1:
                raise DataQualityError(
                    f"cannot infer one Unit Price for product {product!r}"
                )
            prices.append(next(iter(candidates)))
        try:
            datetime.strptime(str(row["Order Date"]).strip(), "%Y-%m-%d")
        except ValueError as exc:
            raise DataQualityError(
                f"invalid Order Date: {row['Order Date']!r}"
            ) from exc

    rows["Region"] = regions
    rows["Product"] = rows["Product"].astype(str).str.strip()
    rows["Quantity"] = quantities
    rows["Unit Price"] = pd.Series(prices, index=rows.index, dtype=object)
    rows["Discount"] = discounts
    rows.columns = [column.replace(" ", "_") for column in rows.columns]

    cleaned = add_virtual_column(
        rows, "Quantity * Unit_Price - Discount", "revenue"
    )
    if "revenue" not in cleaned.columns:
        raise DataQualityError("revenue expression could not be evaluated")
    return cleaned.reset_index(drop=True), CleaningAudit(**audit_values)


def aggregate_revenue(cleaned: pd.DataFrame) -> pd.DataFrame:
    """Aggregate exact revenue into the required lowercase output schema."""
    if not {"Region", "revenue"}.issubset(cleaned.columns):
        raise DataQualityError("cleaned data is missing Region or revenue")

    totals = {region: Decimal("0") for region in REGIONS}
    for region, revenue in zip(cleaned["Region"], cleaned["revenue"]):
        if region not in totals:
            raise DataQualityError(f"unknown region in cleaned data: {region!r}")
        if not isinstance(revenue, Decimal) or not revenue.is_finite():
            raise DataQualityError("revenue must be a finite Decimal")
        totals[region] += revenue

    # The externally required CSV header is exactly: region,revenue.
    return pd.DataFrame(
        [(region, totals[region].quantize(CENT)) for region in REGIONS],
        columns=["region", "revenue"],
    )


def run_pipeline(
    input_path: str | Path = "sales.csv",
    output_path: str | Path = "revenue_by_region.csv",
) -> CleaningAudit:
    """Clean, aggregate, write the required CSV, and return audit evidence."""
    cleaned, audit = clean_sales(input_path)
    aggregate_revenue(cleaned).to_csv(output_path, index=False)
    return audit


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", default="sales.csv")
    parser.add_argument("--output", default="revenue_by_region.csv")
    arguments = parser.parse_args(list(argv) if argv is not None else None)
    print(run_pipeline(arguments.input, arguments.output).to_dict())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
