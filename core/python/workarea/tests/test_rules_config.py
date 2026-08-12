"""Tests for workarea.rules_config."""

import json
from pathlib import Path

import pytest

from workarea.rule_action import RuleAction
from workarea.rules_config import _resolve_default_rules_path, load_default_rules


class TestLoadDefaultRules:
    def test_loads_rules_from_explicit_path(self, tmp_path: Path) -> None:
        rules_path = tmp_path / "rules.json"
        rules_path.write_text(
            json.dumps(
                [
                    {"source": "core/python", "action": "link"},
                    {"source": "rest/api", "action": "link"},
                ]
            )
        )

        rules = load_default_rules(rules_path)

        assert [str(rule.source) for rule in rules] == ["core/python", "rest/api"]
        assert all(rule.action == RuleAction.LINK for rule in rules)

    def test_defaults_to_repository_conf_rules_json(self) -> None:
        """Regression: production code must resolve the real conf/rules.json.

        `cli.commands._build_workarea` relies on `load_default_rules()` (no
        explicit path) to find the packaged/repo `conf/rules.json`; if this
        resolution silently returned no rules, workarea rules (e.g. the
        `core/python`/`rest/api` links) would never be applied.
        """
        rules = load_default_rules()

        sources = {str(rule.source) for rule in rules}
        assert "core/python" in sources
        assert "rest/api" in sources


class TestResolveDefaultRulesPath:
    def test_finds_dev_layout_rules_json(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        repo_root = tmp_path / "repo"
        module_path = repo_root / "core" / "python" / "workarea" / "rules_config.py"
        module_path.parent.mkdir(parents=True)
        module_path.write_text("")
        conf_dir = repo_root / "conf"
        conf_dir.mkdir()
        rules_file = conf_dir / "rules.json"
        rules_file.write_text("[]")

        monkeypatch.setattr(
            "workarea.rules_config.__file__", str(module_path)
        )

        assert _resolve_default_rules_path() == rules_file

    def test_finds_installed_layout_rules_json(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        venv_root = tmp_path / "site-packages"
        module_path = venv_root / "core" / "python" / "workarea" / "rules_config.py"
        module_path.parent.mkdir(parents=True)
        module_path.write_text("")
        installed_conf = venv_root / "installer" / "kbot_installer" / "conf"
        installed_conf.mkdir(parents=True)
        rules_file = installed_conf / "rules.json"
        rules_file.write_text("[]")

        monkeypatch.setattr(
            "workarea.rules_config.__file__", str(module_path)
        )

        assert _resolve_default_rules_path() == rules_file

    def test_raises_when_no_rules_json_found(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        module_path = tmp_path / "isolated" / "rules_config.py"
        module_path.parent.mkdir(parents=True)
        module_path.write_text("")

        monkeypatch.setattr(
            "workarea.rules_config.__file__", str(module_path)
        )

        with pytest.raises(FileNotFoundError):
            _resolve_default_rules_path()
