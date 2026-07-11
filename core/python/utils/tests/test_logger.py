"""Tests for utils.Logger module."""

import json
import logging
import sys

import pytest
from errors import KB11111, LLM00001

from utils.Logger import (
    FINE,
    FINEST,
    DataDogFormatter,
    KbotFormatter,
    KbotLogger,
    NormalizeLevel,
    UpdateLevel,
    UpdateSupportedPackages,
    levels,
    logger,
    mylogger,
    name_to_level,
)
from utils.utils_for_unit_tests import compare


class _RecordingHandler(logging.Handler):
    """Collects emitted records instead of writing them anywhere."""

    def __init__(self) -> None:
        super().__init__()
        self.records: list[logging.LogRecord] = []

    def emit(self, record: logging.LogRecord) -> None:
        self.records.append(record)


@pytest.fixture
def kbot_logger() -> KbotLogger:
    """A standalone KbotLogger, isolated from the shared 'kbot' singleton."""
    instance = KbotLogger("test.kbot_logger")
    instance.propagate = False
    instance.setLevel(logging.DEBUG)
    instance.addHandler(_RecordingHandler())
    return instance


def _records(instance: KbotLogger) -> list[logging.LogRecord]:
    return instance.handlers[0].records


class TestNormalizeLevel:
    """Test cases for NormalizeLevel."""

    @pytest.mark.parametrize(
        "raw, expected",
        [(-5, 0), (0, 0), (3, 3), (5, 5), (10, 5)],
    )
    def test_normalizelevel_valid_clamps_to_range(self, raw: int, expected: int) -> None:
        """Test NormalizeLevel clamps values to the [0, 5] range."""
        assert compare("eq", NormalizeLevel(raw), expected)


class TestLevelTables:
    """Test cases for the module-level level tables."""

    def test_levels_valid_maps_scale_to_stdlib_constants(self) -> None:
        """Test levels maps the 0-5 scale to logging/custom level constants."""
        assert compare("eq", levels[0], logging.CRITICAL)
        assert compare("eq", levels[3], logging.DEBUG)
        assert compare("eq", levels[4], FINE)
        assert compare("eq", levels[5], FINEST)

    def test_nametolevel_valid_maps_names_to_scale(self) -> None:
        """Test name_to_level maps level names to the 0-5 scale."""
        assert compare("eq", name_to_level["debug"], 3)
        assert compare("eq", name_to_level["finest"], 5)

    def test_customlevels_valid_registered_with_logging(self) -> None:
        """Test FINE and FINEST are registered as named logging levels."""
        assert compare("eq", logging.getLevelName(FINE), "FINE")
        assert compare("eq", logging.getLevelName(FINEST), "FINEST")


class TestKbotLoggerFiltering:
    """Test cases for KbotLogger per-package level filtering."""

    def test_isenabledfor_valid_default_bucket(self, kbot_logger: KbotLogger) -> None:
        """Test isEnabledFor uses the 'all' bucket when no package is given."""
        kbot_logger.setLevel(logging.WARNING)

        assert compare("eq", kbot_logger.isEnabledFor(logging.ERROR), True)
        assert compare("eq", kbot_logger.isEnabledFor(logging.INFO), False)

    def test_isenabledfor_valid_per_package_override(self, kbot_logger: KbotLogger) -> None:
        """Test isEnabledFor honors an exact-match per-package override."""
        kbot_logger.setLevel(logging.WARNING)
        kbot_logger.addPackage("storage", logging.DEBUG)

        assert compare("eq", kbot_logger.isEnabledFor(logging.DEBUG, "storage"), True)
        assert compare("eq", kbot_logger.isEnabledFor(logging.DEBUG, "other"), False)

    def test_isenabledfor_invalid_unregistered_package_falls_back_to_all(
        self, kbot_logger: KbotLogger
    ) -> None:
        """Test isEnabledFor falls back to 'all' for an unregistered package."""
        kbot_logger.setLevel(logging.ERROR)

        assert compare("eq", kbot_logger.isEnabledFor(logging.WARNING, "unregistered"), False)

    def test_addpackage_valid_overwrites_existing_level(self, kbot_logger: KbotLogger) -> None:
        """Test addPackage replaces a previously registered level."""
        kbot_logger.addPackage("storage", logging.DEBUG)
        kbot_logger.addPackage("storage", logging.ERROR)

        assert compare("eq", kbot_logger.isEnabledFor(logging.CRITICAL, "storage"), True)
        assert compare("eq", kbot_logger.isEnabledFor(logging.WARNING, "storage"), False)

    def test_rempackage_valid_removes_override(self, kbot_logger: KbotLogger) -> None:
        """Test remPackage drops a per-package override."""
        kbot_logger.setLevel(logging.ERROR)
        kbot_logger.addPackage("storage", logging.DEBUG)

        kbot_logger.remPackage("storage")

        assert compare("eq", kbot_logger.isEnabledFor(logging.DEBUG, "storage"), False)

    def test_rempackage_invalid_protects_all_bucket(self, kbot_logger: KbotLogger) -> None:
        """Test remPackage is a no-op for the 'all' bucket."""
        kbot_logger.setLevel(logging.DEBUG)

        kbot_logger.remPackage("all")

        assert compare("eq", kbot_logger.isEnabledFor(logging.DEBUG), True)

    def test_rempackage_valid_noop_for_unregistered_package(self, kbot_logger: KbotLogger) -> None:
        """Test remPackage silently ignores an unregistered package name."""
        kbot_logger.remPackage("never-added")  # should not raise


