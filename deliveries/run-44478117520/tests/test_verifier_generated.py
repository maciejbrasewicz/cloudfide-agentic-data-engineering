"""Independent falsification tests for virtual-column arithmetic."""

import pandas as pd
from pandas.testing import assert_frame_equal

from solution import add_virtual_column


def test_precedence_parentheses_numeric_result_and_input_immutability():
    """Mixed operations must be evaluated correctly without mutating the input."""
    source = pd.DataFrame(
        {
            "alpha": [2, -3],
            "beta": [4, 5],
            "gamma": [1, 2],
        },
        index=pd.Index(["first", "second"], name="row_id"),
    )
    original = source.copy(deep=True)

    actual = add_virtual_column(
        source,
        "alpha + beta * gamma - (alpha * gamma)",
        "computed_value",
    )

    expected = original.copy(deep=True)
    expected["computed_value"] = pd.Series(
        [4, 13], index=expected.index, dtype="int64"
    )

    assert_frame_equal(actual, expected)
    assert_frame_equal(source, original)
    assert actual is not source
