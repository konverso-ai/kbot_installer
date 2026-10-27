"""Tests for workarea.utils module."""

import json
from pathlib import Path

import pytest
from workarea.rule_action import RuleAction
from workarea.utils import (
    apply_rule,
    apply_rules,
    cleanup_unused_tests_dir,
    clear_workarea,
    copy_source,
    is_broken_symlink,
    iter_sources,
    link_source,
    matches_pattern,
    render_variables,
    repair_broken_links,
    setup_drf_spectacular_static,
    setup_drf_yasg_static,
    setup_kbot_conf,
    setup_products,
    setup_products_registry,
    setup_runtime_dirs,
    should_keep,
)
from workarea.workarea_rule import WorkareaRule


def _rule(**overrides: object) -> WorkareaRule:
    defaults: dict[str, object] = {"source": Path("core"), "action": RuleAction.LINK}
    defaults.update(overrides)
    return WorkareaRule(**defaults)


class TestShouldKeep:
    def test_keeps_when_no_includes_or_excludes(self, tmp_path: Path) -> None:
        path = tmp_path / "a" / "b.py"
        assert should_keep(path, tmp_path, _rule()) is True

    def test_rejects_when_not_matching_includes(self, tmp_path: Path) -> None:
        path = tmp_path / "b.txt"
        rule = _rule(includes=["*.py"])
        assert should_keep(path, tmp_path, rule) is False

    def test_keeps_when_matching_includes(self, tmp_path: Path) -> None:
        path = tmp_path / "b.py"
        rule = _rule(includes=["*.py"])
        assert should_keep(path, tmp_path, rule) is True

    def test_rejects_when_matching_excludes(self, tmp_path: Path) -> None:
        path = tmp_path / "b.pyc"
        rule = _rule(excludes=["*.pyc"])
        assert should_keep(path, tmp_path, rule) is False

    def test_includes_take_precedence_before_excludes_are_checked(
        self, tmp_path: Path
    ) -> None:
        path = tmp_path / "sub" / "b.py"
        rule = _rule(includes=["sub/*.py"], excludes=["*.pyc"])
        assert should_keep(path, tmp_path, rule) is True

    def test_double_star_pattern_matches_top_level_file(self, tmp_path: Path) -> None:
        """Regression: `**/*.py` must also match files directly under root.

        Plain `fnmatch` (unlike shell/gitignore globs) requires a literal `/`
        before `*.py` for a `**/*.py` pattern, so a top-level file like
        `core/python/Bot.py` (relative path `Bot.py`, no `/`) was silently
        excluded from every rule using `**/...` includes.
        """
        path = tmp_path / "Bot.py"
        rule = _rule(includes=["**/*.py"])
        assert should_keep(path, tmp_path, rule) is True

    def test_double_star_pattern_still_matches_nested_file(self, tmp_path: Path) -> None:
        path = tmp_path / "sub" / "Bot.py"
        rule = _rule(includes=["**/*.py"])
        assert should_keep(path, tmp_path, rule) is True


class TestMatchesPattern:
    def test_double_star_matches_zero_directories(self) -> None:
        assert matches_pattern("Bot.py", "**/*.py") is True

    def test_double_star_matches_one_directory(self) -> None:
        assert matches_pattern("sub/Bot.py", "**/*.py") is True

    def test_double_star_matches_several_directories(self) -> None:
        assert matches_pattern("a/b/c/Bot.py", "**/*.py") is True

    def test_double_star_suffix_matches_nested_paths(self) -> None:
        assert matches_pattern("web/images/sub/foo.png", "web/images/**") is True

    def test_rejects_non_matching_extension(self) -> None:
        assert matches_pattern("Bot.txt", "**/*.py") is False

    def test_literal_pattern_matches_exact_name_only(self) -> None:
        assert matches_pattern("RunBot.py", "RunBot.py") is True
        assert matches_pattern("sub/RunBot.py", "RunBot.py") is False


def test_render_variables_replaces_all_occurrences() -> None:
    content = "home=__KBOT_HOME__ user=__KBOT_USER__ again=__KBOT_HOME__"
    result = render_variables(
        content, {"__KBOT_HOME__": "/work", "__KBOT_USER__": "bob"}
    )

    assert result == "home=/work user=bob again=/work"