class TestKbotLoggerLevelMethods:
    """Test cases for KbotLogger's level-specific logging methods."""

    def test_debug_valid_emits_when_enabled(self, kbot_logger: KbotLogger) -> None:
        """Test debug emits a formatted record when enabled."""
        kbot_logger.debug("hello %s", "world")

        records = _records(kbot_logger)
        assert compare("eq", len(records), 1)
        assert compare("eq", records[0].getMessage(), "hello world")
        assert compare("eq", records[0].levelno, logging.DEBUG)
        assert compare("eq", records[0].package, "")

    def test_debug_invalid_suppressed_when_disabled(self, kbot_logger: KbotLogger) -> None:
        """Test debug is suppressed once the level is raised above DEBUG."""
        kbot_logger.setLevel(logging.WARNING)

        kbot_logger.debug("hidden")

        assert compare("eq", _records(kbot_logger), [])

    def test_debug_valid_records_package_kwarg(self, kbot_logger: KbotLogger) -> None:
        """Test the package kwarg is honored even for a direct (non-wrapped) call."""
        kbot_logger.setLevel(logging.ERROR)
        kbot_logger.addPackage("storage", logging.DEBUG)

        kbot_logger.debug("scoped", package="storage")

        record = _records(kbot_logger)[0]
        assert compare("eq", record.package, "storage")

    def test_debug_invalid_suppressed_for_other_package(self, kbot_logger: KbotLogger) -> None:
        """Test a package override does not leak to a different package name."""
        kbot_logger.setLevel(logging.ERROR)
        kbot_logger.addPackage("storage", logging.DEBUG)

        kbot_logger.debug("scoped", package="other")

        assert compare("eq", _records(kbot_logger), [])

    def test_fine_valid_emits_when_enabled(self, kbot_logger: KbotLogger) -> None:
        """Test fine emits at the custom FINE level."""
        kbot_logger.setLevel(FINE)

        kbot_logger.fine("fine message")

        assert compare("eq", _records(kbot_logger)[0].levelno, FINE)

    def test_finest_invalid_suppressed_by_debug_level(self, kbot_logger: KbotLogger) -> None:
        """Test finest is suppressed when only DEBUG is enabled."""
        kbot_logger.setLevel(logging.DEBUG)

        kbot_logger.finest("finest message")

        assert compare("eq", _records(kbot_logger), [])

    def test_info_valid_emits(self, kbot_logger: KbotLogger) -> None:
        """Test info emits at the INFO level."""
        kbot_logger.info("info message")

        assert compare("eq", _records(kbot_logger)[0].levelno, logging.INFO)

    def test_warning_valid_emits(self, kbot_logger: KbotLogger) -> None:
        """Test warning emits at the WARNING level."""
        kbot_logger.warning("warn message")

        assert compare("eq", _records(kbot_logger)[0].levelno, logging.WARNING)

    def test_warn_valid_delegates_and_warns_deprecation(self, kbot_logger: KbotLogger) -> None:
        """Test warn raises a DeprecationWarning and still emits via warning."""
        with pytest.warns(DeprecationWarning):
            kbot_logger.warn("deprecated path")

        assert compare("eq", _records(kbot_logger)[0].levelno, logging.WARNING)

    def test_error_valid_emits(self, kbot_logger: KbotLogger) -> None:
        """Test error emits at the ERROR level."""
        kbot_logger.error("error message")

        assert compare("eq", _records(kbot_logger)[0].levelno, logging.ERROR)

    def test_critical_valid_emits(self, kbot_logger: KbotLogger) -> None:
        """Test critical emits at the CRITICAL level."""
        kbot_logger.critical("critical message")

        assert compare("eq", _records(kbot_logger)[0].levelno, logging.CRITICAL)

    def test_exception_valid_captures_exc_info_by_default(self, kbot_logger: KbotLogger) -> None:
        """Test exception attaches the current exception info by default."""
        try:
            raise ValueError("boom")
        except ValueError:
            kbot_logger.exception("failed")

        record = _records(kbot_logger)[0]
        assert compare("eq", record.levelno, logging.ERROR)
        assert compare("ne", record.exc_info, None)

    def test_exception_valid_respects_explicit_exc_info(self, kbot_logger: KbotLogger) -> None:
        """Test exception honors an explicit exc_info override."""
        kbot_logger.exception("failed", exc_info=False)

        assert compare("eq", _records(kbot_logger)[0].exc_info, False)


