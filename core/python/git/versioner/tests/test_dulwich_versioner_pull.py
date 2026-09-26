"""Tests for the structured pull result of the Dulwich versioner.

These tests wire two real repositories together through a local ``origin``
remote so that ``pull()`` exercises the actual fetch/merge path.
"""

from pathlib import Path

import pytest
from dulwich import porcelain
from dulwich.repo import Repo

from git.versioner.dulwich_versioner import DulwichVersioner
from utils.utils_for_unit_tests import compare

AUTHOR = b"Tester <tester@example.com>"


@pytest.fixture
def versioner() -> DulwichVersioner:
    """Create a DulwichVersioner without authentication."""
    return DulwichVersioner()


def _commit_all(repo: Repo, message: bytes) -> bytes:
    """Stage everything and commit."""
    porcelain.add(repo, paths=".")
    return porcelain.commit(repo, message=message, author=AUTHOR, committer=AUTHOR)


@pytest.fixture
def upstream(tmp_path: Path) -> Path:
    """Create the upstream repository with an initial commit on master."""
    path = tmp_path / "upstream"
    path.mkdir()
    (path / "conf").mkdir()
    (path / "a.txt").write_text("a1")
    (path / "gone.txt").write_text("gone")
    (path / "conf" / "app.conf").write_text("c1")
    with porcelain.init(str(path)) as repo:
        _commit_all(repo, b"initial")
        repo.refs[b"refs/heads/master"] = repo.head()
    return path


@pytest.fixture
def clone(tmp_path: Path, upstream: Path) -> Path:
    """Clone the upstream repository locally."""
    path = tmp_path / "clone"
    with porcelain.clone(str(upstream), str(path), branch=b"master") as repo:
        repo.refs[b"refs/heads/master"] = repo.head()
        repo.refs.set_symbolic_ref(b"HEAD", b"refs/heads/master")
    return path


def _push_upstream_changes(upstream: Path) -> None:
    """Add, modify and delete files upstream, then commit on master."""
    (upstream / "a.txt").write_text("a2")
    (upstream / "gone.txt").unlink()
    (upstream / "new.txt").write_text("new")
    (upstream / "db").mkdir()
    (upstream / "db" / "upgrade_1_to_2.sql").write_text("sql")
    with Repo(str(upstream)) as repo:
        _commit_all(repo, b"upstream changes")
        repo.refs[b"refs/heads/master"] = repo.head()


def test_pull_valid_reports_added_modified_and_deleted(
    versioner: DulwichVersioner, upstream: Path, clone: Path
) -> None:
    _push_upstream_changes(upstream)

    result = versioner.pull(clone, "master")

    compare("eq", result.added, ["db/upgrade_1_to_2.sql", "new.txt"])
    compare("eq", result.modified, ["a.txt"])
    compare("eq", result.deleted, ["gone.txt"])


def test_pull_valid_reports_has_changes(
    versioner: DulwichVersioner, upstream: Path, clone: Path
) -> None:
    _push_upstream_changes(upstream)

    result = versioner.pull(clone, "master")

    compare("eq", result.has_changes, True)
    compare("eq", result.is_fast_forward_noop, False)
    compare(
        "eq",
        result.changed,
        ["a.txt", "db/upgrade_1_to_2.sql", "gone.txt", "new.txt"],
    )


def test_pull_valid_moves_head_to_the_new_commit(
    versioner: DulwichVersioner, upstream: Path, clone: Path
) -> None:
    before = versioner.head_commit_id(clone)
    _push_upstream_changes(upstream)

    result = versioner.pull(clone, "master")

    compare("eq", result.old_commit_id, before)
    compare("eq", result.new_commit_id, versioner.head_commit_id(clone))


def test_pull_valid_without_remote_changes_reports_nothing(
    versioner: DulwichVersioner, clone: Path
) -> None:
    result = versioner.pull(clone, "master")

    compare("eq", result.has_changes, False)
    compare("eq", result.is_fast_forward_noop, True)
    compare("eq", result.changed, [])


def test_pull_valid_applies_changes_to_the_working_tree(
    versioner: DulwichVersioner, upstream: Path, clone: Path
) -> None:
    _push_upstream_changes(upstream)

    versioner.pull(clone, "master")

    compare("eq", (clone / "a.txt").read_text(), "a2")
    compare("eq", (clone / "new.txt").exists(), True)
    compare("eq", (clone / "gone.txt").exists(), False)


def test_safe_pull_valid_returns_the_pull_result(
    versioner: DulwichVersioner, upstream: Path, clone: Path
) -> None:
    _push_upstream_changes(upstream)

    result = versioner.safe_pull(clone, "master")

    compare("eq", result.added, ["db/upgrade_1_to_2.sql", "new.txt"])
    compare("eq", result.deleted, ["gone.txt"])
