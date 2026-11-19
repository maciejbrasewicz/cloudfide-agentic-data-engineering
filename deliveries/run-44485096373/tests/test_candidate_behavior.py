"""Additional tests for safe expressions and the policy-driven pipeline."""

from __future__ import annotations

import csv
from decimal import Decimal

import pandas as pd
import pytest

from pipeline import DataQualityError, aggregate_revenue, clean_sales, run_pipeline
from solution import add_virtual_column


def _write_fixture(path, *, control_quantity: str = "6") -> None:
    columns = [
        "Order ID",
        "Region",
        "Product",
        "Quantity ",
        "Unit Price",
        "Discount",
        "Order Date",
    ]
    rows = [
        ["SO-1", "Central", "Widget", "2", "10.00", "", "2026-01-01"],
        ["SO-1", "Central", "Widget", "2", "10.00", "", "2026-01-01"],
        columns,
        ["SO-2", " east ", "Widget", "-1", "10,00", "1.00", "2026-01-02"],
        ["SO-3", "West", "Widget", "3", "", "", "2026-01-03"],
        ["TOTAL", "", "", control_quantity, "", "1.00", ""],
    ]
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream)
        writer.writerow(columns)
        writer.writerows(rows)


def test_expression_precedence_parentheses_and_input_immutability():
    source = pd.DataFrame(
        {"first": [2, 4], "second": [3, 5], "third": [7, 11]}
    )
    result = add_virtual_column(
        source, " ( first + second ) * third ", "line_total"
    )

    assert result["line_total"].tolist() == [35, 99]
    assert list(source.columns) == ["first", "second", "third"]


@pytest.mark.parametrize(
    "expression",
    [
        "first / second",
        "-first",
        "first ** second",
        "missing + first",
        "first.__class__",
        "__import__('os').system('echo unsafe')",
        "1 + first",
        "",
    ],
)
def test_invalid_or_unsafe_expressions_return_empty(expression):
    frame = pd.DataFrame({"first": [1], "second": [2]})
    assert add_virtual_column(frame, expression, "result").empty


def test_pipeline_cleans_reconciles_and_writes_exact_schema(tmp_path):
    source_path = tmp_path / "sales.csv"
    output_path = tmp_path / "revenue_by_region.csv"
    _write_fixture(source_path)

    cleaned, audit = clean_sales(source_path)
    assert audit.transaction_rows == 4
    assert audit.repeated_header_rows == 1
    assert audit.exact_duplicate_extra_rows == 1
    assert audit.missing_unit_price_rows == 1
    assert audit.blank_discount_rows == 3
    assert audit.negative_quantity_rows == 1
    assert audit.noncanonical_region_rows == 1
    assert audit.comma_price_rows == 1
    assert audit.raw_quantity_total == 6
    assert audit.raw_discount_total == Decimal("1.00")
    assert len(cleaned) == 3
    assert cleaned["revenue"].tolist() == [
        Decimal("20.00"),
        Decimal("-11.00"),
        Decimal("30.00"),
    ]

    totals = aggregate_revenue(cleaned)
    assert list(totals.columns) == ["region", "revenue"]
    assert totals["region"].tolist() == [
        "Central",
        "East",
        "North",
        "South",
        "West",
    ]
    assert totals["revenue"].tolist() == [
        Decimal("20.00"),
        Decimal("-11.00"),
        Decimal("0.00"),
        Decimal("0.00"),
        Decimal("30.00"),
    ]

    run_pipeline(source_path, output_path)
    assert output_path.read_text(encoding="utf-8").splitlines()[0] == "region,revenue"
    written = pd.read_csv(output_path, dtype=str, keep_default_na=False)
    assert list(written.columns) == ["region", "revenue"]
    assert len(written) == 5


def test_control_mismatch_fails_before_cleaning(tmp_path):
    source_path = tmp_path / "bad-control.csv"
    _write_fixture(source_path, control_quantity="5")

    with pytest.raises(DataQualityError, match="do not match"):
        clean_sales(source_path)
