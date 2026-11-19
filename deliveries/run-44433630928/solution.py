"""Safe virtual-column construction for pandas DataFrames."""

from __future__ import annotations

import ast
import re
from typing import Final

import pandas as pd


_VALID_LABEL: Final = re.compile(r"^[A-Za-z_]+$")
_ALLOWED_OPERATORS: Final = (ast.Add, ast.Sub, ast.Mult)


class _InvalidExpression(ValueError):
    """Internal marker for input outside the supported expression grammar."""


def _evaluate(node: ast.AST, frame: pd.DataFrame) -> pd.Series:
    """Interpret the restricted expression tree without eval or exec."""
    if isinstance(node, ast.Expression):
        return _evaluate(node.body, frame)
    if isinstance(node, ast.Name):
        if node.id not in frame.columns:
            raise _InvalidExpression("unknown column")
        return frame[node.id]
    if isinstance(node, ast.BinOp) and isinstance(node.op, _ALLOWED_OPERATORS):
        left = _evaluate(node.left, frame)
        right = _evaluate(node.right, frame)
        if isinstance(node.op, ast.Add):
            return left + right
        if isinstance(node.op, ast.Sub):
            return left - right
        return left * right
    raise _InvalidExpression("unsupported syntax")


def add_virtual_column(
    df: pd.DataFrame, role: str, new_column: str
) -> pd.DataFrame:
    """Return a copied frame with a safely calculated additional column.

    Expressions may contain existing column names, parentheses, and the binary
    operators ``+``, ``-`` and ``*``. Any invalid input or failed calculation
    returns a new empty DataFrame.
    """
    try:
        if not isinstance(df, pd.DataFrame):
            raise _InvalidExpression("df must be a DataFrame")
        if not isinstance(role, str) or not isinstance(new_column, str):
            raise _InvalidExpression("role and new_column must be strings")
        if not _VALID_LABEL.fullmatch(new_column):
            raise _InvalidExpression("invalid new column")
        if new_column in df.columns or not df.columns.is_unique:
            raise _InvalidExpression("colliding or duplicate column")
        if any(
            not isinstance(label, str) or not _VALID_LABEL.fullmatch(label)
            for label in df.columns
        ):
            raise _InvalidExpression("invalid source column")

        tree = ast.parse(role.strip(), mode="eval")
        calculated = _evaluate(tree, df)
        if not isinstance(calculated, pd.Series):
            raise _InvalidExpression("expression did not produce a column")

        result = df.copy(deep=True)
        result[new_column] = calculated
        return result
    except Exception:
        # This function's specified error result is an empty DataFrame. The
        # restricted interpreter above never executes calls or arbitrary code.
        return pd.DataFrame()
