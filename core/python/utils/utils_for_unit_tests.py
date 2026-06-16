"""Comparison helpers for unit tests."""

from typing import Any, Literal

CompareOperator = Literal[
    "eq",
    "ne",
    "not",
    "in",
    "not_in",
    "lt",
    "le",
    "gt",
    "ge",
]


def _compare_eq(param1: Any, param2: Any) -> bool:
    return param1 == param2


def _compare_ne(param1: Any, param2: Any) -> bool:
    return param1 != param2


def _compare_not(param1: Any, _param2: Any = None) -> bool:
    return not param1


def _compare_in(param1: Any, param2: Any) -> bool:
    return param1 in param2


def _compare_not_in(param1: Any, param2: Any) -> bool:
    return param1 not in param2


def _compare_lt(param1: Any, param2: Any) -> bool:
    return param1 < param2


def _compare_le(param1: Any, param2: Any) -> bool:
    return param1 <= param2


def _compare_gt(param1: Any, param2: Any) -> bool:
    return param1 > param2


def _compare_ge(param1: Any, param2: Any) -> bool:
    return param1 >= param2


def compare(operator: CompareOperator, param1: Any, param2: Any = None) -> bool:
    """Compare values using a named operator.

    Operators: ``eq`` (==), ``ne`` (!=), ``not``, ``in``, ``not_in``,
    ``lt``, ``le``, ``gt``, ``ge``.

    ``not`` only uses ``param1``.
    """
    compare_func = globals()[f"_compare_{operator}"]
    return compare_func(param1, param2)
