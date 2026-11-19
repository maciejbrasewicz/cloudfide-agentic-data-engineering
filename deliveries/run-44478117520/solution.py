"""Safe arithmetic virtual columns for pandas DataFrames."""

from __future__ import annotations

import ast
import re
from typing import Any

import pandas as pd


_LABEL = re.compile(r"^[A-Za-z_]+$")
_ALLOWED_BINARY_OPERATORS = (ast.Add, ast.Sub, ast.Mult)


class _InvalidExpression(ValueError):
    """Raised internally when an expression is outside the supported grammar."""


def _evaluate(node: ast.AST, frame: pd.DataFrame) -> Any:
    """Evaluate a restricted arithmetic syntax tree against ``frame``."""
    if isinstance(node, ast.Expression):
        return _evaluate(node.body, frame)
    if isinstance(node, ast.Name):
        if not _LABEL.fullmatch(node.id) or node.id not in frame.columns:
            raise _InvalidExpression("unknown or invalid column")
        return frame[node.id]
    if isinstance(node, ast.BinOp) and isinstance(node.op, _ALLOWED_BINARY_OPERATORS):
        left = _evaluate(node.left, frame)
        right = _evaluate(node.right, frame)
        if isinstance(node.op, ast.Add):
            return left + right
        if isinstance(node.op, ast.Sub):
            return left - right
        return left * right
    raise _InvalidExpression("only names, parentheses, +, - and * are supported")


def add_virtual_column(
    df: pd.DataFrame, role: str, new_column: str
) -> pd.DataFrame:
    """Return a copy of ``df`` with a calculated column, or an empty frame.

    Expressions may contain existing column names, parentheses, and the binary
    operators ``+``, ``-`` and ``*``. They are parsed and walked as a restricted
    AST; no dynamic evaluation is used. Invalid labels, syntax, references, or
    operations return an empty DataFrame without modifying the input.
    """
    if not isinstance(df, pd.DataFrame):
        return pd.DataFrame()
    if not isinstance(role, str) or not isinstance(new_column, str):
        return pd.DataFrame()
    if not _LABEL.fullmatch(new_column) or new_column in df.columns:
        return pd.DataFrame()
    if not df.columns.is_unique or any(
        not isinstance(label, str) or not _LABEL.fullmatch(label)
        for label in df.columns
    ):
        return pd.DataFrame()

    expression = role.strip()
    if not expression:
        return pd.DataFrame()

    try:
        tree = ast.parse(expression, mode="eval")
        result = _evaluate(tree, df)
        if not isinstance(result, pd.Series) or not result.index.equals(df.index):
            raise _InvalidExpression("expression did not produce an aligned column")
        output = df.copy(deep=True)
        output[new_column] = result
        return output
    except (
        SyntaxError,
        _InvalidExpression,
        ArithmeticError,
        TypeError,
        ValueError,
    ):
        return pd.DataFrame()