def test_render_variables_is_noop_without_variables() -> None:
    assert render_variables("hello", {}) == "hello"


class TestIsBrokenSymlink:
    def test_true_for_dangling_symlink(self, tmp_path: Path) -> None:
        link = tmp_path / "link"
        link.symlink_to(tmp_path / "missing")

        assert is_broken_symlink(link) is True

    def test_false_for_valid_symlink(self, tmp_path: Path) -> None:
        target = tmp_path / "target"
        target.write_text("data")
        link = tmp_path / "link"
        link.symlink_to(target)

        assert is_broken_symlink(link) is False

    def test_false_for_regular_file(self, tmp_path: Path) -> None:
        path = tmp_path / "file"
        path.write_text("data")

        assert is_broken_symlink(path) is False


class TestLinkSource:
    def test_creates_real_directory_for_dir_source(self, tmp_path: Path) -> None:
        source = tmp_path / "source_dir"
        source.mkdir()
        target = tmp_path / "target_dir"

        link_source(source, target)

        assert target.is_dir()
        assert not target.is_symlink()

    def test_symlinks_file_source(self, tmp_path: Path) -> None:
        source = tmp_path / "source.txt"
        source.write_text("data")
        target = tmp_path / "nested" / "target.txt"

        link_source(source, target)

        assert target.is_symlink()
        assert target.resolve() == source.resolve()


class TestCopySource:
    def test_creates_real_directory_for_dir_source(self, tmp_path: Path) -> None:
        source = tmp_path / "source_dir"
        source.mkdir()
        target = tmp_path / "target_dir"

        copy_source(source, target)

        assert target.is_dir()
        assert not target.is_symlink()

    def test_copies_file_without_variables(self, tmp_path: Path) -> None:
        source = tmp_path / "source.txt"
        source.write_text("hello __KBOT_HOME__")
        target = tmp_path / "nested" / "target.txt"

        copy_source(source, target)

        assert target.read_text() == "hello __KBOT_HOME__"
        assert not target.is_symlink()

    def test_renders_variables_when_provided(self, tmp_path: Path) -> None:
        source = tmp_path / "source.txt"
        source.write_text("home=__KBOT_HOME__")
        target = tmp_path / "target.txt"

        copy_source(source, target, variables={"__KBOT_HOME__": "/work"})

        assert target.read_text() == "home=/work"

    def test_skips_dangling_symlink(self, tmp_path: Path) -> None:
        source = tmp_path / "marked"
        source.symlink_to("/home/runner/work/kbot/build/marked.js")
        target = tmp_path / "work" / "marked"

        copy_source(source, target)

        assert not target.exists()
        assert not target.is_symlink()


class TestIterSources:
    def test_recursive_yields_nested_files(self, tmp_path: Path) -> None:
        (tmp_path / "sub").mkdir()
        (tmp_path / "top.py").write_text("a")
        (tmp_path / "sub" / "nested.py").write_text("b")

        rule = _rule(recursive=True)
        results = {p.name for p in iter_sources(tmp_path, rule)}

        assert "top.py" in results
        assert "nested.py" in results
        assert "sub" in results

    def test_non_recursive_yields_top_level_only(self, tmp_path: Path) -> None:
        (tmp_path / "sub").mkdir()
        (tmp_path / "top.py").write_text("a")
        (tmp_path / "sub" / "nested.py").write_text("b")

        rule = _rule(recursive=False)
        results = {p.name for p in iter_sources(tmp_path, rule)}

        assert results == {"top.py", "sub"}

    def test_filters_with_includes(self, tmp_path: Path) -> None:
        (tmp_path / "a.py").write_text("a")
        (tmp_path / "b.txt").write_text("b")

        rule = _rule(recursive=False, includes=["*.py"])
        results = {p.name for p in iter_sources(tmp_path, rule)}

        assert results == {"a.py"}


