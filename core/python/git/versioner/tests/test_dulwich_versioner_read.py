"""Tests for the read-only inspection API of the Dulwich versioner.

These tests build real repositories on disk rather than mocking Dulwich, so
they validate the actual behaviour the kbot code base relies on.
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from dulwich import porcelain
from dulwich.repo import Repo

from git.versioner.dulwich_versioner import DulwichVersioner
from git.versioner.errors import (
    BranchNotFoundError,
    NoSuchRepositoryPathError,
    NotAGitRepositoryError,
    RemoteNotFoundError,
    RepositoryNotFoundError,
    VersionerError,
)
from git.versioner.status import RepoStatus
from utils.utils_for_unit_tests import compare

AUTHOR = b"Tester <tester@example.com>"


@pytest.fixture
def versioner() -> DulwichVersioner:
    """Create a DulwichVersioner without authentication."""
    return DulwichVersioner()


def _commit_file(repo: Repo, name: str, content: str = "content") -> bytes:
    """Write, stage and commit a file, returning the new commit id."""
    path = Path(repo.path) / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)
    porcelain.add(repo, paths=[str(path)])
    return porcelain.commit(repo, message=b"msg", author=AUTHOR, committer=AUTHOR)


@pytest.fixture
def repo_path(tmp_path: Path) -> Path:
    """Create a repository with a single commit on the default branch."""
    path = tmp_path / "repo"
    path.mkdir()
    with porcelain.init(str(path)) as repo:
        _commit_file(repo, "tracked.txt")
    return path


def test_head_commit_id_valid_returns_hex_sha(
    versioner: DulwichVersioner, repo_path: Path
) -> None:
    with Repo(str(repo_path)) as repo:
        expected = repo.head().decode()
    result = versioner.head_commit_id(repo_path)
    assert compare("eq", result, expected)
    assert compare("eq", len(result), 40)


def test_head_commit_id_invalid_empty_repository_raises(
    versioner: DulwichVersioner, tmp_path: Path
) -> None:
    path = tmp_path / "empty"
    path.mkdir()
    porcelain.init(str(path)).close()
    with pytest.raises(VersionerError, match="no HEAD commit"):
        versioner.head_commit_id(path)


def test_current_branch_valid_returns_checked_out_branch(
    versioner: DulwichVersioner, repo_path: Path
) -> None:
    with Repo(str(repo_path)) as repo:
        porcelain.branch_create(repo, "feature/x")
        porcelain.checkout(repo, target="feature/x")
    assert compare("eq", versioner.current_branch(repo_path), "feature/x")


def test_remote_url_valid_returns_configured_url(
    versioner: DulwichVersioner, repo_path: Path
) -> None:
    url = "git@github.com:konverso-ai/kbot.git"
    with Repo(str(repo_path)) as repo:
        config = repo.get_config()
        config.set((b"remote", b"origin"), b"url", url.encode())
        config.write_to_path()
    assert compare("eq", versioner.remote_url(repo_path), url)


def test_remote_url_invalid_unknown_remote_raises(
    versioner: DulwichVersioner, repo_path: Path
) -> None:
    with pytest.raises(RemoteNotFoundError):
        versioner.remote_url(repo_path, "nope")


def test_status_valid_reports_staged_unstaged_and_untracked(
    versioner: DulwichVersioner, repo_path: Path
) -> None:
    (repo_path / "tracked.txt").write_text("modified")
    (repo_path / "untracked.txt").write_text("new")
    staged = repo_path / "staged.txt"
    staged.write_text("staged")
    with Repo(str(repo_path)) as repo:
        porcelain.add(repo, paths=[str(staged)])

    status = versioner.status(repo_path)

    assert isinstance(status, RepoStatus)
    assert compare("eq", status.staged_added, ["staged.txt"])
    assert compare("eq", status.unstaged, ["tracked.txt"])
    assert compare("eq", status.untracked, ["untracked.txt"])
    assert compare("eq", status.is_clean, False)
    assert compare("eq", status.has_staged_changes, True)
    assert compare("eq", status.changed, ["staged.txt", "tracked.txt"])


def test_status_valid_clean_repository_is_clean(
    versioner: DulwichVersioner, repo_path: Path
) -> None:
    status = versioner.status(repo_path)
    assert compare("eq", status.is_clean, True)
    assert compare("eq", status.changed, [])


def test_is_bare_valid_reports_working_tree_repository(
    versioner: DulwichVersioner, repo_path: Path
) -> None:
    assert compare("eq", versioner.is_bare(repo_path), False)


def test_is_bare_valid_reports_bare_repository(
    versioner: DulwichVersioner, tmp_path: Path
) -> None:
    path = tmp_path / "bare"
    path.mkdir()
    porcelain.init(str(path), bare=True).close()
    assert compare("eq", versioner.is_bare(path), True)


def test_working_dir_valid_returns_resolved_path(
    versioner: DulwichVersioner, repo_path: Path
) -> None:
    assert compare("eq", versioner.working_dir(repo_path), str(repo_path.resolve()))


def test_working_dir_invalid_bare_repository_raises(
    versioner: DulwichVersioner, tmp_path: Path
) -> None:
    path = tmp_path / "bare"
    path.mkdir()
    porcelain.init(str(path), bare=True).close()
    with pytest.raises(VersionerError, match="no working tree"):
        versioner.working_dir(path)


def test_list_local_branches_valid_returns_sorted_names(
    versioner: DulwichVersioner, repo_path: Path
) -> None:
    with Repo(str(repo_path)) as repo:
        porcelain.branch_create(repo, "zeta")
        porcelain.branch_create(repo, "alpha")
        default = versioner.current_branch(repo_path)
    expected = sorted({"alpha", "zeta", default})
    assert compare("eq", versioner.list_local_branches(repo_path), expected)


def test_ahead_behind_valid_without_remote_tracking_returns_zero(
    versioner: DulwichVersioner, repo_path: Path
) -> None:
    assert compare("eq", versioner.ahead_behind(repo_path), (0, 0))


def test_ahead_behind_valid_counts_local_commits(
    versioner: DulwichVersioner, repo_path: Path
) -> None:
    branch = versioner.current_branch(repo_path)
    with Repo(str(repo_path)) as repo:
        # Pin a remote-tracking ref to the current commit, then move forward.
        repo.refs[f"refs/remotes/origin/{branch}".encode()] = repo.head()
        _commit_file(repo, "second.txt")
        _commit_file(repo, "third.txt")
    assert compare("eq", versioner.ahead_behind(repo_path), (2, 0))


def test_ahead_behind_valid_counts_remote_commits(
    versioner: DulwichVersioner, repo_path: Path
) -> None:
    branch = versioner.current_branch(repo_path)
    with Repo(str(repo_path)) as repo:
        base = repo.head()
        _commit_file(repo, "remote-only.txt")
        _commit_file(repo, "remote-only-2.txt")
        # Remote is two commits ahead; rewind the local branch to the base.
        repo.refs[f"refs/remotes/origin/{branch}".encode()] = repo.head()
        repo.refs[f"refs/heads/{branch}".encode()] = base
    assert compare("eq", versioner.ahead_behind(repo_path), (0, 2))


def test_ahead_behind_valid_counts_diverged_branches(
    versioner: DulwichVersioner, repo_path: Path
) -> None:
    branch = versioner.current_branch(repo_path)
    with Repo(str(repo_path)) as repo:
        base = repo.head()
        _commit_file(repo, "remote-only.txt")
        repo.refs[f"refs/remotes/origin/{branch}".encode()] = repo.head()
        repo.refs[f"refs/heads/{branch}".encode()] = base
        _commit_file(repo, "local-only.txt", "local")
        _commit_file(repo, "local-only-2.txt", "local")
    assert compare("eq", versioner.ahead_behind(repo_path), (2, 1))


def test_ahead_behind_invalid_unknown_branch_raises(
    versioner: DulwichVersioner, repo_path: Path
) -> None:
    with pytest.raises(BranchNotFoundError):
        versioner.ahead_behind(repo_path, "no-such-branch")


@pytest.mark.parametrize(
    "method_name",
    [
        "head_commit_id",
        "current_branch",
        "remote_url",
        "status",
        "is_bare",
        "working_dir",
        "ahead_behind",
        "list_local_branches",
    ],
)
def test_read_methods_invalid_missing_path_raise_no_such_path(
    versioner: DulwichVersioner, tmp_path: Path, method_name: str
) -> None:
    missing = tmp_path / "does-not-exist"
    with pytest.raises(NoSuchRepositoryPathError) as excinfo:
        getattr(versioner, method_name)(missing)
    assert isinstance(excinfo.value, RepositoryNotFoundError)


@pytest.mark.parametrize(
    "method_name",
    [
        "head_commit_id",
        "current_branch",
        "remote_url",
        "status",
        "is_bare",
        "working_dir",
        "ahead_behind",
        "list_local_branches",
    ],
)
def test_read_methods_invalid_not_a_repository_raise_not_a_git_repository(
    versioner: DulwichVersioner, tmp_path: Path, method_name: str
) -> None:
    plain = tmp_path / "plain"
    plain.mkdir()
    with pytest.raises(NotAGitRepositoryError) as excinfo:
        getattr(versioner, method_name)(plain)
    assert isinstance(excinfo.value, RepositoryNotFoundError)


def test_open_repository_valid_closes_repository_on_success(
    versioner: DulwichVersioner, repo_path: Path
) -> None:
    fake_repo = MagicMock()
    with patch.object(versioner, "_get_repository", return_value=fake_repo):
        with versioner._open_repository(repo_path) as repo:
            assert compare("eq", repo is fake_repo, True)
            fake_repo.close.assert_not_called()
    fake_repo.close.assert_called_once()


def test_open_repository_valid_closes_repository_on_error(
    versioner: DulwichVersioner, repo_path: Path
) -> None:
    fake_repo = MagicMock()
    with patch.object(versioner, "_get_repository", return_value=fake_repo):
        with pytest.raises(RuntimeError, match="boom"):
            with versioner._open_repository(repo_path):
                raise RuntimeError("boom")
    fake_repo.close.assert_called_once()


def test_read_methods_valid_do_not_leak_open_repositories(
    versioner: DulwichVersioner, repo_path: Path
) -> None:
    """Every read helper must close the repository it opens."""
    opened: list[MagicMock] = []
    real_get_repository = versioner._get_repository

    def _tracking_get_repository(path: str | Path) -> MagicMock:
        repo = MagicMock(wraps=real_get_repository(path))
        opened.append(repo)
        return repo

    with patch.object(
        versioner, "_get_repository", side_effect=_tracking_get_repository
    ):
        versioner.is_bare(repo_path)
        versioner.list_local_branches(repo_path)

    assert compare("eq", len(opened), 2)
    for repo in opened:
        repo.close.assert_called_once()


#
# describe_head / read_file
#


def test_describe_head_valid_returns_branch_name(
    versioner: DulwichVersioner, repo_path: Path
) -> None:
    compare("eq", versioner.describe_head(repo_path), versioner.current_branch(repo_path))


def test_describe_head_valid_returns_tag_when_detached(
    versioner: DulwichVersioner, repo_path: Path
) -> None:
    versioner.create_tag(repo_path, "v1.2.3")
    head = versioner.head_commit_id(repo_path)
    with Repo(str(repo_path)) as repo:
        repo.refs[b"HEAD"] = head.encode()

    compare("eq", versioner.describe_head(repo_path), "v1.2.3")


def test_describe_head_valid_returns_short_sha_when_detached_without_tag(
    versioner: DulwichVersioner, repo_path: Path
) -> None:
    head = versioner.head_commit_id(repo_path)
    with Repo(str(repo_path)) as repo:
        repo.refs[b"HEAD"] = head.encode()

    compare("eq", versioner.describe_head(repo_path), head[:7])


def test_read_file_valid_returns_committed_content(
    versioner: DulwichVersioner, repo_path: Path
) -> None:
    (repo_path / "tracked.txt").write_text("locally modified")

    compare("eq", versioner.read_file(repo_path, "tracked.txt"), b"content")


def test_read_file_valid_reads_nested_path(
    versioner: DulwichVersioner, repo_path: Path
) -> None:
    with Repo(str(repo_path)) as repo:
        _commit_file(repo, "sub/nested.txt", "nested content")

    compare("eq", versioner.read_file(repo_path, "sub/nested.txt"), b"nested content")


def test_read_file_valid_unknown_path_returns_none(
    versioner: DulwichVersioner, repo_path: Path
) -> None:
    compare("eq", versioner.read_file(repo_path, "nope.txt"), None)


def test_read_file_valid_reads_from_a_tag(
    versioner: DulwichVersioner, repo_path: Path
) -> None:
    versioner.create_tag(repo_path, "before")
    with Repo(str(repo_path)) as repo:
        _commit_file(repo, "tracked.txt", "after")

    compare("eq", versioner.read_file(repo_path, "tracked.txt", "before"), b"content")
    compare("eq", versioner.read_file(repo_path, "tracked.txt"), b"after")


def test_read_file_invalid_unknown_revision_raises(
    versioner: DulwichVersioner, repo_path: Path
) -> None:
    with pytest.raises(VersionerError, match="Unknown revision"):
        versioner.read_file(repo_path, "tracked.txt", "no-such-rev")
