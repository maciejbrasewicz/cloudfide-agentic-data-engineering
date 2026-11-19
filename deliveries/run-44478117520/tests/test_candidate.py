"""Additional tests for restricted expressions and the sales pipeline."""

from __future__ import annotations

import csv
from decimal import Decimal

import pandas as pd

from pipeline import DataQualityError, load_and_clean_sales, run_pipeline
from solution import add_virtual_column


HEADERS = [
    "Order ID",
    "Region",
    "Product",
    "Quantity ",
    "Unit Price",
    "Discount",
    "Order Date",
]


def _write_sales(path, *, control_quantity="18"):
    rows = [
        ["SO-1", "Central", "Widget", "2", "10.00", "", "2026-01-01"],
        ["SO-2", "East", "Widget", "1", "", "", "2026-01-02"],
        ["SO-3", "North", "Widget", "-1", "10.00", "1", "2026-01-03"],
        ["SO-4", "South", "Widget", "1 0", "10.00", "0", "2026-01-04"],
        ["SO-5", " west  ", "Widget", "3", "10,00", "", "2026-01-05"],
        ["SO-5", " west  ", "Widget", "3", "10,00", "", "2026-01-05"],
        HEADERS,
        ["TOTAL", "", "", control_quantity, "", "1", ""],
    ]
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream)
        writer.writerow(HEADERS)
        writer.writerows(rows)


def test_expression_precedence_parentheses_and_input_immutability():
    source = pd.DataFrame(
        {"first": [2, 3], "second": [4, 5], "third": [1, 2]},
        index=[10, 20],
    )
    original = source.copy(deep=True)

    result = add_virtual_column(
        source, " (first + second) * third ", "calculated"
    )

    assert result["calculated"].tolist() == [6, 16]
    assert result.index.equals(source.index)
    assert source.equals(original)


def test_unsafe_or_unsupported_expressions_are_rejected():
    frame = pd.DataFrame({"amount": [2], "price": [3]})
    invalid = [
        "amount / price",
        "-amount",
        "amount ** price",
        "amount.__class__",
        "__import__('os')",
        "missing + amount",
    ]
    assert all(add_virtual_column(frame, role, "result").empty for role in invalid)
    assert add_virtual_column(frame, "amount + price", "bad2").empty


def test_pipeline_repairs_and_writes_required_output_schema(tmp_path):
    source = tmp_path / "sales.csv"
    output = tmp_path / "revenue_by_region.csv"
    _write_sales(source)

    cleaned = load_and_clean_sales(source)
    totals = run_pipeline(source, output)
    written = pd.read_csv(output, dtype=str, keep_default_na=False)

    assert len(cleaned) == 5
    assert cleaned.loc[cleaned["order_id"].eq("SO-2"), "unit_price"].iloc[0] == Decimal("10.00")
    assert cleaned.loc[cleaned["order_id"].eq("SO-3"), "revenue"].iloc[0] == Decimal("-11.00")
    assert list(totals.columns) == ["region", "revenue"]
    assert list(written.columns) == ["region", "revenue"]
    assert totals["region"].tolist() == ["Central", "East", "North", "South", "West"]
    assert totals["revenue"].tolist() == [
        Decimal("20.00"),
        Decimal("10.00"),
        Decimal("-11.00"),
        Decimal("100.00"),
        Decimal("30.00"),
    ]


def test_control_is_checked_before_duplicate_removal(tmp_path):
    source = tmp_path / "sales.csv"
    _write_sales(source, control_quantity="15")

    try:
        load_and_clean_sales(source)
    except DataQualityError as exc:
        assert "raw quantity" in str(exc)
    else:
        raise AssertionError("a control total that ignores the duplicate must fail")
