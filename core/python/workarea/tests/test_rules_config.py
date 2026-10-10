"""Tests for workarea.rules_config."""

import json
from pathlib import Path

import pytest

from workarea.rule_action import RuleAction
from workarea.rules_config import _resolve_default_rules_path, load_default_rules
from workarea.utils import apply_rules


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

    def test_entry_point_scripts_are_real_copies_not_symlinks(self, tmp_path: Path) -> None:
        """Regression: RunBot.py/Learn.py/Load.py must end up as real files.

        The `core/python` rules link every `.py` file, then separately copy
        RunBot.py/Learn.py/Load.py so these entry-point scripts are real
        files (running them as a symlink resolves `sys.path[0]` to the
        product's own source dir instead of the merged workarea, breaking
        imports of files only added by other products, e.g.
        `common/connection/ev_global_auth.py`). `apply_rule` skips a rule for
        any target that already exists, so if the general link rule isn't
        told to exclude these filenames, it creates the symlink first and the
        later copy rule silently never runs.
        """
        product_root = tmp_path / "product"
        core_python = product_root / "core" / "python"
        core_python.mkdir(parents=True)
        (core_python / "Bot.py").write_text("# regular module\n")
        for name in ("RunBot.py", "Learn.py", "Load.py"):
            (core_python / name).write_text(f"# {name} entry point\n")

        work_root = tmp_path / "work"

        apply_rules(
            product_root=product_root,
            work_root=work_root,
            rules=load_default_rules(),
            runtime_variables={},
        )

        assert (work_root / "core" / "python" / "Bot.py").is_symlink()
        for name in ("RunBot.py", "Learn.py", "Load.py"):
            target = work_root / "core" / "python" / name
            assert target.is_file()
            assert not target.is_symlink()

    def test_entry_point_copies_follow_product_changes(self, tmp_path: Path) -> None:
        """Regression: re-applying the rules must refresh outdated entry-point copies.

        `linkproduct.sh` re-runs the layout after `make` updated the product
        sources; a stale workarea `RunBot.py` copy must pick up the change.
        """
        product_root = tmp_path / "product"
        core_python = product_root / "core" / "python"
        core_python.mkdir(parents=True)
        run_bot = core_python / "RunBot.py"
        run_bot.write_text("# old\n")
        work_root = tmp_path / "work"
        rules = load_default_rules()

        apply_rules(product_root=product_root, work_root=work_root, rules=rules, runtime_variables={})
        run_bot.write_text("# new\n")
        apply_rules(product_root=product_root, work_root=work_root, rules=rules, runtime_variables={})

        target = work_root / "core" / "python" / "RunBot.py"
        assert not target.is_symlink()
        assert target.read_text() == "# new\n"

    def test_rc_kbot_is_rendered_copy_following_product_changes(self, tmp_path: Path) -> None:
        """Regression: `bin/rc/kbot` must be a rendered copy kept in sync with the product."""
        product_root = tmp_path / "product"
        rc_dir = product_root / "bin" / "rc"
        rc_dir.mkdir(parents=True)
        rc_kbot = rc_dir / "kbot"
        rc_kbot.write_text("home=__KBOT_HOME__ user=__KBOT_USER__\n")
        work_root = tmp_path / "work"
        rules = load_default_rules()
        variables = {"__KBOT_HOME__": "/work", "__KBOT_USER__": "bob"}

        apply_rules(product_root=product_root, work_root=work_root, rules=rules, runtime_variables=variables)
        target = work_root / "bin" / "rc" / "kbot"
        assert not target.is_symlink()
        assert target.read_text() == "home=/work user=bob\n"

        rc_kbot.write_text("v2 home=__KBOT_HOME__\n")
        apply_rules(product_root=product_root, work_root=work_root, rules=rules, runtime_variables=variables)
        assert target.read_text() == "v2 home=/work\n"

    def test_conf_layout_matches_legacy_setup_conf(self, tmp_path: Path) -> None:
        """Regression: product `conf` entries are laid out like legacy `_SetupConf`.

        Whitelisted `conf` subdirectories are mirrored with per-file symlinks,
        whitelisted top-level files (including globs) are symlinked, and every
        other `conf` entry (e.g. `kbot.conf`, `entities/`) stays in the product,
        read in place through `products/`. The product root `license.key` is
        symlinked at the work root, where `Bot.GetLicenseFile` looks first.
        """
        product_root = tmp_path / "product"
        conf = product_root / "conf"
        (conf / "classifiers" / "nested").mkdir(parents=True)
        (conf / "classifiers" / "nested" / "c.json").write_text("{}\n")
        (conf / "entities").mkdir()
        (conf / "entities" / "e.conf").write_text("# entity\n")
        for name in ("editable_files_kbot.json", "km_tests.conf", "kbot.conf", "httpd.conf"):
            (conf / name).write_text(f"# {name}\n")
        (product_root / "license.key").write_text("key\n")

        work_root = tmp_path / "work"

        apply_rules(
            product_root=product_root,
            work_root=work_root,
            rules=load_default_rules(),
            runtime_variables={},
        )

        work_conf = work_root / "conf"
        classifier = work_conf / "classifiers" / "nested" / "c.json"
        assert classifier.is_symlink()
        assert not (work_conf / "classifiers").is_symlink()
        assert (work_conf / "editable_files_kbot.json").is_symlink()
        assert (work_conf / "km_tests.conf").is_symlink()
        assert not (work_conf / "kbot.conf").exists()
        assert not (work_conf / "httpd.conf").exists()
        assert not (work_conf / "entities").exists()

        license_key = work_root / "license.key"
        assert license_key.is_symlink()
        assert license_key.resolve() == (product_root / "license.key").resolve()


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
