"""Tests for installable.factory module."""

from pathlib import Path
from unittest.mock import MagicMock, patch

from installable.factory import build_workarea
from installable.workarea_installable import WorkareaInstallable
from workarea.rule_action import RuleAction
from workarea.workarea_rule import WorkareaRule


class TestBuildWorkarea:
    """Test cases for build_workarea."""

    def test_buildworkarea_valid_returns_workareainstallable_without_installing(
        self, tmp_path: Path
    ) -> None:
        installer_path = tmp_path / "installer"
        workarea_path = tmp_path / "work"

        mock_product_a = MagicMock(name="dependency")
        mock_product_a.name = "dependency"
        mock_product_b = MagicMock(name="top_level")
        mock_product_b.name = "top_level"
        mock_service = MagicMock()
        mock_service.load_products_from_disk.return_value = [mock_product_a, mock_product_b]

        with patch(
            "installer_support.installer_service.InstallerService",
            return_value=mock_service,
        ) as mock_service_cls:
            result = build_workarea(installer_path, workarea_path)

        mock_service_cls.assert_called_once_with(installer_path)
        assert isinstance(result, WorkareaInstallable)
        assert result.workarea.installer_root == installer_path
        assert result.workarea.work_root == workarea_path
        assert result.workarea.products == [Path("dependency"), Path("top_level")]
        # No install-time side effects: install() was never called on the result.

    def test_buildworkarea_valid_loads_default_rules(self, tmp_path: Path) -> None:
        installer_path = tmp_path / "installer"
        workarea_path = tmp_path / "work"

        mock_service = MagicMock()
        mock_service.load_products_from_disk.return_value = []
        sentinel_rule = WorkareaRule(source=Path("core"), action=RuleAction.LINK)

        with (
            patch(
                "installer_support.installer_service.InstallerService",
                return_value=mock_service,
            ),
            patch("installable.factory.load_default_rules", return_value=[sentinel_rule]) as mock_rules,
        ):
            result = build_workarea(installer_path, workarea_path)

        mock_rules.assert_called_once_with()
        assert result.workarea.rules == [sentinel_rule]