class TestKbotLoggerFindCaller:
    """Test cases for KbotLogger's caller-frame reporting."""

    def test_findcaller_valid_reports_direct_call_site(self, kbot_logger: KbotLogger) -> None:
        """Test a direct call reports this test function as the caller."""
        kbot_logger.debug("direct")

        record = _records(kbot_logger)[0]
        assert compare("eq", record.funcName, "test_findcaller_valid_reports_direct_call_site")
        assert compare("in", "test_logger.py", record.pathname)

    def test_findcaller_valid_reports_call_site_through_package_wrapper(
        self, kbot_logger: KbotLogger
    ) -> None:
        """Test a call routed through KbotPackageLogger still reports the real caller."""
        package_logger = kbot_logger.getPackageLogger("probe")

        package_logger.debug("via wrapper")

        record = _records(kbot_logger)[0]
        assert compare(
            "eq",
            record.funcName,
            "test_findcaller_valid_reports_call_site_through_package_wrapper",
        )

    def test_findcaller_valid_reports_call_site_for_exception_hop(
        self, kbot_logger: KbotLogger
    ) -> None:
        """Test the extra exception -> error hop does not change the reported caller."""
        try:
            raise ValueError("boom")
        except ValueError:
            kbot_logger.exception("caught")

        record = _records(kbot_logger)[0]
        assert compare(
            "eq", record.funcName, "test_findcaller_valid_reports_call_site_for_exception_hop"
        )

    def test_findcaller_valid_reports_call_site_for_warn_hop(self, kbot_logger: KbotLogger) -> None:
        """Test the extra warn -> warning hop does not change the reported caller."""
        with pytest.warns(DeprecationWarning):
            kbot_logger.warn("deprecated")

        record = _records(kbot_logger)[0]
        assert compare(
            "eq", record.funcName, "test_findcaller_valid_reports_call_site_for_warn_hop"
        )

    def test_findcaller_valid_includes_stack_info_when_requested(
        self, kbot_logger: KbotLogger
    ) -> None:
        """Test stack_info=True attaches a formatted stack trace to the record."""
        kbot_logger.debug("with stack", stack_info=True)

        assert compare("ne", _records(kbot_logger)[0].stack_info, None)


