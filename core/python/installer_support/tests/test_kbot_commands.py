"""Tests for installer_support.kbot_commands."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from installer_support.kbot_commands import run_kbot_command, run_kbot_iam_load, validate_license


class TestRunKbotCommand:
    """Tests for run_kbot_command."""

    def test_runkbotcommand_valid_invokes_kbot_sh_with_the_given_subcommand(self, tmp_path: Path) -> None:
        with patch(
            "installer_support.kbot_commands.subprocess.run",
            return_value=MagicMock(returncode=0),
        ) as mock_run:
            run_kbot_command(tmp_path, "load")

        mock_run.assert_called_once_with([str(tmp_path / "bin" / "kbot.sh"), "load"], check=False)

    def test_runkbotcommand_invalid_raises_when_command_fails(self, tmp_path: Path) -> None:
        with (
            patch(
                "installer_support.kbot_commands.subprocess.run",
                return_value=MagicMock(returncode=1),
            ),
            pytest.raises(RuntimeError, match="learn"),
        ):
            run_kbot_command(tmp_path, "learn")


def _write_python_sh(workarea_path: Path, *, output: str, exit_code: int) -> None:
    """Write a stand-in 'bin/python.sh' printing `output` and exiting with `exit_code`."""
    python_sh = workarea_path / "bin" / "python.sh"
    python_sh.parent.mkdir(parents=True)
    python_sh.write_text(f"#!/bin/sh\necho '{output}'\nexit {exit_code}\n")
    python_sh.chmod(0o755)


class TestValidateLicense:
    """Tests for validate_license."""

    def test_validatelicense_valid_returns(self, tmp_path: Path) -> None:
        _write_python_sh(tmp_path, output="Valid LICENSE", exit_code=0)

        validate_license(tmp_path)

    def test_validatelicense_invalid_raises_with_checker_reason(self, tmp_path: Path) -> None:
        _write_python_sh(tmp_path, output="ERROR : LICENSE is expired.", exit_code=1)

        with pytest.raises(RuntimeError, match=r"license\.key.*LICENSE is expired"):
            validate_license(tmp_path)


class TestRunKbotIamLoad:
    """Tests for run_kbot_iam_load."""

    def test_runkbotiamload_valid_invokes_core_sh_load_profiles(self, tmp_path: Path) -> None:
        """'core.sh load -p' is used: unlike 'kbot.sh load', it forwards '-p' to Load.py."""
        with patch(
            "installer_support.kbot_commands.subprocess.run",
            return_value=MagicMock(returncode=0),
        ) as mock_run:
            run_kbot_iam_load(tmp_path)

        mock_run.assert_called_once_with([str(tmp_path / "bin" / "core.sh"), "load", "-p"], check=False)

    def test_runkbotiamload_invalid_raises_when_command_fails(self, tmp_path: Path) -> None:
        """A non-zero exit status is reported as an error."""
        with (
            patch(
                "installer_support.kbot_commands.subprocess.run",
                return_value=MagicMock(returncode=1),
            ),
            pytest.raises(RuntimeError, match="load -p"),
        ):
            run_kbot_iam_load(tmp_path)
