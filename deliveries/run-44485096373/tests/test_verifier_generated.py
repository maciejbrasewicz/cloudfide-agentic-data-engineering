"""Independent falsification tests for virtual-column arithmetic."""

import pandas as pd
from pandas.testing import assert_frame_equal

from solution import add_virtual_column


def test_virtual_column_respects_precedence_and_does_not_mutate_input():
    """A compound expression must calculate rows correctly on a copied frame."""
    source = pd.DataFrame(
        {
            "base": [100, -5, 7],
            "quantity": [2, 4, 0],
            "unit_price": [10, 3, 99],
            "discount": [5, 2, -1],
        },
        index=[11, 4, 29],
    )
    pristine = source.copy(deep=True)

    result = add_virtual_column(
        source,
        "base + quantity * unit_price - discount",
        "net_total",
    )

    expected = pristine.copy(deep=True)
    expected["net_total"] = pd.Series([115, 5, 8], index=expected.index)
    assert_frame_equal(result, expected)
    assert result is not source
    assert_frame_equal(source, pristine)
    assert "net_total" not in source.columns
