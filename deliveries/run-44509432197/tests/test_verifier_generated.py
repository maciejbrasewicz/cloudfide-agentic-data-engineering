import pandas as pd
import pandas.testing as pdt

from solution import add_virtual_column


def test_virtual_column_respects_precedence_numeric_values_and_input_immutability():
    source = pd.DataFrame(
        {
            "base": [10, -4, 7],
            "units": [3, 5, -2],
            "price": [4, -2, 6],
            "discount": [1, 3, -5],
        },
        index=[11, 4, 19],
    )
    before = source.copy(deep=True)

    actual = add_virtual_column(
        source, "base + units * price - discount", "net_value"
    )
    expected = before.copy(deep=True)
    expected["net_value"] = pd.Series([21, -17, 0], index=before.index)

    pdt.assert_frame_equal(actual, expected)
    pdt.assert_frame_equal(source, before)
    assert actual is not source

    # The returned frame must not share writable numeric column storage with input.
    actual.loc[11, "base"] = 999
    assert source.loc[11, "base"] == 10


def test_invalid_expression_fails_closed_without_mutating_input():
    source = pd.DataFrame({"left": [2, 3], "right": [5, 7]})
    before = source.copy(deep=True)

    actual = add_virtual_column(source, "left / right", "ratio")

    assert isinstance(actual, pd.DataFrame)
    assert actual.empty
    pdt.assert_frame_equal(source, before)
