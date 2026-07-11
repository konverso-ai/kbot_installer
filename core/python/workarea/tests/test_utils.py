"""Tests for workarea.utils module."""

from pathlib import Path

import pytest
from workarea.rule_action import RuleAction
from workarea.utils import (
    apply_rule,
    apply_rules,
    cleanup_unused_tests_dir,
    copy_source,
    is_broken_symlink,
    iter_sources,
    link_source,
    render_variables,
    setup_drf_yasg_static,
    setup_kbot_conf,
    setup_products,
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


class TestSetupDrfYasgStatic:
    def test_symlinks_static_dir_when_source_exists(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        fake_pkg_root = tmp_path / "drf_yasg"
        fake_static = fake_pkg_root / "static"
        fake_static.mkdir(parents=True)
        monkeypatch.setattr("workarea.utils.files", lambda _pkg: fake_pkg_root)

        work_root = tmp_path / "work"
        setup_drf_yasg_static(work_root)

        link = work_root / "ui" / "web" / "static"
        assert link.is_symlink()
        assert link.resolve() == fake_static.resolve()

    def test_noop_when_source_missing(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(
            "workarea.utils.files", lambda _pkg: tmp_path / "does_not_exist"
        )

        work_root = tmp_path / "work"
        setup_drf_yasg_static(work_root)

        assert not (work_root / "ui").exists()

    def test_noop_when_target_already_exists(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        fake_pkg_root = tmp_path / "drf_yasg"
        (fake_pkg_root / "static").mkdir(parents=True)
        monkeypatch.setattr("workarea.utils.files", lambda _pkg: fake_pkg_root)

        work_root = tmp_path / "work"
        existing = work_root / "ui" / "web" / "static"
        existing.mkdir(parents=True)

        setup_drf_yasg_static(work_root)

        assert existing.is_dir()
        assert not existing.is_symlink()


class TestCleanupUnusedTestsDir:
    def test_removes_tests_dir_when_unused(self, tmp_path: Path) -> None:
        tests_dir = tmp_path / "tests"
        tests_dir.mkdir()

        cleanup_unused_tests_dir(tmp_path, [tmp_path / "product"], interactive=False)

        assert not tests_dir.exists()

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

    def test_interactive_keeps_on_refusal(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        tests_dir = tmp_path / "tests"
        tests_dir.mkdir()
        monkeypatch.setattr("builtins.input", lambda _prompt: "n")

        cleanup_unused_tests_dir(tmp_path, [], interactive=True)

        assert tests_dir.exists()
