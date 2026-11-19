"""Independent falsification tests for virtual-column arithmetic."""

from decimal import Decimal

import pandas as pd
from pandas.testing import assert_frame_equal

from solution import add_virtual_column


def test_revenue_expression_respects_precedence_decimal_math_and_input_immutability():
    """The pipeline's three-term formula must calculate real rows without mutation."""
    source = pd.DataFrame(
        {
            "quantity": [2, -3, 4],
            "unit_price": [Decimal("10.25"), Decimal("7.10"), Decimal("0.30")],
            "discount": [Decimal("0.50"), Decimal("1.20"), Decimal("0.10")],
        },
        index=[101, 205, 999],
    )
    before = source.copy(deep=True)

    actual = add_virtual_column(
        source, "quantity * unit_price - discount", "net_revenue"
    )

    expected = before.copy(deep=True)
    expected["net_revenue"] = [
        Decimal("20.00"),
        Decimal("-22.50"),
        Decimal("1.10"),
    ]
    assert_frame_equal(actual, expected)
    assert_frame_equal(source, before)
    assert actual is not source


def test_invalid_operator_fails_closed_without_mutating_input():
    source = pd.DataFrame({"left": [8, 9], "right": [2, 3]})
    before = source.copy(deep=True)

    actual = add_virtual_column(source, "left / right", "quotient")

    assert actual.empty
    assert_frame_equal(source, before)
