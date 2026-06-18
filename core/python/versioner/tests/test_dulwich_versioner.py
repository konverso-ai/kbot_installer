"""Tests for Dulwich versioner module."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from dulwich.errors import NotGitRepository
from dulwich.porcelain import Error as DulwichPorcelainError

from auth.base import HttpAuthBase
from versioner.dulwich_versioner import DulwichVersioner
from versioner.base import VersionerBase, VersionerError


class TestDulwichVersioner:
    """Test cases for DulwichVersioner."""

    @pytest.fixture
    def versioner(self) -> DulwichVersioner:
        """Create a DulwichVersioner for testing."""
        return DulwichVersioner()

    @pytest.fixture
    def versioner_with_auth(self) -> DulwichVersioner:
        """Create a DulwichVersioner with authentication for testing."""
        mock_auth = MagicMock(spec=HttpAuthBase)
        return DulwichVersioner(mock_auth)

    @pytest.fixture
    def mock_auth(self) -> MagicMock:
        """Create mock authentication with username/password remote kwargs."""
        mock_auth = MagicMock(spec=HttpAuthBase)
        mock_auth.remote_kwargs.return_value = {
            "username": "user",
            "password": "pass",
        }
        return mock_auth

    def test_inherits_from_versioner_base(self) -> None:
        """Test that DulwichVersioner inherits from VersionerBase."""
        assert issubclass(DulwichVersioner, VersionerBase)

    def test_initialization_with_auth(self, mock_auth: MagicMock) -> None:
        """Test initialization with authentication."""
        versioner = DulwichVersioner(auth=mock_auth)
        assert versioner._get_auth() == mock_auth

    def test_initialization_without_auth(self) -> None:
        """Test initialization without authentication."""
        versioner = DulwichVersioner()
        assert versioner._get_auth() is None

    def test_get_remote_kwargs_without_auth(self, versioner: DulwichVersioner) -> None:
        """Test remote kwargs are empty without authentication."""
        assert versioner._get_remote_kwargs() == {}

    def test_get_remote_kwargs_with_user_pass(self, mock_auth: MagicMock) -> None:
        """Test remote kwargs from username/password authentication."""
        versioner = DulwichVersioner(auth=mock_auth)
        assert versioner._get_remote_kwargs() == {
            "username": "user",
            "password": "pass",
        }
        mock_auth.remote_kwargs.assert_called_once_with()

    def test_get_remote_kwargs_with_keypair(self) -> None:
        """Test remote kwargs from SSH key authentication."""
        mock_auth = MagicMock(spec=HttpAuthBase)
        mock_auth.remote_kwargs.return_value = {
            "username": "git",
            "key_filename": "/priv",
        }
        versioner = DulwichVersioner(auth=mock_auth)
        assert versioner._get_remote_kwargs() == {
            "username": "git",
            "key_filename": "/priv",
        }

    def test_get_repository_with_nonexistent_path(self, versioner: DulwichVersioner) -> None:
        """Test _get_repository raises VersionerError for nonexistent path."""
        with pytest.raises(VersionerError, match="Repository path does not exist"):
            versioner._get_repository("/nonexistent/path")

    def test_get_repository_with_not_git_repository(self, versioner: DulwichVersioner) -> None:
        """Test _get_repository handles NotGitRepository."""
        with (
            patch("pathlib.Path.exists", return_value=True),
            patch(
                "versioner.dulwich_versioner.Repo",
                side_effect=NotGitRepository("not a repo"),
            ),
        ):
            with pytest.raises(VersionerError, match="Failed to open repository"):
                versioner._get_repository("/test/path")

    def test_clone_success(self, versioner: DulwichVersioner) -> None:
        """Test successful clone operation."""
        with patch("versioner.dulwich_versioner.porcelain.clone") as mock_clone:
            versioner.clone("https://github.com/test/repo.git", "/tmp/test")
            mock_clone.assert_called_once_with(
                "https://github.com/test/repo.git",
                "/tmp/test",
            )

    def test_clone_with_auth(self, mock_auth: MagicMock) -> None:
        """Test clone passes authentication kwargs."""
        versioner = DulwichVersioner(auth=mock_auth)
        with patch("versioner.dulwich_versioner.porcelain.clone") as mock_clone:
            versioner.clone("https://github.com/test/repo.git", "/tmp/test")
            mock_clone.assert_called_once_with(
                "https://github.com/test/repo.git",
                "/tmp/test",
                username="user",
                password="pass",
            )

    def test_clone_failure(self, versioner: DulwichVersioner) -> None:
        """Test clone wraps Dulwich errors."""
        with patch(
            "versioner.dulwich_versioner.porcelain.clone",
            side_effect=DulwichPorcelainError("clone failed"),
        ):
            with pytest.raises(VersionerError, match="Failed to clone repository"):
                versioner.clone("https://github.com/test/repo.git", "/tmp/test")

    def test_add_all_files(self, versioner: DulwichVersioner) -> None:
        """Test add with all files."""
        mock_repo = MagicMock()
        with patch.object(versioner, "_get_repository", return_value=mock_repo):
            with patch("versioner.dulwich_versioner.porcelain.add") as mock_add:
                versioner.add("/test/path", None)
                mock_add.assert_called_once_with(mock_repo, paths=".")

    def test_add_specific_files(self, versioner: DulwichVersioner) -> None:
        """Test add with specific files."""
        mock_repo = MagicMock()
        with patch.object(versioner, "_get_repository", return_value=mock_repo):
            with patch("versioner.dulwich_versioner.porcelain.add") as mock_add:
                versioner.add("/test/path", ["file1.txt", "file2.txt"])
                mock_add.assert_called_once_with(
                    mock_repo, paths=["file1.txt", "file2.txt"]
                )

    def test_commit_skips_when_no_staged_changes(self, versioner: DulwichVersioner) -> None:
        """Test commit returns early when there are no staged changes."""
        mock_repo = MagicMock()
        with patch.object(versioner, "_get_repository", return_value=mock_repo):
            with patch.object(versioner, "_has_staged_changes", return_value=False):
                with patch("versioner.dulwich_versioner.porcelain.commit") as mock_commit:
                    versioner.commit("/test/path", "message")
                    mock_commit.assert_not_called()

    def test_commit_success(self, versioner: DulwichVersioner) -> None:
        """Test successful commit."""
        mock_repo = MagicMock()
        with patch.object(versioner, "_get_repository", return_value=mock_repo):
            with patch.object(versioner, "_has_staged_changes", return_value=True):
                with patch("versioner.dulwich_versioner.porcelain.commit") as mock_commit:
                    versioner.commit("/test/path", "test message")
                    mock_commit.assert_called_once_with(
                        mock_repo,
                        message="test message",
                        author=versioner._author.to_bytes(),
                        committer=versioner._author.to_bytes(),
                    )

    def test_checkout_local_branch(self, versioner: DulwichVersioner) -> None:
        """Test checkout of an existing local branch."""
        mock_repo = MagicMock()
        mock_repo.get_refs.return_value = {b"refs/heads/main": b"sha"}
        with patch.object(versioner, "_get_repository", return_value=mock_repo):
            with patch.object(versioner, "_checkout_local_branch") as mock_checkout:
                versioner.checkout("/test/path", "main")
                mock_checkout.assert_called_once_with(mock_repo, "main")

    def test_checkout_remote_branch(self, versioner: DulwichVersioner) -> None:
        """Test checkout of a remote branch."""
        mock_repo = MagicMock()
        mock_repo.get_refs.return_value = {b"refs/remotes/origin/main": b"sha"}
        with patch.object(versioner, "_get_repository", return_value=mock_repo):
            with patch.object(versioner, "_checkout_remote_branch") as mock_checkout:
                versioner.checkout("/test/path", "main")
                mock_checkout.assert_called_once_with(mock_repo, "main")

    def test_checkout_branch_not_found(self, versioner: DulwichVersioner) -> None:
        """Test checkout raises when branch does not exist."""
        mock_repo = MagicMock()
        mock_repo.get_refs.return_value = {}
        with patch.object(versioner, "_get_repository", return_value=mock_repo):
            with patch.object(versioner, "_get_available_branches", return_value=["dev"]):
                with pytest.raises(VersionerError, match="Version 'main' not found"):
                    versioner.checkout("/test/path", "main")

    def test_select_branch_returns_first_match(self, versioner: DulwichVersioner) -> None:
        """Test select_branch returns the first available branch."""
        mock_repo = MagicMock()
        mock_repo.get_refs.return_value = {
            b"refs/heads/main": b"sha1",
            b"refs/remotes/origin/develop": b"sha2",
        }
        with patch.object(versioner, "_get_repository", return_value=mock_repo):
            assert versioner.select_branch("/test/path", ["missing", "main"]) == "main"

    def test_select_branch_returns_none(self, versioner: DulwichVersioner) -> None:
        """Test select_branch returns None when no branch matches."""
        mock_repo = MagicMock()
        mock_repo.get_refs.return_value = {}
        with patch.object(versioner, "_get_repository", return_value=mock_repo):
            assert versioner.select_branch("/test/path", ["main", "master"]) is None

    def test_select_branch_empty_list(self, versioner: DulwichVersioner) -> None:
        """Test select_branch with empty branch list."""
        assert versioner.select_branch("/test/path", []) is None

    def test_stash_returns_false_when_clean(self, versioner: DulwichVersioner) -> None:
        """Test stash returns False when there are no changes."""
        mock_repo = MagicMock()
        with patch.object(versioner, "_get_repository", return_value=mock_repo):
            with patch.object(versioner, "_has_working_tree_changes", return_value=False):
                assert versioner.stash("/test/path") is False

    def test_stash_success(self, versioner: DulwichVersioner) -> None:
        """Test stash returns True when changes are stashed."""
        mock_repo = MagicMock()
        with patch.object(versioner, "_get_repository", return_value=mock_repo):
            with patch.object(versioner, "_has_working_tree_changes", return_value=True):
                with patch("versioner.dulwich_versioner.porcelain.stash_push"):
                    assert versioner.stash("/test/path", "message") is True

    def test_remote_exists_true(self, versioner: DulwichVersioner) -> None:
        """Test remote_exists returns True on success."""
        with patch("versioner.dulwich_versioner.porcelain.ls_remote"):
            assert versioner.remote_exists("https://example.com/repo.git")

    def test_remote_exists_false(self, versioner: DulwichVersioner) -> None:
        """Test remote_exists returns False on failure."""
        with patch(
            "versioner.dulwich_versioner.porcelain.ls_remote",
            side_effect=DulwichPorcelainError("not found"),
        ):
            assert not versioner.remote_exists(
                "https://example.com/missing.git"
            )

    def test_str_repr(self, versioner_with_auth: DulwichVersioner) -> None:
        """Test string representations."""
        assert "DulwichVersioner" in str(versioner_with_auth)
        assert "DulwichVersioner" in repr(versioner_with_auth)

    def test_factory_creates_dulwich_versioner(self) -> None:
        """Test factory can create DulwichVersioner by name."""
        from versioner.factory import create_versioner

        versioner = create_versioner("dulwich")
        assert isinstance(versioner, DulwichVersioner)
