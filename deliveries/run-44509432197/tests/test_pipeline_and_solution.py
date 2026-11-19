"""Project tests for safe expressions, cleaning policy, and CLI behavior."""

from __future__ import annotations

from decimal import Decimal

import pandas as pd
import pytest

import pipeline
from pipeline import DataQualityError, SOURCE_COLUMNS, clean_sales, run_pipeline
from solution import add_virtual_column


def _raw_fixture() -> pd.DataFrame:
    rows = [
        ["A", " central ", "Widget", "1 0", "2,50", "", "2026-01-01"],
        ["B", "EAST", "Gadget", "2", "5.00", "1.00", "2026-01-02"],
        ["C", "North", "Widget", "-1", "", "", "2026-01-03"],
        ["D", "South", "Other", "3", "4.00", "0.50", "2026-01-04"],
        ["E", "West", "Desk", "1", "10.00", "", "2026-01-05"],
        ["E", "West", "Desk", "1", "10.00", "", "2026-01-05"],
        SOURCE_COLUMNS,
        ["TOTAL", "", "", "16", "", "1.50", ""],
    ]
    return pd.DataFrame(rows, columns=SOURCE_COLUMNS, dtype=str)


def test_virtual_column_chaining_is_exact_and_non_mutating() -> None:
    original = pd.DataFrame(
        {
            "quantity": [Decimal("2")],
            "price": [Decimal("3.25")],
            "discount": [Decimal("0.50")],
        }
    )
    result = add_virtual_column(
        original, " quantity * price - discount ", "line_revenue"
    )
    assert result.loc[0, "line_revenue"] == Decimal("6.00")
    assert list(original.columns) == ["quantity", "price", "discount"]


@pytest.mark.parametrize(
    "expression",
    [
        "quantity / price",
        "quantity ** price",
        "-quantity",
        "quantity + 1",
        "missing + price",
        "__import__('os').system('echo unsafe')",
        "quantity[0]",
        "",
    ],
)
def test_invalid_expressions_are_rejected(expression: str) -> None:
    frame = pd.DataFrame({"quantity": [2], "price": [3]})
    assert add_virtual_column(frame, expression, "result").empty


def test_cleaning_reconciles_before_dedup_and_applies_policy() -> None:
    cleaned, stats = clean_sales(_raw_fixture())
    assert len(cleaned) == 5
    assert stats["raw_quantity_total"] == Decimal("16")
    assert stats["raw_discount_total"] == Decimal("1.50")
    assert stats["exact_duplicate_extra_rows"] == 1
    assert stats["missing_unit_price_rows"] == 1
    assert stats["negative_quantity_rows"] == 1
    north = cleaned.loc[cleaned["region"] == "North"].iloc[0]
    assert north["unit_price"] == Decimal("2.50")
    assert north["revenue"] == Decimal("-2.50")


def test_control_mismatch_fails_instead_of_deduplicating_around_it() -> None:
    raw = _raw_fixture()
    raw.loc[raw["Order ID"] == "TOTAL", "Quantity "] = "15"
    with pytest.raises(DataQualityError, match="does not reconcile"):
        clean_sales(raw)


def test_pipeline_writes_deterministic_exact_output(tmp_path) -> None:
    source = tmp_path / "sales.csv"
    destination = tmp_path / "regional.csv"
    _raw_fixture().to_csv(source, index=False)
    regional, stats = run_pipeline(source, destination)
    assert regional["revenue"].tolist() == [
        Decimal("25.00"),
        Decimal("9.00"),
        Decimal("-2.50"),
        Decimal("11.50"),
        Decimal("10.00"),
    ]
    assert stats["transaction_rows"] == 6
    assert destination.read_text(encoding="utf-8") == (
        "region,revenue\n"
        "Central,25.00\n"
        "East,9.00\n"
        "North,-2.50\n"
        "South,11.50\n"
        "West,10.00\n"
    )


def test_cli_accepts_input_and_output_flags(monkeypatch) -> None:
    observed: list[tuple[str, str]] = []

    def fake_run(source: str, destination: str):
        observed.append((source, destination))
        return pd.DataFrame(), {}

    monkeypatch.setattr(pipeline, "run_pipeline", fake_run)
    pipeline.main(["--input", "in.csv", "--output", "out.csv"])
    assert observed == [("in.csv", "out.csv")]
