"""Tests for Dulwich versioner module."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from dulwich.errors import GitProtocolError, NotGitRepository
from dulwich.porcelain import Error as DulwichPorcelainError

from auth.base import HttpAuthBase
from git.versioner.base import VersionerBase, VersionerError
from git.versioner.dulwich_versioner import DulwichVersioner
from utils.utils_for_unit_tests import compare


@pytest.fixture
def bare_versioner() -> DulwichVersioner:
    """Create a DulwichVersioner without authentication."""
    return DulwichVersioner()


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
        mock_auth.git_cli_environment.return_value = None
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
        mock_auth.git_cli_environment.return_value = None
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
                "git.versioner.dulwich_versioner.Repo",
                side_effect=NotGitRepository("not a repo"),
            ),
        ):
            with pytest.raises(VersionerError, match="Failed to open repository"):
                versioner._get_repository("/test/path")

    def test_clone_success(self, versioner: DulwichVersioner) -> None:
        """Test successful clone operation."""
        with patch("git.versioner.dulwich_versioner.porcelain.clone") as mock_clone:
            versioner.clone("https://github.com/test/repo.git", "/tmp/test")
            mock_clone.assert_called_once_with(
                "https://github.com/test/repo.git",
                "/tmp/test",
            )

    def test_clone_with_branch_and_depth(self, versioner: DulwichVersioner) -> None:
        """Test shallow clone of a specific branch."""
        with patch("git.versioner.dulwich_versioner.porcelain.clone") as mock_clone:
            versioner.clone(
                "https://github.com/test/repo.git",
                "/tmp/test",
                branch="main",
                depth=1,
            )
            mock_clone.assert_called_once_with(
                "https://github.com/test/repo.git",
                "/tmp/test",
                branch="main",
                depth=1,
            )

    def test_list_remote_branches(self, versioner: DulwichVersioner) -> None:
        """Test listing remote branch names."""
        with patch(
            "git.versioner.dulwich_versioner.porcelain.ls_remote",
            return_value={
                b"refs/heads/main": b"sha1",
                b"refs/heads/master": b"sha2",
                b"refs/tags/v1": b"sha3",
            },
        ):
            assert versioner.list_remote_branches(
                "https://github.com/test/repo.git"
            ) == ["main", "master"]

    def test_clone_with_auth(self, mock_auth: MagicMock) -> None:
        """Test clone passes authentication kwargs."""
        versioner = DulwichVersioner(auth=mock_auth)
        with patch("git.versioner.dulwich_versioner.porcelain.clone") as mock_clone:
            versioner.clone("https://github.com/test/repo.git", "/tmp/test")
            mock_clone.assert_called_once_with(
                "https://github.com/test/repo.git",
                "/tmp/test",
                username="user",
                password="pass",
            )

    @patch.dict("os.environ", {"SSH_AUTH_SOCK": "/tmp/ssh-agent"}, clear=True)
    def test_clone_with_ssh_auth_uses_git_cli(self) -> None:
        """Test SSH authentication clones through the git CLI."""
        from auth.factory import create_auth

        auth = create_auth("ssh", username="git", use_agent=True)
        versioner = DulwichVersioner(auth=auth)
        git_env = auth.git_cli_environment()
        with (
            patch.object(versioner, "_clone_with_git_cli") as mock_git_clone,
            patch("git.versioner.dulwich_versioner.porcelain.clone") as mock_dulwich_clone,
        ):
            versioner.clone(
                "git@github.com:test/repo.git",
                "/tmp/test",
                branch="main",
                depth=1,
            )
            mock_git_clone.assert_called_once_with(
                "git@github.com:test/repo.git",
                Path("/tmp/test"),
                git_env,
                branch="main",
                depth=1,
            )
            mock_dulwich_clone.assert_not_called()

    @patch.dict("os.environ", {"SSH_AUTH_SOCK": "/tmp/ssh-agent"}, clear=True)
    def test_list_remote_branches_with_ssh_auth_uses_git_cli(self) -> None:
        """Test SSH authentication lists branches through the git CLI."""
        from auth.factory import create_auth

        auth = create_auth("ssh", username="git", use_agent=True)
        versioner = DulwichVersioner(auth=auth)
        git_env = auth.git_cli_environment()
        with (
            patch.object(
                versioner,
                "_list_remote_branches_with_git_cli",
                return_value=["main"],
            ) as mock_git_ls,
            patch("git.versioner.dulwich_versioner.porcelain.ls_remote") as mock_dulwich_ls,
        ):
            assert versioner.list_remote_branches(
                "git@github.com:test/repo.git"
            ) == ["main"]
            mock_git_ls.assert_called_once_with(
                "git@github.com:test/repo.git",
                git_env,
            )
            mock_dulwich_ls.assert_not_called()

    def test_clone_failure(self, versioner: DulwichVersioner) -> None:
        """Test clone wraps Dulwich errors."""
        with patch(
            "git.versioner.dulwich_versioner.porcelain.clone",
            side_effect=DulwichPorcelainError("clone failed"),
        ):
            with pytest.raises(VersionerError, match="Failed to clone repository"):
                versioner.clone("https://github.com/test/repo.git", "/tmp/test")

    def test_add_all_files(self, versioner: DulwichVersioner) -> None:
        """Test add with all files."""
        mock_repo = MagicMock()
        with patch.object(versioner, "_get_repository", return_value=mock_repo):
            with patch("git.versioner.dulwich_versioner.porcelain.add") as mock_add:
                versioner.add("/test/path", None)
                mock_add.assert_called_once_with(mock_repo, paths=".")

    def test_add_specific_files(self, versioner: DulwichVersioner) -> None:
        """Test add with specific files."""
        mock_repo = MagicMock()
        with patch.object(versioner, "_get_repository", return_value=mock_repo):
            with patch("git.versioner.dulwich_versioner.porcelain.add") as mock_add:
                versioner.add("/test/path", ["file1.txt", "file2.txt"])
                mock_add.assert_called_once_with(
                    mock_repo, paths=["file1.txt", "file2.txt"]
                )

    def test_commit_skips_when_no_staged_changes(self, versioner: DulwichVersioner) -> None:
        """Test commit returns early when there are no staged changes."""
        mock_repo = MagicMock()
        with patch.object(versioner, "_get_repository", return_value=mock_repo):
            with patch.object(versioner, "_has_staged_changes", return_value=False):
                with patch("git.versioner.dulwich_versioner.porcelain.commit") as mock_commit:
                    versioner.commit("/test/path", "message")
                    mock_commit.assert_not_called()

    def test_commit_success(self, versioner: DulwichVersioner) -> None:
        """Test successful commit."""
        mock_repo = MagicMock()
        with patch.object(versioner, "_get_repository", return_value=mock_repo):
            with patch.object(versioner, "_has_staged_changes", return_value=True):
                with patch("git.versioner.dulwich_versioner.porcelain.commit") as mock_commit:
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
                with patch("git.versioner.dulwich_versioner.porcelain.stash_push"):
                    assert versioner.stash("/test/path", "message") is True

    def test_remote_exists_true(self, versioner: DulwichVersioner) -> None:
        """Test remote_exists returns True on success."""
        with patch("git.versioner.dulwich_versioner.porcelain.ls_remote"):
            assert versioner.remote_exists("https://example.com/repo.git")

    def test_remote_exists_false(self, versioner: DulwichVersioner) -> None:
        """Test remote_exists returns False on failure."""
        with patch(
            "git.versioner.dulwich_versioner.porcelain.ls_remote",
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
        from git.versioner.factory import create_versioner

        versioner = create_versioner("dulwich")
        assert isinstance(versioner, DulwichVersioner)


@pytest.mark.parametrize(
    "params, expected",
    [
        (
            {
                "returncode": 0,
                "stdout": "abc123\trefs/heads/main\ndef456\trefs/heads/dev\n",
                "stderr": "",
            },
            ["dev", "main"],
        ),
        (
            {
                "returncode": 0,
                "stdout": "abc123\trefs/heads/main\n\n",
                "stderr": "",
            },
            ["main"],
        ),
    ],
)
def test_list_remote_branches_with_git_cli_valid_parses_branches(
    bare_versioner: DulwichVersioner,
    params: dict,
    expected: list[str],
) -> None:
    mock_result = MagicMock()
    mock_result.returncode = params["returncode"]
    mock_result.stdout = params["stdout"]
    mock_result.stderr = params["stderr"]
    with patch(
        "git.versioner.dulwich_versioner.subprocess.run",
        return_value=mock_result,
    ):
        branches = bare_versioner._list_remote_branches_with_git_cli(
            "git@github.com:test/repo.git",
            {"GIT_SSH_COMMAND": "ssh"},
        )
    assert compare("eq", branches, expected)


@pytest.mark.parametrize(
    "params, expected",
    [
        ({"side_effect": FileNotFoundError("git")}, VersionerError),
        (
            {
                "returncode": 1,
                "stdout": "",
                "stderr": "permission denied",
            },
            VersionerError,
        ),
    ],
)
def test_list_remote_branches_with_git_cli_invalid_raises(
    bare_versioner: DulwichVersioner,
    params: dict,
    expected: type[BaseException],
) -> None:
    if "side_effect" in params:
        with (
            patch(
                "git.versioner.dulwich_versioner.subprocess.run",
                side_effect=params["side_effect"],
            ),
            pytest.raises(expected, match="git executable not found"),
        ):
            bare_versioner._list_remote_branches_with_git_cli(
                "git@github.com:test/repo.git",
                {},
            )
        return

    mock_result = MagicMock()
    mock_result.returncode = params["returncode"]
    mock_result.stdout = params["stdout"]
    mock_result.stderr = params["stderr"]
    with (
        patch(
            "git.versioner.dulwich_versioner.subprocess.run",
            return_value=mock_result,
        ),
        pytest.raises(expected, match="Failed to list remote branches"),
    ):
        bare_versioner._list_remote_branches_with_git_cli(
            "git@github.com:test/repo.git",
            {},
        )


@pytest.mark.parametrize(
    "params, expected",
    [
        (
            {
                "returncode": 0,
                "stdout": "",
                "stderr": "",
                "branch": None,
                "depth": None,
            },
            None,
        ),
        (
            {
                "returncode": 0,
                "stdout": "",
                "stderr": "",
                "branch": "main",
                "depth": 1,
            },
            None,
        ),
    ],
)
def test_clone_with_git_cli_valid_succeeds(
    bare_versioner: DulwichVersioner,
    params: dict,
    expected: None,
) -> None:
    _ = expected
    mock_result = MagicMock()
    mock_result.returncode = params["returncode"]
    mock_result.stdout = params["stdout"]
    mock_result.stderr = params["stderr"]
    with patch(
        "git.versioner.dulwich_versioner.subprocess.run",
        return_value=mock_result,
    ) as mock_run:
        bare_versioner._clone_with_git_cli(
            "git@github.com:test/repo.git",
            Path("/tmp/test"),
            {"GIT_SSH_COMMAND": "ssh"},
            branch=params["branch"],
            depth=params["depth"],
        )
    cmd = mock_run.call_args.args[0]
    assert compare("eq", cmd[0:2], ["git", "clone"])
    if params["branch"] is not None:
        assert compare("in", "--branch", cmd)
    if params["depth"] is not None:
        assert compare("in", "--depth", cmd)


@pytest.mark.parametrize(
    "params, expected",
    [
        ({"side_effect": FileNotFoundError("git")}, VersionerError),
        (
            {
                "returncode": 128,
                "stdout": "",
                "stderr": "fatal: repository not found",
            },
            VersionerError,
        ),
    ],
)
def test_clone_with_git_cli_invalid_raises(
    bare_versioner: DulwichVersioner,
    params: dict,
    expected: type[BaseException],
) -> None:
    if "side_effect" in params:
        with (
            patch(
                "git.versioner.dulwich_versioner.subprocess.run",
                side_effect=params["side_effect"],
            ),
            pytest.raises(expected, match="git executable not found"),
        ):
            bare_versioner._clone_with_git_cli(
                "git@github.com:test/repo.git",
                Path("/tmp/test"),
                {},
            )
        return

    mock_result = MagicMock()
    mock_result.returncode = params["returncode"]
    mock_result.stdout = params["stdout"]
    mock_result.stderr = params["stderr"]
    with (
        patch(
            "git.versioner.dulwich_versioner.subprocess.run",
            return_value=mock_result,
        ),
        pytest.raises(expected, match="Failed to clone repository"),
    ):
        bare_versioner._clone_with_git_cli(
            "git@github.com:test/repo.git",
            Path("/tmp/test"),
            {},
        )


@pytest.mark.parametrize(
    "params, expected",
    [
        (
            {
                "staged": {"add": [], "delete": [], "modify": []},
                "unstaged": [],
                "untracked": [],
            },
            False,
        ),
        (
            {
                "staged": {"add": ["file.txt"], "delete": [], "modify": []},
                "unstaged": [],
                "untracked": [],
            },
            True,
        ),
        (
            {
                "staged": {"add": [], "delete": [], "modify": []},
                "unstaged": ["file.txt"],
                "untracked": [],
            },
            True,
        ),
        (
            {
                "staged": {"add": [], "delete": [], "modify": []},
                "unstaged": [],
                "untracked": ["file.txt"],
            },
            True,
        ),
    ],
)
def test_has_working_tree_changes_valid_detects_changes(
    params: dict,
    expected: bool,
) -> None:
    mock_status = MagicMock()
    mock_status.staged = params["staged"]
    mock_status.unstaged = params["unstaged"]
    mock_status.untracked = params["untracked"]
    mock_repo = MagicMock()
    with patch(
        "git.versioner.dulwich_versioner.porcelain.status",
        return_value=mock_status,
    ):
        result = DulwichVersioner._has_working_tree_changes(mock_repo)
    assert compare("eq", result, expected)


@pytest.mark.parametrize(
    "params, expected",
    [
        (
            {"staged": {"add": [], "delete": [], "modify": []}},
            False,
        ),
        (
            {"staged": {"add": [], "delete": ["file.txt"], "modify": []}},
            True,
        ),
        (
            {"staged": {"add": [], "delete": [], "modify": ["file.txt"]}},
            True,
        ),
    ],
)
def test_has_staged_changes_valid_detects_staged(
    params: dict,
    expected: bool,
) -> None:
    mock_status = MagicMock()
    mock_status.staged = params["staged"]
    mock_repo = MagicMock()
    with patch(
        "git.versioner.dulwich_versioner.porcelain.status",
        return_value=mock_status,
    ):
        result = DulwichVersioner._has_staged_changes(mock_repo)
    assert compare("eq", result, expected)


@pytest.mark.parametrize(
    "params, expected",
    [
        ({"branch_ref": b"refs/heads/main"}, "main"),
        ({"branch_ref": b"refs/heads/feature/x"}, "feature/x"),
    ],
)
def test_get_current_branch_name_valid_returns_branch(
    bare_versioner: DulwichVersioner,
    params: dict,
    expected: str,
) -> None:
    mock_repo = MagicMock()
    mock_repo.refs.follow.return_value = (b"HEAD", params["branch_ref"])
    assert compare(
        "eq",
        bare_versioner._get_current_branch_name(mock_repo),
        expected,
    )


@pytest.mark.parametrize(
    "params, expected",
    [
        ({"branch_ref": None}, VersionerError),
        ({"branch_ref": b"refs/remotes/origin/main"}, VersionerError),
    ],
)
def test_get_current_branch_name_invalid_raises(
    bare_versioner: DulwichVersioner,
    params: dict,
    expected: type[BaseException],
) -> None:
    mock_repo = MagicMock()
    mock_repo.refs.follow.return_value = (b"HEAD", params["branch_ref"])
    with pytest.raises(expected, match="No current branch found"):
        bare_versioner._get_current_branch_name(mock_repo)


def test_add_invalid_wraps_dulwich_error(bare_versioner: DulwichVersioner) -> None:
    with (
        patch.object(
            bare_versioner,
            "_get_repository",
            side_effect=NotGitRepository("not a repo"),
        ),
        pytest.raises(VersionerError, match="Failed to add files"),
    ):
        bare_versioner.add("/test/path", ["file.txt"])


def test_fetch_valid_fetches_origin(bare_versioner: DulwichVersioner) -> None:
    mock_repo = MagicMock()
    with (
        patch.object(bare_versioner, "_get_repository", return_value=mock_repo),
        patch("git.versioner.dulwich_versioner.porcelain.fetch") as mock_fetch,
    ):
        bare_versioner.fetch("/test/path")
    mock_fetch.assert_called_once_with(mock_repo, b"origin")


@pytest.mark.parametrize(
    "params, expected",
    [
        ({"error": KeyError("origin")}, VersionerError),
        ({"error": GitProtocolError("network")}, VersionerError),
        ({"error": RuntimeError("unexpected")}, VersionerError),
    ],
)
def test_fetch_invalid_raises(
    bare_versioner: DulwichVersioner,
    params: dict,
    expected: type[BaseException],
) -> None:
    mock_repo = MagicMock()
    with (
        patch.object(bare_versioner, "_get_repository", return_value=mock_repo),
        patch(
            "git.versioner.dulwich_versioner.porcelain.fetch",
            side_effect=params["error"],
        ),
        pytest.raises(expected),
    ):
        bare_versioner.fetch("/test/path")


def test_pull_valid_merges_remote_branch(bare_versioner: DulwichVersioner) -> None:
    mock_repo = MagicMock()
    mock_repo.get_refs.return_value = {b"refs/remotes/origin/main": b"sha1"}
    with (
        patch.object(bare_versioner, "_get_repository", return_value=mock_repo),
        patch.object(bare_versioner, "_get_current_branch_name", return_value="main"),
        patch("git.versioner.dulwich_versioner.porcelain.fetch"),
        patch("git.versioner.dulwich_versioner.porcelain.merge") as mock_merge,
    ):
        bare_versioner.pull("/test/path", "main")
    mock_merge.assert_called_once_with(mock_repo, "origin/main")


def test_pull_invalid_raises_when_remote_branch_missing(
    bare_versioner: DulwichVersioner,
) -> None:
    mock_repo = MagicMock()
    mock_repo.get_refs.return_value = {}
    with (
        patch.object(bare_versioner, "_get_repository", return_value=mock_repo),
        patch("git.versioner.dulwich_versioner.porcelain.fetch"),
        pytest.raises(VersionerError, match="Remote branch"),
    ):
        bare_versioner.pull("/test/path", "main")


def test_pull_invalid_raises_when_origin_missing(
    bare_versioner: DulwichVersioner,
) -> None:
    mock_repo = MagicMock()
    mock_repo.get_refs.return_value = {b"refs/remotes/origin/main": b"sha1"}
    with (
        patch.object(bare_versioner, "_get_repository", return_value=mock_repo),
        patch(
            "git.versioner.dulwich_versioner.porcelain.fetch",
            side_effect=KeyError("origin"),
        ),
        pytest.raises(VersionerError, match="No 'origin' remote found"),
    ):
        bare_versioner.pull("/test/path", "main")


@pytest.mark.parametrize(
    "params, expected",
    [
        ({"error": GitProtocolError("network")}, VersionerError),
        ({"error": RuntimeError("unexpected")}, VersionerError),
    ],
)
def test_pull_invalid_raises_on_fetch_or_merge_failure(
    bare_versioner: DulwichVersioner,
    params: dict,
    expected: type[BaseException],
) -> None:
    mock_repo = MagicMock()
    mock_repo.get_refs.return_value = {b"refs/remotes/origin/main": b"sha1"}
    with (
        patch.object(bare_versioner, "_get_repository", return_value=mock_repo),
        patch(
            "git.versioner.dulwich_versioner.porcelain.fetch",
            side_effect=params["error"],
        ),
        pytest.raises(expected, match="Failed to pull"),
    ):
        bare_versioner.pull("/test/path", "main")


def test_commit_invalid_wraps_dulwich_error(bare_versioner: DulwichVersioner) -> None:
    mock_repo = MagicMock()
    with (
        patch.object(bare_versioner, "_get_repository", return_value=mock_repo),
        patch.object(bare_versioner, "_has_staged_changes", return_value=True),
        patch(
            "git.versioner.dulwich_versioner.porcelain.commit",
            side_effect=DulwichPorcelainError("commit failed"),
        ),
        pytest.raises(VersionerError, match="Failed to commit changes"),
    ):
        bare_versioner.commit("/test/path", "message")


def test_push_valid_pushes_current_branch(bare_versioner: DulwichVersioner) -> None:
    mock_repo = MagicMock()
    with (
        patch.object(bare_versioner, "_get_repository", return_value=mock_repo),
        patch.object(bare_versioner, "_get_current_branch_name", return_value="main"),
        patch("git.versioner.dulwich_versioner.porcelain.push") as mock_push,
    ):
        bare_versioner.push("/test/path", "main")
    mock_push.assert_called_once_with(
        mock_repo,
        b"origin",
        refspecs=["refs/heads/main:refs/heads/main"],
    )


def test_push_invalid_raises_when_no_current_branch(
    bare_versioner: DulwichVersioner,
) -> None:
    mock_repo = MagicMock()
    with (
        patch.object(bare_versioner, "_get_repository", return_value=mock_repo),
        patch.object(
            bare_versioner,
            "_get_current_branch_name",
            side_effect=VersionerError("No current branch found"),
        ),
        pytest.raises(VersionerError, match="No current branch found"),
    ):
        bare_versioner.push("/test/path", "main")


@pytest.mark.parametrize(
    "params, expected",
    [
        ({"error": DulwichPorcelainError("push failed")}, VersionerError),
        ({"error": RuntimeError("unexpected")}, VersionerError),
    ],
)
def test_push_invalid_raises(
    bare_versioner: DulwichVersioner,
    params: dict,
    expected: type[BaseException],
) -> None:
    mock_repo = MagicMock()
    with (
        patch.object(bare_versioner, "_get_repository", return_value=mock_repo),
        patch.object(bare_versioner, "_get_current_branch_name", return_value="main"),
        patch(
            "git.versioner.dulwich_versioner.porcelain.push",
            side_effect=params["error"],
        ),
        pytest.raises(expected, match="Failed to push"),
    ):
        bare_versioner.push("/test/path", "main")


def test_push_branches_valid_pushes_multiple(bare_versioner: DulwichVersioner) -> None:
    mock_repo = MagicMock()
    with (
        patch.object(bare_versioner, "_get_repository", return_value=mock_repo),
        patch("git.versioner.dulwich_versioner.porcelain.push") as mock_push,
    ):
        bare_versioner.push_branches("/test/path", ["main", "dev"])
    mock_push.assert_called_once_with(
        mock_repo,
        b"origin",
        refspecs=[
            "refs/heads/main:refs/heads/main",
            "refs/heads/dev:refs/heads/dev",
        ],
    )


def test_push_branches_valid_empty_list_is_noop(
    bare_versioner: DulwichVersioner,
) -> None:
    with patch("git.versioner.dulwich_versioner.porcelain.push") as mock_push:
        bare_versioner.push_branches("/test/path", [])
    mock_push.assert_not_called()


def test_push_branches_invalid_reraises_versioner_error(
    bare_versioner: DulwichVersioner,
) -> None:
    with (
        patch.object(
            bare_versioner,
            "_get_repository",
            side_effect=VersionerError("repository missing"),
        ),
        pytest.raises(VersionerError, match="repository missing"),
    ):
        bare_versioner.push_branches("/test/path", ["main"])


@pytest.mark.parametrize(
    "params, expected",
    [
        ({"error": DulwichPorcelainError("push failed")}, VersionerError),
        ({"error": RuntimeError("unexpected")}, VersionerError),
    ],
)
def test_push_branches_invalid_raises(
    bare_versioner: DulwichVersioner,
    params: dict,
    expected: type[BaseException],
) -> None:
    mock_repo = MagicMock()
    with (
        patch.object(bare_versioner, "_get_repository", return_value=mock_repo),
        patch(
            "git.versioner.dulwich_versioner.porcelain.push",
            side_effect=params["error"],
        ),
        pytest.raises(expected, match="Failed to push branches"),
    ):
        bare_versioner.push_branches("/test/path", ["main"])


def test_clone_valid_removes_existing_target(bare_versioner: DulwichVersioner) -> None:
    with (
        patch("git.versioner.dulwich_versioner.shutil.rmtree") as mock_rmtree,
        patch("git.versioner.dulwich_versioner.porcelain.clone"),
        patch.object(Path, "exists", side_effect=[True, False]),
        patch.object(Path, "mkdir"),
    ):
        bare_versioner.clone("https://github.com/test/repo.git", "/tmp/test")
    mock_rmtree.assert_called_once()


def test_clone_invalid_target_still_exists(bare_versioner: DulwichVersioner) -> None:
    with (
        patch("git.versioner.dulwich_versioner.shutil.rmtree"),
        patch.object(Path, "exists", return_value=True),
        patch.object(Path, "mkdir"),
        pytest.raises(VersionerError, match="Target directory still exists"),
    ):
        bare_versioner.clone("https://github.com/test/repo.git", "/tmp/test")


def test_clone_invalid_wraps_generic_error(bare_versioner: DulwichVersioner) -> None:
    with (
        patch.object(Path, "exists", return_value=False),
        patch.object(Path, "mkdir", side_effect=OSError("disk full")),
        pytest.raises(VersionerError, match="Failed to clone repository"),
    ):
        bare_versioner.clone("https://github.com/test/repo.git", "/tmp/test")


@patch.dict("os.environ", {"SSH_AUTH_SOCK": "/tmp/ssh-agent"}, clear=True)
def test_list_remote_branches_invalid_reraises_versioner_error() -> None:
    from auth.factory import create_auth

    auth = create_auth("ssh", username="git", use_agent=True)
    versioner = DulwichVersioner(auth=auth)
    with (
        patch.object(
            versioner,
            "_list_remote_branches_with_git_cli",
            side_effect=VersionerError("ssh failed"),
        ),
        pytest.raises(VersionerError, match="ssh failed"),
    ):
        versioner.list_remote_branches("git@github.com:test/repo.git")


@pytest.mark.parametrize(
    "params, expected",
    [
        ({"error": DulwichPorcelainError("ls-remote failed")}, VersionerError),
        ({"error": RuntimeError("unexpected")}, VersionerError),
    ],
)
def test_list_remote_branches_invalid_raises(
    bare_versioner: DulwichVersioner,
    params: dict,
    expected: type[BaseException],
) -> None:
    with (
        patch(
            "git.versioner.dulwich_versioner.porcelain.ls_remote",
            side_effect=params["error"],
        ),
        pytest.raises(expected, match="Failed to list remote branches"),
    ):
        bare_versioner.list_remote_branches("https://github.com/test/repo.git")


def test_get_available_branches_valid_lists_local_and_remote(
    bare_versioner: DulwichVersioner,
) -> None:
    mock_repo = MagicMock()
    mock_repo.get_refs.return_value = {
        b"refs/heads/main": b"sha1",
        b"refs/remotes/origin/develop": b"sha2",
        b"refs/tags/v1": b"sha3",
    }
    assert compare(
        "eq",
        bare_versioner._get_available_branches(mock_repo),
        ["main", "develop"],
    )


@pytest.mark.parametrize(
    "params, expected",
    [
        ({"branch": "missing", "available": ["main", "dev"]}, "Version 'missing' not found. Available versions: main, dev"),
        ({"branch": "missing", "available": []}, "Version 'missing' not found"),
    ],
)
def test_create_branch_not_found_error_valid_builds_message(
    bare_versioner: DulwichVersioner,
    params: dict,
    expected: str,
) -> None:
    error = bare_versioner._create_branch_not_found_error(
        params["branch"],
        params["available"],
    )
    assert compare("eq", str(error), expected)


def test_checkout_remote_branch_valid_creates_and_checks_out(
    bare_versioner: DulwichVersioner,
) -> None:
    mock_repo = MagicMock()
    with (
        patch("git.versioner.dulwich_versioner.porcelain.branch_create") as mock_create,
        patch("git.versioner.dulwich_versioner.porcelain.checkout") as mock_checkout,
    ):
        bare_versioner._checkout_remote_branch(mock_repo, "main")
    mock_create.assert_called_once_with(mock_repo, "main", objectish="origin/main")
    mock_checkout.assert_called_once_with(mock_repo, target="main")


def test_checkout_remote_branch_invalid_wraps_error(
    bare_versioner: DulwichVersioner,
) -> None:
    mock_repo = MagicMock()
    with (
        patch(
            "git.versioner.dulwich_versioner.porcelain.branch_create",
            side_effect=DulwichPorcelainError("branch failed"),
        ),
        pytest.raises(VersionerError, match="Failed to create and checkout branch"),
    ):
        bare_versioner._checkout_remote_branch(mock_repo, "main")


def test_checkout_local_branch_valid_checks_out(
    bare_versioner: DulwichVersioner,
) -> None:
    mock_repo = MagicMock()
    with patch(
        "git.versioner.dulwich_versioner.porcelain.checkout",
    ) as mock_checkout:
        bare_versioner._checkout_local_branch(mock_repo, "main")
    mock_checkout.assert_called_once_with(mock_repo, target="main")


def test_checkout_local_branch_invalid_wraps_error(
    bare_versioner: DulwichVersioner,
) -> None:
    mock_repo = MagicMock()
    with (
        patch(
            "git.versioner.dulwich_versioner.porcelain.checkout",
            side_effect=DulwichPorcelainError("checkout failed"),
        ),
        pytest.raises(VersionerError, match="Failed to checkout local branch"),
    ):
        bare_versioner._checkout_local_branch(mock_repo, "main")


def test_checkout_invalid_wraps_dulwich_error(bare_versioner: DulwichVersioner) -> None:
    mock_repo = MagicMock()
    mock_repo.get_refs.side_effect = DulwichPorcelainError("refs failed")
    with (
        patch.object(bare_versioner, "_get_repository", return_value=mock_repo),
        pytest.raises(VersionerError, match="Failed to checkout branch"),
    ):
        bare_versioner.checkout("/test/path", "main")


def test_select_branch_valid_returns_remote_match(
    bare_versioner: DulwichVersioner,
) -> None:
    mock_repo = MagicMock()
    mock_repo.get_refs.return_value = {b"refs/remotes/origin/develop": b"sha2"}
    with patch.object(bare_versioner, "_get_repository", return_value=mock_repo):
        assert compare(
            "eq",
            bare_versioner.select_branch("/test/path", ["develop"]),
            "develop",
        )


def test_stash_invalid_wraps_dulwich_error(bare_versioner: DulwichVersioner) -> None:
    mock_repo = MagicMock()
    with (
        patch.object(bare_versioner, "_get_repository", return_value=mock_repo),
        patch.object(bare_versioner, "_has_working_tree_changes", return_value=True),
        patch(
            "git.versioner.dulwich_versioner.porcelain.stash_push",
            side_effect=DulwichPorcelainError("stash failed"),
        ),
        pytest.raises(VersionerError, match="Failed to stash changes"),
    ):
        bare_versioner.stash("/test/path")


def test_safe_pull_valid_without_stash(bare_versioner: DulwichVersioner) -> None:
    mock_repo = MagicMock()
    with (
        patch.object(bare_versioner, "_get_repository", return_value=mock_repo),
        patch.object(bare_versioner, "stash", return_value=False),
        patch.object(bare_versioner, "pull") as mock_pull,
        patch.object(bare_versioner, "_apply_stash") as mock_apply,
    ):
        bare_versioner.safe_pull("/test/path", "main")
    mock_pull.assert_called_once_with("/test/path", "main")
    mock_apply.assert_not_called()


def test_safe_pull_valid_restores_stash_after_success(
    bare_versioner: DulwichVersioner,
) -> None:
    mock_repo = MagicMock()
    with (
        patch.object(bare_versioner, "_get_repository", return_value=mock_repo),
        patch.object(bare_versioner, "stash", return_value=True),
        patch.object(bare_versioner, "pull"),
        patch.object(bare_versioner, "_apply_stash") as mock_apply,
    ):
        bare_versioner.safe_pull("/test/path", "main")
    mock_apply.assert_called_once_with(mock_repo)


def test_safe_pull_valid_restores_stash_after_pull_failure(
    bare_versioner: DulwichVersioner,
) -> None:
    mock_repo = MagicMock()
    with (
        patch.object(bare_versioner, "_get_repository", return_value=mock_repo),
        patch.object(bare_versioner, "stash", return_value=True),
        patch.object(
            bare_versioner,
            "pull",
            side_effect=VersionerError("pull failed"),
        ),
        patch.object(bare_versioner, "_apply_stash") as mock_apply,
    ):
        with pytest.raises(VersionerError, match="pull failed"):
            bare_versioner.safe_pull("/test/path", "main")
    mock_apply.assert_called_once_with(mock_repo)


def test_safe_pull_invalid_wraps_dulwich_error(bare_versioner: DulwichVersioner) -> None:
    with (
        patch.object(
            bare_versioner,
            "_get_repository",
            side_effect=NotGitRepository("not a repo"),
        ),
        pytest.raises(VersionerError, match="Failed to perform safe pull"),
    ):
        bare_versioner.safe_pull("/test/path", "main")


def test_apply_stash_valid_no_entries_is_noop(bare_versioner: DulwichVersioner) -> None:
    mock_repo = MagicMock()
    with (
        patch(
            "git.versioner.dulwich_versioner.porcelain.stash_list",
            return_value=[],
        ),
        patch("git.versioner.dulwich_versioner.porcelain.stash_pop") as mock_pop,
    ):
        bare_versioner._apply_stash(mock_repo)
    mock_pop.assert_not_called()


def test_apply_stash_valid_pops_most_recent(bare_versioner: DulwichVersioner) -> None:
    mock_repo = MagicMock()
    with (
        patch(
            "git.versioner.dulwich_versioner.porcelain.stash_list",
            return_value=[b"stash@{0}"],
        ),
        patch("git.versioner.dulwich_versioner.porcelain.stash_pop") as mock_pop,
    ):
        bare_versioner._apply_stash(mock_repo)
    mock_pop.assert_called_once_with(mock_repo)


def test_apply_stash_invalid_wraps_dulwich_error(
    bare_versioner: DulwichVersioner,
) -> None:
    mock_repo = MagicMock()
    with (
        patch(
            "git.versioner.dulwich_versioner.porcelain.stash_list",
            return_value=[b"stash@{0}"],
        ),
        patch(
            "git.versioner.dulwich_versioner.porcelain.stash_pop",
            side_effect=DulwichPorcelainError("pop failed"),
        ),
        pytest.raises(VersionerError, match="Failed to apply stash"),
    ):
        bare_versioner._apply_stash(mock_repo)


def test_safe_pull_valid_logs_when_stash_restore_fails(
    bare_versioner: DulwichVersioner,
) -> None:
    mock_repo = MagicMock()
    with (
        patch.object(bare_versioner, "_get_repository", return_value=mock_repo),
        patch.object(bare_versioner, "stash", return_value=True),
        patch.object(
            bare_versioner,
            "pull",
            side_effect=VersionerError("pull failed"),
        ),
        patch.object(
            bare_versioner,
            "_apply_stash",
            side_effect=VersionerError("restore failed"),
        ),
        patch("git.versioner.dulwich_versioner.log.warning") as mock_warning,
    ):
        with pytest.raises(VersionerError, match="pull failed"):
            bare_versioner.safe_pull("/test/path", "main")
    mock_warning.assert_called_once()


@patch.dict("os.environ", {"SSH_AUTH_SOCK": "/tmp/ssh-agent"}, clear=True)
def test_remote_exists_valid_uses_git_cli() -> None:
    from auth.factory import create_auth

    auth = create_auth("ssh", username="git", use_agent=True)
    versioner = DulwichVersioner(auth=auth)
    git_env = auth.git_cli_environment()
    with patch.object(
        versioner,
        "_list_remote_branches_with_git_cli",
        return_value=["main"],
    ) as mock_git_ls:
        assert compare(
            "eq",
            versioner.remote_exists("git@github.com:test/repo.git"),
            True,
        )
    mock_git_ls.assert_called_once_with("git@github.com:test/repo.git", git_env)
