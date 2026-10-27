"""Tests for workarea.workarea_rule module."""

from pathlib import Path

from workarea.rule_action import RuleAction
from workarea.workarea_rule import WorkareaRule, WorkareaRules


def test_defaults() -> None:
    rule = WorkareaRule(source=Path("core"), action=RuleAction.LINK)

    assert rule.source == Path("core")
    assert rule.target is None
    assert rule.recursive is True
    assert rule.includes == []
    assert rule.excludes == []
    assert rule.placeholders == []


def test_target_path_defaults_to_source_when_target_is_none() -> None:
    rule = WorkareaRule(source=Path("core"), action=RuleAction.LINK)

    assert rule.target_path() == Path("core")


def test_target_path_uses_target_when_set() -> None:
    rule = WorkareaRule(
        source=Path("core"), target=Path("other"), action=RuleAction.COPY
    )

    assert rule.target_path() == Path("other")


def test_round_trips_through_json() -> None:
    rule = WorkareaRule(
        source=Path("core"),
        target=Path("work/core"),
        action=RuleAction.COPY,
        recursive=False,
        includes=["*.py"],
        excludes=["*.pyc"],
        placeholders=["__KBOT_HOME__"],
    )

    loaded = WorkareaRule.from_json(rule.to_json(indent=None))

    assert loaded == rule


class TestWorkareaRules:
    def test_iterates_over_rules(self) -> None:
        first = WorkareaRule(source=Path("a"), action=RuleAction.LINK)
        second = WorkareaRule(source=Path("b"), action=RuleAction.COPY)
        rules = WorkareaRules([first, second])

        assert list(rules) == [first, second]

    def test_len(self) -> None:
        first = WorkareaRule(source=Path("a"), action=RuleAction.LINK)
        rules = WorkareaRules([first])

        assert len(rules) == 1

    def test_getitem(self) -> None:
        first = WorkareaRule(source=Path("a"), action=RuleAction.LINK)
        second = WorkareaRule(source=Path("b"), action=RuleAction.COPY)
        rules = WorkareaRules([first, second])

        assert rules[0] == first
        assert rules[1] == second

    def test_from_json_builds_list_of_rules(self) -> None:
        payload = (
            '[{"source": "core", "action": "link"}, '
            '{"source": "rest", "action": "copy", "recursive": false}]'
        )

        rules = WorkareaRules.from_json(payload)

        assert len(rules) == 2
        assert rules[0].source == Path("core")
        assert rules[0].action == RuleAction.LINK
        assert rules[1].recursive is False
