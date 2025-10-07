"""Tests for utils module."""

import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from kbot_installer.core.utils import ensure_directory, version_to_branch


class TestVersionToBranch:
    """Test cases for version_to_branch function."""

    def test_version_to_branch_dev(self) -> None:
        """Test version_to_branch with 'dev' version."""
        result = version_to_branch("dev")
        assert result == "dev"

    def test_version_to_branch_master(self) -> None:
        """Test version_to_branch with 'master' version."""
        result = version_to_branch("master")
        assert result == "master"

    def test_version_to_branch_release_version(self) -> None:
        """Test version_to_branch with release version."""
        result = version_to_branch("2025.03")
        assert result == "release-2025.03"

    def test_version_to_branch_release_version_with_dash(self) -> None:
        """Test version_to_branch with release version containing dashes."""
        result = version_to_branch("2025.03.1")
        assert result == "release-2025.03.1"

    def test_version_to_branch_dev_suffix(self) -> None:
        """Test version_to_branch with dev suffix."""
        result = version_to_branch("2025.03-dev")
        assert result == "release-2025.03-dev"

    def test_version_to_branch_dev_suffix_complex(self) -> None:
        """Test version_to_branch with complex dev suffix."""
        result = version_to_branch("2025.03.1-dev")
        assert result == "release-2025.03.1-dev"

    def test_version_to_branch_empty_string(self) -> None:
        """Test version_to_branch with empty string."""
        result = version_to_branch("")
        assert result == "release-"

    def test_version_to_branch_special_characters(self) -> None:
        """Test version_to_branch with special characters."""
        result = version_to_branch("v1.0.0")
        assert result == "release-v1.0.0"

    def test_version_to_branch_numeric_only(self) -> None:
        """Test version_to_branch with numeric only version."""
        result = version_to_branch("123")
        assert result == "release-123"


class TestEnsureDirectory:
    """Test cases for ensure_directory function."""

    def test_ensure_directory_existing_directory(self) -> None:
        """Test ensure_directory with existing directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            result = ensure_directory(temp_dir)
            assert isinstance(result, Path)
            assert result.exists()
            assert result.is_dir()

    def test_ensure_directory_new_directory(self) -> None:
        """Test ensure_directory with new directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            new_dir = Path(temp_dir) / "new_subdir"
            result = ensure_directory(new_dir)
            assert isinstance(result, Path)
            assert result.exists()
            assert result.is_dir()
            assert result == new_dir

    def test_ensure_directory_nested_directories(self) -> None:
        """Test ensure_directory with nested directories."""
        with tempfile.TemporaryDirectory() as temp_dir:
            nested_dir = Path(temp_dir) / "level1" / "level2" / "level3"
            result = ensure_directory(nested_dir)
            assert isinstance(result, Path)
            assert result.exists()
            assert result.is_dir()
            assert result == nested_dir

    def test_ensure_directory_with_string_path(self) -> None:
        """Test ensure_directory with string path."""
        with tempfile.TemporaryDirectory() as temp_dir:
            string_path = str(Path(temp_dir) / "string_path")
            result = ensure_directory(string_path)
            assert isinstance(result, Path)
            assert result.exists()
            assert result.is_dir()

    def test_ensure_directory_with_path_object(self) -> None:
        """Test ensure_directory with Path object."""
        with tempfile.TemporaryDirectory() as temp_dir:
            path_obj = Path(temp_dir) / "path_object"
            result = ensure_directory(path_obj)
            assert isinstance(result, Path)
            assert result.exists()
            assert result.is_dir()
            assert result == path_obj

    def test_ensure_directory_already_exists(self) -> None:
        """Test ensure_directory when directory already exists."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create directory first
            existing_dir = Path(temp_dir) / "existing"
            existing_dir.mkdir()

            # Call ensure_directory on existing directory
            result = ensure_directory(existing_dir)
            assert isinstance(result, Path)
            assert result.exists()
            assert result.is_dir()
            assert result == existing_dir

    def test_ensure_directory_parents_true(self) -> None:
        """Test ensure_directory creates parent directories."""
        with tempfile.TemporaryDirectory() as temp_dir:
            deep_dir = Path(temp_dir) / "a" / "b" / "c" / "d"
            result = ensure_directory(deep_dir)
            assert isinstance(result, Path)
            assert result.exists()
            assert result.is_dir()
            assert result == deep_dir

    @patch("pathlib.Path.mkdir")
    def test_ensure_directory_os_error(self, mock_mkdir) -> None:
        """Test ensure_directory raises OSError when mkdir fails."""
        mock_mkdir.side_effect = OSError("Permission denied")

        with pytest.raises(OSError, match="Permission denied"):
            ensure_directory("/invalid/path")

    def test_ensure_directory_return_type(self) -> None:
        """Test ensure_directory returns Path object."""
        with tempfile.TemporaryDirectory() as temp_dir:
            result = ensure_directory(temp_dir)
            assert isinstance(result, Path)

    def test_ensure_directory_relative_path(self) -> None:
        """Test ensure_directory with relative path."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Change to temp directory
            import os

            original_cwd = Path.cwd()
            try:
                os.chdir(temp_dir)
                result = ensure_directory("relative_dir")
                assert isinstance(result, Path)
                assert result.exists()
                assert result.is_dir()
                assert result.name == "relative_dir"
            finally:
                os.chdir(original_cwd)
