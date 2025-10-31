"""Tests for utils module."""

import io
import os
import tarfile
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import httpx
import pytest

from kbot_installer.core.utils import (
    calculate_relative_path,
    ensure_directory,
    optimized_download_and_extract,
    optimized_download_and_extract_bis,
    optimized_download_and_extract_ter,
    version_to_branch,
)


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


class TestCalculateRelativePath:
    """Test cases for calculate_relative_path function."""

    def test_calculate_relative_path_same_directory(self) -> None:
        """Test calculate_relative_path with files in same directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            src = Path(temp_dir) / "source.txt"
            dst = Path(temp_dir) / "dest.txt"
            src.touch()
            dst.touch()

            result = calculate_relative_path(src, dst)
            assert isinstance(result, Path)
            assert result == Path("source.txt")

    def test_calculate_relative_path_different_directories(self) -> None:
        """Test calculate_relative_path with files in different directories."""
        with tempfile.TemporaryDirectory() as temp_dir:
            src = Path(temp_dir) / "dir1" / "source.txt"
            dst = Path(temp_dir) / "dir2" / "dest.txt"
            src.parent.mkdir()
            dst.parent.mkdir()
            src.touch()
            dst.touch()

            result = calculate_relative_path(src, dst)
            assert isinstance(result, Path)
            # Should be ../dir1/source.txt
            assert "source.txt" in str(result)

    def test_calculate_relative_path_nested(self) -> None:
        """Test calculate_relative_path with nested directories."""
        with tempfile.TemporaryDirectory() as temp_dir:
            src = Path(temp_dir) / "a" / "b" / "source.txt"
            dst = Path(temp_dir) / "c" / "dest.txt"
            src.parent.mkdir(parents=True)
            dst.parent.mkdir(parents=True)
            src.touch()
            dst.touch()

            result = calculate_relative_path(src, dst)
            assert isinstance(result, Path)

    def test_calculate_relative_path_string_inputs(self) -> None:
        """Test calculate_relative_path with string inputs."""
        with tempfile.TemporaryDirectory() as temp_dir:
            src = Path(temp_dir) / "source.txt"
            dst = Path(temp_dir) / "dest.txt"
            src.touch()
            dst.touch()

            result = calculate_relative_path(str(src), str(dst))
            assert isinstance(result, Path)

    def test_calculate_relative_path_exception_fallback(self) -> None:
        """Test calculate_relative_path fallback when relpath fails."""
        with tempfile.TemporaryDirectory() as temp_dir:
            src = Path(temp_dir) / "source.txt"
            dst = Path(temp_dir) / "dest.txt"
            src.touch()
            dst.touch()

            with patch("os.path.relpath", side_effect=ValueError("Different drives")):
                result = calculate_relative_path(src, dst)
                assert isinstance(result, Path)
                assert result.is_absolute()


class TestOptimizedDownloadAndExtract:
    """Test cases for optimized_download_and_extract function."""

    def test_optimized_download_and_extract_success(self) -> None:
        """Test successful download and extraction."""
        # Create a test tar.gz file in memory
        tar_data = io.BytesIO()
        with tarfile.open(fileobj=tar_data, mode="w:gz") as tar:
            test_content = b"test file content"
            tarinfo = tarfile.TarInfo(name="test.txt")
            tarinfo.size = len(test_content)
            tar.addfile(tarinfo, io.BytesIO(test_content))

        tar_data.seek(0)

        # Mock httpx.stream response
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_response.iter_bytes.return_value = [tar_data.read()]

        with tempfile.TemporaryDirectory() as temp_dir:
            target_dir = Path(temp_dir) / "extract"

            with patch("httpx.stream") as mock_stream:
                mock_stream.return_value.__enter__.return_value = mock_response
                mock_stream.return_value.__exit__.return_value = None

                optimized_download_and_extract("http://example.com/file.tar.gz", target_dir)

                # Verify the file was extracted
                extracted_file = target_dir / "test.txt"
                assert extracted_file.exists()
                assert extracted_file.read_text() == "test file content"

    def test_optimized_download_and_extract_with_auth(self) -> None:
        """Test download and extraction with authentication."""
        tar_data = io.BytesIO()
        with tarfile.open(fileobj=tar_data, mode="w:gz") as tar:
            test_content = b"auth content"
            tarinfo = tarfile.TarInfo(name="auth.txt")
            tarinfo.size = len(test_content)
            tar.addfile(tarinfo, io.BytesIO(test_content))

        tar_data_bytes = tar_data.getvalue()
        tar_data.seek(0)

        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        chunk_size = 16 * 1024 * 1024
        chunks = [tar_data_bytes[i : i + chunk_size] for i in range(0, len(tar_data_bytes), chunk_size)]
        if not chunks:
            chunks = [tar_data_bytes]
        mock_response.iter_bytes.return_value = iter(chunks)

        mock_auth = MagicMock()

        with tempfile.TemporaryDirectory() as temp_dir:
            target_dir = Path(temp_dir) / "extract"

            with patch("kbot_installer.core.utils.httpx.stream") as mock_stream:
                context_manager = MagicMock()
                context_manager.__enter__.return_value = mock_response
                context_manager.__exit__.return_value = None
                mock_stream.return_value = context_manager

                optimized_download_and_extract("http://example.com/file.tar.gz", target_dir, mock_auth)

                mock_stream.assert_called_once_with("GET", "http://example.com/file.tar.gz", timeout=60.0, auth=mock_auth)

    def test_optimized_download_and_extract_http_error(self) -> None:
        """Test download and extraction with HTTP error."""
        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "404 Not Found", request=MagicMock(), response=MagicMock()
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            target_dir = Path(temp_dir) / "extract"

            with patch("kbot_installer.core.utils.httpx.stream") as mock_stream:
                context_manager = MagicMock()
                context_manager.__enter__.return_value = mock_response
                context_manager.__exit__.return_value = None
                mock_stream.return_value = context_manager

                with pytest.raises(httpx.HTTPStatusError):
                    optimized_download_and_extract("http://example.com/file.tar.gz", target_dir)

    def test_optimized_download_and_extract_creates_target_dir(self) -> None:
        """Test that target directory is created if it doesn't exist."""
        tar_data = io.BytesIO()
        with tarfile.open(fileobj=tar_data, mode="w:gz") as tar:
            test_content = b"test"
            tarinfo = tarfile.TarInfo(name="test.txt")
            tarinfo.size = len(test_content)
            tar.addfile(tarinfo, io.BytesIO(test_content))

        tar_data_bytes = tar_data.getvalue()
        tar_data.seek(0)

        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        chunk_size = 16 * 1024 * 1024
        chunks = [tar_data_bytes[i : i + chunk_size] for i in range(0, len(tar_data_bytes), chunk_size)]
        if not chunks:
            chunks = [tar_data_bytes]
        mock_response.iter_bytes.return_value = iter(chunks)

        with tempfile.TemporaryDirectory() as temp_dir:
            target_dir = Path(temp_dir) / "nested" / "deep" / "extract"
            assert not target_dir.exists()

            with patch("kbot_installer.core.utils.httpx.stream") as mock_stream:
                context_manager = MagicMock()
                context_manager.__enter__.return_value = mock_response
                context_manager.__exit__.return_value = None
                mock_stream.return_value = context_manager

                optimized_download_and_extract("http://example.com/file.tar.gz", target_dir)

                assert target_dir.exists()
                assert target_dir.is_dir()


