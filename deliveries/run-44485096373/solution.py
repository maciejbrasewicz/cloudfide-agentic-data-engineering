"""Safe virtual-column arithmetic for pandas DataFrames."""

from __future__ import annotations

import ast
import re
from collections.abc import Callable
from typing import Any

import pandas as pd


_VALID_LABEL = re.compile(r"[A-Za-z_]+\Z")
_BINARY_OPERATORS: dict[type[ast.operator], Callable[[Any, Any], Any]] = {
    ast.Add: lambda left, right: left + right,
    ast.Sub: lambda left, right: left - right,
    ast.Mult: lambda left, right: left * right,
}


class _InvalidExpression(Exception):
    """Internal marker for expressions outside the supported grammar."""


def _evaluate(node: ast.AST, frame: pd.DataFrame) -> Any:
    """Evaluate only names and the three explicitly allowed binary operators."""
    if isinstance(node, ast.Expression):
        return _evaluate(node.body, frame)
    if isinstance(node, ast.Name):
        if node.id not in frame.columns:
            raise _InvalidExpression("unknown column")
        return frame[node.id]
    if isinstance(node, ast.BinOp) and type(node.op) in _BINARY_OPERATORS:
        left = _evaluate(node.left, frame)
        right = _evaluate(node.right, frame)
        return _BINARY_OPERATORS[type(node.op)](left, right)
    raise _InvalidExpression("unsupported expression node")


def add_virtual_column(
    df: pd.DataFrame, role: str, new_column: str
) -> pd.DataFrame:
    """Return a copy of *df* with a safely calculated column.

    The expression grammar consists solely of existing column names,
    parentheses, and binary ``+``, ``-``, and ``*``. Python's parser supplies
    precedence, but this function never evaluates Python code. Invalid labels,
    syntax, operations, or references produce the assignment's required empty
    DataFrame.
    """
    if not isinstance(df, pd.DataFrame):
        return pd.DataFrame()
    if not isinstance(role, str) or not isinstance(new_column, str):
        return pd.DataFrame()
    if _VALID_LABEL.fullmatch(new_column) is None or not df.columns.is_unique:
        return pd.DataFrame()
    if any(
        not isinstance(label, str) or _VALID_LABEL.fullmatch(label) is None
        for label in df.columns
    ):
        return pd.DataFrame()

    expression = role.strip()
    if not expression:
        return pd.DataFrame()

    try:
        tree = ast.parse(expression, mode="eval")
        value = _evaluate(tree, df)
        result = df.copy(deep=True)
        result[new_column] = value
    except (
        SyntaxError,
        _InvalidExpression,
        ArithmeticError,
        TypeError,
        ValueError,
        KeyError,
    ):
        return pd.DataFrame()
    return result
