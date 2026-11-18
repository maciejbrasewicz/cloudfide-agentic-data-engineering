"""Safe, vectorized arithmetic over pandas columns (no eval/exec)."""
from __future__ import annotations

import ast
import operator
import re
from decimal import Decimal
from numbers import Number

import pandas as pd

_LABEL = re.compile(r"[A-Za-z_]+\Z")
_OPERATORS = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul}


def add_virtual_column(df: pd.DataFrame, role: str, new_column: str) -> pd.DataFrame:
    """Return a *new* frame with the calculated column, or an empty frame on invalid input.

    Column identifiers use ASCII letters/underscores; supported expressions consist
    solely of referenced columns, +, -, *, optional unary signs and parentheses.
    No arbitrary Python expression, literal, function, or attribute is executed.
    """
    invalid = pd.DataFrame()
    if not isinstance(df, pd.DataFrame) or not isinstance(role, str):
        return invalid
    if not isinstance(new_column, str) or not _LABEL.fullmatch(new_column):
        return invalid
    if df.columns.has_duplicates or new_column in df.columns:
        return invalid
    if not all(isinstance(column, str) and _LABEL.fullmatch(column) for column in df.columns):
        return invalid
    if len(role) > 2048 or not role.strip():
        return invalid

    try:
        syntax = ast.parse(role.strip(), mode="eval")
        if sum(1 for _ in ast.walk(syntax)) > 128:
            return invalid
        referenced: set[str] = set()

        def evaluate(node: ast.AST) -> pd.Series:
            if isinstance(node, ast.Name):
                if node.id not in df.columns:
                    raise ValueError("unknown column")
                referenced.add(node.id)
                return df[node.id]
            if isinstance(node, ast.BinOp) and type(node.op) in _OPERATORS:
                return _OPERATORS[type(node.op)](evaluate(node.left), evaluate(node.right))
            if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub)):
                value = evaluate(node.operand)
                return value if isinstance(node.op, ast.UAdd) else -value
            raise ValueError("unsupported expression")

        # Validate referenced data before arithmetic; string multiplication by an
        # integer is legal in Python but not a meaningful mathematical column.
        nodes = {node.id for node in ast.walk(syntax) if isinstance(node, ast.Name)}
        if not nodes or not nodes.issubset(df.columns):
            return invalid
        for name in nodes:
            values = df[name]
            if not (pd.api.types.is_numeric_dtype(values.dtype) and not pd.api.types.is_bool_dtype(values.dtype)):
                if not values.map(lambda value: isinstance(value, (Number, Decimal)) and not isinstance(value, bool)).all():
                    return invalid
        result = evaluate(syntax.body)
        if not isinstance(result, pd.Series):
            return invalid
        output = df.copy(deep=True)
        output[new_column] = result
        return output
    except (SyntaxError, TypeError, ValueError, ArithmeticError, OverflowError, RecursionError, KeyError):
        return invalid