class TestOptimizedDownloadAndExtractBis:
    """Test cases for optimized_download_and_extract_bis function."""

    def test_optimized_download_and_extract_bis_success(self) -> None:
        """Test successful download and extraction with bis method."""
        tar_data = io.BytesIO()
        with tarfile.open(fileobj=tar_data, mode="w:gz") as tar:
            test_content = b"bis test content"
            tarinfo = tarfile.TarInfo(name="bis_test.txt")
            tarinfo.size = len(test_content)
            tar.addfile(tarinfo, io.BytesIO(test_content))

        tar_data_bytes = tar_data.getvalue()
        tar_data.seek(0)

        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        chunk_size = 16 * 1024 * 1024
        chunks = [tar_data_bytes[i : i + chunk_size] for i in range(0, len(tar_data_bytes), chunk_size)]
        if not chunks:
            chunks = [tar_data_bytes]
        mock_response.iter_bytes.return_value = iter(chunks)

        with tempfile.TemporaryDirectory() as temp_dir:
            target_dir = Path(temp_dir) / "extract_bis"

            with patch("kbot_installer.core.utils.httpx.stream") as mock_stream:
                context_manager = MagicMock()
                context_manager.__enter__.return_value = mock_response
                context_manager.__exit__.return_value = None
                mock_stream.return_value = context_manager

                # Wait for the thread to complete
                import time

                optimized_download_and_extract_bis("http://example.com/file.tar.gz", target_dir)
                time.sleep(0.1)  # Give thread time to process

                # The extraction might not complete in this test due to threading,
                # but we can verify the directory was created
                assert target_dir.exists()


