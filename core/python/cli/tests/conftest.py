"""Shared fixtures and steps for the pytest-bdd acceptance scenarios of the PO sheets KBOT-INST-0N."""

import re

import pytest

from cli.tests.bdd.steps_common import *  # noqa: F403
from cli.tests.bdd.environment import env  # noqa: F401

# Traceability tags of the PO sheets: they carry no pytest behaviour.
_TRACE_TAG = re.compile(r"^(AC-|BR-|since-|until-)")


def pytest_configure(config: pytest.Config) -> None:
    """Declare the feature tags that change how a scenario runs."""
    config.addinivalue_line("markers", "manual: scenario of a PO sheet that is checked by hand")
    config.addinivalue_line("markers", "known-defect: scenario failing on a defect recorded as an open question")


def pytest_bdd_apply_tag(tag: str, function: object) -> bool | None:
    """Drop the traceability tags; other tags become markers (the default behaviour)."""
    return True if _TRACE_TAG.match(tag) else None


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    """Skip @manual scenarios and expect @known-defect ones (scenario or Examples tag) to fail."""
    for item in items:
        if item.get_closest_marker("manual"):
            item.add_marker(pytest.mark.skip(reason="manual scenario"))
        if item.get_closest_marker("known-defect"):
            item.add_marker(pytest.mark.xfail(strict=True, reason="open question on the PO sheet"))
