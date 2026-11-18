from decimal import Decimal

import pandas as pd
import pytest

from solution import add_virtual_column


def test_operator_precedence_and_parentheses():
    df = pd.DataFrame({"a": [2, 3], "b": [4, 5], "c": [6, 7]})
    assert add_virtual_column(df, "a + b*c", "total").total.tolist() == [26, 38]
    assert add_virtual_column(df, "(a+b)*c", "total").total.tolist() == [36, 56]


def test_decimal_money_and_immutability():
    df = pd.DataFrame({"quantity": [2], "unit_price": [Decimal("0.10")], "discount": [Decimal("0.01")]})
    result = add_virtual_column(df, "quantity * unit_price - discount", "revenue")
    assert result.revenue.iloc[0] == Decimal("0.19")
    assert "revenue" not in df.columns


@pytest.mark.parametrize("expression", [
    "a / b", "a ** b", "a and b", "a[0]", "a.__class__",
    "__import__('os')", "a + unknown", "1 + 2", "a + 1", "",
])
def test_disallowed_expressions_return_empty(expression):
    df = pd.DataFrame({"a": [1], "b": [2]})
    assert add_virtual_column(df, expression, "out").empty


@pytest.mark.parametrize("columns", [["bad1", "good"], ["good", "bad name"], ["good", "good"]])
def test_bad_column_labels_return_empty(columns):
    df = pd.DataFrame([[1, 2]], columns=columns)
    assert add_virtual_column(df, "good + good", "result").empty


def test_bad_output_name_and_collision():
    df = pd.DataFrame({"a": [1], "b": [2]})
    assert add_virtual_column(df, "a + b", "new2").empty
    assert add_virtual_column(df, "a + b", "a").empty


def test_string_repetition_is_not_arithmetic():
    df = pd.DataFrame({"a": ["x"], "b": [3]})
    assert add_virtual_column(df, "a * b", "result").empty


def test_dataframe_index_and_dtype_unchanged():
    df = pd.DataFrame({"a": [1, 2], "b": [3, 4]}, index=[5, 9])
    result = add_virtual_column(df, "a-b", "delta")
    assert result.index.tolist() == [5, 9]
    assert result["a"].dtype == df["a"].dtype
    assert df.columns.tolist() == ["a", "b"]