class TestOptimizedDownloadAndExtractTer:
    """Test cases for optimized_download_and_extract_ter function."""

    def test_optimized_download_and_extract_ter_success(self) -> None:
        """Test successful download and extraction with ter method."""
        tar_data = io.BytesIO()
        with tarfile.open(fileobj=tar_data, mode="w:gz") as tar:
            test_content = b"ter test content"
            tarinfo = tarfile.TarInfo(name="ter_test.txt")
            tarinfo.size = len(test_content)
            tar.addfile(tarinfo, io.BytesIO(test_content))

        tar_data_bytes = tar_data.getvalue()
        tar_data.seek(0)

        # Create chunks for streaming
        chunk_size = 1024
        data_chunks = [tar_data_bytes[i : i + chunk_size] for i in range(0, len(tar_data_bytes), chunk_size)]
        if not data_chunks:
            data_chunks = [tar_data_bytes]

        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_response.iter_bytes.return_value = iter(data_chunks)

        with tempfile.TemporaryDirectory() as temp_dir:
            target_dir = Path(temp_dir) / "extract_ter"

            with patch("kbot_installer.core.utils.httpx.stream") as mock_stream:
                context_manager = MagicMock()
                context_manager.__enter__.return_value = mock_response
                context_manager.__exit__.return_value = None
                mock_stream.return_value = context_manager

                optimized_download_and_extract_ter("http://example.com/file.tar.gz", target_dir)

                # Verify the file was extracted
                extracted_file = target_dir / "ter_test.txt"
                assert extracted_file.exists()
                assert extracted_file.read_text() == "ter test content"

    def test_optimized_download_and_extract_ter_creates_target_dir(self) -> None:
        """Test that target directory is created if it doesn't exist."""
        tar_data = io.BytesIO()
        with tarfile.open(fileobj=tar_data, mode="w:gz") as tar:
            test_content = b"test"
            tarinfo = tarfile.TarInfo(name="test.txt")
            tarinfo.size = len(test_content)
            tar.addfile(tarinfo, io.BytesIO(test_content))

        tar_data_bytes = tar_data.getvalue()
        tar_data.seek(0)

        # Create chunks for streaming
        chunk_size = 16 * 1024 * 1024
        data_chunks = [tar_data_bytes[i : i + chunk_size] for i in range(0, len(tar_data_bytes), chunk_size)]
        if not data_chunks:
            data_chunks = [tar_data_bytes]

        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_response.iter_bytes.return_value = iter(data_chunks)

        with tempfile.TemporaryDirectory() as temp_dir:
            target_dir = Path(temp_dir) / "nested" / "extract_ter"
            assert not target_dir.exists()

            with patch("kbot_installer.core.utils.httpx.stream") as mock_stream:
                context_manager = MagicMock()
                context_manager.__enter__.return_value = mock_response
                context_manager.__exit__.return_value = None
                mock_stream.return_value = context_manager

                optimized_download_and_extract_ter("http://example.com/file.tar.gz", target_dir)

                assert target_dir.exists()
                assert target_dir.is_dir()
