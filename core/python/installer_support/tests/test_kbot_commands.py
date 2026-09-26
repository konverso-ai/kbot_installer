"""Tests for installer_support.kbot_commands."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from installer_support.kbot_commands import run_kbot_command


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
