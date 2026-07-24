"""Comparison helpers for unit tests."""

from collections.abc import Container
from typing import Literal, Protocol, TypeVar

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

T = TypeVar("T")


class Comparable(Protocol):
    """Protocol for values supporting rich ordering comparisons."""

    def __lt__(self, other: object) -> bool:
        """Return whether self is less than other."""

    def __le__(self, other: object) -> bool:
        """Return whether self is less than or equal to other."""

    def __gt__(self, other: object) -> bool:
        """Return whether self is greater than other."""

    def __ge__(self, other: object) -> bool:
        """Return whether self is greater than or equal to other."""


C = TypeVar("C", bound=Comparable)


def _compare_eq(param1: object, param2: object) -> bool:
    return param1 == param2


def _compare_ne(param1: object, param2: object) -> bool:
    return param1 != param2


def _compare_not(param1: object, _param2: object = None) -> bool:
    return not param1


def _compare_in(param1: T, param2: Container[T]) -> bool:
    return param1 in param2


def _compare_not_in(param1: T, param2: Container[T]) -> bool:
    return param1 not in param2


def _compare_lt(param1: C, param2: C) -> bool:
    return param1 < param2


def _compare_le(param1: C, param2: C) -> bool:
    return param1 <= param2


def _compare_gt(param1: C, param2: C) -> bool:
    return param1 > param2


def _compare_ge(param1: C, param2: C) -> bool:
    return param1 >= param2


def compare(operator: CompareOperator, param1: object, param2: object = None) -> bool:
    """Compare values using a named operator.

    Operators: ``eq`` (==), ``ne`` (!=), ``not``, ``in``, ``not_in``,
    ``lt``, ``le``, ``gt``, ``ge``.

    ``not`` only uses ``param1``.
    """
    compare_func = globals()[f"_compare_{operator}"]
    return compare_func(param1, param2)
