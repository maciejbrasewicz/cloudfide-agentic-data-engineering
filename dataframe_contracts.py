"""Pandera boundary for the cleaned finance transaction DataFrame.

No coercion is permitted here: Pandera must detect a corrupted value rather
than helpfully rewrite the output or silently reinterpret a business record.
"""
from __future__ import annotations

from decimal import Decimal
from typing import Any

import pandas as pd
import pandera.pandas as pa
from pandera.errors import SchemaError, SchemaErrors

_ALLOWED_REGIONS = {"Central", "East", "North", "South", "West"}
_CENT = Decimal("0.01")


def _cent_amount(value: Any) -> bool:
    return (
        isinstance(value, Decimal)
        and value.is_finite()
        and value.as_tuple().exponent >= -2
    )


TRANSACTION_SCHEMA = pa.DataFrameSchema(
    {
        "order_id": pa.Column("object", checks=pa.Check.str_matches(r"^SO-[0-9]{5}$")),
        "region": pa.Column("object", checks=pa.Check.isin(sorted(_ALLOWED_REGIONS))),
        "product": pa.Column("object", checks=pa.Check.str_length(min_value=1)),
        "quantity": pa.Column("int64", nullable=False),
        "unit_price": pa.Column(
            "object", checks=pa.Check(_cent_amount, element_wise=True), nullable=False
        ),
        "discount": pa.Column(
            "object", checks=pa.Check(_cent_amount, element_wise=True), nullable=False
        ),
        "order_date": pa.Column("object", checks=pa.Check.str_matches(r"^\d{4}-\d{2}-\d{2}$")),
        "revenue": pa.Column(
            "object", checks=pa.Check(_cent_amount, element_wise=True), nullable=False
        ),
    },
    checks=[
        pa.Check(
            lambda frame: all(
                (quantity * unit_price - discount) == revenue
                for quantity, unit_price, discount, revenue in zip(
                    frame["quantity"], frame["unit_price"], frame["discount"], frame["revenue"]
                )
            ),
            error="Decimal line revenue must match quantity * unit_price - discount",
        ),
        pa.Check(
            lambda frame: all(value >= 0 for value in frame["unit_price"]),
            error="Unit prices must not be negative",
        ),
        pa.Check(
            lambda frame: all(value >= 0 for value in frame["discount"]),
            error="Discounts must not be negative",
        ),
    ],
    coerce=False,
    strict=False,
    unique_column_names=True,
)


def validate_clean_transactions(frame: pd.DataFrame) -> pd.DataFrame:
    """Fail closed; preserve source values, index and full Decimal precision."""
    try:
        return TRANSACTION_SCHEMA.validate(frame, lazy=True)
    except (SchemaError, SchemaErrors, TypeError, ValueError) as exc:
        raise ValueError("Pandera rejected cleaned transaction schema") from exc
