"""Tests for LicensePrompter class."""

import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

from kbot_installer.core.interactivity.license_prompter import LicensePrompter


class TestLicensePrompterInitialization:
    """Test cases for LicensePrompter initialization."""

    def test_init_defaults(self) -> None:
        """Test initialization with default values."""
        prompter = LicensePrompter()
        assert prompter.use_defaults is False
        assert prompter.silent is False

    def test_init_use_defaults(self) -> None:
        """Test initialization with use_defaults=True."""
        prompter = LicensePrompter(use_defaults=True)
        assert prompter.use_defaults is True

    def test_init_silent(self) -> None:
        """Test initialization with silent=True."""
        prompter = LicensePrompter(silent=True)
        assert prompter.silent is True


class TestLicensePrompterPromptLicenseAgreement:
    """Test cases for LicensePrompter.prompt_license_agreement."""

    def test_prompt_license_agreement_license_key_exists(self) -> None:
        """Test prompt_license_agreement when license.key already exists."""
        with tempfile.TemporaryDirectory() as temp_dir:
            target_path = Path(temp_dir)
            license_key = target_path / "license.key"
            license_key.write_text("", encoding="utf-8")

            prompter = LicensePrompter()
            result = prompter.prompt_license_agreement(target_path)
            assert result is True

    def test_prompt_license_agreement_license_accepted_param(self) -> None:
        """Test prompt_license_agreement with license_accepted=True."""
        with tempfile.TemporaryDirectory() as temp_dir:
            target_path = Path(temp_dir)
            prompter = LicensePrompter()
            result = prompter.prompt_license_agreement(
                target_path, license_accepted=True
            )
            assert result is True

    def test_prompt_license_agreement_use_defaults(self) -> None:
        """Test prompt_license_agreement with use_defaults=True."""
        with tempfile.TemporaryDirectory() as temp_dir:
            target_path = Path(temp_dir)
            prompter = LicensePrompter(use_defaults=True)
            result = prompter.prompt_license_agreement(target_path)
            assert result is True
            # Should create license.key file
            license_key = target_path / "license.key"
            assert license_key.exists()

    @patch("builtins.input", return_value="y")
    @patch("builtins.print")
    def test_prompt_license_agreement_accepts_license(
        self, mock_print: Mock, mock_input: Mock
    ) -> None:
        """Test prompt_license_agreement when user accepts license."""
        with tempfile.TemporaryDirectory() as temp_dir:
            target_path = Path(temp_dir)
            prompter = LicensePrompter()

            # Mock LICENSE file does not exist (but license.key should be created)
            original_exists = Path.exists

            def mock_exists(self_path: Path) -> bool:
                # LICENSE file doesn't exist, but other files work normally
                if "LICENSE" in str(self_path):
                    return False
                # Use original exists for license.key
                return original_exists(self_path)

            with patch(
                "pathlib.Path.exists",
                side_effect=mock_exists,
                autospec=True,
            ):
                result = prompter.prompt_license_agreement(target_path)
                assert result is True
                license_key = target_path / "license.key"
                assert license_key.exists()

    @patch("builtins.input", return_value="n")
    @patch("builtins.print")
    def test_prompt_license_agreement_rejects_license(
        self, mock_print: Mock, mock_input: Mock
    ) -> None:
        """Test prompt_license_agreement when user rejects license."""
        with tempfile.TemporaryDirectory() as temp_dir:
            target_path = Path(temp_dir)
            prompter = LicensePrompter()

            # Mock LICENSE file exists
            with patch(
                "kbot_installer.core.interactivity.license_prompter.Path.exists",
                return_value=False,
            ):
                result = prompter.prompt_license_agreement(target_path)
                assert result is False
                license_key = target_path / "license.key"
                assert not license_key.exists()

    @patch("builtins.input", return_value="y")
    @patch("builtins.print")
    @patch(
        "kbot_installer.core.interactivity.license_prompter.Path.read_text",
        return_value="MIT License\nCopyright...",
    )
    def test_prompt_license_agreement_displays_license(
        self, mock_read_text: Mock, mock_print: Mock, mock_input: Mock
    ) -> None:
        """Test prompt_license_agreement displays license text when file exists."""
        with tempfile.TemporaryDirectory() as temp_dir:
            target_path = Path(temp_dir)
            prompter = LicensePrompter()

            # Mock LICENSE file exists and can be read
            original_exists = Path.exists

            def mock_exists(self_path: Path) -> bool:
                # LICENSE file exists
                if "LICENSE" in str(self_path):
                    return True
                # Use original exists for license.key
                return original_exists(self_path)

            with patch(
                "pathlib.Path.exists",
                side_effect=mock_exists,
                autospec=True,
            ):
                result = prompter.prompt_license_agreement(target_path)
                assert result is True
                # Should print license text
                assert mock_print.called
                license_key = target_path / "license.key"
                assert license_key.exists()