class TestApplyRule:
    def test_skips_when_source_root_missing(self, tmp_path: Path) -> None:
        product_root = tmp_path / "product"
        work_root = tmp_path / "work"
        rule = _rule(source=Path("missing"))

        apply_rule(product_root, work_root, rule, runtime_variables={})

        assert not work_root.exists()

    def test_links_matching_files(self, tmp_path: Path) -> None:
        product_root = tmp_path / "product"
        (product_root / "core").mkdir(parents=True)
        source_file = product_root / "core" / "a.py"
        source_file.write_text("data")
        work_root = tmp_path / "work"

        rule = _rule(source=Path("core"), action=RuleAction.LINK)
        apply_rule(product_root, work_root, rule, runtime_variables={})

        target = work_root / "core" / "a.py"
        assert target.is_symlink()

    def test_links_top_level_file_matched_by_double_star_includes(
        self, tmp_path: Path
    ) -> None:
        """Regression: rules like conf/rules.json's `core/python` -> `**/*.py`.

        must also link top-level product files (e.g. `core/python/Bot.py`),
        not just files nested in subdirectories.
        """
        product_root = tmp_path / "product"
        (product_root / "core" / "python").mkdir(parents=True)
        source_file = product_root / "core" / "python" / "Bot.py"
        source_file.write_text("data")
        work_root = tmp_path / "work"

        rule = _rule(
            source=Path("core/python"),
            action=RuleAction.LINK,
            includes=["**/*.py", "**/*.so"],
        )
        apply_rule(product_root, work_root, rule, runtime_variables={})

        target = work_root / "core" / "python" / "Bot.py"
        assert target.is_symlink()
        assert target.resolve() == source_file.resolve()

    def test_copies_matching_files_with_placeholders(self, tmp_path: Path) -> None:
        product_root = tmp_path / "product"
        (product_root / "core").mkdir(parents=True)
        source_file = product_root / "core" / "conf.txt"
        source_file.write_text("home=__KBOT_HOME__")
        work_root = tmp_path / "work"

        rule = _rule(
            source=Path("core"),
            action=RuleAction.COPY,
            placeholders=["__KBOT_HOME__"],
        )
        apply_rule(
            product_root,
            work_root,
            rule,
            runtime_variables={"__KBOT_HOME__": "/work"},
        )

        target = work_root / "core" / "conf.txt"
        assert target.read_text() == "home=/work"

    def test_skips_target_that_already_exists(self, tmp_path: Path) -> None:
        product_root = tmp_path / "product"
        (product_root / "core").mkdir(parents=True)
        source_file = product_root / "core" / "a.py"
        source_file.write_text("new")
        work_root = tmp_path / "work"
        existing_target = work_root / "core" / "a.py"
        existing_target.parent.mkdir(parents=True)
        existing_target.write_text("existing")

        rule = _rule(source=Path("core"), action=RuleAction.COPY)
        apply_rule(product_root, work_root, rule, runtime_variables={})

        assert existing_target.read_text() == "existing"

    def test_uses_target_path_override(self, tmp_path: Path) -> None:
        product_root = tmp_path / "product"
        (product_root / "core").mkdir(parents=True)
        (product_root / "core" / "a.py").write_text("data")
        work_root = tmp_path / "work"

        rule = _rule(
            source=Path("core"), target=Path("elsewhere"), action=RuleAction.LINK
        )
        apply_rule(product_root, work_root, rule, runtime_variables={})

        assert (work_root / "elsewhere" / "a.py").is_symlink()
        assert not (work_root / "core").exists()

    @staticmethod
    def _copy_setup(tmp_path: Path, source_text: str, target_text: str) -> tuple[Path, Path, Path]:
        product_root = tmp_path / "product"
        (product_root / "core").mkdir(parents=True)
        source_file = product_root / "core" / "a.py"
        source_file.write_text(source_text)
        work_root = tmp_path / "work"
        target = work_root / "core" / "a.py"
        target.parent.mkdir(parents=True)
        target.write_text(target_text)
        return product_root, work_root, target

    def test_refresh_rewrites_outdated_copy(self, tmp_path: Path) -> None:
        product_root, work_root, target = self._copy_setup(tmp_path, "new", "old")

        rule = _rule(source=Path("core"), action=RuleAction.COPY, refresh=True)
        apply_rule(product_root, work_root, rule, runtime_variables={})

        assert target.read_text() == "new"
        assert not target.is_symlink()

    def test_refresh_replaces_symlink_target_without_touching_source(self, tmp_path: Path) -> None:
        product_root = tmp_path / "product"
        (product_root / "core").mkdir(parents=True)
        source_file = product_root / "core" / "a.py"
        source_file.write_text("src")
        work_root = tmp_path / "work"
        target = work_root / "core" / "a.py"
        target.parent.mkdir(parents=True)
        target.symlink_to(source_file)

        rule = _rule(
            source=Path("core"),
            action=RuleAction.COPY,
            placeholders=["__KBOT_HOME__"],
            refresh=True,
        )
        apply_rule(product_root, work_root, rule, runtime_variables={"__KBOT_HOME__": "/work"})

        assert not target.is_symlink()
        assert target.read_text() == "src"
        assert source_file.read_text() == "src"

    def test_refresh_compares_rendered_placeholders(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        product_root, work_root, target = self._copy_setup(tmp_path, "home=__KBOT_HOME__", "home=/work")

        def _no_prompt(_prompt: str) -> str:
            raise AssertionError("up-to-date rendered copy must not prompt")

        monkeypatch.setattr("builtins.input", _no_prompt)

        rule = _rule(
            source=Path("core"),
            action=RuleAction.COPY,
            placeholders=["__KBOT_HOME__"],
            refresh=True,
        )
        apply_rule(
            product_root,
            work_root,
            rule,
            runtime_variables={"__KBOT_HOME__": "/work"},
            interactive=True,
        )

        assert target.read_text() == "home=/work"

    def test_refresh_interactive_refusal_keeps_copy(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        product_root, work_root, target = self._copy_setup(tmp_path, "new", "old")
        monkeypatch.setattr("builtins.input", lambda _prompt: "n")

        rule = _rule(source=Path("core"), action=RuleAction.COPY, refresh=True)
        apply_rule(product_root, work_root, rule, runtime_variables={}, interactive=True)

        assert target.read_text() == "old"

    def test_claimed_target_not_refreshed_by_later_product(self, tmp_path: Path) -> None:
        products = []
        for name, text in (("product1", "first"), ("product2", "second")):
            root = tmp_path / name
            (root / "core").mkdir(parents=True)
            (root / "core" / "a.py").write_text(text)
            products.append(root)
        work_root = tmp_path / "work"
        rules = [_rule(source=Path("core"), action=RuleAction.COPY, refresh=True)]

        for _ in range(2):
            claimed: set[Path] = set()
            for product_root in products:
                apply_rules(product_root, work_root, rules, runtime_variables={}, claimed=claimed)

            assert (work_root / "core" / "a.py").read_text() == "first"


def test_apply_rules_applies_every_rule(tmp_path: Path) -> None:
    product_root = tmp_path / "product"
    (product_root / "core").mkdir(parents=True)
    (product_root / "core" / "a.py").write_text("a")
    (product_root / "rest").mkdir(parents=True)
    (product_root / "rest" / "b.py").write_text("b")
    work_root = tmp_path / "work"

    rules = [
        _rule(source=Path("core"), action=RuleAction.LINK),
        _rule(source=Path("rest"), action=RuleAction.COPY),
    ]

    apply_rules(product_root, work_root, rules, runtime_variables={})

    assert (work_root / "core" / "a.py").is_symlink()
    assert (work_root / "rest" / "b.py").read_text() == "b"


class TestSetupKbotConf:
    def test_creates_conf_file(self, tmp_path: Path) -> None:
        setup_kbot_conf(tmp_path)

        conf_path = tmp_path / "conf" / "kbot.conf"
        assert conf_path.exists()
        assert "Kbot configuration file" in conf_path.read_text()

    def test_does_not_overwrite_existing_file(self, tmp_path: Path) -> None:
        conf_path = tmp_path / "conf" / "kbot.conf"
        conf_path.parent.mkdir(parents=True)
        conf_path.write_text("custom content")

        setup_kbot_conf(tmp_path)

        assert conf_path.read_text() == "custom content"


def test_setup_runtime_dirs_creates_expected_tree(tmp_path: Path) -> None:
    setup_runtime_dirs(tmp_path)

    for relative in [
        "logs/httpd",
        "var/pkl",
        "var/pkl/storage",
        "var/pkl/test_results",
        "var/cache",
    ]:
        assert (tmp_path / relative).is_dir()


class TestSetupProducts:
    def test_symlinks_each_product(self, tmp_path: Path) -> None:
        product = tmp_path / "installer" / "kbot"
        product.mkdir(parents=True)
        work_root = tmp_path / "work"

        setup_products(work_root, [product])

        link = work_root / "products" / "kbot"
        assert link.is_symlink()
        assert link.resolve() == product.resolve()

    def test_skips_when_target_already_exists(self, tmp_path: Path) -> None:
        product = tmp_path / "installer" / "kbot"
        product.mkdir(parents=True)
        work_root = tmp_path / "work"
        existing = work_root / "products" / "kbot"
        existing.mkdir(parents=True)

        setup_products(work_root, [product])

        assert existing.is_dir()
        assert not existing.is_symlink()


def _write_product(installer_root: Path, name: str, parents: list[str] | None = None) -> Path:
    product_root = installer_root / name
    product_root.mkdir(parents=True)
    parents_xml = "".join(f'<parent name="{parent}"/>' for parent in parents or [])
    (product_root / "description.xml").write_text(
        f'<product name="{name}" version="2026.01" build="" date="" type="solution">'
        f"<parents>{parents_xml}</parents></product>"
    )
    return product_root


def _read_registry(work_root: Path) -> list[dict[str, object]]:
    return json.loads((work_root / "var" / "products.json").read_text(encoding="utf-8"))


class TestSetupProductsRegistry:
    def test_lists_products_children_first_like_legacy_deps(self, tmp_path: Path) -> None:
        """Order must match the legacy utils/deps.py output: first kbot.env defining a variable wins."""
        installer = tmp_path / "installer"
        roots = [
            _write_product(installer, "site", ["keys", "customer"]),
            _write_product(installer, "customer", ["gsuite", "easyvista"]),
            _write_product(installer, "easyvista", ["ithd"]),
            _write_product(installer, "gsuite", ["ithd"]),
            _write_product(installer, "ithd", ["kbot"]),
            _write_product(installer, "keys", ["kbot"]),
            _write_product(installer, "kbot", ["kbot_installer", "3rdparty"]),
            _write_product(installer, "3rdparty"),
            _write_product(installer, "kbot_installer"),
        ]
        work_root = tmp_path / "work"

        setup_products_registry(work_root, sorted(roots))

        assert [entry["name"] for entry in _read_registry(work_root)] == [
            "site",
            "customer",
            "easyvista",
            "gsuite",
            "ithd",
            "keys",
            "kbot",
            "3rdparty",
            "kbot_installer",
        ]

    def test_entry_has_path_description_and_merged_json(self, tmp_path: Path) -> None:
        product_root = _write_product(tmp_path / "installer", "kbot")
        (product_root / "description.json").write_text(
            json.dumps({"name": "kbot", "version": "2026.01", "date": "2026/09/25", "type": "solution"})
        )
        work_root = tmp_path / "work"

        setup_products_registry(work_root, [product_root])

        [entry] = _read_registry(work_root)
        assert entry["path"] == str(product_root)
        assert entry["description"] == str(product_root / "description.xml")
        assert entry["date"] == "2026/09/25"
        assert entry["parents"] == []

    def test_ignores_roots_without_description_and_missing_parents(self, tmp_path: Path) -> None:
        installer = tmp_path / "installer"
        product_root = _write_product(installer, "site", ["not_installed"])
        (installer / "no_description").mkdir()
        work_root = tmp_path / "work"

        setup_products_registry(work_root, [installer / "no_description", product_root])

        assert [entry["name"] for entry in _read_registry(work_root)] == ["site"]

    def test_overwrites_existing_registry(self, tmp_path: Path) -> None:
        product_root = _write_product(tmp_path / "installer", "kbot")
        work_root = tmp_path / "work"
        (work_root / "var").mkdir(parents=True)
        (work_root / "var" / "products.json").write_text("[]")

        setup_products_registry(work_root, [product_root])

        assert [entry["name"] for entry in _read_registry(work_root)] == ["kbot"]

    def test_raises_on_circular_dependencies(self, tmp_path: Path) -> None:
        installer = tmp_path / "installer"
        roots = [_write_product(installer, "a", ["b"]), _write_product(installer, "b", ["a"])]

        with pytest.raises(ValueError, match="Circular product dependency"):
            setup_products_registry(tmp_path / "work", roots)


def _write_versions_env(installer_root: Path) -> Path:
    thirdparty = installer_root / "3rdparty"
    thirdparty.mkdir(parents=True, exist_ok=True)
    (thirdparty / "versions.env").write_text(
        "PYTHON_VERSION=3.10.15\n"
        "PYTHON_MAJOR_VERSION=3.10\n"
        "THIRDPARTY_PATH=${THIRDPARTY_HOME}\n"
        "PYTHON_DIR=${THIRDPARTY_PATH}/Python-${PYTHON_VERSION}\n",
        encoding="utf-8",
    )
    return thirdparty / "Python-3.10.15" / "lib" / "python3.10" / "site-packages"


class TestSetupDrfYasgStatic:
    def test_symlinks_static_dir_when_source_exists(self, tmp_path: Path) -> None:
        site_packages = _write_versions_env(tmp_path)
        fake_static = site_packages / "drf_yasg" / "static"
        fake_static.mkdir(parents=True)

        work_root = tmp_path / "work"
        setup_drf_yasg_static(work_root, tmp_path)

        link = work_root / "ui" / "web" / "static"
        assert link.is_symlink()
        assert link.resolve() == fake_static.resolve()

    def test_noop_when_source_missing(self, tmp_path: Path) -> None:
        _write_versions_env(tmp_path)

        work_root = tmp_path / "work"
        setup_drf_yasg_static(work_root, tmp_path)

        assert not (work_root / "ui").exists()

    def test_noop_when_target_already_exists(self, tmp_path: Path) -> None:
        site_packages = _write_versions_env(tmp_path)
        (site_packages / "drf_yasg" / "static").mkdir(parents=True)

        work_root = tmp_path / "work"
        existing = work_root / "ui" / "web" / "static"
        existing.mkdir(parents=True)

        setup_drf_yasg_static(work_root, tmp_path)

        assert existing.is_dir()
        assert not existing.is_symlink()

    def test_noop_when_versions_env_missing(self, tmp_path: Path) -> None:
        work_root = tmp_path / "work"
        setup_drf_yasg_static(work_root, tmp_path)

        assert not (work_root / "ui").exists()


class TestCleanupUnusedTestsDir:
    def test_removes_tests_dir_when_unused(self, tmp_path: Path) -> None:
        tests_dir = tmp_path / "tests"
        tests_dir.mkdir()

        cleanup_unused_tests_dir(tmp_path, [tmp_path / "product"], interactive=False)

        assert not tests_dir.exists()

    def test_does_nothing_when_tests_dir_does_not_exist(self, tmp_path: Path) -> None:
        """No-op (and no crash) when the workarea never had a 'tests' directory."""
        cleanup_unused_tests_dir(tmp_path, [tmp_path / "product"], interactive=False)

        assert not (tmp_path / "tests").exists()

    def test_keeps_tests_dir_when_a_product_uses_it(self, tmp_path: Path) -> None:
        tests_dir = tmp_path / "tests"
        tests_dir.mkdir()
        product_root = tmp_path / "product"
        (product_root / "tests").mkdir(parents=True)

        cleanup_unused_tests_dir(tmp_path, [product_root], interactive=False)

        assert tests_dir.exists()

    def test_interactive_removes_on_confirmation(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        tests_dir = tmp_path / "tests"
        tests_dir.mkdir()
        monkeypatch.setattr("builtins.input", lambda _prompt: "y")

        cleanup_unused_tests_dir(tmp_path, [], interactive=True)

        assert not tests_dir.exists()

    def test_interactive_removes_on_empty_answer(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Pressing Enter accepts the [Y/n] default."""
        tests_dir = tmp_path / "tests"
        tests_dir.mkdir()
        monkeypatch.setattr("builtins.input", lambda _prompt: "")

        cleanup_unused_tests_dir(tmp_path, [], interactive=True)

        assert not tests_dir.exists()

    def test_interactive_keeps_on_refusal(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        tests_dir = tmp_path / "tests"
        tests_dir.mkdir()
        monkeypatch.setattr("builtins.input", lambda _prompt: "n")

        cleanup_unused_tests_dir(tmp_path, [], interactive=True)

        assert tests_dir.exists()


class TestClearWorkarea:
    def test_removes_files_symlinks_and_directories(self, tmp_path: Path) -> None:
        work_root = tmp_path / "work"
        work_root.mkdir()
        (work_root / "file.txt").write_text("data")
        (work_root / "a_dir").mkdir()
        (work_root / "a_dir" / "nested.txt").write_text("nested")
        target = tmp_path / "link_target.txt"
        target.write_text("target")
        (work_root / "link").symlink_to(target)

        clear_workarea(work_root)

        assert work_root.exists()
        assert list(work_root.iterdir()) == []
        assert target.exists()  # symlink target itself is untouched


class TestRepairBrokenLinks:
    def test_removes_only_broken_symlinks(self, tmp_path: Path) -> None:
        work_root = tmp_path / "work"
        work_root.mkdir()
        valid_target = work_root / "target.txt"
        valid_target.write_text("data")
        valid_link = work_root / "valid_link"
        valid_link.symlink_to(valid_target)
        broken_link = work_root / "broken_link"
        broken_link.symlink_to(work_root / "missing")
        regular_file = work_root / "regular.txt"
        regular_file.write_text("data")

        repair_broken_links(work_root.rglob("*"))

        assert not broken_link.exists()
        assert valid_link.is_symlink()
        assert regular_file.exists()

    def test_interactive_keeps_link_on_refusal(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        work_root = tmp_path / "work"
        work_root.mkdir()
        broken_link = work_root / "broken_link"
        broken_link.symlink_to(work_root / "missing")
        monkeypatch.setattr("builtins.input", lambda _prompt: "n")

        repair_broken_links(work_root.rglob("*"), interactive=True)

        assert broken_link.is_symlink()

    def test_interactive_removes_link_on_confirmation(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        work_root = tmp_path / "work"
        work_root.mkdir()
        broken_link = work_root / "broken_link"
        broken_link.symlink_to(work_root / "missing")
        monkeypatch.setattr("builtins.input", lambda _prompt: "y")

        repair_broken_links(work_root.rglob("*"), interactive=True)

        assert not broken_link.exists()

    def test_interactive_removes_link_on_empty_answer(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Pressing Enter accepts the [Y/n] default."""
        work_root = tmp_path / "work"
        work_root.mkdir()
        broken_link = work_root / "broken_link"
        broken_link.symlink_to(work_root / "missing")
        monkeypatch.setattr("builtins.input", lambda _prompt: "")

        repair_broken_links(work_root.rglob("*"), interactive=True)

        assert not broken_link.exists()


class TestSetupDrfSpectacularStatic:
    def test_symlinks_sidecar_static_dir(self, tmp_path: Path) -> None:
        """drf_spectacular has no static dir: the assets ship in drf_spectacular_sidecar."""
        site_packages = _write_versions_env(tmp_path)
        (site_packages / "drf_spectacular").mkdir(parents=True)
        sidecar_static = site_packages / "drf_spectacular_sidecar" / "static"
        sidecar_static.mkdir(parents=True)

        work_root = tmp_path / "work"
        setup_drf_spectacular_static(work_root, tmp_path)

        link = work_root / "ui" / "web" / "static"
        assert link.is_symlink()
        assert link.resolve() == sidecar_static.resolve()

    def test_noop_when_sidecar_missing(self, tmp_path: Path) -> None:
        site_packages = _write_versions_env(tmp_path)
        (site_packages / "drf_spectacular").mkdir(parents=True)

        work_root = tmp_path / "work"
        setup_drf_spectacular_static(work_root, tmp_path)

        assert not (work_root / "ui").exists()
