"""Tests for workarea.workarea module."""

from pathlib import Path

import pytest
from pydantic import ValidationError
from workarea.rule_action import RuleAction
from workarea.workarea import Workarea
from workarea.workarea_rule import WorkareaRule


def test_builds_with_required_fields_only() -> None:
    """rules defaults to an empty list when not provided."""
    workarea = Workarea(
        installer_root=Path("/installer"),
        work_root=Path("/work"),
        products=[Path("kbot"), Path("snow")],
    )

    assert workarea.installer_root == Path("/installer")
    assert workarea.work_root == Path("/work")
    assert workarea.products == [Path("kbot"), Path("snow")]
    assert workarea.rules == []


def test_builds_with_rules() -> None:
    rule = WorkareaRule(source=Path("core"), action=RuleAction.LINK)
    workarea = Workarea(
        installer_root=Path("/installer"),
        work_root=Path("/work"),
        products=[],
        rules=[rule],
    )

    assert workarea.rules == [rule]


@pytest.mark.parametrize("missing_field", ["installer_root", "work_root", "products"])
def test_missing_required_field_raises(missing_field: str) -> None:
    kwargs = {
        "installer_root": Path("/installer"),
        "work_root": Path("/work"),
        "products": [],
    }
    del kwargs[missing_field]

    with pytest.raises(ValidationError):
        Workarea(**kwargs)


def test_coerces_string_paths() -> None:
    workarea = Workarea(
        installer_root="/installer",
        work_root="/work",
        products=["kbot"],
    )

    assert workarea.installer_root == Path("/installer")
    assert workarea.work_root == Path("/work")
    assert workarea.products == [Path("kbot")]
