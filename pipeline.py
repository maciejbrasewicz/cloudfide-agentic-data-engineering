"""A deterministic, auditable sales ETL that runs without Azure credentials."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from decimal import Decimal, InvalidOperation
from pathlib import Path

import pandas as pd

from contracts import DataPolicy, read_policy
from dataframe_contracts import validate_clean_transactions
from solution import add_virtual_column

ROOT = Path(__file__).resolve().parent
CENTS = Decimal("0.01")
FIELDS = {
    "Order ID": "order_id",
    "Region": "region",
    "Product": "product",
    "Quantity ": "quantity",
    "Unit Price": "unit_price",
    "Discount": "discount",
    "Order Date": "order_date",
}
REGIONS = frozenset({"Central", "East", "North", "South", "West"})
ID_PATTERN = re.compile(r"SO-\d{5}\Z")


class DataQualityError(ValueError):
    """Data cannot be safely repaired without an unsupported assumption."""


def parse_decimal(value: str, *, field: str) -> Decimal:
    try:
        cleaned = value.strip().replace(",", ".")
        number = Decimal(cleaned)
        if not number.is_finite() or number.as_tuple().exponent < -2:
            raise ValueError("non-finite or sub-cent amount")
        return number.quantize(CENTS)
    except (InvalidOperation, ValueError) as exc:
        raise DataQualityError(f"Invalid {field}: {value!r}") from exc


def clean_sales(raw: pd.DataFrame, policy: DataPolicy | None = None) -> tuple[pd.DataFrame, dict]:
    """Normalize source data under an explicit, validated business decision contract."""
    if policy is None:
        policy = read_policy(ROOT / "contracts/data_policy.json")
    if set(raw.columns) != set(FIELDS) or len(raw.columns) != len(FIELDS):
        raise DataQualityError("Unexpected source schema")
    rows = raw.rename(columns=FIELDS).copy(deep=True)
    # Detect exact duplicates in source values, before trimming or parsing can
    # make two distinct raw order lines look identical.
    source_lines = rows.loc[~rows.order_id.isin(["Order ID", "TOTAL"])]
    raw_duplicate_indices = source_lines.index[source_lines.duplicated(keep="first")]
    raw_region_deviations = int((
        rows.loc[~rows.order_id.isin(["Order ID", "TOTAL"]), "region"]
        != rows.loc[~rows.order_id.isin(["Order ID", "TOTAL"]), "region"].str.strip().str.title()
    ).sum())
    # Only normalize columns explicitly permitted by the approved policy.
    # All other source fields must retain their original meaning.
    headers = rows[rows.order_id == "Order ID"]
    totals = rows[rows.order_id == "TOTAL"]
    if len(totals) != 1:
        raise DataQualityError("Expected exactly one TOTAL control row")
    expected_header = {normalized: original for original, normalized in FIELDS.items()}
    for _, record in headers.iterrows():
        if any(record[column] != expected for column, expected in expected_header.items()):
            raise DataQualityError("Malformed repeated header row")
    control = totals.iloc[0]
    if any(control[column] != "" for column in ("region", "product", "unit_price", "order_date")):
        raise DataQualityError("Malformed TOTAL control row metadata")
    transactions = rows[~rows.order_id.isin(["Order ID", "TOTAL"])].copy()
    for col in ("order_id", "product", "unit_price", "discount", "order_date"):
        if (transactions[col] != transactions[col].str.strip()).any():
            raise DataQualityError(f"Unapproved surrounding whitespace in {col}")
    if not transactions.order_id.map(lambda x: bool(ID_PATTERN.fullmatch(x))).all():
        raise DataQualityError("Malformed order ID; manual investigation required")

    # Quantities may contain an embedded space as a thousands separator.
    bad_quantity_pattern = transactions.quantity.map(lambda q: not bool(re.fullmatch(r"-?\d+(?: \d{3})*", q)))
    if bad_quantity_pattern.any():
        raise DataQualityError("Invalid quantity representation")
    spaced_quantities = int(transactions.quantity.str.contains(" ", regex=False).sum())
    transactions["quantity"] = transactions.quantity.map(lambda q: int(q.replace(" ", "")))

    discounted = transactions.discount.map(lambda d: parse_decimal(d, field="discount") if d else Decimal("0.00"))
    raw_total_quantity = int(transactions.quantity.sum())
    raw_total_discount = sum(discounted, Decimal("0.00"))
    control_quantity = int(totals.iloc[0].quantity.replace(" ", ""))
    control_discount = parse_decimal(totals.iloc[0].discount, field="TOTAL.discount")
    if raw_total_quantity != control_quantity or raw_total_discount != control_discount:
        raise DataQualityError("Raw source TOTAL mismatch; stop before cleaning")

    # Preserve source-row identity: normalization-equivalent lines are NOT
    # evidence of duplicated source transactions.
    before_dedup = len(transactions)
    if policy.duplicates == "remove_exact_duplicates":
        transactions = transactions.drop(index=raw_duplicate_indices).copy()
    duplicates = before_dedup - len(transactions)

    if policy.region == "strict" and not raw.loc[transactions.index, "Region"].isin(REGIONS).all():
        raise DataQualityError("Unknown region: noncanonical raw value rejected under strict policy")
    if policy.region == "strip_and_title_case":
        transactions["region"] = transactions.region.str.strip().str.title()
    if not transactions.region.isin(REGIONS).all():
        raise DataQualityError("Unknown region")
    comma_prices = int(transactions.unit_price.str.contains(",", regex=False).sum())
    missing_prices = int((transactions.unit_price == "").sum())
    missing_discounts = int((transactions.discount == "").sum())
    if missing_discounts and policy.missing_discount == "fail":
        raise DataQualityError("Blank discounts rejected by approved policy")
    transactions["discount"] = transactions.discount.map(lambda x: parse_decimal(x, field="discount") if x else Decimal("0.00"))
    if any(value < 0 for value in transactions.discount):
        raise DataQualityError("Unexpected negative discount")
    if missing_prices and policy.missing_unit_price == "fail":
        raise DataQualityError("Missing unit prices rejected by approved policy")
    transactions["unit_price"] = transactions.unit_price.map(lambda x: parse_decimal(x, field="unit_price") if x else None)

    # Only infer an absent price if the *normalized* reference price is unique.
    references = transactions[transactions.unit_price.notna()].groupby("product")["unit_price"].agg(
        lambda col: frozenset(col)
    )
    def complete_price(row: pd.Series) -> Decimal:
        if row.unit_price is not None:
            return row.unit_price
        candidates = references.get(row["product"], frozenset())
        if len(candidates) != 1:
            raise DataQualityError(f"Ambiguous missing price for product {row['product']!r}")
        return next(iter(candidates))

    transactions["unit_price"] = transactions.apply(complete_price, axis=1)
    if any(value < 0 for value in transactions.unit_price):
        raise DataQualityError("Unexpected negative price")
    if policy.negative_quantity == "reject" and (transactions.quantity < 0).any():
        raise DataQualityError("Negative quantities rejected by approved policy")
    dates = pd.to_datetime(transactions.order_date, format="%Y-%m-%d", errors="coerce")
    if dates.isna().any():
        raise DataQualityError("Invalid order date")

    # Use the required function rather than bypassing it with ad hoc arithmetic.
    cleaned = add_virtual_column(transactions, "quantity * unit_price - discount", "revenue")
    if len(cleaned) != len(transactions) or "revenue" not in cleaned:
        raise DataQualityError("Virtual-column evaluation failed")
    if cleaned.revenue.map(lambda x: not isinstance(x, Decimal)).any():
        raise DataQualityError("Non-decimal revenue")
    try:
        cleaned = validate_clean_transactions(cleaned)
    except ValueError as exc:
        raise DataQualityError("Pandera transaction contract rejected the data") from exc

    report = {
        "policy_version": policy.version,
        "source_rows": len(raw),
        "repeated_headers": len(headers),
        "total_control_rows": len(totals),
        "transactions_before_dedup": before_dedup,
        "raw_control_quantity": raw_total_quantity,
        "raw_control_discount": str(raw_total_discount),
        "exact_duplicates_removed": duplicates,
        "transactions_after_dedup": len(cleaned),
        "regions_normalized": raw_region_deviations,
        "comma_decimal_prices": comma_prices,
        "spaced_quantities": spaced_quantities,
        "missing_unit_prices_recovered": missing_prices,
        "blank_discounts_zeroed": missing_discounts,
        "negative_quantities_retained": int((cleaned.quantity < 0).sum()),
        "reconciliation_status": "passed",
    }
    return cleaned, report


def run_pipeline(source: Path, output: Path, report_path: Path | None, policy: Path) -> dict:
    # Reject path aliases before the first write: input and policy files are
    # immutable, and output/report files cannot overwrite each other.
    paths = [source.resolve(), output.resolve(), policy.resolve()]
    if report_path is not None:
        paths.append(report_path.resolve())
    if len(paths) != len(set(paths)):
        raise DataQualityError("Source, policy, output and report paths must be distinct")
    source_hash = hashlib.sha256(source.read_bytes()).hexdigest()
    policy_hash = hashlib.sha256(policy.read_bytes()).hexdigest()
    approved_policy = read_policy(policy)
    raw = pd.read_csv(source, dtype=str, keep_default_na=False)
    cleaned, report = clean_sales(raw, approved_policy)
    result = cleaned.groupby("region", sort=True)["revenue"].sum()
    if len(result) != 5 or set(result.index) != REGIONS:
        raise DataQualityError("Unexpected region group set")
    source_total = sum(cleaned.revenue, Decimal("0.00"))
    result_total = sum(result.tolist(), Decimal("0.00"))
    if source_total != result_total:
        raise DataQualityError("Revenue mismatch after grouping")
    result_df = pd.DataFrame({"region": result.index, "revenue": [f"{x.quantize(CENTS):.2f}" for x in result]})
    output.parent.mkdir(parents=True, exist_ok=True)
    result_df.to_csv(output, index=False, lineterminator="\n")
    report.update({
        "region_count": len(result),
        "net_revenue": f"{result_total:.2f}",
        "source_sha256": source_hash,
        "output_sha256": hashlib.sha256(output.read_bytes()).hexdigest(),
        "policy_sha256": policy_hash,
    })
    if report_path is not None:
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="Clean sales CSV, verify source controls, and aggregate revenue")
    parser.add_argument("--input", type=Path, default=ROOT / "sales.csv")
    parser.add_argument("--output", type=Path, default=ROOT / "revenue_by_region.csv")
    parser.add_argument("--report", type=Path, default=ROOT / "reports" / "data_quality.json")
    parser.add_argument("--policy", type=Path, default=ROOT / "contracts" / "data_policy.json")
    args = parser.parse_args()
    print(json.dumps(run_pipeline(args.input, args.output, args.report, args.policy), indent=2))


if __name__ == "__main__":
    main()