class TestKbotLoggerPackages:
    """Test cases for KbotLogger's package-logger registry."""

    def test_getpackagelogger_valid_returns_cached_instance(self, kbot_logger: KbotLogger) -> None:
        """Test getPackageLogger returns the same instance for the same name."""
        first = kbot_logger.getPackageLogger("storage")
        second = kbot_logger.getPackageLogger("storage")

        assert compare("eq", first, second)

    def test_getpackagelogger_valid_returns_distinct_instances_per_name(
        self, kbot_logger: KbotLogger
    ) -> None:
        """Test getPackageLogger returns distinct instances for distinct names."""
        storage_logger = kbot_logger.getPackageLogger("storage")
        git_logger = kbot_logger.getPackageLogger("git")

        assert compare("ne", storage_logger, git_logger)

    def test_packages_valid_lists_registered_names(self, kbot_logger: KbotLogger) -> None:
        """Test packages exposes every name registered via getPackageLogger."""
        kbot_logger.getPackageLogger("storage")
        kbot_logger.getPackageLogger("git")

        assert compare("eq", set(kbot_logger.packages), {"storage", "git"})


class TestKbotLoggerBuildHandler:
    """Test cases for KbotLogger.buildHandler."""

    def test_buildhandler_valid_getproduct_uses_nullhandler(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test the GetProduct entry point wires a NullHandler."""
        monkeypatch.setattr(sys, "argv", ["GetProduct.py"])
        instance = KbotLogger("test.buildhandler.getproduct")

        instance.buildHandler(logging.WARNING)

        assert compare("eq", len(instance.handlers), 1)
        assert compare("eq", type(instance.handlers[0]), logging.NullHandler)

    def test_buildhandler_valid_default_uses_stream_handler(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test any other entry point wires a single stdout stream handler."""
        monkeypatch.setattr(sys, "argv", ["some_script.py"])
        instance = KbotLogger("test.buildhandler.default")

        instance.buildHandler(logging.WARNING)

        assert compare("eq", len(instance.handlers), 1)
        handler = instance.handlers[0]
        assert compare("eq", type(handler), logging.StreamHandler)
        assert compare("eq", handler.level, logging.WARNING)
        assert compare("eq", type(handler.formatter), KbotFormatter)

    def test_buildhandler_valid_runbot_uses_two_rotating_handlers(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path
    ) -> None:
        """Test the RunBot entry point wires a kbot and a datadog rotating handler."""
        (tmp_path / "logs").mkdir()
        monkeypatch.setattr(sys, "argv", ["RunBot.py"])
        monkeypatch.setenv("KBOT_HOME", str(tmp_path))
        instance = KbotLogger("test.buildhandler.runbot")

        instance.buildHandler(logging.ERROR)

        assert compare("eq", len(instance.handlers), 2)
        for handler in instance.handlers:
            assert compare("eq", handler.level, logging.ERROR)
        formatters = {type(h.formatter) for h in instance.handlers}
        assert compare("eq", formatters, {DataDogFormatter, KbotFormatter})
        assert compare("eq", (tmp_path / "logs" / "core.log").exists(), True)
        assert compare("eq", (tmp_path / "logs" / "core.json").exists(), True)


class TestKbotPackageLogger:
    """Test cases for KbotPackageLogger."""

    @pytest.fixture
    def package_logger(self, kbot_logger: KbotLogger):
        kbot_logger.setLevel(FINEST)
        return kbot_logger.getPackageLogger("storage")

    def test_debug_valid_tags_record_with_package_name(
        self, kbot_logger: KbotLogger, package_logger
    ) -> None:
        """Test a package-scoped call tags the record with its package name."""
        package_logger.debug("scoped message")

        assert compare("eq", _records(kbot_logger)[0].package, "storage")

    @pytest.mark.parametrize(
        "method_name, expected_level",
        [
            ("fine", FINE),
            ("finest", FINEST),
            ("debug", logging.DEBUG),
            ("info", logging.INFO),
            ("warning", logging.WARNING),
            ("error", logging.ERROR),
            ("critical", logging.CRITICAL),
        ],
    )
    def test_levelmethods_valid_forward_to_logger(
        self, kbot_logger: KbotLogger, package_logger, method_name: str, expected_level: int
    ) -> None:
        """Test each level method forwards to the matching KbotLogger method."""
        getattr(package_logger, method_name)("msg")

        assert compare("eq", _records(kbot_logger)[0].levelno, expected_level)

    def test_warn_valid_forwards_with_deprecation(
        self, kbot_logger: KbotLogger, package_logger
    ) -> None:
        """Test warn forwards through KbotLogger's deprecation path."""
        with pytest.warns(DeprecationWarning):
            package_logger.warn("deprecated")

        assert compare("eq", _records(kbot_logger)[0].levelno, logging.WARNING)

    def test_exception_valid_forwards_with_exc_info(
        self, kbot_logger: KbotLogger, package_logger
    ) -> None:
        """Test exception forwards and still captures exc_info."""
        try:
            raise ValueError("boom")
        except ValueError:
            package_logger.exception("caught")

        assert compare("ne", _records(kbot_logger)[0].exc_info, None)

    def test_log_valid_uses_errorcode_level_and_message(
        self, kbot_logger: KbotLogger, package_logger
    ) -> None:
        """Test log uses the ErrorCode's own level and message by default."""
        error = LLM00001()

        package_logger.log(error)

        record = _records(kbot_logger)[0]
        assert compare("eq", record.levelname, "DEBUG")
        assert compare("eq", record.getMessage(), error.message)

    def test_log_valid_overrides_message_and_level(
        self, kbot_logger: KbotLogger, package_logger
    ) -> None:
        """Test log honors explicit message/level overrides."""
        error = KB11111()

        package_logger.log(error, message="custom", level="error")

        record = _records(kbot_logger)[0]
        assert compare("eq", record.levelname, "ERROR")
        assert compare("eq", record.getMessage(), "custom")

    def test_log_and_raise_valid_logs_then_raises(
        self, kbot_logger: KbotLogger, package_logger
    ) -> None:
        """Test log_and_raise emits a record and then raises the same error."""
        error = KB11111()

        with pytest.raises(KB11111):
            package_logger.log_and_raise(error)

        assert compare("eq", len(_records(kbot_logger)), 1)

    def test_onetime_valid_logs_first_occurrence_only(
        self, kbot_logger: KbotLogger, package_logger
    ) -> None:
        """Test oneTime logs a given message only once, counting repeats."""
        package_logger.oneTime("warning", "Deprecated call %s", "foo")
        package_logger.oneTime("warning", "Deprecated call %s", "foo")
        package_logger.oneTime("warning", "Deprecated call %s", "foo")

        assert compare("eq", len(_records(kbot_logger)), 1)
        message_hash = hash("Deprecated call foo")
        assert compare("eq", package_logger.ONE_TIME_MESSAGES[message_hash].count, 3)

    def test_onetime_valid_distinct_messages_each_log_once(
        self, kbot_logger: KbotLogger, package_logger
    ) -> None:
        """Test oneTime treats distinct expanded messages independently."""
        package_logger.oneTime("warning", "message one")
        package_logger.oneTime("warning", "message two")

        assert compare("eq", len(_records(kbot_logger)), 2)


class TestKbotFormatter:
    """Test cases for KbotFormatter."""

    @staticmethod
    def _make_record(pathname: str) -> logging.LogRecord:
        record = logging.LogRecord(
            name="kbot",
            level=logging.INFO,
            pathname=pathname,
            lineno=10,
            msg="hello",
            args=(),
            exc_info=None,
            func="do_thing",
        )
        record.package = "storage"
        return record

    def test_format_valid_uses_module_name_directly(self) -> None:
        """Test format uses the record's module name as-is for regular modules."""
        formatter = KbotFormatter()

        formatted = formatter.format(self._make_record("/repo/service/nexus_service.py"))

        assert compare("in", "nexus_service::do_thing(10)", formatted)
        assert compare("in", "storage", formatted)

    def test_format_valid_expands_init_module_with_parent_package(self) -> None:
        """Test format qualifies '__init__' records with their parent package."""
        formatter = KbotFormatter()

        formatted = formatter.format(self._make_record("/repo/service/__init__.py"))

        assert compare("in", "service.__init__", formatted)


class TestDataDogFormatter:
    """Test cases for DataDogFormatter."""

    @staticmethod
    def _make_record(pathname: str = "/repo/service/nexus_service.py") -> logging.LogRecord:
        record = logging.LogRecord(
            name="kbot",
            level=logging.WARNING,
            pathname=pathname,
            lineno=1,
            msg="hello",
            args=(),
            exc_info=None,
        )
        record.package = "storage"
        return record

    def test_addfields_valid_sets_timestamp_and_uppercase_level(self) -> None:
        """Test format injects a timestamp and an uppercased level."""
        formatter = DataDogFormatter()

        payload = json.loads(formatter.format(self._make_record()))

        assert compare("eq", payload["level"], "WARNING")
        assert compare("in", "timestamp", payload)
        assert compare("eq", payload["kmodule"], "nexus_service")
        assert compare("eq", payload["package"], "storage")


@pytest.fixture
def restore_kbot_singleton():
    """Snapshot and restore the shared 'kbot' singleton's mutable state."""
    original_handlers = list(logger.handlers)
    original_filters = dict(logger._KbotLogger__filters)  # noqa: SLF001
    try:
        yield
    finally:
        logger.handlers = original_handlers
        logger._KbotLogger__filters.clear()  # noqa: SLF001
        logger._KbotLogger__filters.update(original_filters)  # noqa: SLF001


class TestModuleLevelSingleton:
    """Test cases for the shared 'kbot' logger singleton and its runtime helpers."""

    def test_module_valid_restores_default_logger_class(self) -> None:
        """Test the module leaves logging's default logger class untouched."""
        assert compare("eq", logging.getLoggerClass(), logging.Logger)

    def test_module_valid_disables_propagation(self) -> None:
        """Test the 'kbot' logger does not propagate to the root logger."""
        assert compare("eq", logger.propagate, False)

    def test_mylogger_valid_is_utils_package_logger(self) -> None:
        """Test mylogger is the 'utils' package logger bound to the singleton."""
        assert compare("eq", mylogger.name, "utils")
        assert compare("eq", mylogger.logger, logger)

    def test_updatelevel_valid_updates_logger_and_handlers(self, restore_kbot_singleton) -> None:
        """Test UpdateLevel updates both the logger and every attached handler."""
        handler = _RecordingHandler()
        logger.addHandler(handler)

        UpdateLevel(3)  # DEBUG

        assert compare("eq", handler.level, logging.DEBUG)
        assert compare("eq", logger.isEnabledFor(logging.DEBUG), True)

    def test_updatesupportedpackages_valid_add_sets_package_level(
        self, restore_kbot_singleton
    ) -> None:
        """Test 'add' registers a per-package level override."""
        UpdateSupportedPackages("add probe_pkg 5")

        assert compare("eq", logger.isEnabledFor(FINEST, "probe_pkg"), True)

    def test_updatesupportedpackages_valid_rem_clears_package_level(
        self, restore_kbot_singleton
    ) -> None:
        """Test 'rem' removes a previously registered package override."""
        UpdateSupportedPackages("add probe_pkg 5")

        UpdateSupportedPackages("rem probe_pkg")

        assert compare("eq", logger.isEnabledFor(FINEST, "probe_pkg"), False)

    def test_updatesupportedpackages_invalid_add_without_level_is_noop(
        self, restore_kbot_singleton
    ) -> None:
        """Test 'add' without a level argument does not register anything."""
        before = dict(logger._KbotLogger__filters)  # noqa: SLF001

        UpdateSupportedPackages("add probe_pkg_only_name")

        assert compare("eq", dict(logger._KbotLogger__filters), before)  # noqa: SLF001

    def test_updatesupportedpackages_invalid_non_numeric_level_is_noop(
        self, restore_kbot_singleton
    ) -> None:
        """Test 'add' with a non-numeric level does not register anything."""
        before = dict(logger._KbotLogger__filters)  # noqa: SLF001

        UpdateSupportedPackages("add probe_pkg notanumber")

        assert compare("eq", dict(logger._KbotLogger__filters), before)  # noqa: SLF001

    def test_updatesupportedpackages_invalid_unknown_command_returns_none(
        self, restore_kbot_singleton
    ) -> None:
        """Test an unrecognized command is handled without raising."""
        assert compare("eq", UpdateSupportedPackages("unknown command"), None)

    def test_updatesupportedpackages_invalid_swallows_addpackage_errors(
        self, restore_kbot_singleton, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test a failure in addPackage/remPackage is caught and does not propagate."""
        monkeypatch.setattr(
            logger, "addPackage", lambda *_a, **_kw: (_ for _ in ()).throw(RuntimeError("boom"))
        )

        assert compare("eq", UpdateSupportedPackages("add probe_pkg 3"), None)
