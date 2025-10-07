"""Tests for provider utils module."""

import io
import tarfile
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import httpx
import pytest

from kbot_installer.core.provider.utils import FileInfo
from kbot_installer.core.utils import optimized_download_and_extract


class TestFileInfo:
    """Test cases for FileInfo dataclass."""

    def test_file_info_creation(self) -> None:
        """Test FileInfo creation with all parameters."""
        file_info = FileInfo(
            name="test_product",
            host="nexus.example.com",
            repository="raw",
            branch="master",
            size=1024,
            temp_path="/tmp/test",
        )

        assert file_info.name == "test_product"
        assert file_info.host == "nexus.example.com"
        assert file_info.repository == "raw"
        assert file_info.branch == "master"
        assert file_info.size == 1024
        assert file_info.temp_path == "/tmp/test"

    def test_file_info_url_property(self) -> None:
        """Test FileInfo URL property generation."""
        file_info = FileInfo(
            name="test_product",
            host="nexus.example.com",
            repository="raw",
            branch="master",
        )

        expected_url = "https://nexus.example.com/repository/raw/master/test_product/test_product_latest.tar.gz"
        assert file_info.url == expected_url

    def test_file_info_filename_property(self) -> None:
        """Test FileInfo filename property."""
        file_info = FileInfo(
            name="test_product",
            host="nexus.example.com",
            repository="raw",
            branch="master",
        )

        assert file_info.filename == "test_product_latest.tar.gz"


class TestOptimizedDownloadAndExtract:
    """Test cases for optimized_download_and_extract function."""

    def test_optimized_download_and_extract_success(self) -> None:
        """Test successful download and extraction."""
        # Create a test tar.gz file in memory
        tar_data = io.BytesIO()
        with tarfile.open(fileobj=tar_data, mode="w:gz") as tar:
            # Add a test file
            test_content = b"test file content"
            tarinfo = tarfile.TarInfo(name="test.txt")
            tarinfo.size = len(test_content)
            tar.addfile(tarinfo, io.BytesIO(test_content))

        tar_data.seek(0)

        # Mock httpx.stream response
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_response.iter_bytes.return_value = tar_data

        with tempfile.TemporaryDirectory() as temp_dir:
            target_dir = Path(temp_dir)
            file_info = FileInfo(
                name="test_product",
                host="nexus.example.com",
                repository="raw",
                branch="master",
                temp_path=temp_dir,
            )

            with patch("httpx.stream") as mock_stream:
                mock_stream.return_value.__enter__.return_value = mock_response
                mock_stream.return_value.__exit__.return_value = None

                # Call the function
                optimized_download_and_extract(file_info.url, target_dir, None)

                # Verify the file was extracted
                extracted_file = target_dir / "test.txt"
                assert extracted_file.exists()
                assert extracted_file.read_text() == "test file content"

                # Verify httpx.stream was called with correct parameters
                mock_stream.assert_called_once_with(
                    "GET", file_info.url, timeout=60.0, auth=None
                )

    def test_optimized_download_and_extract_with_auth(self) -> None:
        """Test download and extraction with authentication."""
        # Create a test tar.gz file in memory
        tar_data = io.BytesIO()
        with tarfile.open(fileobj=tar_data, mode="w:gz") as tar:
            test_content = b"authenticated content"
            tarinfo = tarfile.TarInfo(name="auth_test.txt")
            tarinfo.size = len(test_content)
            tar.addfile(tarinfo, io.BytesIO(test_content))

        tar_data.seek(0)

        # Mock httpx.stream response
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_response.iter_bytes.return_value = tar_data

        # Mock auth object
        mock_auth = MagicMock(spec=httpx.Auth)

        with tempfile.TemporaryDirectory() as temp_dir:
            target_dir = Path(temp_dir)
            file_info = FileInfo(
                name="test_product",
                host="nexus.example.com",
                repository="raw",
                branch="master",
                temp_path=temp_dir,
            )

            with patch("httpx.stream") as mock_stream:
                mock_stream.return_value.__enter__.return_value = mock_response
                mock_stream.return_value.__exit__.return_value = None

                # Call the function with auth
                optimized_download_and_extract(file_info.url, target_dir, mock_auth)

                # Verify the file was extracted
                extracted_file = target_dir / "auth_test.txt"
                assert extracted_file.exists()
                assert extracted_file.read_text() == "authenticated content"

                # Verify httpx.stream was called with auth
                mock_stream.assert_called_once_with(
                    "GET", file_info.url, timeout=60.0, auth=mock_auth
                )

    def test_optimized_download_and_extract_http_error(self) -> None:
        """Test download and extraction with HTTP error."""
        with tempfile.TemporaryDirectory() as temp_dir:
            target_dir = Path(temp_dir)
            file_info = FileInfo(
                name="test_product",
                host="nexus.example.com",
                repository="raw",
                branch="master",
                temp_path=temp_dir,
            )

            # Mock httpx.stream response with HTTP error
            mock_response = MagicMock()
            mock_response.raise_for_status.side_effect = httpx.HTTPError(
                "404 Not Found"
            )

            with patch("httpx.stream") as mock_stream:
                mock_stream.return_value.__enter__.return_value = mock_response
                mock_stream.return_value.__exit__.return_value = None

                # Call the function and expect HTTP error
                with pytest.raises(httpx.HTTPError, match="404 Not Found"):
                    optimized_download_and_extract(file_info.url, target_dir, None)

    def test_optimized_download_and_extract_tar_error(self) -> None:
        """Test download and extraction with corrupted tar file."""
        # Create invalid tar data
        invalid_tar_data = b"not a valid tar file"

        # Mock httpx.stream response
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_response.iter_bytes.return_value = io.BytesIO(invalid_tar_data)

        with tempfile.TemporaryDirectory() as temp_dir:
            target_dir = Path(temp_dir)
            file_info = FileInfo(
                name="test_product",
                host="nexus.example.com",
                repository="raw",
                branch="master",
                temp_path=temp_dir,
            )

            with patch("httpx.stream") as mock_stream:
                mock_stream.return_value.__enter__.return_value = mock_response
                mock_stream.return_value.__exit__.return_value = None

                # Call the function and expect tar error
                with pytest.raises(tarfile.TarError):
                    optimized_download_and_extract(file_info.url, target_dir, None)

    def test_optimized_download_and_extract_creates_target_directory(self) -> None:
        """Test that target directory is created if it doesn't exist."""
        # Create a test tar.gz file in memory
        tar_data = io.BytesIO()
        with tarfile.open(fileobj=tar_data, mode="w:gz") as tar:
            test_content = b"test content"
            tarinfo = tarfile.TarInfo(name="test.txt")
            tarinfo.size = len(test_content)
            tar.addfile(tarinfo, io.BytesIO(test_content))

        tar_data.seek(0)

        # Mock httpx.stream response
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_response.iter_bytes.return_value = tar_data

        with tempfile.TemporaryDirectory() as temp_dir:
            # Create a nested directory that doesn't exist
            target_dir = Path(temp_dir) / "nested" / "directory"
            file_info = FileInfo(
                name="test_product",
                host="nexus.example.com",
                repository="raw",
                branch="master",
                temp_path=str(target_dir),
            )

            with patch("httpx.stream") as mock_stream:
                mock_stream.return_value.__enter__.return_value = mock_response
                mock_stream.return_value.__exit__.return_value = None

                # Call the function
                optimized_download_and_extract(file_info.url, target_dir, None)

                # Verify the directory was created
                assert target_dir.exists()
                assert target_dir.is_dir()

                # Verify the file was extracted
                extracted_file = target_dir / "test.txt"
                assert extracted_file.exists()
