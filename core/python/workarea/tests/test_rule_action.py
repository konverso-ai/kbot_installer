"""Tests for workarea.rule_action module."""

from workarea.rule_action import RuleAction


def test_members_and_values() -> None:
    assert RuleAction.LINK == "link"
    assert RuleAction.COPY == "copy"
    assert RuleAction.IGNORE == "ignore"


def test_is_str_subclass() -> None:
    assert isinstance(RuleAction.LINK, str)


def test_constructed_from_value() -> None:
    assert RuleAction("copy") is RuleAction.COPY
