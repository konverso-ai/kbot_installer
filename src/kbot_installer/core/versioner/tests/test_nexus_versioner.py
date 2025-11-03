"""Tests for nexus_versioner module."""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from kbot_installer.core.auth.http_auth.http_auth_base import HttpAuthBase
from kbot_installer.core.versioner.nexus_versioner import NexusVersioner
from kbot_installer.core.versioner.versioner_base import VersionerError


class TestNexusVersioner:
    """Test cases for NexusVersioner class."""

    @pytest.fixture
    def versioner(self) -> NexusVersioner:
        """Create a NexusVersioner instance for testing."""
        return NexusVersioner(domain="konverso.ai", repository="kbot_raw", auth=None)

    @pytest.fixture
    def versioner_with_auth(self) -> NexusVersioner:
        """Create a NexusVersioner instance with authentication."""
        mock_auth = MagicMock(spec=HttpAuthBase)
        return NexusVersioner(
            domain="konverso.ai", repository="kbot_raw", auth=mock_auth
        )

    def test_initialization(self) -> None:
        """Test NexusVersioner initialization."""
        versioner = NexusVersioner("konverso.ai", "kbot_raw")

        assert versioner.domain == "konverso.ai"
        assert versioner.repository == "kbot_raw"
        assert versioner.auth is None
        assert versioner.name == "nexus"
        assert versioner.base_url == "https://konverso.ai"

    def test_initialization_with_auth(self) -> None:
        """Test NexusVersioner initialization with authentication."""
        mock_auth = MagicMock(spec=HttpAuthBase)
        versioner = NexusVersioner("konverso.ai", "kbot_raw", mock_auth)

        assert versioner.domain == "konverso.ai"
        assert versioner.repository == "kbot_raw"
        assert versioner.auth is mock_auth
        assert versioner.name == "nexus"
        assert versioner.base_url == "https://konverso.ai"

    def test_get_auth(self, versioner: NexusVersioner) -> None:
        """Test _get_auth method."""
        assert versioner._get_auth() is None

    def test_get_auth_with_auth(self, versioner_with_auth: NexusVersioner) -> None:
        """Test _get_auth method with authentication."""
        assert versioner_with_auth._get_auth() is versioner_with_auth.auth

    def test_clone_success(self, versioner: NexusVersioner) -> None:
        """Test successful clone operation."""
        with tempfile.TemporaryDirectory() as temp_dir:
            target_path = Path(temp_dir) / "test_repo"

            with patch.object(versioner, "_download_repository") as mock_download:
                mock_download.return_value = None

                versioner.clone("test_repo", target_path)

                mock_download.assert_called_once_with("test_repo", target_path)

    def test_clone_handles_download_error(self, versioner: NexusVersioner) -> None:
        """Test clone handles download error."""
        with tempfile.TemporaryDirectory() as temp_dir:
            target_path = Path(temp_dir) / "test_repo"

            with patch.object(versioner, "_download_repository") as mock_download:
                mock_download.side_effect = Exception("Download failed")

                with pytest.raises(VersionerError, match="Failed to clone repository"):
                    versioner.clone("test_repo", target_path)

    def test_checkout_not_supported(self, versioner: NexusVersioner) -> None:
        """Test checkout raises error as not supported."""
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_path = Path(temp_dir) / "test_repo"

            with pytest.raises(
                VersionerError, match="Checkout not supported for Nexus repositories"
            ):
                versioner.checkout(repo_path, "main")

    def test_select_branch_not_supported(self, versioner: NexusVersioner) -> None:
        """Test select_branch raises error as not supported."""
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_path = Path(temp_dir) / "test_repo"

            with pytest.raises(
                VersionerError,
                match="Branch selection not supported for Nexus repositories",
            ):
                versioner.select_branch(repo_path, ["main", "master"])

    def test_add_not_supported(self, versioner: NexusVersioner) -> None:
        """Test add raises error as not supported."""
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_path = Path(temp_dir) / "test_repo"

            with pytest.raises(
                VersionerError,
                match="Git operations not supported for Nexus repositories",
            ):
                versioner.add(repo_path, ["file.txt"])

    def test_pull_equivalent_to_clone(self, versioner: NexusVersioner) -> None:
        """Test pull is equivalent to clone for Nexus repositories."""
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_path = Path(temp_dir) / "test_repo"

            # Mock the clone method to avoid actual download
            with patch.object(versioner, "clone") as mock_clone:
                versioner.pull(repo_path, "main")

                # Verify clone was called with the correct arguments
                mock_clone.assert_called_once_with("test_repo", repo_path)

    def test_pull_with_different_branch(self, versioner: NexusVersioner) -> None:
        """Test pull ignores branch parameter for Nexus repositories."""
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_path = Path(temp_dir) / "my_repo"

            # Mock the clone method to avoid actual download
            with patch.object(versioner, "clone") as mock_clone:
                versioner.pull(repo_path, "develop")

                # Verify clone was called with the correct arguments (branch ignored)
                mock_clone.assert_called_once_with("my_repo", repo_path)

    def test_pull_with_string_path(self, versioner: NexusVersioner) -> None:
        """Test pull works with string path."""
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_path = str(Path(temp_dir) / "string_repo")

            # Mock the clone method to avoid actual download
            with patch.object(versioner, "clone") as mock_clone:
                versioner.pull(repo_path, "main")

                # Verify clone was called with the correct arguments
                mock_clone.assert_called_once_with("string_repo", repo_path)

    def test_pull_with_nested_path(self, versioner: NexusVersioner) -> None:
        """Test pull extracts repository name from nested path."""
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_path = Path(temp_dir) / "nested" / "deep" / "repository_name"

            # Mock the clone method to avoid actual download
            with patch.object(versioner, "clone") as mock_clone:
                versioner.pull(repo_path, "main")

                # Verify clone was called with the correct repository name
                mock_clone.assert_called_once_with("repository_name", repo_path)

    def test_pull_clone_failure(self, versioner: NexusVersioner) -> None:
        """Test pull handles clone failure."""
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_path = Path(temp_dir) / "failing_repo"

            # Mock clone to raise an exception
            with patch.object(versioner, "clone") as mock_clone:
                mock_clone.side_effect = VersionerError("Clone failed")

                with pytest.raises(
                    VersionerError, match="Failed to pull latest changes"
                ):
                    versioner.pull(repo_path, "main")

    def test_pull_with_auth(self, versioner_with_auth: NexusVersioner) -> None:
        """Test pull works with authentication."""
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_path = Path(temp_dir) / "auth_repo"

            # Mock the clone method to avoid actual download
            with patch.object(versioner_with_auth, "clone") as mock_clone:
                versioner_with_auth.pull(repo_path, "main")

                # Verify clone was called with the correct arguments
                mock_clone.assert_called_once_with("auth_repo", repo_path)

    def test_pull_logs_success_message(self, versioner: NexusVersioner) -> None:
        """Test pull logs success message."""
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_path = Path(temp_dir) / "logged_repo"

            # Mock the clone method to avoid actual download
            with patch.object(versioner, "clone"):
                with patch(
                    "kbot_installer.core.versioner.nexus_versioner.logger"
                ) as mock_logger:
                    versioner.pull(repo_path, "main")

                    # Verify success message was logged
                    mock_logger.info.assert_called_once_with(
                        "Successfully pulled latest version of repository '%s' to %s",
                        "logged_repo",
                        repo_path,
                    )

    def test_commit_not_supported(self, versioner: NexusVersioner) -> None:
        """Test commit raises error as not supported."""
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_path = Path(temp_dir) / "test_repo"

            with pytest.raises(
                VersionerError,
                match="Git operations not supported for Nexus repositories",
            ):
                versioner.commit(repo_path, "Test commit")

    def test_push_not_supported(self, versioner: NexusVersioner) -> None:
        """Test push raises error as not supported."""
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_path = Path(temp_dir) / "test_repo"

            with pytest.raises(
                VersionerError,
                match="Git operations not supported for Nexus repositories",
            ):
                versioner.push(repo_path, "main")

    def test_check_remote_repository_exists_success(
        self, versioner: NexusVersioner
    ) -> None:
        """Test check_remote_repository_exists with successful response."""
        with patch.object(
            versioner, "_check_nexus_repository_exists_sync"
        ) as mock_check:
            mock_check.return_value = True

            result = versioner.check_remote_repository_exists("test_repo")

            assert result is True
            mock_check.assert_called_once_with("test_repo")

    def test_check_remote_repository_exists_failure(
        self, versioner: NexusVersioner
    ) -> None:
        """Test check_remote_repository_exists with failed response."""
        with patch.object(
            versioner, "_check_nexus_repository_exists_sync"
        ) as mock_check:
            mock_check.return_value = False

            result = versioner.check_remote_repository_exists("test_repo")

            assert result is False
            mock_check.assert_called_once_with("test_repo")

    def test_check_remote_repository_exists_handles_error(
        self, versioner: NexusVersioner
    ) -> None:
        """Test check_remote_repository_exists handles exceptions."""
        with patch.object(
            versioner, "_check_nexus_repository_exists_sync"
        ) as mock_check:
            mock_check.side_effect = Exception("API error")

            result = versioner.check_remote_repository_exists("test_repo")

            assert result is False

    def test_download_repository_success(self, versioner: NexusVersioner) -> None:
        """Test _download_repository successful download."""
        with tempfile.TemporaryDirectory() as temp_dir:
            target_path = Path(temp_dir) / "test_repo"

            with (
                patch.object(
                    versioner, "_check_nexus_repository_exists_sync"
                ) as mock_check,
                patch(
                    "kbot_installer.core.versioner.nexus_versioner.optimized_download_and_extract"
                ) as mock_download,
            ):
                mock_check.return_value = True
                mock_download.return_value = None

                versioner._download_repository("test_repo", target_path)

                mock_check.assert_called_once_with("test_repo")
                mock_download.assert_called_once()

    def test_download_repository_not_found(self, versioner: NexusVersioner) -> None:
        """Test _download_repository when repository not found."""
        with tempfile.TemporaryDirectory() as temp_dir:
            target_path = Path(temp_dir) / "test_repo"

            with patch.object(
                versioner, "_check_nexus_repository_exists_sync"
            ) as mock_check:
                mock_check.return_value = False

                with pytest.raises(
                    VersionerError, match="Repository 'test_repo' not found in Nexus"
                ):
                    versioner._download_repository("test_repo", target_path)

    def test_check_nexus_repository_exists_sync_success(
        self, versioner: NexusVersioner
    ) -> None:
        """Test _check_nexus_repository_exists_sync with successful HEAD response."""
        with patch("httpx.Client") as mock_client:
            mock_response = MagicMock()
            mock_response.status_code = 200

            mock_client.return_value.__enter__.return_value.head.return_value = (
                mock_response
            )

            result = versioner._check_nexus_repository_exists_sync("test_repo")

            assert result is True

    def test_check_nexus_repository_exists_sync_not_found(
        self, versioner: NexusVersioner
    ) -> None:
        """Test _check_nexus_repository_exists_sync when repository not found."""
        with patch("httpx.Client") as mock_client:
            mock_response = MagicMock()
            mock_response.status_code = 404

            mock_client.return_value.__enter__.return_value.head.return_value = (
                mock_response
            )

            result = versioner._check_nexus_repository_exists_sync("test_repo")

            assert result is False

    def test_check_nexus_repository_exists_sync_api_error(
        self, versioner: NexusVersioner
    ) -> None:
        """Test _check_nexus_repository_exists_sync handles connection errors."""
        with patch("httpx.Client") as mock_client:
            mock_client.return_value.__enter__.return_value.head.side_effect = (
                Exception("Connection error")
            )

            result = versioner._check_nexus_repository_exists_sync("test_repo")

            assert result is False

    def test_str_representation(self, versioner: NexusVersioner) -> None:
        """Test string representation."""
        expected = "nexusVersioner(https://konverso.ai)"
        assert str(versioner) == expected

    def test_repr_representation(self, versioner: NexusVersioner) -> None:
        """Test detailed string representation."""
        expected = "NexusVersioner(name='nexus', base_url='https://konverso.ai')"
        assert repr(versioner) == expected

    def test_download_repository_with_auth(
        self, versioner_with_auth: NexusVersioner
    ) -> None:
        """Test _download_repository with authentication."""
        with tempfile.TemporaryDirectory() as temp_dir:
            target_path = Path(temp_dir) / "test_repo"

            with (
                patch.object(
                    versioner_with_auth, "_check_nexus_repository_exists_sync"
                ) as mock_check,
                patch(
                    "kbot_installer.core.versioner.nexus_versioner.optimized_download_and_extract"
                ) as mock_download,
            ):
                mock_check.return_value = True
                mock_download.return_value = None
                mock_auth = MagicMock()
                mock_auth.get_auth.return_value = ("test", "test")
                versioner_with_auth.auth = mock_auth

                versioner_with_auth._download_repository("test_repo", target_path)

                mock_check.assert_called_once_with("test_repo")
                mock_download.assert_called_once()

    def test_download_repository_download_error(
        self, versioner: NexusVersioner
    ) -> None:
        """Test _download_repository handles download error."""
        with tempfile.TemporaryDirectory() as temp_dir:
            target_path = Path(temp_dir) / "test_repo"

            with (
                patch.object(
                    versioner, "_check_nexus_repository_exists_sync"
                ) as mock_check,
                patch(
                    "kbot_installer.core.versioner.nexus_versioner.optimized_download_and_extract"
                ) as mock_download,
            ):
                mock_check.return_value = True
                mock_download.side_effect = Exception("Download failed")

                with pytest.raises(
                    VersionerError, match="Failed to download repository"
                ):
                    versioner._download_repository("test_repo", target_path)

    def test_check_nexus_repository_exists_sync_with_auth(
        self, versioner_with_auth: NexusVersioner
    ) -> None:
        """Test _check_nexus_repository_exists_sync with authentication."""
        with patch("httpx.Client") as mock_client:
            mock_response = MagicMock()
            mock_response.status_code = 200

            mock_client.return_value.__enter__.return_value.head.return_value = (
                mock_response
            )

            mock_auth = MagicMock()
            mock_auth.get_auth.return_value = {"username": "test", "password": "test"}
            versioner_with_auth.auth = mock_auth

            result = versioner_with_auth._check_nexus_repository_exists_sync(
                "test_repo"
            )

            assert result is True

    def test_check_nexus_repository_exists_sync_httpx_error(
        self, versioner: NexusVersioner
    ) -> None:
        """Test _check_nexus_repository_exists_sync handles httpx errors."""
        with patch("httpx.Client") as mock_client:
            mock_client.return_value.__enter__.side_effect = Exception("HTTP error")

            result = versioner._check_nexus_repository_exists_sync("test_repo")

            assert result is False

    def test_base_url_construction(self) -> None:
        """Test base URL construction with different domains."""
        versioner1 = NexusVersioner("example.com", "repo1")
        assert versioner1.base_url == "https://example.com"

        versioner2 = NexusVersioner("test.org", "repo2")
        assert versioner2.base_url == "https://test.org"

    def test_attributes_access(self) -> None:
        """Test direct attribute access."""
        versioner = NexusVersioner("test.com", "test_repo")

        assert versioner.domain == "test.com"
        assert versioner.repository == "test_repo"
        assert versioner.name == "nexus"
        assert versioner.base_url == "https://test.com"
        assert versioner.auth is None

    def test_attributes_access_with_auth(self) -> None:
        """Test direct attribute access with authentication."""
        mock_auth = MagicMock(spec=HttpAuthBase)
        versioner = NexusVersioner("test.com", "test_repo", mock_auth)

        assert versioner.domain == "test.com"
        assert versioner.repository == "test_repo"
        assert versioner.name == "nexus"
        assert versioner.base_url == "https://test.com"
        assert versioner.auth is mock_auth

    def test_clone_with_path_object(self, versioner: NexusVersioner) -> None:
        """Test clone with Path object."""
        with tempfile.TemporaryDirectory() as temp_dir:
            target_path = Path(temp_dir) / "test_repo"

            with patch.object(versioner, "_download_repository") as mock_download:
                mock_download.return_value = None

                versioner.clone("test_repo", target_path)

                mock_download.assert_called_once_with("test_repo", target_path)

    def test_check_remote_repository_exists_with_exception_in_check(
        self, versioner: NexusVersioner
    ) -> None:
        """Test check_remote_repository_exists when _check_nexus_repository_exists_sync raises exception."""
        with patch.object(
            versioner, "_check_nexus_repository_exists_sync"
        ) as mock_check:
            mock_check.side_effect = Exception("Unexpected error")

            result = versioner.check_remote_repository_exists("test_repo")

            assert result is False

    def test_download_repository_creates_parent_directory(
        self, versioner: NexusVersioner
    ) -> None:
        """Test _download_repository creates parent directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            target_path = Path(temp_dir) / "nested" / "test_repo"

            with (
                patch.object(
                    versioner, "_check_nexus_repository_exists_sync"
                ) as mock_check,
                patch(
                    "kbot_installer.core.versioner.nexus_versioner.optimized_download_and_extract"
                ) as mock_download,
                patch.object(Path, "mkdir") as mock_mkdir,
            ):
                mock_check.return_value = True
                mock_download.return_value = None

                versioner._download_repository("test_repo", target_path)

                mock_mkdir.assert_called_once_with(parents=True, exist_ok=True)
