"""Narrow, evidence-producing tools for Foundry agents. No shell or arbitrary file writes."""
from __future__ import annotations

import json
import subprocess
import sys

import pandas as pd
from agent_framework import tool

from pipeline import ROOT
from .telemetry import observed_tool

_READABLE = {
    "solution.py", "pipeline.py", "contracts.py", "contracts/data_policy.json",
    "test_virtual_column.py", "tests/test_pipeline.py", "tests/test_solution.py",
    "tests/test_contracts.py", "tests/test_properties.py",
    "README.md", "docs/architecture.md", "tests/test_policy_execution.py",
    "tests/test_randomized_regression.py", "tests/test_agent_reports.py",
    "tests/test_foundry_discoveries.py", "tests/test_raw_oracle.py",
}


@tool(approval_mode="never_require")
@observed_tool("profile_source")
def profile_source() -> str:
    """Profile the original CSV without invoking the ETL under review; return measured counts."""
    raw = pd.read_csv(ROOT / "sales.csv", dtype=str, keep_default_na=False)
    tx = raw[raw["Order ID"].str.startswith("SO-")]
    report = {
        "source_rows": len(raw),
        "source_columns": raw.columns.tolist(),
        "transaction_rows_before_dedup": len(tx),
        "repeated_header_rows": int((raw["Order ID"] == "Order ID").sum()),
        "total_rows": int((raw["Order ID"] == "TOTAL").sum()),
        "exact_duplicate_rows": int(tx.duplicated().sum()),
        "region_variants": tx.Region.value_counts().to_dict(),
        "noncanonical_regions": int((tx.Region != tx.Region.str.strip().str.title()).sum()),
        "missing_unit_prices": int((tx["Unit Price"] == "").sum()),
        "blank_discounts": int((tx.Discount == "").sum()),
        "negative_quantity_rows": int(tx["Quantity "].str.startswith("-").sum()),
        "thousands_separator_quantities": int(tx["Quantity "].str.contains(" ", regex=False).sum()),
        "comma_decimal_prices": int(tx["Unit Price"].str.contains(",", regex=False).sum()),
        "control_row": raw.loc[raw["Order ID"] == "TOTAL"].to_dict(orient="records"),
    }
    return json.dumps(report, ensure_ascii=False)


@tool(approval_mode="never_require")
@observed_tool("inspect_orders")
def inspect_orders(order_ids: str) -> str:
    """Read up to 10 comma-separated order IDs from original source, preserving actual rows."""
    ids = [item.strip() for item in order_ids.split(",") if item.strip()][:10]
    if not all(item.startswith("SO-") and len(item) == 8 for item in ids):
        return json.dumps({"error": "invalid IDs"})
    raw = pd.read_csv(ROOT / "sales.csv", dtype=str, keep_default_na=False)
    return raw[raw["Order ID"].isin(ids)].head(20).to_json(orient="records")


@tool(approval_mode="never_require")
@observed_tool("read_project_file")
def read_project_file(relative_path: str) -> str:
    """Read at most 16000 characters from a specific allowlisted engineering file."""
    if relative_path not in _READABLE:
        return "DENIED: path not on read allowlist"
    return (ROOT / relative_path).read_text(encoding="utf-8")[:16_000]


@tool(approval_mode="never_require")
@observed_tool("check_quality")
def check_quality() -> str:
    """Run the fixed pytest suite in a bounded subprocess (no arbitrary commands)."""
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", "-q"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        timeout=90,
        check=False,
    )
    return json.dumps({"exit_code": proc.returncode, "stdout": proc.stdout[-5000:], "stderr": proc.stderr[-1500:]})


@tool(approval_mode="never_require")
@observed_tool("inspect_approved_policy")
def inspect_approved_policy() -> str:
    """Read the exact approved, immutable policy currently used by the deterministic ETL."""
    return (ROOT / "contracts/data_policy.json").read_text(encoding="utf-8")


@tool(approval_mode="never_require")
@observed_tool("inspect_reconciliation")
def inspect_reconciliation() -> str:
    """Read the machine-generated report and tracked region totals for verification."""
    report = json.loads((ROOT / "reports/data_quality.json").read_text(encoding="utf-8"))
    result = (ROOT / "revenue_by_region.csv").read_text(encoding="utf-8")
    return json.dumps({"data_quality": report, "region_csv": result})
