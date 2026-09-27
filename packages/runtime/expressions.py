"""A minimal, safe expression language for ALO `when` and `expression` fields.

Draft 0.1 does not freeze an expression language (see docs/spec.md, section 8).
This module implements a reference evaluator: a small subset of Python
expression syntax, interpreted by walking a whitelisted AST rather than by
calling ``eval``. Only literals, boolean/comparison/arithmetic operators, and
dotted identifier lookups against a nested-mapping context are supported.
"""

from __future__ import annotations

import ast
from collections.abc import Mapping
from typing import Any


class ExpressionError(ValueError):
    """Raised when an expression is invalid or cannot be evaluated."""


_ALLOWED_BOOL_OPS = (ast.And, ast.Or)
_ALLOWED_UNARY_OPS = (ast.Not, ast.USub, ast.UAdd)
_ALLOWED_BIN_OPS = (ast.Add, ast.Sub, ast.Mult, ast.Div, ast.FloorDiv, ast.Mod, ast.Pow)
_ALLOWED_COMPARE_OPS = (
    ast.Eq,
    ast.NotEq,
    ast.Lt,
    ast.LtE,
    ast.Gt,
    ast.GtE,
    ast.In,
    ast.NotIn,
)


def evaluate(expression: str, context: Mapping[str, Any]) -> Any:
    """Evaluate ``expression`` against ``context`` and return its value."""

    try:
        tree = ast.parse(expression, mode="eval")
    except SyntaxError as error:
        raise ExpressionError(f"invalid expression: {expression!r}: {error}") from error
    return _eval(tree.body, context, expression)


def _eval(node: ast.AST, context: Mapping[str, Any], expression: str) -> Any:
    if isinstance(node, ast.Constant):
        if isinstance(node.value, (str, int, float, bool)) or node.value is None:
            return node.value
        raise ExpressionError(f"unsupported literal in expression: {expression!r}")

    if isinstance(node, ast.Name):
        if node.id in context:
            return context[node.id]
        raise ExpressionError(f"unknown identifier {node.id!r} in expression: {expression!r}")

    if isinstance(node, ast.Attribute):
        base = _eval(node.value, context, expression)
        if isinstance(base, Mapping) and node.attr in base:
            return base[node.attr]
        raise ExpressionError(
            f"unknown attribute {node.attr!r} in expression: {expression!r}"
        )

    if isinstance(node, ast.BoolOp) and isinstance(node.op, _ALLOWED_BOOL_OPS):
        values = (_eval(value, context, expression) for value in node.values)
        if isinstance(node.op, ast.And):
            result: Any = True
            for value in values:
                result = value
                if not value:
                    return result
            return result
        result = False
        for value in values:
            result = value
            if value:
                return result
        return result

    if isinstance(node, ast.UnaryOp) and isinstance(node.op, _ALLOWED_UNARY_OPS):
        operand = _eval(node.operand, context, expression)
        if isinstance(node.op, ast.Not):
            return not operand
        if isinstance(node.op, ast.USub):
            return -operand
        return +operand

    if isinstance(node, ast.BinOp) and isinstance(node.op, _ALLOWED_BIN_OPS):
        left = _eval(node.left, context, expression)
        right = _eval(node.right, context, expression)
        return _apply_bin_op(node.op, left, right, expression)

    if isinstance(node, ast.Compare):
        left = _eval(node.left, context, expression)
        for op, comparator in zip(node.ops, node.comparators):
            if not isinstance(op, _ALLOWED_COMPARE_OPS):
                raise ExpressionError(
                    f"unsupported comparison in expression: {expression!r}"
                )
            right = _eval(comparator, context, expression)
            if not _apply_compare(op, left, right):
                return False
            left = right
        return True

    if isinstance(node, (ast.List, ast.Tuple)):
        return [_eval(element, context, expression) for element in node.elts]

    raise ExpressionError(
        f"unsupported syntax {type(node).__name__} in expression: {expression!r}"
    )


def _apply_bin_op(op: ast.operator, left: Any, right: Any, expression: str) -> Any:
    if isinstance(op, ast.Add):
        return left + right
    if isinstance(op, ast.Sub):
        return left - right
    if isinstance(op, ast.Mult):
        return left * right
    if isinstance(op, ast.Div):
        return left / right
    if isinstance(op, ast.FloorDiv):
        return left // right
    if isinstance(op, ast.Mod):
        return left % right
    if isinstance(op, ast.Pow):
        return left**right
    raise ExpressionError(f"unsupported operator in expression: {expression!r}")


def _apply_compare(op: ast.cmpop, left: Any, right: Any) -> bool:
    if isinstance(op, ast.Eq):
        return left == right
    if isinstance(op, ast.NotEq):
        return left != right
    if isinstance(op, ast.Lt):
        return left < right
    if isinstance(op, ast.LtE):
        return left <= right
    if isinstance(op, ast.Gt):
        return left > right
    if isinstance(op, ast.GtE):
        return left >= right
    if isinstance(op, ast.In):
        return left in right
    if isinstance(op, ast.NotIn):
        return left not in right
    raise ExpressionError("unsupported comparison operator")
