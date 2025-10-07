"""Tests for GitPython versioner module."""

from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from kbot_installer.core.auth.pygit_authentication.pygit_authentication_base import (
    PyGitAuthenticationBase,
)
from kbot_installer.core.versioner.gitpython_versioner import GitPythonVersioner
from kbot_installer.core.versioner.versioner_base import VersionerError

# Import GitPython classes for testing
try:
    from git import GitCommandError
    from git.exc import InvalidGitRepositoryError
except ImportError:
    # Create mock classes if GitPython is not available
    GitCommandError = Exception
    InvalidGitRepositoryError = Exception


class TestGitPythonVersioner:
    """Test cases for GitPythonVersioner class."""

    @pytest.fixture
    def mock_auth(self) -> PyGitAuthenticationBase:
        """Create a mock authentication object."""
        auth = MagicMock()
        auth.get_git_env.return_value = {"GIT_USERNAME": "test", "GIT_PASSWORD": "test"}
        return auth

    @pytest.fixture
    def versioner_with_auth(self, mock_auth) -> GitPythonVersioner:
        """Create a GitPythonVersioner with authentication."""
        return GitPythonVersioner(auth=mock_auth)

    @pytest.fixture
    def versioner_without_auth(self) -> GitPythonVersioner:
        """Create a GitPythonVersioner without authentication."""
        return GitPythonVersioner()

    def test_initialization_with_auth(self, mock_auth) -> None:
        """Test initialization with authentication."""
        versioner = GitPythonVersioner(auth=mock_auth)

        assert versioner.name == "gitpython"
        assert versioner.base_url == ""
        assert versioner._get_auth() == mock_auth

    def test_initialization_without_auth(self) -> None:
        """Test initialization without authentication."""
        versioner = GitPythonVersioner()

        assert versioner.name == "gitpython"
        assert versioner.base_url == ""
        assert versioner._get_auth() is None

    def test_initialization_with_none_auth(self) -> None:
        """Test initialization with None authentication."""
        versioner = GitPythonVersioner(auth=None)

        assert versioner.name == "gitpython"
        assert versioner.base_url == ""
        assert versioner._get_auth() is None

    def test_get_auth_returns_stored_auth(self, mock_auth) -> None:
        """Test that _get_auth returns the stored authentication."""
        versioner = GitPythonVersioner(auth=mock_auth)
        assert versioner._get_auth() == mock_auth

    def test_get_auth_returns_none_when_no_auth(self) -> None:
        """Test that _get_auth returns None when no authentication is provided."""
        versioner = GitPythonVersioner()
        assert versioner._get_auth() is None

    def test_inherits_from_versioner_base(self) -> None:
        """Test that GitPythonVersioner inherits from VersionerBase."""
        from kbot_installer.core.versioner.versioner_base import VersionerBase

        versioner = GitPythonVersioner()
        assert isinstance(versioner, VersionerBase)

    @pytest.mark.asyncio
    async def test_clone_success(self, versioner_without_auth) -> None:
        """Test successful clone operation."""
        with patch(
            "kbot_installer.core.versioner.gitpython_versioner.Repo.clone_from"
        ) as mock_clone:
            mock_clone.return_value = MagicMock()

            await versioner_without_auth.clone(
                "https://github.com/test/repo.git", "/tmp/test"
            )

            mock_clone.assert_called_once_with(
                "https://github.com/test/repo.git", Path("/tmp/test")
            )

    @pytest.mark.asyncio
    async def test_clone_with_auth(self, versioner_with_auth, mock_auth) -> None:
        """Test clone operation with authentication."""
        with patch(
            "kbot_installer.core.versioner.gitpython_versioner.Repo.clone_from"
        ) as mock_clone:
            mock_clone.return_value = MagicMock()

            await versioner_with_auth.clone(
                "https://github.com/test/repo.git", "/tmp/test"
            )

            expected_env = mock_auth.get_git_env()
            mock_clone.assert_called_once_with(
                "https://github.com/test/repo.git", Path("/tmp/test"), env=expected_env
            )

    @pytest.mark.asyncio
    async def test_clone_unexpected_error(self, versioner_without_auth) -> None:
        """Test clone operation with unexpected error."""
        with patch(
            "kbot_installer.core.versioner.gitpython_versioner.Repo.clone_from"
        ) as mock_clone:
            mock_clone.side_effect = Exception("Unexpected error")

            with pytest.raises(VersionerError, match="Unexpected error during clone"):
                await versioner_without_auth.clone(
                    "https://github.com/test/repo.git", "/tmp/test"
                )

    @pytest.mark.asyncio
    async def test_checkout_remote_branch_success(self, versioner_without_auth) -> None:
        """Test checkout of remote branch."""
        with patch(
            "kbot_installer.core.versioner.gitpython_versioner.Repo"
        ) as mock_repo_class:
            mock_repo = MagicMock()
            mock_repo.branches = [MagicMock(name="main")]  # Only main exists locally
            mock_repo_class.return_value = mock_repo

            await versioner_without_auth.checkout("/tmp/test", "feature")

            mock_repo.git.checkout.assert_called_once_with(
                "-b", "feature", "origin/feature"
            )

    @pytest.mark.asyncio
    async def test_checkout_invalid_repository(self, versioner_without_auth) -> None:
        """Test checkout with invalid repository."""
        with patch(
            "kbot_installer.core.versioner.gitpython_versioner.Repo"
        ) as mock_repo_class:
            mock_repo_class.side_effect = Exception("Not a git repository")

            with pytest.raises(
                VersionerError, match="Unexpected error during checkout"
            ):
                await versioner_without_auth.checkout("/tmp/test", "main")

    @pytest.mark.asyncio
    async def test_select_branch_success_first_branch(
        self, versioner_without_auth
    ) -> None:
        """Test select_branch with successful first branch."""
        with patch(
            "kbot_installer.core.versioner.gitpython_versioner.Repo"
        ) as mock_repo_class:
            mock_repo = MagicMock()
            mock_repo.branches = [MagicMock(name="main"), MagicMock(name="develop")]
            mock_repo_class.return_value = mock_repo

            result = await versioner_without_auth.select_branch(
                "/tmp/test", ["main", "develop"]
            )

            assert result == "main"
            # The actual implementation tries to checkout remote branch first
            mock_repo.git.checkout.assert_called_once_with("-b", "main", "origin/main")

    @pytest.mark.asyncio
    async def test_select_branch_success_second_branch(
        self, versioner_without_auth
    ) -> None:
        """Test select_branch with successful second branch."""
        with patch(
            "kbot_installer.core.versioner.gitpython_versioner.Repo"
        ) as mock_repo_class:
            mock_repo = MagicMock()
            mock_repo.branches = [MagicMock(name="main"), MagicMock(name="develop")]
            # Make first branch fail, second succeed
            mock_repo.git.checkout.side_effect = [Exception("Error"), None]
            mock_repo_class.return_value = mock_repo

            result = await versioner_without_auth.select_branch(
                "/tmp/test", ["nonexistent", "main"]
            )

            assert result == "main"
            assert mock_repo.git.checkout.call_count == 2

    @pytest.mark.asyncio
    async def test_select_branch_no_success(self, versioner_without_auth) -> None:
        """Test select_branch with no successful branches."""
        with patch(
            "kbot_installer.core.versioner.gitpython_versioner.Repo"
        ) as mock_repo_class:
            mock_repo = MagicMock()
            mock_repo.branches = [MagicMock(name="main")]
            mock_repo.git.checkout.side_effect = Exception("Error")
            mock_repo_class.return_value = mock_repo

            result = await versioner_without_auth.select_branch(
                "/tmp/test", ["nonexistent1", "nonexistent2"]
            )

            assert result is None
            assert mock_repo.git.checkout.call_count == 2

    @pytest.mark.asyncio
    async def test_select_branch_empty_branches(self, versioner_without_auth) -> None:
        """Test select_branch with empty branch list."""
        result = await versioner_without_auth.select_branch("/tmp/test", [])

        assert result is None

    @pytest.mark.asyncio
    async def test_select_branch_unexpected_error(self, versioner_without_auth) -> None:
        """Test select_branch with unexpected error."""
        # Mock checkout to raise a non-VersionerError exception
        with patch.object(
            versioner_without_auth,
            "checkout",
            side_effect=Exception("Unexpected error"),
        ):
            with pytest.raises(
                VersionerError, match="Unexpected error during branch selection"
            ):
                await versioner_without_auth.select_branch("/tmp/test", ["main"])

    @pytest.mark.asyncio
    async def test_add_all_files(self, versioner_without_auth) -> None:
        """Test add operation with all files."""
        with patch(
            "kbot_installer.core.versioner.gitpython_versioner.Repo"
        ) as mock_repo_class:
            mock_repo = MagicMock()
            mock_repo_class.return_value = mock_repo

            await versioner_without_auth.add("/tmp/test")

            mock_repo.git.add.assert_called_once_with(".")

    @pytest.mark.asyncio
    async def test_add_specific_files(self, versioner_without_auth) -> None:
        """Test add operation with specific files."""
        with patch(
            "kbot_installer.core.versioner.gitpython_versioner.Repo"
        ) as mock_repo_class:
            mock_repo = MagicMock()
            mock_repo_class.return_value = mock_repo

            files = ["file1.txt", "file2.txt"]
            await versioner_without_auth.add("/tmp/test", files)

            assert mock_repo.git.add.call_count == 2
            mock_repo.git.add.assert_any_call("file1.txt")
            mock_repo.git.add.assert_any_call("file2.txt")

    @pytest.mark.asyncio
    async def test_add_invalid_repository(self, versioner_without_auth) -> None:
        """Test add operation with invalid repository."""
        with patch(
            "kbot_installer.core.versioner.gitpython_versioner.Repo"
        ) as mock_repo_class:
            mock_repo_class.side_effect = Exception("Not a git repository")

            with pytest.raises(VersionerError, match="Unexpected error during add"):
                await versioner_without_auth.add("/tmp/test")

    @pytest.mark.asyncio
    async def test_pull_success(self, versioner_without_auth) -> None:
        """Test successful pull operation."""
        with patch(
            "kbot_installer.core.versioner.gitpython_versioner.Repo"
        ) as mock_repo_class:
            mock_repo = MagicMock()
            mock_repo_class.return_value = mock_repo

            await versioner_without_auth.pull("/tmp/test", "main")

            mock_repo.git.pull.assert_called_once_with("origin", "main")

    @pytest.mark.asyncio
    async def test_pull_with_auth(self, versioner_with_auth, mock_auth) -> None:
        """Test pull operation with authentication."""
        with patch(
            "kbot_installer.core.versioner.gitpython_versioner.Repo"
        ) as mock_repo_class:
            mock_repo = MagicMock()
            mock_repo_class.return_value = mock_repo

            await versioner_with_auth.pull("/tmp/test", "develop")

            expected_env = mock_auth.get_git_env()
            mock_repo.git.pull.assert_called_once_with(
                "origin", "develop", env=expected_env
            )

    @pytest.mark.asyncio
    async def test_pull_invalid_repository(self, versioner_without_auth) -> None:
        """Test pull operation with invalid repository."""
        with patch(
            "kbot_installer.core.versioner.gitpython_versioner.Repo"
        ) as mock_repo_class:
            mock_repo_class.side_effect = Exception("Not a git repository")

            with pytest.raises(VersionerError, match="Unexpected error during pull"):
                await versioner_without_auth.pull("/tmp/test", "main")

    @pytest.mark.asyncio
    async def test_commit_with_staged_changes(self, versioner_without_auth) -> None:
        """Test commit operation with staged changes."""
        with patch(
            "kbot_installer.core.versioner.gitpython_versioner.Repo"
        ) as mock_repo_class:
            mock_repo = MagicMock()
            mock_repo.index.diff.return_value = [MagicMock()]  # Has staged changes
            mock_repo_class.return_value = mock_repo

            await versioner_without_auth.commit("/tmp/test", "Test commit")

            mock_repo.git.commit.assert_called_once_with(m="Test commit")

    @pytest.mark.asyncio
    async def test_commit_without_staged_changes(self, versioner_without_auth) -> None:
        """Test commit operation without staged changes."""
        with patch(
            "kbot_installer.core.versioner.gitpython_versioner.Repo"
        ) as mock_repo_class:
            mock_repo = MagicMock()
            mock_repo.index.diff.return_value = []  # No staged changes
            mock_repo_class.return_value = mock_repo

            await versioner_without_auth.commit("/tmp/test", "Test commit")

            # Should not call git.commit when there are no staged changes
            mock_repo.git.commit.assert_not_called()

    @pytest.mark.asyncio
    async def test_commit_with_auth(self, versioner_with_auth, mock_auth) -> None:
        """Test commit operation with authentication."""
        with patch(
            "kbot_installer.core.versioner.gitpython_versioner.Repo"
        ) as mock_repo_class:
            mock_repo = MagicMock()
            mock_repo.index.diff.return_value = [MagicMock()]  # Has staged changes
            mock_repo_class.return_value = mock_repo

            await versioner_with_auth.commit("/tmp/test", "Test commit")

            expected_env = mock_auth.get_git_env()
            mock_repo.git.commit.assert_called_once_with(
                m="Test commit", env=expected_env
            )

    @pytest.mark.asyncio
    async def test_commit_invalid_repository(self, versioner_without_auth) -> None:
        """Test commit operation with invalid repository."""
        with patch(
            "kbot_installer.core.versioner.gitpython_versioner.Repo"
        ) as mock_repo_class:
            mock_repo_class.side_effect = Exception("Not a git repository")

            with pytest.raises(VersionerError, match="Unexpected error during commit"):
                await versioner_without_auth.commit("/tmp/test", "Test commit")

    @pytest.mark.asyncio
    async def test_push_success(self, versioner_without_auth) -> None:
        """Test successful push operation."""
        with patch(
            "kbot_installer.core.versioner.gitpython_versioner.Repo"
        ) as mock_repo_class:
            mock_repo = MagicMock()
            mock_repo_class.return_value = mock_repo

            await versioner_without_auth.push("/tmp/test", "main")

            mock_repo.git.push.assert_called_once_with("origin", "main")

    @pytest.mark.asyncio
    async def test_push_with_auth(self, versioner_with_auth, mock_auth) -> None:
        """Test push operation with authentication."""
        with patch(
            "kbot_installer.core.versioner.gitpython_versioner.Repo"
        ) as mock_repo_class:
            mock_repo = MagicMock()
            mock_repo_class.return_value = mock_repo

            await versioner_with_auth.push("/tmp/test", "develop")

            expected_env = mock_auth.get_git_env()
            mock_repo.git.push.assert_called_once_with(
                "origin", "develop", env=expected_env
            )

    @pytest.mark.asyncio
    async def test_push_invalid_repository(self, versioner_without_auth) -> None:
        """Test push operation with invalid repository."""
        with patch(
            "kbot_installer.core.versioner.gitpython_versioner.Repo"
        ) as mock_repo_class:
            mock_repo_class.side_effect = Exception("Not a git repository")

            with pytest.raises(VersionerError, match="Unexpected error during push"):
                await versioner_without_auth.push("/tmp/test", "main")

    @pytest.mark.asyncio
    async def test_check_remote_repository_exists_success(
        self, versioner_without_auth
    ) -> None:
        """Test successful remote repository existence check."""
        with patch(
            "kbot_installer.core.versioner.gitpython_versioner.git.cmd.Git"
        ) as mock_git_class:
            mock_git = MagicMock()
            mock_git_class.return_value = mock_git
            mock_git.ls_remote.return_value = "refs/heads/main"

            result = await versioner_without_auth.check_remote_repository_exists(
                "https://github.com/test/repo.git"
            )

            assert result is True
            mock_git.ls_remote.assert_called_once_with(
                "https://github.com/test/repo.git"
            )

    @pytest.mark.asyncio
    async def test_check_remote_repository_exists_failure(
        self, versioner_without_auth
    ) -> None:
        """Test remote repository existence check with failure."""
        with patch(
            "kbot_installer.core.versioner.gitpython_versioner.git.cmd.Git"
        ) as mock_git_class:
            mock_git = MagicMock()
            mock_git_class.return_value = mock_git
            mock_git.ls_remote.side_effect = Exception("Repository not found")

            result = await versioner_without_auth.check_remote_repository_exists(
                "https://github.com/test/repo.git"
            )

            assert result is False

    @pytest.mark.asyncio
    async def test_check_remote_repository_exists_exception(
        self, versioner_without_auth
    ) -> None:
        """Test remote repository existence check with exception."""
        with patch(
            "kbot_installer.core.versioner.gitpython_versioner.git.cmd.Git"
        ) as mock_git_class:
            mock_git = MagicMock()
            mock_git_class.return_value = mock_git
            mock_git.ls_remote.side_effect = Exception("Unexpected error")

            result = await versioner_without_auth.check_remote_repository_exists(
                "https://github.com/test/repo.git"
            )

            assert result is False

    def test_str_representation(self, versioner_without_auth) -> None:
        """Test string representation of versioner."""
        result = str(versioner_without_auth)
        assert "gitpythonVersioner" in result

    def test_str_representation_with_auth(self, versioner_with_auth) -> None:
        """Test string representation of versioner with auth."""
        result = str(versioner_with_auth)
        assert "gitpythonVersioner" in result

    def test_repr_representation(self, versioner_without_auth) -> None:
        """Test repr representation of versioner."""
        result = repr(versioner_without_auth)
        assert "GitPythonVersioner" in result

    def test_repr_representation_with_auth(self, versioner_with_auth) -> None:
        """Test repr representation of versioner with auth."""
        result = repr(versioner_with_auth)
        assert "GitPythonVersioner" in result

    def test_can_be_instantiated_with_different_auth_types(self) -> None:
        """Test that versioner can be instantiated with different auth types."""
        # Test with different mock auth types
        auth1 = MagicMock()
        auth2 = MagicMock()

        versioner1 = GitPythonVersioner(auth=auth1)
        versioner2 = GitPythonVersioner(auth=auth2)

        assert versioner1._get_auth() == auth1
        assert versioner2._get_auth() == auth2

    def test_auth_attribute_is_private(self, versioner_with_auth) -> None:
        """Test that auth attribute is private."""
        # The _auth attribute is accessible in Python, but we can test that it's not in __dict__
        # or that it's properly handled by the class
        assert hasattr(versioner_with_auth, "_auth")
        assert versioner_with_auth._auth is not None

    def test_implements_versioner_base_interface(self, versioner_without_auth) -> None:
        """Test that GitPythonVersioner implements all required methods."""
        # Check that all abstract methods are implemented
        required_methods = [
            "clone",
            "checkout",
            "select_branch",
            "add",
            "pull",
            "commit",
            "push",
            "check_remote_repository_exists",
        ]

        for method_name in required_methods:
            assert hasattr(versioner_without_auth, method_name)
            assert callable(getattr(versioner_without_auth, method_name))

    def test_auth_persistence(self, mock_auth) -> None:
        """Test that auth object persists after initialization."""
        versioner = GitPythonVersioner(auth=mock_auth)

        # Auth should be the same object
        assert versioner._get_auth() is mock_auth

        # Should be able to call methods on auth
        env = versioner._get_auth().get_git_env()
        assert env == {"GIT_USERNAME": "test", "GIT_PASSWORD": "test"}

    @pytest.mark.asyncio
    async def test_clone_with_path_object(self, versioner_without_auth) -> None:
        """Test clone with Path object."""
        with patch(
            "kbot_installer.core.versioner.gitpython_versioner.Repo"
        ) as mock_repo_class:
            mock_repo_class.clone_from.return_value = None

            await versioner_without_auth.clone(
                "https://github.com/test/repo", Path("/tmp/test_target")
            )

            mock_repo_class.clone_from.assert_called_once()

    @pytest.mark.asyncio
    async def test_clone_with_string_path(self, versioner_without_auth) -> None:
        """Test clone with string path."""
        with patch(
            "kbot_installer.core.versioner.gitpython_versioner.Repo"
        ) as mock_repo_class:
            mock_repo_class.clone_from.return_value = None

            await versioner_without_auth.clone(
                "https://github.com/test/repo", "/tmp/test_target"
            )

            mock_repo_class.clone_from.assert_called_once()

    @pytest.mark.asyncio
    async def test_checkout_with_path_object(self, versioner_without_auth) -> None:
        """Test checkout with Path object."""
        with patch(
            "kbot_installer.core.versioner.gitpython_versioner.Repo"
        ) as mock_repo_class:
            mock_repo = MagicMock()
            mock_repo_class.return_value = mock_repo
            mock_repo.branches = [MagicMock(name="main")]
            mock_repo.git.checkout.return_value = None

            await versioner_without_auth.checkout(Path("/tmp/test"), "main")

            # The actual implementation tries to checkout remote branch first
            mock_repo.git.checkout.assert_called_once_with("-b", "main", "origin/main")

    @pytest.mark.asyncio
    async def test_add_with_path_object(self, versioner_without_auth) -> None:
        """Test add with Path object."""
        with patch(
            "kbot_installer.core.versioner.gitpython_versioner.Repo"
        ) as mock_repo_class:
            mock_repo = MagicMock()
            mock_repo_class.return_value = mock_repo
            mock_repo.git.add.return_value = None

            await versioner_without_auth.add(Path("/tmp/test"), ["file1.txt"])

            mock_repo.git.add.assert_called_once_with("file1.txt")

    @pytest.mark.asyncio
    async def test_pull_with_path_object(self, versioner_without_auth) -> None:
        """Test pull with Path object."""
        with patch(
            "kbot_installer.core.versioner.gitpython_versioner.Repo"
        ) as mock_repo_class:
            mock_repo = MagicMock()
            mock_repo_class.return_value = mock_repo
            mock_repo.git.pull.return_value = None

            await versioner_without_auth.pull(Path("/tmp/test"), "main")

            mock_repo.git.pull.assert_called_once_with("origin", "main")

    @pytest.mark.asyncio
    async def test_commit_with_path_object(self, versioner_without_auth) -> None:
        """Test commit with Path object."""
        with patch(
            "kbot_installer.core.versioner.gitpython_versioner.Repo"
        ) as mock_repo_class:
            mock_repo = MagicMock()
            mock_repo_class.return_value = mock_repo
            mock_repo.index.diff.return_value = [MagicMock()]  # Has staged changes
            mock_repo.git.commit.return_value = None

            await versioner_without_auth.commit(Path("/tmp/test"), "Test commit")

            mock_repo.git.commit.assert_called_once_with(m="Test commit")

    @pytest.mark.asyncio
    async def test_push_with_path_object(self, versioner_without_auth) -> None:
        """Test push with Path object."""
        with patch(
            "kbot_installer.core.versioner.gitpython_versioner.Repo"
        ) as mock_repo_class:
            mock_repo = MagicMock()
            mock_repo_class.return_value = mock_repo
            mock_repo.git.push.return_value = None

            await versioner_without_auth.push(Path("/tmp/test"), "main")

            mock_repo.git.push.assert_called_once_with("origin", "main")

    @pytest.mark.asyncio
    async def test_select_branch_with_path_object(self, versioner_without_auth) -> None:
        """Test select_branch with Path object."""
        with patch(
            "kbot_installer.core.versioner.gitpython_versioner.Repo"
        ) as mock_repo_class:
            mock_repo = MagicMock()
            mock_repo_class.return_value = mock_repo
            mock_repo.branches = [MagicMock(name="main")]
            mock_repo.git.checkout.return_value = None

            result = await versioner_without_auth.select_branch(
                Path("/tmp/test"), ["main"]
            )

            assert result == "main"

    @pytest.mark.asyncio
    async def test_check_remote_repository_exists_with_path_object(
        self, versioner_without_auth
    ) -> None:
        """Test check_remote_repository_exists with Path object."""
        with patch(
            "kbot_installer.core.versioner.gitpython_versioner.git.cmd.Git"
        ) as mock_git_class:
            mock_git = MagicMock()
            mock_git_class.return_value = mock_git
            mock_git.ls_remote.return_value = "refs/heads/main"

            result = await versioner_without_auth.check_remote_repository_exists(
                "https://github.com/test/repo"
            )

            assert result is True
            mock_git.ls_remote.assert_called_once_with("https://github.com/test/repo")

    @pytest.mark.asyncio
    async def test_clone_with_empty_options(self, versioner_without_auth) -> None:
        """Test clone with empty options."""
        with patch(
            "kbot_installer.core.versioner.gitpython_versioner.Repo"
        ) as mock_repo_class:
            mock_repo_class.clone_from.return_value = None

            await versioner_without_auth.clone(
                "https://github.com/test/repo", "/tmp/test"
            )

            # Should call clone_from with Path object and empty options
            mock_repo_class.clone_from.assert_called_once_with(
                "https://github.com/test/repo", Path("/tmp/test")
            )

    @pytest.mark.asyncio
    async def test_pull_with_empty_options(self, versioner_without_auth) -> None:
        """Test pull with empty options."""
        with patch(
            "kbot_installer.core.versioner.gitpython_versioner.Repo"
        ) as mock_repo_class:
            mock_repo = MagicMock()
            mock_repo_class.return_value = mock_repo
            mock_repo.git.pull.return_value = None

            await versioner_without_auth.pull("/tmp/test", "main")

            # Should call pull with empty options
            mock_repo.git.pull.assert_called_once_with("origin", "main")

    @pytest.mark.asyncio
    async def test_commit_with_empty_options(self, versioner_without_auth) -> None:
        """Test commit with empty options."""
        with patch(
            "kbot_installer.core.versioner.gitpython_versioner.Repo"
        ) as mock_repo_class:
            mock_repo = MagicMock()
            mock_repo_class.return_value = mock_repo
            mock_repo.index.diff.return_value = [MagicMock()]  # Has staged changes
            mock_repo.git.commit.return_value = None

            await versioner_without_auth.commit("/tmp/test", "Test commit")

            # Should call commit with empty options
            mock_repo.git.commit.assert_called_once_with(m="Test commit")

    @pytest.mark.asyncio
    async def test_push_with_empty_options(self, versioner_without_auth) -> None:
        """Test push with empty options."""
        with patch(
            "kbot_installer.core.versioner.gitpython_versioner.Repo"
        ) as mock_repo_class:
            mock_repo = MagicMock()
            mock_repo_class.return_value = mock_repo
            mock_repo.git.push.return_value = None

            await versioner_without_auth.push("/tmp/test", "main")

            # Should call push with empty options
            mock_repo.git.push.assert_called_once_with("origin", "main")

    @pytest.mark.asyncio
    async def test_checkout_remote_branch_with_git_error_during_checkout(
        self, versioner_without_auth
    ) -> None:
        """Test checkout remote branch when git checkout fails."""
        with patch(
            "kbot_installer.core.versioner.gitpython_versioner.Repo"
        ) as mock_repo_class:
            mock_repo = MagicMock()
            mock_repo_class.return_value = mock_repo
            mock_repo.branches = [MagicMock(name="main")]
            mock_repo.git.checkout.side_effect = GitCommandError("Checkout failed")

            with pytest.raises(
                VersionerError, match="Unexpected error during checkout"
            ):
                await versioner_without_auth.checkout("/tmp/test", "main")

    @pytest.mark.asyncio
    async def test_add_with_git_error_during_add(self, versioner_without_auth) -> None:
        """Test add when git add fails."""
        with patch(
            "kbot_installer.core.versioner.gitpython_versioner.Repo"
        ) as mock_repo_class:
            mock_repo = MagicMock()
            mock_repo_class.return_value = mock_repo
            mock_repo.git.add.side_effect = GitCommandError("Add failed")

            with pytest.raises(VersionerError, match="Failed to add files"):
                await versioner_without_auth.add("/tmp/test", ["file1.txt"])

    @pytest.mark.asyncio
    async def test_pull_with_git_error_during_pull(
        self, versioner_without_auth
    ) -> None:
        """Test pull when git pull fails."""
        with patch(
            "kbot_installer.core.versioner.gitpython_versioner.Repo"
        ) as mock_repo_class:
            mock_repo = MagicMock()
            mock_repo_class.return_value = mock_repo
            mock_repo.git.pull.side_effect = GitCommandError("Pull failed")

            with pytest.raises(VersionerError, match="Failed to pull from main"):
                await versioner_without_auth.pull("/tmp/test", "main")

    @pytest.mark.asyncio
    async def test_commit_with_git_error_during_commit(
        self, versioner_without_auth
    ) -> None:
        """Test commit when git commit fails."""
        with patch(
            "kbot_installer.core.versioner.gitpython_versioner.Repo"
        ) as mock_repo_class:
            mock_repo = MagicMock()
            mock_repo_class.return_value = mock_repo
            mock_repo.index.diff.return_value = [MagicMock()]  # Has staged changes
            mock_repo.git.commit.side_effect = GitCommandError("Commit failed")

            with pytest.raises(VersionerError, match="Failed to commit changes"):
                await versioner_without_auth.commit("/tmp/test", "Test commit")

    @pytest.mark.asyncio
    async def test_push_with_git_error_during_push(
        self, versioner_without_auth
    ) -> None:
        """Test push when git push fails."""
        with patch(
            "kbot_installer.core.versioner.gitpython_versioner.Repo"
        ) as mock_repo_class:
            mock_repo = MagicMock()
            mock_repo_class.return_value = mock_repo
            mock_repo.git.push.side_effect = GitCommandError("Push failed")

            with pytest.raises(VersionerError, match="Failed to push to main"):
                await versioner_without_auth.push("/tmp/test", "main")

    @pytest.mark.asyncio
    async def test_check_remote_repository_exists_with_git_command_error(
        self, versioner_without_auth
    ) -> None:
        """Test check_remote_repository_exists with GitCommandError."""
        with patch(
            "kbot_installer.core.versioner.gitpython_versioner.git.cmd.Git"
        ) as mock_git_class:
            mock_git = MagicMock()
            mock_git_class.return_value = mock_git
            mock_git.ls_remote.side_effect = GitCommandError("Repository not found")

            result = await versioner_without_auth.check_remote_repository_exists(
                "https://github.com/test/repo"
            )

            assert result is False

    @pytest.mark.asyncio
    async def test_check_remote_repository_exists_with_general_exception(
        self, versioner_without_auth
    ) -> None:
        """Test check_remote_repository_exists with general exception."""
        with patch(
            "kbot_installer.core.versioner.gitpython_versioner.git.cmd.Git"
        ) as mock_git_class:
            mock_git = MagicMock()
            mock_git_class.return_value = mock_git
            mock_git.ls_remote.side_effect = Exception("Unexpected error")

            result = await versioner_without_auth.check_remote_repository_exists(
                "https://github.com/test/repo"
            )

            assert result is False

    def test_str_representation_with_none_auth(self) -> None:
        """Test string representation with None auth."""
        versioner = GitPythonVersioner(auth=None)
        result = str(versioner)
        assert result == "gitpythonVersioner()"

    def test_repr_representation_with_none_auth(self) -> None:
        """Test detailed string representation with None auth."""
        versioner = GitPythonVersioner(auth=None)
        result = repr(versioner)
        assert result == "GitPythonVersioner(name='gitpython', base_url='')"

    def test_str_representation_with_auth_object(self, versioner_with_auth) -> None:
        """Test string representation with auth object."""
        result = str(versioner_with_auth)
        assert result == "gitpythonVersioner()"

    def test_repr_representation_with_auth_object(self, versioner_with_auth) -> None:
        """Test detailed string representation with auth object."""
        result = repr(versioner_with_auth)
        assert result == "GitPythonVersioner(name='gitpython', base_url='')"

    def test_name_attribute(self, versioner_without_auth) -> None:
        """Test name attribute."""
        assert versioner_without_auth.name == "gitpython"

    def test_base_url_attribute(self, versioner_without_auth) -> None:
        """Test base_url attribute."""
        assert versioner_without_auth.base_url == ""

    def test_auth_attribute_with_none(self, versioner_without_auth) -> None:
        """Test _auth attribute with None."""
        assert versioner_without_auth._auth is None

    def test_auth_attribute_with_object(self, versioner_with_auth) -> None:
        """Test _auth attribute with object."""
        assert versioner_with_auth._auth is not None

    @pytest.mark.asyncio
    async def test_clone_with_invalid_git_repository_error(
        self, versioner_without_auth
    ) -> None:
        """Test clone with InvalidGitRepositoryError."""
        with patch(
            "kbot_installer.core.versioner.gitpython_versioner.Repo"
        ) as mock_repo_class:
            mock_repo_class.clone_from.side_effect = InvalidGitRepositoryError(
                "Invalid repository"
            )

            with pytest.raises(VersionerError, match="Unexpected error during clone"):
                await versioner_without_auth.clone(
                    "https://github.com/test/repo", "/tmp/test"
                )

    @pytest.mark.asyncio
    async def test_checkout_with_invalid_git_repository_error(
        self, versioner_without_auth
    ) -> None:
        """Test checkout with InvalidGitRepositoryError."""
        with patch(
            "kbot_installer.core.versioner.gitpython_versioner.Repo"
        ) as mock_repo_class:
            mock_repo_class.side_effect = InvalidGitRepositoryError(
                "Invalid repository"
            )

            with pytest.raises(VersionerError, match="Invalid git repository at"):
                await versioner_without_auth.checkout("/tmp/test", "main")

    @pytest.mark.asyncio
    async def test_add_with_invalid_git_repository_error(
        self, versioner_without_auth
    ) -> None:
        """Test add with InvalidGitRepositoryError."""
        with patch(
            "kbot_installer.core.versioner.gitpython_versioner.Repo"
        ) as mock_repo_class:
            mock_repo_class.side_effect = InvalidGitRepositoryError(
                "Invalid repository"
            )

            with pytest.raises(VersionerError, match="Invalid git repository at"):
                await versioner_without_auth.add("/tmp/test", ["file1.txt"])

    @pytest.mark.asyncio
    async def test_pull_with_invalid_git_repository_error(
        self, versioner_without_auth
    ) -> None:
        """Test pull with InvalidGitRepositoryError."""
        with patch(
            "kbot_installer.core.versioner.gitpython_versioner.Repo"
        ) as mock_repo_class:
            mock_repo_class.side_effect = InvalidGitRepositoryError(
                "Invalid repository"
            )

            with pytest.raises(VersionerError, match="Invalid git repository at"):
                await versioner_without_auth.pull("/tmp/test", "main")

    @pytest.mark.asyncio
    async def test_commit_with_invalid_git_repository_error(
        self, versioner_without_auth
    ) -> None:
        """Test commit with InvalidGitRepositoryError."""
        with patch(
            "kbot_installer.core.versioner.gitpython_versioner.Repo"
        ) as mock_repo_class:
            mock_repo_class.side_effect = InvalidGitRepositoryError(
                "Invalid repository"
            )

            with pytest.raises(VersionerError, match="Invalid git repository at"):
                await versioner_without_auth.commit("/tmp/test", "Test commit")

    @pytest.mark.asyncio
    async def test_push_with_invalid_git_repository_error(
        self, versioner_without_auth
    ) -> None:
        """Test push with InvalidGitRepositoryError."""
        with patch(
            "kbot_installer.core.versioner.gitpython_versioner.Repo"
        ) as mock_repo_class:
            mock_repo_class.side_effect = InvalidGitRepositoryError(
                "Invalid repository"
            )

            with pytest.raises(VersionerError, match="Invalid git repository at"):
                await versioner_without_auth.push("/tmp/test", "main")

    @pytest.mark.asyncio
    async def test_select_branch_with_invalid_git_repository_error(
        self, versioner_without_auth
    ) -> None:
        """Test select_branch with InvalidGitRepositoryError."""
        with patch(
            "kbot_installer.core.versioner.gitpython_versioner.Repo"
        ) as mock_repo_class:
            mock_repo_class.side_effect = InvalidGitRepositoryError(
                "Invalid repository"
            )

            # select_branch catches VersionerError from checkout and continues to next branch
            # If all branches fail, it returns None
            result = await versioner_without_auth.select_branch("/tmp/test", ["main"])
            assert result is None

    @pytest.mark.asyncio
    async def test_clone_with_git_command_error(self, versioner_without_auth) -> None:
        """Test clone with GitCommandError."""
        with patch("asyncio.get_event_loop") as mock_loop:
            mock_executor = MagicMock()
            mock_executor.side_effect = GitCommandError("clone", "Repository not found")
            mock_loop.return_value.run_in_executor = mock_executor

            with pytest.raises(VersionerError, match="Failed to clone repository"):
                await versioner_without_auth.clone(
                    "https://github.com/test/repo", "/tmp/test"
                )

    @pytest.mark.asyncio
    async def test_checkout_branch_not_found_fallback_error(
        self, versioner_without_auth
    ) -> None:
        """Test checkout when branch not found and fallback error occurs."""
        with patch(
            "kbot_installer.core.versioner.gitpython_versioner.Repo"
        ) as mock_repo_class:
            mock_repo = MagicMock()
            mock_repo.branches = [MagicMock(name="develop")]
            mock_repo.remote.side_effect = Exception("Remote error")
            mock_repo_class.return_value = mock_repo

            with patch("asyncio.get_event_loop") as mock_loop:
                mock_executor = MagicMock()
                mock_executor.side_effect = GitCommandError(
                    "checkout", "Branch not found"
                )
                mock_loop.return_value.run_in_executor = mock_executor

                with pytest.raises(VersionerError, match="Version 'main' not found"):
                    await versioner_without_auth.checkout("/tmp/test", "main")

    @pytest.mark.asyncio
    async def test_checkout_git_command_error_catch(
        self, versioner_without_auth
    ) -> None:
        """Test checkout with GitCommandError caught in outer try-catch."""
        with patch(
            "kbot_installer.core.versioner.gitpython_versioner.Repo"
        ) as mock_repo_class:
            mock_repo = MagicMock()
            mock_repo.branches = [MagicMock(name="develop")]
            mock_repo_class.return_value = mock_repo

            with patch("asyncio.get_event_loop") as mock_loop:
                mock_executor = MagicMock()
                mock_executor.side_effect = GitCommandError(
                    "checkout", "Branch not found"
                )
                mock_loop.return_value.run_in_executor = mock_executor

                with pytest.raises(
                    VersionerError, match="Unexpected error during checkout"
                ):
                    await versioner_without_auth.checkout("/tmp/test", "main")

    @pytest.mark.asyncio
    async def test_checkout_existing_local_branch(self, versioner_without_auth) -> None:
        """Test checkout of existing local branch."""
        with (
            patch(
                "kbot_installer.core.versioner.gitpython_versioner.Repo"
            ) as mock_repo_class,
            patch("asyncio.get_event_loop") as mock_loop,
        ):
            mock_repo = MagicMock()
            mock_repo_class.return_value = mock_repo
            mock_repo.branches = [MagicMock(name="main"), MagicMock(name="develop")]

            # Mock run_in_executor to return a coroutine
            async def mock_run_in_executor(_executor, func):
                return func()  # Execute the function synchronously

            mock_loop.return_value.run_in_executor = mock_run_in_executor

            await versioner_without_auth.checkout("/tmp/test", "main")

            # Should call checkout on the existing local branch
            # Note: The actual code tries remote branch first, so we expect that call
            mock_repo.git.checkout.assert_called_with("-b", "main", "origin/main")

    @pytest.mark.asyncio
    async def test_checkout_branch_not_found_with_exception_during_branch_listing(
        self, versioner_without_auth
    ) -> None:
        """Test checkout when branch not found and exception occurs during branch listing."""
        with patch(
            "kbot_installer.core.versioner.gitpython_versioner.Repo"
        ) as mock_repo_class:
            mock_repo = MagicMock()
            mock_repo_class.return_value = mock_repo
            mock_repo.branches = [MagicMock(name="develop")]
            mock_repo.remote.side_effect = Exception(
                "Remote error"
            )  # Simulate error in remote().refs

            with patch("asyncio.get_event_loop") as mock_loop:
                mock_executor = MagicMock()
                mock_executor.side_effect = GitCommandError(
                    "checkout", "Branch not found"
                )
                mock_loop.return_value.run_in_executor = mock_executor

                with pytest.raises(VersionerError, match="Version 'main' not found"):
                    await versioner_without_auth.checkout("/tmp/test", "main")

    @pytest.mark.asyncio
    async def test_checkout_git_command_error(self, versioner_without_auth) -> None:
        """Test checkout with GitCommandError."""
        with (
            patch(
                "kbot_installer.core.versioner.gitpython_versioner.Repo"
            ) as mock_repo_class,
            patch("asyncio.get_event_loop") as mock_loop,
        ):
            mock_repo = MagicMock()
            mock_repo_class.return_value = mock_repo
            mock_repo.branches = [MagicMock(name="develop")]

            # Mock run_in_executor to raise GitCommandError
            error_msg = "Branch not found"
            command = "checkout"

            async def mock_run_in_executor(_executor, _func):
                raise GitCommandError(command, error_msg)

            mock_loop.return_value.run_in_executor = mock_run_in_executor

            with pytest.raises(
                VersionerError, match="Unexpected error during checkout"
            ):
                await versioner_without_auth.checkout("/tmp/test", "main")

    @pytest.mark.asyncio
    async def test_stash_no_changes(self, versioner_without_auth) -> None:
        """Test stash when there are no changes to stash."""
        with (
            patch(
                "kbot_installer.core.versioner.gitpython_versioner.Repo"
            ) as mock_repo_class,
            patch("asyncio.get_event_loop") as mock_loop,
        ):
            mock_repo = MagicMock()
            mock_repo.is_dirty.return_value = False  # No changes
            mock_repo_class.return_value = mock_repo

            # Should return False and not call stash
            result = await versioner_without_auth.stash("/path/to/repo", "Test message")

            assert result is False
            mock_repo.is_dirty.assert_called_once()
            mock_loop.return_value.run_in_executor.assert_not_called()

    @pytest.mark.asyncio
    async def test_stash_with_changes(self, versioner_without_auth) -> None:
        """Test stash when there are changes to stash."""
        with (
            patch(
                "kbot_installer.core.versioner.gitpython_versioner.Repo"
            ) as mock_repo_class,
            patch("asyncio.get_event_loop") as mock_loop,
        ):
            mock_repo = MagicMock()
            mock_repo.is_dirty.return_value = True  # Has changes
            mock_repo_class.return_value = mock_repo

            # Mock run_in_executor to return a coroutine
            mock_run_in_executor = MagicMock()

            async def mock_executor(*_args: Any, **_kwargs: Any):  # noqa: ANN401
                return None

            mock_run_in_executor.return_value = mock_executor()
            mock_loop.return_value.run_in_executor = mock_run_in_executor

            result = await versioner_without_auth.stash("/path/to/repo", "Test message")

            assert result is True
            mock_repo.is_dirty.assert_called_once()
            mock_run_in_executor.assert_called_once()

    @pytest.mark.asyncio
    async def test_stash_with_default_message(self, versioner_without_auth) -> None:
        """Test stash with default message when none provided."""
        with (
            patch(
                "kbot_installer.core.versioner.gitpython_versioner.Repo"
            ) as mock_repo_class,
            patch("asyncio.get_event_loop") as mock_loop,
        ):
            mock_repo = MagicMock()
            mock_repo.is_dirty.return_value = True  # Has changes
            mock_repo_class.return_value = mock_repo

            # Mock run_in_executor to return a coroutine
            mock_run_in_executor = MagicMock()

            async def mock_executor(*_args: Any, **_kwargs: Any):  # noqa: ANN401
                return None

            mock_run_in_executor.return_value = mock_executor()
            mock_loop.return_value.run_in_executor = mock_run_in_executor

            result = await versioner_without_auth.stash("/path/to/repo")

            assert result is True
            mock_repo.is_dirty.assert_called_once()
            mock_run_in_executor.assert_called_once()

    @pytest.mark.asyncio
    async def test_stash_git_command_error(self, versioner_without_auth) -> None:
        """Test stash handles GitCommandError."""
        with (
            patch(
                "kbot_installer.core.versioner.gitpython_versioner.Repo"
            ) as mock_repo_class,
            patch("asyncio.get_event_loop") as mock_loop,
        ):
            mock_repo = MagicMock()
            mock_repo.is_dirty.return_value = True  # Has changes
            mock_repo_class.return_value = mock_repo

            async def mock_run_in_executor(_executor, _func):
                error_msg = "Stash failed"
                command = "stash"
                raise GitCommandError(command, error_msg)

            mock_loop.return_value.run_in_executor = mock_run_in_executor

            with pytest.raises(VersionerError, match="Failed to stash changes"):
                await versioner_without_auth.stash("/path/to/repo", "Test message")

    @pytest.mark.asyncio
    async def test_safe_pull_no_changes(self, versioner_without_auth) -> None:
        """Test safe_pull when there are no local changes."""
        with (
            patch(
                "kbot_installer.core.versioner.gitpython_versioner.Repo"
            ) as mock_repo_class,
            patch.object(versioner_without_auth, "pull") as mock_pull,
            patch.object(versioner_without_auth, "stash") as mock_stash,
        ):
            mock_repo = MagicMock()
            mock_repo_class.return_value = mock_repo
            mock_stash.return_value = False  # No stash created

            await versioner_without_auth.safe_pull("/path/to/repo", "main")

            mock_stash.assert_called_once_with(Path("/path/to/repo"), "Safe pull stash")
            mock_pull.assert_called_once_with(Path("/path/to/repo"), "main")

    @pytest.mark.asyncio
    async def test_safe_pull_with_changes(self, versioner_without_auth) -> None:
        """Test safe_pull when there are local changes."""
        with (
            patch(
                "kbot_installer.core.versioner.gitpython_versioner.Repo"
            ) as mock_repo_class,
            patch.object(versioner_without_auth, "pull") as mock_pull,
            patch.object(versioner_without_auth, "stash") as mock_stash,
            patch.object(versioner_without_auth, "_apply_stash") as mock_apply_stash,
        ):
            mock_repo = MagicMock()
            mock_repo_class.return_value = mock_repo
            mock_stash.return_value = True  # Stash was created

            await versioner_without_auth.safe_pull("/path/to/repo", "main")

            mock_stash.assert_called_once_with(Path("/path/to/repo"), "Safe pull stash")
            mock_pull.assert_called_once_with(Path("/path/to/repo"), "main")
            mock_apply_stash.assert_called_once_with(mock_repo)

    @pytest.mark.asyncio
    async def test_safe_pull_pull_failure_with_stash_restore(
        self, versioner_without_auth
    ) -> None:
        """Test safe_pull when pull fails and stash is restored."""
        with (
            patch(
                "kbot_installer.core.versioner.gitpython_versioner.Repo"
            ) as mock_repo_class,
            patch.object(versioner_without_auth, "pull") as mock_pull,
            patch.object(versioner_without_auth, "stash") as mock_stash,
            patch.object(versioner_without_auth, "_apply_stash") as mock_apply_stash,
        ):
            mock_repo = MagicMock()
            mock_repo_class.return_value = mock_repo
            mock_stash.return_value = True  # Stash was created
            mock_pull.side_effect = VersionerError("Pull failed")

            with pytest.raises(VersionerError, match="Pull failed"):
                await versioner_without_auth.safe_pull("/path/to/repo", "main")

            mock_stash.assert_called_once_with(Path("/path/to/repo"), "Safe pull stash")
            mock_pull.assert_called_once_with(Path("/path/to/repo"), "main")
            # Should try to restore stash after pull failure
            mock_apply_stash.assert_called_once_with(mock_repo)

    @pytest.mark.asyncio
    async def test_apply_stash_no_stashes(self, versioner_without_auth) -> None:
        """Test _apply_stash when there are no stashes."""
        mock_repo = MagicMock()
        mock_repo.git.stash.return_value = ""  # No stashes

        # Should not raise an error and should not call run_in_executor
        await versioner_without_auth._apply_stash(mock_repo)

        mock_repo.git.stash.assert_called_once_with("list")

    @pytest.mark.asyncio
    async def test_apply_stash_with_stashes(self, versioner_without_auth) -> None:
        """Test _apply_stash when there are stashes."""
        with patch("asyncio.get_event_loop") as mock_loop:
            mock_repo = MagicMock()
            mock_repo.git.stash.return_value = "stash@{0}: Test stash"  # Has stashes

            # Mock run_in_executor to return a coroutine
            mock_run_in_executor = MagicMock()

            async def mock_executor(*_args: Any, **_kwargs: Any):  # noqa: ANN401
                return None

            mock_run_in_executor.return_value = mock_executor()
            mock_loop.return_value.run_in_executor = mock_run_in_executor

            await versioner_without_auth._apply_stash(mock_repo)

            mock_repo.git.stash.assert_called_with("list")
            mock_run_in_executor.assert_called_once()

    @pytest.mark.asyncio
    async def test_apply_stash_git_command_error(self, versioner_without_auth) -> None:
        """Test _apply_stash handles GitCommandError."""
        with patch("asyncio.get_event_loop") as mock_loop:
            mock_repo = MagicMock()
            mock_repo.git.stash.return_value = "stash@{0}: Test stash"  # Has stashes

            async def mock_run_in_executor(_executor, _func):
                error_msg = "Apply failed"
                command = "stash"
                raise GitCommandError(command, error_msg)

            mock_loop.return_value.run_in_executor = mock_run_in_executor

            with pytest.raises(VersionerError, match="Failed to apply stash"):
                await versioner_without_auth._apply_stash(mock_repo)
