"""Safe creation of calculated pandas columns."""

from __future__ import annotations

import ast
import re

import pandas as pd

_IDENTIFIER = re.compile(r"^[A-Za-z_]+$")
_ALLOWED_BINARY_OPERATORS = (ast.Add, ast.Sub, ast.Mult)


def _valid_label(value: object) -> bool:
    return isinstance(value, str) and _IDENTIFIER.fullmatch(value) is not None


def _valid_expression(node: ast.AST, columns: set[str]) -> bool:
    """Accept only known names joined by the three supported binary operators."""
    if isinstance(node, ast.Name):
        return _valid_label(node.id) and node.id in columns
    if isinstance(node, ast.BinOp) and isinstance(node.op, _ALLOWED_BINARY_OPERATORS):
        return _valid_expression(node.left, columns) and _valid_expression(
            node.right, columns
        )
    return False


def _calculate(node: ast.AST, frame: pd.DataFrame) -> pd.Series:
    """Evaluate an already validated arithmetic AST without eval/exec."""
    if isinstance(node, ast.Name):
        return frame[node.id]
    if isinstance(node, ast.BinOp):
        left = _calculate(node.left, frame)
        right = _calculate(node.right, frame)
        if isinstance(node.op, ast.Add):
            return left + right
        if isinstance(node.op, ast.Sub):
            return left - right
        if isinstance(node.op, ast.Mult):
            return left * right
    raise ValueError("unsupported expression")


def add_virtual_column(
    df: pd.DataFrame, role: str, new_column: str
) -> pd.DataFrame:
    """Return a copied DataFrame with a safely calculated column.

    Valid expressions contain existing column names and binary ``+``, ``-`` or
    ``*`` operations only. Any invalid or ambiguous input returns a new empty
    DataFrame. The input frame is never mutated.
    """
    if not isinstance(df, pd.DataFrame) or not isinstance(role, str):
        return pd.DataFrame()

    labels = list(df.columns)
    if (
        not _valid_label(new_column)
        or any(not _valid_label(label) for label in labels)
        or len(set(labels)) != len(labels)
        or new_column in labels
    ):
        return pd.DataFrame()

    expression_text = role.strip()
    if not expression_text:
        return pd.DataFrame()
    try:
        expression = ast.parse(expression_text, mode="eval")
    except (SyntaxError, TypeError, ValueError):
        return pd.DataFrame()

    if not _valid_expression(expression.body, set(labels)):
        return pd.DataFrame()

    result = df.copy(deep=True)
    try:
        result[new_column] = _calculate(expression.body, result)
    except (ArithmeticError, KeyError, TypeError, ValueError):
        return pd.DataFrame()
    return result
