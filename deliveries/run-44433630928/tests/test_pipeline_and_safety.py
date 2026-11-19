from __future__ import annotations

import csv
from decimal import Decimal
from pathlib import Path

import pandas as pd
import pytest

from pipeline import DataQualityError, clean_sales, main, revenue_by_region
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


def _write_fixture(path: Path, *, control_quantity: str = "3") -> None:
    rows = [
        ["SO-1", "north", "Widget", "2", "10,00", "", "2026-01-01"],
        ["SO-1", "north", "Widget", "2", "10,00", "", "2026-01-01"],
        ["Order ID", "Region", "Product", "Quantity", "Unit Price", "Discount", "Order Date"],
        ["SO-2", " south ", "Widget", "-1", "", "1.00", "2026-01-02"],
        ["TOTAL", "", "", control_quantity, "", "1.00", ""],
    ]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(HEADERS)
        writer.writerows(rows)


def test_compound_expression_precedence_and_input_is_unchanged() -> None:
    original = pd.DataFrame(
        {
            "quantity": [Decimal("2")],
            "unit_price": [Decimal("3.50")],
            "discount": [Decimal("1.25")],
        }
    )
    result = add_virtual_column(
        original, "quantity * unit_price - discount", "revenue"
    )
    assert result["revenue"].tolist() == [Decimal("5.75")]
    assert "revenue" not in original.columns


@pytest.mark.parametrize(
    "expression",
    [
        "left / right",
        "left ** right",
        "-left",
        "1 + left",
        "missing + right",
        "__import__('os').getcwd()",
    ],
)
def test_unsafe_or_unsupported_expressions_are_empty(expression: str) -> None:
    frame = pd.DataFrame({"left": [2], "right": [1]})
    assert add_virtual_column(frame, expression, "answer").empty


def test_pipeline_repairs_data_and_aggregates_all_regions(tmp_path: Path) -> None:
    source = tmp_path / "sales.csv"
    _write_fixture(source)

    cleaned = clean_sales(source)
    assert len(cleaned) == 2
    assert cleaned["quantity"].tolist() == [Decimal("2"), Decimal("-1")]
    assert cleaned["unit_price"].tolist() == [Decimal("10.00"), Decimal("10.00")]
    assert cleaned["discount"].tolist() == [Decimal("0"), Decimal("1.00")]
    assert cleaned["revenue"].tolist() == [Decimal("20.00"), Decimal("-11.00")]

    aggregate = revenue_by_region(cleaned)
    assert aggregate["region"].tolist() == ["Central", "East", "North", "South", "West"]
    assert aggregate["revenue"].tolist() == [
        Decimal("0.00"),
        Decimal("0.00"),
        Decimal("20.00"),
        Decimal("-11.00"),
        Decimal("0.00"),
    ]


def test_raw_control_mismatch_fails_before_cleaning(tmp_path: Path) -> None:
    source = tmp_path / "bad.csv"
    _write_fixture(source, control_quantity="1")
    with pytest.raises(DataQualityError, match="raw controls do not reconcile"):
        clean_sales(source)


def test_cli_accepts_input_and_output_flags(tmp_path: Path) -> None:
    source = tmp_path / "sales.csv"
    destination = tmp_path / "result.csv"
    _write_fixture(source)

    assert main(["--input", str(source), "--output", str(destination)]) == 0
    assert destination.read_text(encoding="utf-8") == (
        "region,revenue\n"
        "Central,0.00\n"
        "East,0.00\n"
        "North,20.00\n"
        "South,-11.00\n"
        "West,0.00\n"
    )
