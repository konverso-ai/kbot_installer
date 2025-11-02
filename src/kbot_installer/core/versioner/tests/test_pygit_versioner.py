"""Tests for pygit_versioner module."""

from pathlib import Path
from unittest.mock import MagicMock, PropertyMock, patch

import pygit2
import pytest

from kbot_installer.core.auth.pygit_authentication.pygit_authentication_base import (
    PyGitAuthenticationBase,
)
from kbot_installer.core.versioner.pygit_versioner import PygitVersioner
from kbot_installer.core.versioner.versioner_base import VersionerBase, VersionerError


class TestPygitVersioner:
    """Test cases for PygitVersioner."""

    @pytest.fixture
    def versioner(self) -> PygitVersioner:
        """Create a PygitVersioner for testing."""
        return PygitVersioner()

    @pytest.fixture
    def versioner_with_auth(self) -> PygitVersioner:
        """Create a PygitVersioner with authentication for testing."""
        mock_auth = MagicMock(spec=PyGitAuthenticationBase)
        return PygitVersioner(mock_auth)

    @pytest.fixture
    def mock_repo(self) -> tuple[MagicMock, MagicMock]:
        """Create a mock repository."""
        mock_repo = MagicMock()
        mock_remote = MagicMock()
        mock_repo.remotes = {"origin": mock_remote}
        mock_repo.head.shorthand = "main"
        return mock_repo, mock_remote

    @pytest.fixture
    def mock_auth(self) -> tuple[MagicMock, MagicMock]:
        """Create mock authentication."""
        mock_auth = MagicMock()
        mock_callbacks = MagicMock()
        mock_auth.get_connector.return_value = mock_callbacks
        return mock_auth, mock_callbacks

    def test_inherits_from_versioner_base(self) -> None:
        """Test that PygitVersioner inherits from VersionerBase."""
        assert issubclass(PygitVersioner, VersionerBase)

    def test_initialization_with_auth(self) -> None:
        """Test that PygitVersioner initializes with authentication."""
        mock_auth = MagicMock(spec=PyGitAuthenticationBase)
        versioner = PygitVersioner(mock_auth)

        assert versioner._auth == mock_auth

    def test_initialization_without_auth(self) -> None:
        """Test that PygitVersioner initializes without authentication."""
        versioner = PygitVersioner()

        assert versioner._auth is None

    def test_initialization_with_none_auth(self) -> None:
        """Test that PygitVersioner initializes with None authentication."""
        versioner = PygitVersioner(None)

        assert versioner._auth is None

    def test_get_auth_returns_stored_auth(self) -> None:
        """Test that _get_auth returns the stored authentication."""
        mock_auth = MagicMock(spec=PyGitAuthenticationBase)
        versioner = PygitVersioner(mock_auth)

        assert versioner._get_auth() == mock_auth

    def test_get_auth_returns_none_when_no_auth(self) -> None:
        """Test that _get_auth returns None when no authentication."""
        versioner = PygitVersioner()

        assert versioner._get_auth() is None

    def test_get_auth_returns_none_when_none_auth(self) -> None:
        """Test that _get_auth returns None when authentication is None."""
        versioner = PygitVersioner(None)

        assert versioner._get_auth() is None

    def test_can_be_instantiated_with_different_auth_types(self) -> None:
        """Test that PygitVersioner can be instantiated with different auth types."""
        # Test with PyGitAuthenticationBase
        mock_auth = MagicMock(spec=PyGitAuthenticationBase)
        versioner1 = PygitVersioner(mock_auth)
        assert versioner1._auth == mock_auth

        # Test with None
        versioner2 = PygitVersioner(None)
        assert versioner2._auth is None

        # Test with no arguments
        versioner3 = PygitVersioner()
        assert versioner3._auth is None

    def test_auth_attribute_is_private(self) -> None:
        """Test that the auth attribute is private."""
        mock_auth = MagicMock(spec=PyGitAuthenticationBase)
        versioner = PygitVersioner(mock_auth)

        # Should not be accessible directly
        assert not hasattr(versioner, "auth")
        assert hasattr(versioner, "_auth")

    def test_implements_versioner_base_interface(self) -> None:
        """Test that PygitVersioner implements VersionerBase interface."""
        versioner = PygitVersioner()

        # Check that required methods are available
        assert hasattr(versioner, "_get_auth")
        assert hasattr(versioner, "clone")
        assert hasattr(versioner, "checkout")
        assert hasattr(versioner, "select_branch")
        assert hasattr(versioner, "add")
        assert hasattr(versioner, "pull")
        assert hasattr(versioner, "commit")
        assert hasattr(versioner, "push")

        # Check that methods are callable
        assert callable(versioner._get_auth)
        assert callable(versioner.clone)
        assert callable(versioner.checkout)
        assert callable(versioner.select_branch)
        assert callable(versioner.add)
        assert callable(versioner.pull)
        assert callable(versioner.commit)
        assert callable(versioner.push)

    def test_auth_persistence(self) -> None:
        """Test that authentication persists after initialization."""
        mock_auth = MagicMock(spec=PyGitAuthenticationBase)
        versioner = PygitVersioner(mock_auth)

        # Multiple calls should return the same auth object
        assert versioner._get_auth() == mock_auth
        assert versioner._get_auth() == mock_auth
        assert versioner._get_auth() is mock_auth

    def test_get_repository_with_existing_path(self, versioner) -> None:
        """Test that _get_repository works with existing path."""
        with patch("pygit2.Repository") as mock_repo_class:
            mock_repo = MagicMock()
            mock_repo_class.return_value = mock_repo

            with patch("pathlib.Path.exists", return_value=True):
                result = versioner._get_repository("/test/path")

                assert result == mock_repo
                mock_repo_class.assert_called_once_with("/test/path")

    def test_get_repository_with_nonexistent_path(self, versioner) -> None:
        """Test that _get_repository raises VersionerError for nonexistent path."""
        with (
            patch("pathlib.Path.exists", return_value=False),
            pytest.raises(VersionerError, match="Repository path does not exist"),
        ):
            versioner._get_repository("/nonexistent/path")

    def test_get_repository_with_git_error(self, versioner) -> None:
        """Test that _get_repository handles pygit2.GitError."""
        import pygit2

        with (
            patch("pathlib.Path.exists", return_value=True),
            patch("pygit2.Repository", side_effect=pygit2.GitError("Git error")),
        ):
            with pytest.raises(VersionerError, match="Failed to open repository"):
                versioner._get_repository("/test/path")

    @pytest.mark.asyncio
    async def test_add_with_all_files(self, versioner) -> None:
        """Test that add works with all files."""
        with patch.object(versioner, "_get_repository") as mock_get_repo:
            mock_repo = MagicMock()
            mock_index = MagicMock()
            mock_repo.index = mock_index
            mock_get_repo.return_value = mock_repo

            await versioner.add("/test/path", None)

            mock_index.add_all.assert_called_once()
            mock_index.write.assert_called_once()

    @pytest.mark.asyncio
    async def test_add_with_git_error(self, versioner) -> None:
        """Test that add handles pygit2.GitError."""
        import pygit2

        with patch.object(versioner, "_get_repository") as mock_get_repo:
            mock_repo = MagicMock()
            mock_index = MagicMock()
            mock_repo.index = mock_index
            mock_get_repo.return_value = mock_repo
            mock_index.add_all.side_effect = pygit2.GitError("Git error")

            with pytest.raises(
                VersionerError, match="Failed to add files to repository"
            ):
                await versioner.add("/test/path", None)

    @pytest.mark.asyncio
    async def test_pull_with_authentication(
        self, versioner_with_auth, mock_repo, mock_auth
    ) -> None:
        """Test that pull works with authentication."""
        mock_repo_obj, mock_remote = mock_repo
        mock_auth_obj, mock_callbacks = mock_auth

        with (
            patch.object(
                versioner_with_auth, "_get_repository", return_value=mock_repo_obj
            ),
            patch.object(versioner_with_auth, "_get_auth", return_value=mock_auth_obj),
        ):
            mock_ref = MagicMock()
            mock_repo_obj.lookup_reference.return_value = mock_ref

            await versioner_with_auth.pull("/test/path", "main")

            mock_remote.fetch.assert_called_once_with(callbacks=mock_callbacks)
            mock_repo_obj.merge_analysis.assert_called_once_with(mock_ref.target)
            mock_repo_obj.merge.assert_called_once_with(mock_ref.target)

    @pytest.mark.asyncio
    async def test_pull_without_authentication(self, versioner, mock_repo) -> None:
        """Test that pull works without authentication."""
        mock_repo_obj, mock_remote = mock_repo

        with (
            patch.object(versioner, "_get_repository", return_value=mock_repo_obj),
            patch.object(versioner, "_get_auth", return_value=None),
        ):
            mock_ref = MagicMock()
            mock_repo_obj.lookup_reference.return_value = mock_ref

            await versioner.pull("/test/path", "main")

            mock_remote.fetch.assert_called_once_with()
            mock_repo_obj.merge_analysis.assert_called_once_with(mock_ref.target)
            mock_repo_obj.merge.assert_called_once_with(mock_ref.target)

    @pytest.mark.asyncio
    async def test_pull_with_missing_origin(self, versioner) -> None:
        """Test that pull handles missing origin remote."""
        with patch.object(versioner, "_get_repository") as mock_get_repo:
            mock_repo = MagicMock()
            mock_repo.remotes = {}
            mock_get_repo.return_value = mock_repo

            with pytest.raises(VersionerError, match="No 'origin' remote found"):
                await versioner.pull("/test/path", "main")

    @pytest.mark.asyncio
    async def test_pull_with_missing_remote_branch(self, versioner) -> None:
        """Test that pull handles missing remote branch."""
        with patch.object(versioner, "_get_repository") as mock_get_repo:
            mock_repo = MagicMock()
            mock_remote = MagicMock()
            mock_repo.remotes = {"origin": mock_remote}
            mock_repo.head.shorthand = "main"
            mock_repo.lookup_reference.side_effect = KeyError("Not found")
            mock_get_repo.return_value = mock_repo

            with pytest.raises(
                VersionerError, match="Remote branch 'origin/main' not found"
            ):
                await versioner.pull("/test/path", "main")

    @pytest.mark.asyncio
    async def test_pull_with_no_current_branch(self, versioner) -> None:
        """Test that pull handles no current branch."""
        import pygit2

        # Create a custom mock head that raises GitError when shorthand is accessed
        class MockHead:
            @property
            def shorthand(self):
                error_msg = "No current branch"
                raise pygit2.GitError(error_msg)

        with patch.object(versioner, "_get_repository") as mock_get_repo:
            mock_repo = MagicMock()
            mock_remote = MagicMock()
            mock_repo.remotes = {"origin": mock_remote}
            mock_repo.lookup_reference.return_value = MagicMock()
            mock_get_repo.return_value = mock_repo

            # Use the custom mock head
            mock_repo.head = MockHead()

            with pytest.raises(VersionerError, match="No current branch found"):
                await versioner.pull("/test/path", "main")

    @pytest.mark.asyncio
    async def test_commit_with_staged_changes(self, versioner) -> None:
        """Test that commit works with staged changes."""
        mock_repo = MagicMock()
        mock_index = MagicMock()
        mock_repo.index = mock_index
        mock_repo.head.target = "HEAD"
        mock_index.write_tree.return_value = "tree_oid"

        with patch.object(versioner, "_get_repository", return_value=mock_repo):
            await versioner.commit("/test/path", "Test commit")

            mock_repo.create_commit.assert_called_once()
            call_args = mock_repo.create_commit.call_args
            assert call_args[0][0] == "HEAD"  # ref
            assert call_args[0][4] == "tree_oid"  # tree
            assert call_args[0][5] == ["HEAD"]  # parent

    @pytest.mark.asyncio
    async def test_commit_with_no_staged_changes(self, versioner) -> None:
        """Test that commit returns without error when no staged changes."""
        with patch.object(versioner, "_get_repository") as mock_get_repo:
            mock_repo = MagicMock()
            mock_index = MagicMock()
            mock_repo.index = mock_index

            # Mock HEAD exists and trees are the same (no changes)
            mock_head = MagicMock()
            mock_head.target = "some_commit_hash"
            mock_repo.head = mock_head
            mock_head.peel.return_value.tree = "same_tree_id"
            mock_index.write_tree.return_value = "same_tree_id"
            mock_get_repo.return_value = mock_repo

            # Should return without error when no changes to commit
            await versioner.commit("/test/path", "Test commit")

    @pytest.mark.asyncio
    async def test_commit_with_initial_commit(self, versioner) -> None:
        """Test that commit works with initial commit (no HEAD)."""
        mock_repo = MagicMock()
        mock_index = MagicMock()
        mock_repo.index = mock_index
        mock_repo.head.target = None
        mock_index.write_tree.return_value = "tree_oid"

        with patch.object(versioner, "_get_repository", return_value=mock_repo):
            await versioner.commit("/test/path", "Initial commit")

            mock_repo.create_commit.assert_called_once()
            call_args = mock_repo.create_commit.call_args
            assert call_args[0][5] == []  # Empty parent list

    @pytest.mark.asyncio
    async def test_push_with_authentication(self, versioner_with_auth) -> None:
        """Test that push works with authentication."""
        with patch.object(versioner_with_auth, "_get_repository") as mock_get_repo:
            mock_repo = MagicMock()
            mock_remote = MagicMock()
            mock_repo.remotes = {"origin": mock_remote}
            mock_repo.head.shorthand = "main"
            mock_get_repo.return_value = mock_repo

            with patch.object(versioner_with_auth, "_get_auth") as mock_get_auth:
                mock_auth = MagicMock()
                mock_callbacks = MagicMock()
                mock_auth.get_connector.return_value = mock_callbacks
                mock_get_auth.return_value = mock_auth

                await versioner_with_auth.push("/test/path", "main")

                mock_remote.push.assert_called_once_with(
                    ["refs/heads/main:refs/heads/main"], callbacks=mock_callbacks
                )

    @pytest.mark.asyncio
    async def test_push_without_authentication(self, versioner) -> None:
        """Test that push works without authentication."""
        with patch.object(versioner, "_get_repository") as mock_get_repo:
            mock_repo = MagicMock()
            mock_remote = MagicMock()
            mock_repo.remotes = {"origin": mock_remote}
            mock_repo.head.shorthand = "main"
            mock_get_repo.return_value = mock_repo

            with patch.object(versioner, "_get_auth", return_value=None):
                await versioner.push("/test/path", "main")

                mock_remote.push.assert_called_once_with(
                    ["refs/heads/main:refs/heads/main"]
                )

    @pytest.mark.asyncio
    async def test_push_with_missing_origin(self, versioner) -> None:
        """Test that push handles missing origin remote."""
        with patch.object(versioner, "_get_repository") as mock_get_repo:
            mock_repo = MagicMock()
            mock_repo.remotes = {}
            mock_get_repo.return_value = mock_repo

            with pytest.raises(VersionerError, match="No 'origin' remote found"):
                await versioner.push("/test/path", "main")

    @pytest.mark.asyncio
    async def test_push_with_no_current_branch(self, versioner) -> None:
        """Test that push handles no current branch."""
        import pygit2

        # Create a custom mock head that raises GitError when shorthand is accessed
        class MockHead:
            @property
            def shorthand(self):
                error_msg = "No current branch"
                raise pygit2.GitError(error_msg)

        with patch.object(versioner, "_get_repository") as mock_get_repo:
            mock_repo = MagicMock()
            mock_remote = MagicMock()
            mock_repo.remotes = {"origin": mock_remote}
            mock_get_repo.return_value = mock_repo

            # Use the custom mock head
            mock_repo.head = MockHead()

            with pytest.raises(VersionerError, match="No current branch found"):
                await versioner.push("/test/path", "main")

    @pytest.mark.asyncio
    async def test_push_with_git_error(self, versioner) -> None:
        """Test that push handles pygit2.GitError."""
        import pygit2

        with patch.object(versioner, "_get_repository") as mock_get_repo:
            mock_repo = MagicMock()
            mock_remote = MagicMock()
            mock_repo.remotes = {"origin": mock_remote}
            mock_repo.head.shorthand = "main"
            mock_get_repo.return_value = mock_repo
            mock_remote.push.side_effect = pygit2.GitError("Git error")

            with pytest.raises(
                VersionerError, match="Failed to push to remote repository"
            ):
                await versioner.push("/test/path", "main")

    @pytest.mark.asyncio
    async def test_clone_with_authentication(
        self, versioner_with_auth, mock_auth
    ) -> None:
        """Test that clone works with authentication."""
        mock_auth_obj, mock_callbacks = mock_auth

        with (
            patch.object(versioner_with_auth, "_get_auth", return_value=mock_auth_obj),
            patch("pygit2.clone_repository") as mock_clone,
            patch("pathlib.Path.mkdir") as mock_mkdir,
        ):
            await versioner_with_auth.clone(
                "https://github.com/test/repo.git", "/test/path"
            )

            mock_mkdir.assert_called_once_with(parents=True, exist_ok=True)
            mock_clone.assert_called_once_with(
                "https://github.com/test/repo.git",
                "/test/path",
                callbacks=mock_callbacks,
            )

    @pytest.mark.asyncio
    async def test_clone_without_authentication(self, versioner) -> None:
        """Test that clone works without authentication."""
        with (
            patch.object(versioner, "_get_auth", return_value=None),
            patch("pygit2.clone_repository") as mock_clone,
            patch("pathlib.Path.mkdir") as mock_mkdir,
        ):
            await versioner.clone("https://github.com/test/repo.git", "/test/path")

            mock_mkdir.assert_called_once_with(parents=True, exist_ok=True)
            mock_clone.assert_called_once_with(
                "https://github.com/test/repo.git", "/test/path"
            )

    @pytest.mark.asyncio
    async def test_clone_with_git_error(self, versioner) -> None:
        """Test that clone handles pygit2.GitError."""
        import pygit2

        with (
            patch.object(versioner, "_get_auth", return_value=None),
            patch("pygit2.clone_repository", side_effect=pygit2.GitError("Git error")),
            patch("pathlib.Path.mkdir"),
        ):
            with pytest.raises(VersionerError, match="Failed to clone repository"):
                await versioner.clone("https://github.com/test/repo.git", "/test/path")

    @pytest.mark.asyncio
    async def test_select_branch_success_first_branch(self, versioner) -> None:
        """Test select_branch with successful first branch."""
        with patch.object(versioner, "_get_repository") as mock_get_repo:
            mock_repo = MagicMock()
            mock_repo.references = [
                "refs/heads/main",
                "refs/heads/other",
                "refs/remotes/origin/master",
            ]
            mock_get_repo.return_value = mock_repo

            result = await versioner.select_branch("/test/repo", ["main", "master"])

            assert result == "main"
            mock_get_repo.assert_called_once_with("/test/repo")

    @pytest.mark.asyncio
    async def test_select_branch_success_second_branch(self, versioner) -> None:
        """Test select_branch with successful second branch."""
        with patch.object(versioner, "_get_repository") as mock_get_repo:
            mock_repo = MagicMock()
            mock_repo.references = ["refs/heads/other", "refs/remotes/origin/master"]
            mock_get_repo.return_value = mock_repo

            result = await versioner.select_branch("/test/repo", ["main", "master"])

            assert result == "master"
            mock_get_repo.assert_called_once_with("/test/repo")

    @pytest.mark.asyncio
    async def test_select_branch_no_success(self, versioner) -> None:
        """Test select_branch with no successful branches."""
        with patch.object(versioner, "_get_repository") as mock_get_repo:
            mock_repo = MagicMock()
            mock_repo.references = ["refs/heads/other", "refs/remotes/origin/feature"]
            mock_get_repo.return_value = mock_repo

            result = await versioner.select_branch(
                "/test/repo", ["main", "master", "develop"]
            )

            assert result is None
            mock_get_repo.assert_called_once_with("/test/repo")

    @pytest.mark.asyncio
    async def test_select_branch_empty_branches(self, versioner) -> None:
        """Test select_branch with empty branches list."""
        result = await versioner.select_branch("/test/repo", [])

        assert result is None

    @pytest.mark.asyncio
    async def test_select_branch_single_branch_success(self, versioner) -> None:
        """Test select_branch with single successful branch."""
        with patch.object(versioner, "_get_repository") as mock_get_repo:
            mock_repo = MagicMock()
            mock_repo.references = ["refs/heads/main", "refs/heads/other"]
            mock_get_repo.return_value = mock_repo

            result = await versioner.select_branch("/test/repo", ["main"])

            assert result == "main"
            mock_get_repo.assert_called_once_with("/test/repo")

    @pytest.mark.asyncio
    async def test_select_branch_single_branch_failure(self, versioner) -> None:
        """Test select_branch with single failing branch."""
        with patch.object(versioner, "_get_repository") as mock_get_repo:
            mock_repo = MagicMock()
            mock_repo.references = ["refs/heads/other", "refs/remotes/origin/feature"]
            mock_get_repo.return_value = mock_repo

            result = await versioner.select_branch("/test/repo", ["main"])

            assert result is None
            mock_get_repo.assert_called_once_with("/test/repo")

    def test_check_remote_repository_exists_success(self, versioner) -> None:
        """Test check_remote_repository_exists with successful repository."""
        with (
            patch("tempfile.mkdtemp", return_value="/tmp/test"),
            patch("pygit2.init_repository") as mock_init,
            patch("pygit2.Repository") as mock_repo_class,
            patch("pathlib.Path.exists", return_value=True),
            patch("shutil.rmtree") as mock_rmtree,
        ):
            mock_repo = MagicMock()
            mock_remote = MagicMock()
            mock_repo.remotes.create_anonymous.return_value = mock_remote
            mock_repo_class.return_value = mock_repo

            result = versioner.check_remote_repository_exists(
                "https://github.com/test/repo.git"
            )

            assert result is True
            mock_init.assert_called_once_with("/tmp/test", bare=True)
            mock_remote.ls_remotes.assert_called_once_with()
            mock_rmtree.assert_called_once_with(Path("/tmp/test"), ignore_errors=True)

    def test_check_remote_repository_exists_failure(self, versioner) -> None:
        """Test check_remote_repository_exists with repository not found."""
        import pygit2

        with (
            patch("tempfile.mkdtemp", return_value="/tmp/test"),
            patch("pygit2.init_repository"),
            patch("pygit2.Repository") as mock_repo_class,
            patch("pathlib.Path.exists", return_value=True),
            patch("shutil.rmtree") as mock_rmtree,
        ):
            mock_repo = MagicMock()
            mock_remote = MagicMock()
            mock_repo.remotes.create_anonymous.return_value = mock_remote
            mock_remote.ls_remotes.side_effect = pygit2.GitError("Repository not found")
            mock_repo_class.return_value = mock_repo

            result = versioner.check_remote_repository_exists(
                "https://github.com/nonexistent/repo.git"
            )

            assert result is False
            mock_rmtree.assert_called_once_with(Path("/tmp/test"), ignore_errors=True)

    def test_check_remote_repository_exists_handles_exception(self, versioner) -> None:
        """Test check_remote_repository_exists handles unexpected exceptions."""
        with (
            patch("tempfile.mkdtemp", side_effect=OSError("Permission denied")),
            patch("shutil.rmtree") as mock_rmtree,
        ):
            result = versioner.check_remote_repository_exists(
                "https://github.com/test/repo.git"
            )

            assert result is False
            # Should not call rmtree if temp directory creation fails
            mock_rmtree.assert_not_called()

    @pytest.mark.asyncio
    async def test_checkout_remote_branch_success(self, versioner) -> None:
        """Test checkout of existing remote branch."""
        with (
            patch("pygit2.Repository") as mock_repo_class,
            patch("pathlib.Path.exists", return_value=True),
        ):
            mock_repo = MagicMock()
            mock_repo_class.return_value = mock_repo

            # Mock repository references
            mock_repo.references = [
                "refs/remotes/origin/feature-branch",
                "refs/heads/main",
            ]

            # Mock remote reference lookup
            mock_remote_ref = MagicMock()
            mock_remote_ref.peel.return_value = "commit_hash"
            mock_repo.lookup_reference.return_value = mock_remote_ref

            # Mock branch creation and checkout
            mock_repo.create_branch.return_value = None
            mock_repo.checkout.return_value = None

            await versioner.checkout("/path/to/repo", "feature-branch")

            mock_repo.create_branch.assert_called_once_with(
                "feature-branch", "commit_hash"
            )
            mock_repo.checkout.assert_called_once_with("refs/heads/feature-branch")

    @pytest.mark.asyncio
    async def test_checkout_branch_not_found(self, versioner) -> None:
        """Test checkout of non-existent branch."""
        with (
            patch("pygit2.Repository") as mock_repo_class,
            patch("pathlib.Path.exists", return_value=True),
        ):
            mock_repo = MagicMock()
            mock_repo_class.return_value = mock_repo

            # Mock repository references - no matching branches
            mock_repo.references = [
                "refs/heads/main",
                "refs/remotes/origin/main",
            ]

            with pytest.raises(
                VersionerError, match="Version 'feature-branch' not found"
            ):
                await versioner.checkout("/path/to/repo", "feature-branch")

    @pytest.mark.asyncio
    async def test_checkout_branch_not_found_with_available_branches(
        self, versioner
    ) -> None:
        """Test checkout of non-existent branch with available branches listed."""
        with (
            patch("pygit2.Repository") as mock_repo_class,
            patch("pathlib.Path.exists", return_value=True),
        ):
            mock_repo = MagicMock()
            mock_repo_class.return_value = mock_repo

            # Mock repository references with various branches
            mock_repo.references = [
                "refs/heads/main",
                "refs/heads/develop",
                "refs/remotes/origin/main",
                "refs/remotes/origin/develop",
            ]

            with pytest.raises(
                VersionerError, match="Version 'feature-branch' not found"
            ):
                await versioner.checkout("/path/to/repo", "feature-branch")

    @pytest.mark.asyncio
    async def test_checkout_branch_not_found_no_available_branches(
        self, versioner
    ) -> None:
        """Test checkout of non-existent branch with no available branches."""
        with (
            patch("pygit2.Repository") as mock_repo_class,
            patch("pathlib.Path.exists", return_value=True),
        ):
            mock_repo = MagicMock()
            mock_repo_class.return_value = mock_repo

            # Mock repository references - no branches
            mock_repo.references = []

            with pytest.raises(
                VersionerError, match="Version 'feature-branch' not found"
            ):
                await versioner.checkout("/path/to/repo", "feature-branch")

    @pytest.mark.asyncio
    async def test_checkout_remote_branch_creation_failure(self, versioner) -> None:
        """Test checkout when remote branch creation fails."""
        with (
            patch("pygit2.Repository") as mock_repo_class,
            patch("pathlib.Path.exists", return_value=True),
        ):
            mock_repo = MagicMock()
            mock_repo_class.return_value = mock_repo

            # Mock repository references
            mock_repo.references = [
                "refs/remotes/origin/feature-branch",
            ]

            # Mock remote reference lookup
            mock_remote_ref = MagicMock()
            mock_remote_ref.peel.return_value = "commit_hash"
            mock_repo.lookup_reference.return_value = mock_remote_ref

            # Mock branch creation failure
            mock_repo.create_branch.side_effect = pygit2.GitError(
                "Branch creation failed"
            )

            with pytest.raises(
                VersionerError, match="Failed to create and checkout branch"
            ):
                await versioner.checkout("/path/to/repo", "feature-branch")

    @pytest.mark.asyncio
    async def test_checkout_local_branch_checkout_failure(self, versioner) -> None:
        """Test checkout when local branch checkout fails."""
        with (
            patch("pygit2.Repository") as mock_repo_class,
            patch("pathlib.Path.exists", return_value=True),
        ):
            mock_repo = MagicMock()
            mock_repo_class.return_value = mock_repo

            # Mock repository references
            mock_repo.references = [
                "refs/heads/feature-branch",
            ]

            # Mock checkout failure
            mock_repo.checkout.side_effect = pygit2.GitError("Checkout failed")

            with pytest.raises(VersionerError, match="Failed to checkout local branch"):
                await versioner.checkout("/path/to/repo", "feature-branch")

    def test_str_representation(self, versioner) -> None:
        """Test string representation of versioner."""
        str_repr = str(versioner)
        assert "PygitVersioner" in str_repr
        assert "auth=False" in str_repr

    def test_str_representation_with_auth(self, versioner_with_auth) -> None:
        """Test string representation of versioner with auth."""
        str_repr = str(versioner_with_auth)
        assert "PygitVersioner" in str_repr
        assert "auth=" in str_repr

    def test_repr_representation(self, versioner) -> None:
        """Test detailed string representation of versioner."""
        repr_str = repr(versioner)
        assert "PygitVersioner" in repr_str
        assert "auth=None" in repr_str

    def test_repr_representation_with_auth(self, versioner_with_auth) -> None:
        """Test detailed string representation of versioner with auth."""
        repr_str = repr(versioner_with_auth)
        assert "PygitVersioner" in repr_str
        assert "auth=" in repr_str

    def test_check_remote_repository_exists_with_fetch_success(self, versioner) -> None:
        """Test _check_remote_repository_exists_with_fetch with successful repository."""
        with (
            patch("tempfile.mkdtemp", return_value="/tmp/test"),
            patch("pygit2.init_repository") as mock_init,
            patch("pygit2.Repository") as mock_repo_class,
            patch("pathlib.Path.exists", return_value=True),
            patch("shutil.rmtree") as mock_rmtree,
        ):
            mock_repo = MagicMock()
            mock_remote = MagicMock()
            mock_repo.remotes.create_anonymous.return_value = mock_remote
            mock_repo_class.return_value = mock_repo

            result = versioner._check_remote_repository_exists_with_fetch(
                "https://github.com/test/repo.git"
            )

            assert result is True
            mock_init.assert_called_once_with("/tmp/test", bare=True)
            mock_remote.ls_remotes.assert_called_once_with()
            mock_rmtree.assert_called_once_with(Path("/tmp/test"), ignore_errors=True)

    def test_check_remote_repository_exists_with_fetch_with_auth(
        self, versioner_with_auth
    ) -> None:
        """Test _check_remote_repository_exists_with_fetch with authentication."""
        with (
            patch("tempfile.mkdtemp", return_value="/tmp/test"),
            patch("pygit2.init_repository"),
            patch("pygit2.Repository") as mock_repo_class,
            patch("pathlib.Path.exists", return_value=True),
            patch("shutil.rmtree"),
        ):
            mock_repo = MagicMock()
            mock_remote = MagicMock()
            mock_auth = MagicMock()
            mock_callbacks = MagicMock()
            mock_auth.get_connector.return_value = mock_callbacks
            versioner_with_auth._get_auth = MagicMock(return_value=mock_auth)
            mock_repo.remotes.create_anonymous.return_value = mock_remote
            mock_repo_class.return_value = mock_repo

            result = versioner_with_auth._check_remote_repository_exists_with_fetch(
                "https://github.com/test/repo.git"
            )

            assert result is True
            mock_remote.ls_remotes.assert_called_once_with(callbacks=mock_callbacks)

    def test_check_remote_repository_exists_with_fetch_failure(self, versioner) -> None:
        """Test _check_remote_repository_exists_with_fetch with repository failure."""
        with (
            patch("tempfile.mkdtemp", return_value="/tmp/test"),
            patch("pygit2.init_repository"),
            patch("pygit2.Repository") as mock_repo_class,
            patch("pathlib.Path.exists", return_value=True),
            patch("shutil.rmtree") as mock_rmtree,
        ):
            mock_repo = MagicMock()
            mock_remote = MagicMock()
            mock_remote.ls_remotes.side_effect = pygit2.GitError("Repository not found")
            mock_repo.remotes.create_anonymous.return_value = mock_remote
            mock_repo_class.return_value = mock_repo

            result = versioner._check_remote_repository_exists_with_fetch(
                "https://github.com/test/repo.git"
            )

            assert result is False
            mock_rmtree.assert_called_once_with(Path("/tmp/test"), ignore_errors=True)

    def test_check_remote_repository_exists_with_fetch_handles_exception(
        self, versioner
    ) -> None:
        """Test _check_remote_repository_exists_with_fetch handles unexpected exceptions."""
        with (
            patch("tempfile.mkdtemp", return_value="/tmp/test"),
            patch("pygit2.init_repository"),
            patch("pygit2.Repository") as mock_repo_class,
            patch("pathlib.Path.exists", return_value=True),
            patch("shutil.rmtree") as mock_rmtree,
        ):
            mock_repo = MagicMock()
            mock_remote = MagicMock()
            mock_remote.ls_remotes.side_effect = Exception("Unexpected error")
            mock_repo.remotes.create_anonymous.return_value = mock_remote
            mock_repo_class.return_value = mock_repo

            result = versioner._check_remote_repository_exists_with_fetch(
                "https://github.com/test/repo.git"
            )

            assert result is False
            mock_rmtree.assert_called_once_with(Path("/tmp/test"), ignore_errors=True)

    def test_check_remote_repository_exists_with_fetch_cleanup_on_error(
        self, versioner
    ) -> None:
        """Test _check_remote_repository_exists_with_fetch cleans up on error."""
        with (
            patch("tempfile.mkdtemp", return_value="/tmp/test"),
            patch("pygit2.init_repository"),
            patch("pygit2.Repository") as mock_repo_class,
            patch("pathlib.Path.exists", return_value=True),
            patch("shutil.rmtree") as mock_rmtree,
        ):
            mock_repo = MagicMock()
            mock_remote = MagicMock()
            mock_remote.ls_remotes.side_effect = pygit2.GitError("Repository not found")
            mock_repo.remotes.create_anonymous.return_value = mock_remote
            mock_repo_class.return_value = mock_repo

            result = versioner._check_remote_repository_exists_with_fetch(
                "https://github.com/test/repo.git"
            )

            assert result is False
            mock_rmtree.assert_called_once_with(Path("/tmp/test"), ignore_errors=True)

    def test_check_remote_repository_exists_with_fetch_cleanup_in_finally(
        self, versioner
    ) -> None:
        """Test _check_remote_repository_exists_with_fetch cleanup in finally block."""
        with (
            patch("tempfile.mkdtemp", return_value="/tmp/test"),
            patch("pygit2.init_repository"),
            patch("pygit2.Repository") as mock_repo_class,
            patch("pathlib.Path.exists", return_value=True),
            patch("shutil.rmtree") as mock_rmtree,
        ):
            mock_repo = MagicMock()
            mock_remote = MagicMock()
            mock_remote.ls_remotes.side_effect = pygit2.GitError("Repository not found")
            mock_repo.remotes.create_anonymous.return_value = mock_remote
            mock_repo_class.return_value = mock_repo

            result = versioner._check_remote_repository_exists_with_fetch(
                "https://github.com/test/repo.git"
            )

            assert result is False
            # Should call rmtree in finally block even on error
            mock_rmtree.assert_called_once_with(Path("/tmp/test"), ignore_errors=True)

    @pytest.mark.asyncio
    async def test_add_with_specific_files(self, versioner) -> None:
        """Test add operation with specific files."""
        with (
            patch(
                "kbot_installer.core.versioner.pygit_versioner.pygit2.Repository"
            ) as mock_repo_class,
            patch("pathlib.Path.exists", return_value=True),
        ):
            mock_repo = MagicMock()
            mock_repo_class.return_value = mock_repo
            mock_index = MagicMock()
            mock_repo.index = mock_index

            await versioner.add("/path/to/repo", ["file1.txt", "file2.txt"])

            mock_index.add.assert_any_call("file1.txt")
            mock_index.add.assert_any_call("file2.txt")
            mock_index.write.assert_called_once()

    @pytest.mark.asyncio
    async def test_add_git_error(self, versioner) -> None:
        """Test add operation with git error."""
        with (
            patch(
                "kbot_installer.core.versioner.pygit_versioner.pygit2.Repository"
            ) as mock_repo_class,
            patch("pathlib.Path.exists", return_value=True),
        ):
            mock_repo = MagicMock()
            mock_repo_class.return_value = mock_repo
            mock_index = MagicMock()
            mock_repo.index = mock_index
            mock_index.add.side_effect = pygit2.GitError("Git error")

            with pytest.raises(
                VersionerError, match="Failed to add files to repository"
            ):
                await versioner.add("/path/to/repo", ["file1.txt"])

    @pytest.mark.asyncio
    async def test_pull_no_origin_remote(self, versioner) -> None:
        """Test pull when no origin remote exists."""
        with (
            patch(
                "kbot_installer.core.versioner.pygit_versioner.pygit2.Repository"
            ) as mock_repo_class,
            patch("pathlib.Path.exists", return_value=True),
        ):
            mock_repo = MagicMock()
            mock_repo_class.return_value = mock_repo
            mock_repo.remotes = {}  # No origin remote

            with pytest.raises(
                VersionerError, match="No 'origin' remote found in repository"
            ):
                await versioner.pull("/path/to/repo", "main")

    @pytest.mark.asyncio
    async def test_pull_remote_branch_not_found(self, versioner) -> None:
        """Test pull when remote branch not found."""
        with (
            patch(
                "kbot_installer.core.versioner.pygit_versioner.pygit2.Repository"
            ) as mock_repo_class,
            patch("pathlib.Path.exists", return_value=True),
        ):
            mock_repo = MagicMock()
            mock_repo_class.return_value = mock_repo
            mock_remote = MagicMock()
            mock_repo.remotes = {"origin": mock_remote}
            mock_repo.lookup_reference.side_effect = KeyError("Branch not found")

            with pytest.raises(
                VersionerError, match="Remote branch 'origin/main' not found"
            ):
                await versioner.pull("/path/to/repo", "main")

    @pytest.mark.asyncio
    async def test_pull_no_current_branch(self, versioner) -> None:
        """Test pull when no current branch exists."""
        with (
            patch(
                "kbot_installer.core.versioner.pygit_versioner.pygit2.Repository"
            ) as mock_repo_class,
            patch("pathlib.Path.exists", return_value=True),
        ):
            mock_repo = MagicMock()
            mock_repo_class.return_value = mock_repo
            mock_remote = MagicMock()
            mock_repo.remotes = {"origin": mock_remote}
            mock_remote_ref = MagicMock()
            mock_repo.lookup_reference.return_value = mock_remote_ref
            # Mock head.shorthand to raise GitError when accessed
            mock_repo.head = MagicMock()
            # Use side_effect on the property itself
            type(mock_repo.head).shorthand = PropertyMock(
                side_effect=pygit2.GitError("No current branch")
            )

            with pytest.raises(VersionerError, match="No current branch found"):
                await versioner.pull("/path/to/repo", "main")

    @pytest.mark.asyncio
    async def test_pull_merge_failure(self, versioner) -> None:
        """Test pull when merge fails."""
        with (
            patch(
                "kbot_installer.core.versioner.pygit_versioner.pygit2.Repository"
            ) as mock_repo_class,
            patch("pathlib.Path.exists", return_value=True),
        ):
            mock_repo = MagicMock()
            mock_repo_class.return_value = mock_repo
            mock_remote = MagicMock()
            mock_repo.remotes = {"origin": mock_remote}
            mock_remote_ref = MagicMock()
            mock_repo.lookup_reference.return_value = mock_remote_ref
            mock_repo.head.shorthand = "main"
            mock_repo.merge.side_effect = pygit2.GitError("Merge failed")

            with pytest.raises(VersionerError, match="Failed to merge remote changes"):
                await versioner.pull("/path/to/repo", "main")

    @pytest.mark.asyncio
    async def test_pull_git_error(self, versioner) -> None:
        """Test pull with general git error."""
        with (
            patch(
                "kbot_installer.core.versioner.pygit_versioner.pygit2.Repository"
            ) as mock_repo_class,
            patch("pathlib.Path.exists", return_value=True),
        ):
            mock_repo = MagicMock()
            mock_repo_class.return_value = mock_repo
            mock_remote = MagicMock()
            mock_repo.remotes = {"origin": mock_remote}
            mock_remote.fetch.side_effect = pygit2.GitError("Fetch failed")

            with pytest.raises(
                VersionerError, match="Failed to pull from remote repository"
            ):
                await versioner.pull("/path/to/repo", "main")

    @pytest.mark.asyncio
    async def test_commit_no_staged_changes(self, versioner) -> None:
        """Test commit when no staged changes exist."""
        with (
            patch(
                "kbot_installer.core.versioner.pygit_versioner.pygit2.Repository"
            ) as mock_repo_class,
            patch("pathlib.Path.exists", return_value=True),
        ):
            mock_repo = MagicMock()
            mock_repo_class.return_value = mock_repo
            mock_index = MagicMock()
            mock_repo.index = mock_index

            # Mock HEAD exists and trees are the same (no changes)
            mock_head = MagicMock()
            mock_head.target = "some_commit_hash"
            mock_repo.head = mock_head
            mock_head.peel.return_value.tree = "same_tree_id"
            mock_index.write_tree.return_value = "same_tree_id"

            # Should return without error when no changes to commit
            await versioner.commit("/path/to/repo", "Test commit")

    @pytest.mark.asyncio
    async def test_commit_initial_commit(self, versioner) -> None:
        """Test commit for initial commit (no HEAD)."""
        with (
            patch(
                "kbot_installer.core.versioner.pygit_versioner.pygit2.Repository"
            ) as mock_repo_class,
            patch("pathlib.Path.exists", return_value=True),
        ):
            mock_repo = MagicMock()
            mock_repo_class.return_value = mock_repo
            mock_index = MagicMock()
            mock_repo.index = mock_index
            mock_index.__bool__ = MagicMock(return_value=True)  # Has staged changes
            mock_repo.head.target = None  # No HEAD
            mock_repo.create_commit = MagicMock()

            await versioner.commit("/path/to/repo", "Initial commit")

            mock_repo.create_commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_commit_git_error(self, versioner) -> None:
        """Test commit with git error."""
        with (
            patch(
                "kbot_installer.core.versioner.pygit_versioner.pygit2.Repository"
            ) as mock_repo_class,
            patch("pathlib.Path.exists", return_value=True),
        ):
            mock_repo = MagicMock()
            mock_repo_class.return_value = mock_repo
            mock_index = MagicMock()
            mock_repo.index = mock_index
            mock_index.__bool__ = MagicMock(return_value=True)
            mock_repo.head.target = "commit_hash"
            mock_repo.create_commit.side_effect = pygit2.GitError("Commit failed")

            with pytest.raises(VersionerError, match="Failed to commit changes"):
                await versioner.commit("/path/to/repo", "Test commit")

    @pytest.mark.asyncio
    async def test_commit_git_error_no_head(self, versioner) -> None:
        """Test commit with git error when no HEAD exists."""
        with (
            patch(
                "kbot_installer.core.versioner.pygit_versioner.pygit2.Repository"
            ) as mock_repo_class,
            patch("pathlib.Path.exists", return_value=True),
        ):
            mock_repo = MagicMock()
            mock_repo_class.return_value = mock_repo
            mock_index = MagicMock()
            mock_repo.index = mock_index
            mock_index.__bool__.return_value = True  # Has staged changes
            mock_repo.head.target = None  # No HEAD
            mock_repo.create_commit.side_effect = pygit2.GitError("Commit failed")

            with pytest.raises(VersionerError, match="Failed to commit changes"):
                await versioner.commit("/path/to/repo", "Test commit")

    @pytest.mark.asyncio
    async def test_push_no_origin_remote(self, versioner) -> None:
        """Test push when no origin remote exists."""
        with (
            patch(
                "kbot_installer.core.versioner.pygit_versioner.pygit2.Repository"
            ) as mock_repo_class,
            patch("pathlib.Path.exists", return_value=True),
        ):
            mock_repo = MagicMock()
            mock_repo_class.return_value = mock_repo
            mock_repo.remotes = {}  # No origin remote

            with pytest.raises(
                VersionerError, match="No 'origin' remote found in repository"
            ):
                await versioner.push("/path/to/repo", "main")

    @pytest.mark.asyncio
    async def test_push_no_current_branch(self, versioner) -> None:
        """Test push when no current branch exists."""
        with (
            patch(
                "kbot_installer.core.versioner.pygit_versioner.pygit2.Repository"
            ) as mock_repo_class,
            patch("pathlib.Path.exists", return_value=True),
        ):
            mock_repo = MagicMock()
            mock_repo_class.return_value = mock_repo
            mock_remote = MagicMock()
            mock_repo.remotes = {"origin": mock_remote}
            # Mock head.shorthand to raise GitError when accessed
            mock_repo.head = MagicMock()
            # Use side_effect on the property itself
            type(mock_repo.head).shorthand = PropertyMock(
                side_effect=pygit2.GitError("No current branch")
            )

            with pytest.raises(VersionerError, match="No current branch found"):
                await versioner.push("/path/to/repo", "main")

    @pytest.mark.asyncio
    async def test_push_git_error(self, versioner) -> None:
        """Test push with git error."""
        with (
            patch(
                "kbot_installer.core.versioner.pygit_versioner.pygit2.Repository"
            ) as mock_repo_class,
            patch("pathlib.Path.exists", return_value=True),
        ):
            mock_repo = MagicMock()
            mock_repo_class.return_value = mock_repo
            mock_remote = MagicMock()
            mock_repo.remotes = {"origin": mock_remote}
            mock_repo.head.shorthand = "main"
            mock_remote.push.side_effect = pygit2.GitError("Push failed")

            with pytest.raises(
                VersionerError, match="Failed to push to remote repository"
            ):
                await versioner.push("/path/to/repo", "main")

    @pytest.mark.asyncio
    async def test_clone_with_auth(self, versioner_with_auth) -> None:
        """Test clone with authentication."""
        with (
            patch(
                "kbot_installer.core.versioner.pygit_versioner.pygit2.clone_repository"
            ) as mock_clone,
            patch("pathlib.Path.exists", return_value=False),
            patch("pathlib.Path.mkdir") as mock_mkdir,
        ):
            await versioner_with_auth.clone(
                "https://github.com/test/repo", "/tmp/test_target"
            )

            mock_clone.assert_called_once()
            mock_mkdir.assert_called_once()

    @pytest.mark.asyncio
    async def test_clone_target_exists_cleanup_fails(self, versioner) -> None:
        """Test clone when target exists and cleanup fails."""
        with (
            patch(
                "kbot_installer.core.versioner.pygit_versioner.pygit2.clone_repository"
            ),
            patch("pathlib.Path.exists") as mock_exists,
            patch("shutil.rmtree") as mock_rmtree,
            patch("pathlib.Path.mkdir"),
        ):
            mock_exists.return_value = True
            mock_rmtree.side_effect = OSError("Cleanup failed")

            # The OSError from rmtree is not caught by the try/except in clone method
            with pytest.raises(OSError, match="Cleanup failed"):
                await versioner.clone("https://github.com/test/repo", "/path/to/target")

    @pytest.mark.asyncio
    async def test_clone_target_still_exists_after_cleanup(self, versioner) -> None:
        """Test clone when target still exists after cleanup."""
        with (
            patch(
                "kbot_installer.core.versioner.pygit_versioner.pygit2.clone_repository"
            ),
            patch("pathlib.Path.exists") as mock_exists,
            patch("shutil.rmtree") as mock_rmtree,
            patch("pathlib.Path.mkdir"),
        ):
            # Target exists, cleanup succeeds, but target still exists after cleanup
            mock_exists.side_effect = [True, True]  # Exists before and after cleanup
            mock_rmtree.return_value = None  # Cleanup succeeds

            with pytest.raises(
                VersionerError, match="Target directory still exists after cleanup"
            ):
                await versioner.clone("https://github.com/test/repo", "/tmp/test")

    @pytest.mark.asyncio
    async def test_clone_git_error(self, versioner) -> None:
        """Test clone with git error."""
        with (
            patch(
                "kbot_installer.core.versioner.pygit_versioner.pygit2.clone_repository"
            ) as mock_clone,
            patch("pathlib.Path.exists", return_value=False),
            patch("pathlib.Path.mkdir"),
        ):
            mock_clone.side_effect = pygit2.GitError("Clone failed")

            with pytest.raises(VersionerError, match="Failed to clone repository from"):
                await versioner.clone("https://github.com/test/repo", "/path/to/target")

    @pytest.mark.asyncio
    async def test_checkout_branch_creation_failure(self, versioner) -> None:
        """Test checkout when branch creation fails."""
        with (
            patch(
                "kbot_installer.core.versioner.pygit_versioner.pygit2.Repository"
            ) as mock_repo_class,
            patch("pathlib.Path.exists", return_value=True),
        ):
            mock_repo = MagicMock()
            mock_repo_class.return_value = mock_repo
            mock_repo.references = ["refs/remotes/origin/feature-branch"]
            mock_remote_ref = MagicMock()
            mock_remote_ref.peel.return_value = "commit_hash"
            mock_repo.lookup_reference.return_value = mock_remote_ref
            mock_repo.create_branch.side_effect = pygit2.GitError(
                "Branch creation failed"
            )

            with pytest.raises(
                VersionerError, match="Failed to create and checkout branch"
            ):
                await versioner.checkout("/path/to/repo", "feature-branch")

    @pytest.mark.asyncio
    async def test_checkout_local_branch_failure(self, versioner) -> None:
        """Test checkout when local branch checkout fails."""
        with (
            patch(
                "kbot_installer.core.versioner.pygit_versioner.pygit2.Repository"
            ) as mock_repo_class,
            patch("pathlib.Path.exists", return_value=True),
        ):
            mock_repo = MagicMock()
            mock_repo_class.return_value = mock_repo
            mock_repo.references = ["refs/heads/main"]
            mock_repo.checkout.side_effect = pygit2.GitError("Checkout failed")

            with pytest.raises(VersionerError, match="Failed to checkout local branch"):
                await versioner.checkout("/path/to/repo", "main")

    @pytest.mark.asyncio
    async def test_checkout_git_error(self, versioner) -> None:
        """Test checkout with general git error."""
        with (
            patch(
                "kbot_installer.core.versioner.pygit_versioner.pygit2.Repository"
            ) as mock_repo_class,
            patch("pathlib.Path.exists", return_value=True),
        ):
            mock_repo = MagicMock()
            mock_repo_class.return_value = mock_repo
            mock_repo.references = []
            mock_repo.lookup_reference.side_effect = pygit2.GitError("Git error")

            with pytest.raises(VersionerError, match="Version 'main' not found"):
                await versioner.checkout("/path/to/repo", "main")

    @pytest.mark.asyncio
    async def test_checkout_existing_local_branch(self, versioner) -> None:
        """Test checkout of existing local branch."""
        with (
            patch(
                "kbot_installer.core.versioner.pygit_versioner.pygit2.Repository"
            ) as mock_repo_class,
            patch("pathlib.Path.exists", return_value=True),
        ):
            mock_repo = MagicMock()
            mock_repo_class.return_value = mock_repo
            mock_repo.references = ["refs/heads/main", "refs/remotes/origin/main"]
            mock_remote_ref = MagicMock()
            mock_remote_ref.peel.return_value = "commit_hash"
            mock_repo.lookup_reference.return_value = mock_remote_ref

            await versioner.checkout("/path/to/repo", "main")

            # Should call checkout on the local branch
            mock_repo.checkout.assert_called_once_with("refs/heads/main")

    @pytest.mark.asyncio
    async def test_select_branch_with_empty_list(self, versioner) -> None:
        """Test select_branch with empty branch list."""
        with (
            patch(
                "kbot_installer.core.versioner.pygit_versioner.pygit2.Repository"
            ) as mock_repo_class,
            patch("pathlib.Path.exists", return_value=True),
        ):
            mock_repo = MagicMock()
            mock_repo_class.return_value = mock_repo
            mock_repo.references = []

            result = await versioner.select_branch("/path/to/repo", [])

            assert result is None

    @pytest.mark.asyncio
    async def test_select_branch_repository_error(self, versioner) -> None:
        """Test select_branch with repository error."""
        with (
            patch(
                "kbot_installer.core.versioner.pygit_versioner.pygit2.Repository"
            ) as mock_repo_class,
            patch("pathlib.Path.exists", return_value=True),
        ):
            mock_repo_class.side_effect = pygit2.GitError("Repository error")

            with pytest.raises(VersionerError, match="Failed to open repository"):
                await versioner.select_branch("/path/to/repo", ["main"])

    def test_check_remote_repository_exists_with_auth(
        self, versioner_with_auth
    ) -> None:
        """Test check_remote_repository_exists with authentication."""
        with patch.object(
            versioner_with_auth, "_check_remote_repository_exists_with_fetch"
        ) as mock_check:
            mock_check.return_value = True

            result = versioner_with_auth.check_remote_repository_exists(
                "https://github.com/test/repo"
            )

            assert result is True
            mock_check.assert_called_once_with("https://github.com/test/repo")

    def test_check_remote_repository_exists_exception(self, versioner) -> None:
        """Test check_remote_repository_exists handles exceptions."""
        with patch.object(
            versioner, "_check_remote_repository_exists_with_fetch"
        ) as mock_check:
            mock_check.side_effect = Exception("Unexpected error")

            result = versioner.check_remote_repository_exists(
                "https://github.com/test/repo"
            )

            assert result is False

    def test_check_remote_repository_exists_with_fetch_temp_dir_creation_failure(
        self, versioner
    ) -> None:
        """Test _check_remote_repository_exists_with_fetch when temp dir creation fails."""
        with patch("tempfile.mkdtemp") as mock_mkdtemp:
            mock_mkdtemp.side_effect = OSError("Temp dir creation failed")

            result = versioner._check_remote_repository_exists_with_fetch(
                "https://github.com/test/repo"
            )

            assert result is False

    def test_check_remote_repository_exists_with_fetch_cleanup_error(
        self, versioner
    ) -> None:
        """Test _check_remote_repository_exists_with_fetch with cleanup error."""
        with (
            patch("tempfile.mkdtemp") as mock_mkdtemp,
            patch("pygit2.init_repository"),
            patch("pygit2.Repository") as mock_repo_class,
            patch("shutil.rmtree") as mock_rmtree,
            patch("pathlib.Path.exists", return_value=True),
        ):
            mock_mkdtemp.return_value = "/tmp/test"
            mock_repo = MagicMock()
            mock_repo_class.return_value = mock_repo
            mock_remote = MagicMock()
            mock_repo.remotes.create_anonymous.return_value = mock_remote
            mock_remote.ls_remotes.side_effect = pygit2.GitError("Git error")
            # rmtree with ignore_errors=True doesn't raise exceptions, so we don't mock side_effect

            result = versioner._check_remote_repository_exists_with_fetch(
                "https://github.com/test/repo"
            )

            assert result is False
            mock_rmtree.assert_called_once()

    @pytest.mark.asyncio
    async def test_stash_no_changes(self, versioner) -> None:
        """Test stash when there are no changes to stash."""
        with (
            patch("pathlib.Path.exists", return_value=True),
            patch(
                "kbot_installer.core.versioner.pygit_versioner.pygit2.Repository"
            ) as mock_repo_class,
        ):
            mock_repo = MagicMock()
            mock_repo.status.return_value = {}  # No changes
            mock_repo_class.return_value = mock_repo

            # Should return False and not call stash
            result = await versioner.stash("/path/to/repo", "Test message")

            assert result is False
            mock_repo.status.assert_called_once()
            mock_repo.stash.assert_not_called()

    @pytest.mark.asyncio
    async def test_stash_with_changes(self, versioner) -> None:
        """Test stash when there are changes to stash."""
        with (
            patch("pathlib.Path.exists", return_value=True),
            patch(
                "kbot_installer.core.versioner.pygit_versioner.pygit2.Repository"
            ) as mock_repo_class,
        ):
            mock_repo = MagicMock()
            mock_repo.status.return_value = {"file1.txt": 1}  # Has changes
            mock_repo_class.return_value = mock_repo

            result = await versioner.stash("/path/to/repo", "Test message")

            assert result is True
            mock_repo.status.assert_called_once()
            mock_repo.stash.assert_called_once()
            # Check that Signature was created with correct parameters
            call_args = mock_repo.stash.call_args
            assert call_args[0][1] == "Test message"  # message parameter

    @pytest.mark.asyncio
    async def test_stash_with_default_message(self, versioner) -> None:
        """Test stash with default message when none provided."""
        with (
            patch("pathlib.Path.exists", return_value=True),
            patch(
                "kbot_installer.core.versioner.pygit_versioner.pygit2.Repository"
            ) as mock_repo_class,
        ):
            mock_repo = MagicMock()
            mock_repo.status.return_value = {"file1.txt": 1}  # Has changes
            mock_repo_class.return_value = mock_repo

            result = await versioner.stash("/path/to/repo")

            assert result is True
            mock_repo.stash.assert_called_once()
            call_args = mock_repo.stash.call_args
            assert call_args[0][1] == "Auto-stash by versioner"

    @pytest.mark.asyncio
    async def test_stash_git_error(self, versioner) -> None:
        """Test stash handles GitError."""
        with (
            patch("pathlib.Path.exists", return_value=True),
            patch(
                "kbot_installer.core.versioner.pygit_versioner.pygit2.Repository"
            ) as mock_repo_class,
        ):
            mock_repo = MagicMock()
            mock_repo.status.return_value = {"file1.txt": 1}  # Has changes
            mock_repo.stash.side_effect = pygit2.GitError("Stash failed")
            mock_repo_class.return_value = mock_repo

            with pytest.raises(VersionerError, match="Failed to stash changes"):
                await versioner.stash("/path/to/repo", "Test message")

    @pytest.mark.asyncio
    async def test_safe_pull_no_changes(self, versioner) -> None:
        """Test safe_pull when there are no local changes."""
        with (
            patch("pathlib.Path.exists", return_value=True),
            patch(
                "kbot_installer.core.versioner.pygit_versioner.pygit2.Repository"
            ) as mock_repo_class,
            patch.object(versioner, "pull") as mock_pull,
            patch.object(versioner, "stash") as mock_stash,
        ):
            mock_repo = MagicMock()
            mock_repo_class.return_value = mock_repo
            mock_stash.return_value = False  # No stash created

            await versioner.safe_pull("/path/to/repo", "main")

            mock_stash.assert_called_once_with("/path/to/repo", "Safe pull stash")
            mock_pull.assert_called_once_with("/path/to/repo", "main")

    @pytest.mark.asyncio
    async def test_safe_pull_with_changes(self, versioner) -> None:
        """Test safe_pull when there are local changes."""
        with (
            patch("pathlib.Path.exists", return_value=True),
            patch(
                "kbot_installer.core.versioner.pygit_versioner.pygit2.Repository"
            ) as mock_repo_class,
            patch.object(versioner, "pull") as mock_pull,
            patch.object(versioner, "stash") as mock_stash,
            patch.object(versioner, "_apply_stash") as mock_apply_stash,
        ):
            mock_repo = MagicMock()
            mock_repo_class.return_value = mock_repo
            mock_stash.return_value = True  # Stash was created

            await versioner.safe_pull("/path/to/repo", "main")

            mock_stash.assert_called_once_with("/path/to/repo", "Safe pull stash")
            mock_pull.assert_called_once_with("/path/to/repo", "main")
            mock_apply_stash.assert_called_once_with(mock_repo)

    @pytest.mark.asyncio
    async def test_safe_pull_pull_failure_with_stash_restore(self, versioner) -> None:
        """Test safe_pull when pull fails and stash is restored."""
        with (
            patch("pathlib.Path.exists", return_value=True),
            patch(
                "kbot_installer.core.versioner.pygit_versioner.pygit2.Repository"
            ) as mock_repo_class,
            patch.object(versioner, "pull") as mock_pull,
            patch.object(versioner, "stash") as mock_stash,
            patch.object(versioner, "_apply_stash") as mock_apply_stash,
        ):
            mock_repo = MagicMock()
            mock_repo_class.return_value = mock_repo
            mock_stash.return_value = True  # Stash was created
            mock_pull.side_effect = VersionerError("Pull failed")

            with pytest.raises(VersionerError, match="Pull failed"):
                await versioner.safe_pull("/path/to/repo", "main")

            mock_stash.assert_called_once_with("/path/to/repo", "Safe pull stash")
            mock_pull.assert_called_once_with("/path/to/repo", "main")
            # Should try to restore stash after pull failure
            mock_apply_stash.assert_called_once_with(mock_repo)

    @pytest.mark.asyncio
    async def test_apply_stash_no_stashes(self, versioner) -> None:
        """Test _apply_stash when there are no stashes."""
        mock_repo = MagicMock()
        mock_repo.references = []  # No stash references

        # Should not raise an error and should not call stash_apply
        await versioner._apply_stash(mock_repo)

        mock_repo.stash_apply.assert_not_called()

    @pytest.mark.asyncio
    async def test_apply_stash_with_stashes(self, versioner) -> None:
        """Test _apply_stash when there are stashes."""
        mock_repo = MagicMock()
        mock_repo.references = ["refs/stash", "refs/heads/main"]  # Has stash

        await versioner._apply_stash(mock_repo)

        mock_repo.stash_apply.assert_called_once_with(0)

    @pytest.mark.asyncio
    async def test_apply_stash_git_error(self, versioner) -> None:
        """Test _apply_stash handles GitError."""
        mock_repo = MagicMock()
        mock_repo.references = ["refs/stash"]
        mock_repo.stash_apply.side_effect = pygit2.GitError("Apply failed")

        with pytest.raises(VersionerError, match="Failed to apply stash"):
            await versioner._apply_stash(mock_repo)
