"""Independent P3 oracle: original CSV -> expected regional revenue via stdlib.

Never imports/executes a candidate module. Operates on original source bytes
and sandbox-produced CSV. The model's claimed test results are never trusted.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
from collections import defaultdict
from decimal import Decimal, InvalidOperation
from pathlib import Path


COLUMNS = ("Order ID", "Region", "Product", "Quantity ", "Unit Price", "Discount", "Order Date")
REGIONS = frozenset({"Central", "East", "North", "South", "West"})
CENTS = Decimal("0.01")
AMOUNT = re.compile(r"\d+(?:[.,]\d{1,2})?\Z")
QUANTITY = re.compile(r"-?\d+(?: \d{3})*\Z")


class SandboxValidationError(ValueError):
    """Candidate result contradicts independently calculated source evidence."""


def _decimal(value: str, *, blank_zero: bool = False) -> Decimal:
    if blank_zero and value == "":
        return Decimal("0.00")
    if not AMOUNT.fullmatch(value):
        raise SandboxValidationError("Invalid original monetary field")
    try:
        return Decimal(value.replace(",", ".")).quantize(CENTS)
    except InvalidOperation as exc:
        raise SandboxValidationError("Unparseable original monetary field") from exc


def _quantity(value: str) -> int:
    if not QUANTITY.fullmatch(value):
        raise SandboxValidationError("Invalid original quantity")
    return int(value.replace(" ", ""))


def expected_revenues(source: Path) -> tuple[dict[str, Decimal], dict[str, int]]:
    with source.open(newline="", encoding="utf-8-sig") as stream:
        reader = csv.DictReader(stream)
        if tuple(reader.fieldnames or ()) != COLUMNS:
            raise SandboxValidationError("Original CSV header has changed")
        rows = list(reader)
    if any(None in row or any(value is None for value in row.values()) for row in rows):
        raise SandboxValidationError("Original CSV width mismatch")
    headers = [r for r in rows if r["Order ID"] == "Order ID"]
    controls = [r for r in rows if r["Order ID"] == "TOTAL"]
    tx = [r for r in rows if re.fullmatch(r"SO-\d{5}", r["Order ID"])]
    if len(headers) != 1 or len(controls) != 1 or len(tx) + 2 != len(rows):
        raise SandboxValidationError("Unexpected original source structure")
    control = controls[0]
    raw_qty = sum(_quantity(r["Quantity "]) for r in tx)
    raw_discount = sum((_decimal(r["Discount"], blank_zero=True) for r in tx), Decimal("0.00"))
    if raw_qty != _quantity(control["Quantity "]) or raw_discount != _decimal(control["Discount"]):
        raise SandboxValidationError("Original source control totals disagree")
    seen: set[tuple[str, ...]] = set()
    unique: list[dict[str, str]] = []
    for row in tx:
        key = tuple(row[col] for col in COLUMNS)
        if key not in seen:
            seen.add(key)
            unique.append(row)
    product_prices: dict[str, set[Decimal]] = defaultdict(set)
    for row in unique:
        if row["Unit Price"]:
            product_prices[row["Product"]].add(_decimal(row["Unit Price"]))
    totals: dict[str, Decimal] = defaultdict(lambda: Decimal("0.00"))
    for row in unique:
        region = row["Region"].strip().title()
        if region not in REGIONS:
            raise SandboxValidationError("Original source region is invalid")
        product = row["Product"]
        if row["Unit Price"]:
            price = _decimal(row["Unit Price"])
        else:
            candidates = product_prices[product]
            if len(candidates) != 1:
                raise SandboxValidationError("Original missing price cannot be uniquely recovered")
            price = next(iter(candidates))
        qty = _quantity(row["Quantity "])
        discount = _decimal(row["Discount"], blank_zero=True)
        totals[region] += qty * price - discount
    if set(totals) != REGIONS:
        raise SandboxValidationError("Expected five original regions")
    return dict(totals), {
        "raw_rows": len(rows), "raw_transactions": len(tx),
        "unique_transactions": len(unique),
        "duplicate_extras": len(tx) - len(unique),
    }


def compare_output(source: Path, output: Path) -> dict:
    expected, counts = expected_revenues(source)
    with output.open(newline="", encoding="utf-8") as stream:
        reader = csv.DictReader(stream)
        if reader.fieldnames != ["region", "revenue"]:
            raise SandboxValidationError("Candidate output schema must be region,revenue")
        data = list(reader)
    if len(data) != 5 or [r["region"] for r in data] != sorted(REGIONS):
        raise SandboxValidationError("Candidate must output five uniquely sorted regions")
    observed = {}
    for row in data:
        if set(row) != {"region", "revenue"} or not re.fullmatch(r"-?\d+\.\d{2}", row["revenue"]):
            raise SandboxValidationError("Malformed financial value or unexpected output field")
        observed[row["region"]] = Decimal(row["revenue"])
    if observed != expected:
        failures = {
            region: {"expected": str(expected[region]), "actual": str(observed.get(region))}
            for region in sorted(REGIONS) if observed.get(region) != expected[region]
        }
        raise SandboxValidationError("Independent source-vs-output reconciliation failed: " + json.dumps(failures))
    total = sum(expected.values(), Decimal("0.00"))
    return {
        "reconciliation": "passed", "source_counts": counts,
        "regions": {name: f"{amount:.2f}" for name, amount in sorted(expected.items())},
        "net_revenue": f"{total:.2f}",
        "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        "output_sha256": hashlib.sha256(output.read_bytes()).hexdigest(),
    }


def validate_runner(source: Path, output_dir: Path) -> dict:
    """Require the sandbox tests and pipeline command to exit zero before oracle."""
    test_exit = int((output_dir / "test_exit_code.txt").read_text(encoding="utf-8").strip())
    pipeline_exit = int((output_dir / "pipeline_exit_code.txt").read_text(encoding="utf-8").strip())
    verdict: dict = {
        "schema_version": 1, "source": "independent_p3_stdlib_oracle",
        "sandbox_test_exit_code": test_exit,
        "sandbox_pipeline_exit_code": pipeline_exit,
        "sandbox_network": "disabled",
        "azure_credentials_in_sandbox": False,
    }
    if test_exit == 0 and pipeline_exit == 0:
        verdict.update(compare_output(source, output_dir / "revenue_by_region.csv"))
        verdict["status"] = "PASSED"
    else:
        verdict["status"] = "FAILED"
        verdict["failure"] = "Sandbox test suite or candidate pipeline exited nonzero"
    return verdict


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--sandbox-output", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    args = parser.parse_args()
    try:
        receipt = validate_runner(args.source, args.sandbox_output)
    except (SandboxValidationError, FileNotFoundError, ValueError) as exc:
        receipt = {
            "schema_version": 1, "source": "independent_p3_stdlib_oracle",
            "status": "FAILED", "failure": str(exc),
        }
    args.receipt.parent.mkdir(parents=True, exist_ok=True)
    args.receipt.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": receipt["status"], "reconciliation": receipt.get("reconciliation")}))
    if receipt["status"] != "PASSED":
        raise SystemExit(2)


if __name__ == "__main__":
    main()
