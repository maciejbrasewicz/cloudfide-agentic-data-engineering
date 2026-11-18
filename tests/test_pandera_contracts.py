"""Pandera must enforce the real Decimal contract without type coercion."""
from __future__ import annotations

from decimal import Decimal

import pandas as pd
import pytest

from dataframe_contracts import validate_clean_transactions


@pytest.fixture
def valid():
    return pd.DataFrame({
        "order_id": ["SO-00001", "SO-00002"],
        "region": ["North", "East"],
        "product": ["SKU_A", "SKU_B"],
        "quantity": [3, -2],
        "unit_price": [Decimal("12.50"), Decimal("4.00")],
        "discount": [Decimal("0.50"), Decimal("0.00")],
        "order_date": ["2026-01-01", "2026-01-02"],
        "revenue": [Decimal("37.00"), Decimal("-8.00")],
    })


def test_pandera_preserves_exact_values_and_negative_quantities(valid):
    original = valid.copy(deep=True)
    result = validate_clean_transactions(valid)
    pd.testing.assert_frame_equal(original, result)
    assert all(isinstance(x, Decimal) for x in result["revenue"])


@pytest.mark.parametrize("column,bad", [
    ("region", "Unapproved"),
    ("order_id", "DROP TABLE orders"),
    ("unit_price", "12.50"),
    ("discount", float("nan")),
    ("revenue", Decimal("36.99")),
    ("order_date", "not-a-date"),
    ("product", ""),
])
def test_invalid_cleaned_dataframe_rejected(valid, column, bad):
    value = valid.copy(deep=True)
    value.at[0, column] = bad
    with pytest.raises(ValueError, match="Pandera"):
        validate_clean_transactions(value)


def test_no_undocumented_numeric_conversion(valid):
    value = valid.copy(deep=True)
    value.loc[0, "quantity"] = "3"
    with pytest.raises(ValueError, match="Pandera"):
        validate_clean_transactions(value)
