"""Tests for the write API of the Dulwich versioner.

These tests build real repositories on disk rather than mocking Dulwich, so
they validate the actual behaviour the kbot code base relies on.
"""

from pathlib import Path

import pytest
from dulwich import porcelain
from dulwich.repo import Repo

from git.versioner.author import Author
from git.versioner.dulwich_versioner import DulwichVersioner
from git.versioner.errors import VersionerError
from utils.utils_for_unit_tests import compare

AUTHOR = b"Tester <tester@example.com>"


@pytest.fixture
def versioner() -> DulwichVersioner:
    """Create a DulwichVersioner without authentication."""
    return DulwichVersioner()


def _commit_all(repo: Repo, message: bytes = b"msg") -> bytes:
    """Stage everything and commit."""
    porcelain.add(repo, paths=".")
    return porcelain.commit(repo, message=message, author=AUTHOR, committer=AUTHOR)


@pytest.fixture
def repo_path(tmp_path: Path) -> Path:
    """Create a repository with two committed files."""
    path = tmp_path / "repo"
    path.mkdir()
    (path / "sub").mkdir()
    (path / "a.txt").write_text("a1")
    (path / "sub" / "b.txt").write_text("b1")
    with porcelain.init(str(path)) as repo:
        _commit_all(repo)
    return path


#
# add
#


def test_add_valid_stages_named_files(
    versioner: DulwichVersioner, repo_path: Path
) -> None:
    (repo_path / "new.txt").write_text("new")
    versioner.add(repo_path, ["new.txt"])
    assert compare("eq", versioner.status(repo_path).staged_added, ["new.txt"])


def test_add_valid_without_files_stages_deletions(
    versioner: DulwichVersioner, repo_path: Path
) -> None:
    """add(None) must behave like 'git add --all' and stage deletions."""
    (repo_path / "a.txt").unlink()
    (repo_path / "new.txt").write_text("new")

    versioner.add(repo_path)

    status = versioner.status(repo_path)
    assert compare("eq", status.staged_deleted, ["a.txt"])
    assert compare("eq", status.staged_added, ["new.txt"])


#
# remove
#


def test_remove_valid_deletes_file_and_stages_deletion(
    versioner: DulwichVersioner, repo_path: Path
) -> None:
    versioner.remove(repo_path, ["sub/b.txt"])

    assert compare("eq", (repo_path / "sub" / "b.txt").exists(), False)
    assert compare("eq", versioner.status(repo_path).staged_deleted, ["sub/b.txt"])


def test_remove_valid_empty_list_is_noop(
    versioner: DulwichVersioner, repo_path: Path
) -> None:
    versioner.remove(repo_path, [])
    assert compare("eq", versioner.status(repo_path).is_clean, True)


def test_remove_invalid_unknown_path_raises(
    versioner: DulwichVersioner, repo_path: Path
) -> None:
    with pytest.raises(VersionerError, match="Failed to remove files"):
        versioner.remove(repo_path, ["does-not-exist.txt"])


#
# unstage
#


def test_unstage_valid_keeps_working_tree_changes(
    versioner: DulwichVersioner, repo_path: Path
) -> None:
    (repo_path / "a.txt").write_text("a2")
    versioner.add(repo_path, ["a.txt"])
    assert compare("eq", versioner.status(repo_path).staged_modified, ["a.txt"])

    versioner.unstage(repo_path, ["a.txt"])

    status = versioner.status(repo_path)
    assert compare("eq", status.staged, [])
    assert compare("eq", status.unstaged, ["a.txt"])
    assert compare("eq", (repo_path / "a.txt").read_text(), "a2")


def test_unstage_valid_empty_list_is_noop(
    versioner: DulwichVersioner, repo_path: Path
) -> None:
    versioner.unstage(repo_path, [])
    assert compare("eq", versioner.status(repo_path).is_clean, True)


#
# restore_files
#


def test_restore_files_valid_discards_working_tree_changes(
    versioner: DulwichVersioner, repo_path: Path
) -> None:
    (repo_path / "a.txt").write_text("modified")

    versioner.restore_files(repo_path, ["a.txt"])

    assert compare("eq", (repo_path / "a.txt").read_text(), "a1")
    assert compare("eq", versioner.status(repo_path).is_clean, True)


def test_restore_files_valid_leaves_other_files_untouched(
    versioner: DulwichVersioner, repo_path: Path
) -> None:
    (repo_path / "a.txt").write_text("modified-a")
    (repo_path / "sub" / "b.txt").write_text("modified-b")

    versioner.restore_files(repo_path, ["a.txt"])

    assert compare("eq", (repo_path / "a.txt").read_text(), "a1")
    assert compare("eq", (repo_path / "sub" / "b.txt").read_text(), "modified-b")


#
# reset_hard
#


def test_reset_hard_valid_discards_all_changes(
    versioner: DulwichVersioner, repo_path: Path
) -> None:
    (repo_path / "a.txt").write_text("modified")
    versioner.add(repo_path, ["a.txt"])

    versioner.reset_hard(repo_path)

    assert compare("eq", (repo_path / "a.txt").read_text(), "a1")
    assert compare("eq", versioner.status(repo_path).is_clean, True)


def test_reset_hard_valid_rewinds_to_tag(
    versioner: DulwichVersioner, repo_path: Path
) -> None:
    versioner.create_tag(repo_path, "checkpoint")
    original = versioner.head_commit_id(repo_path)

    (repo_path / "a.txt").write_text("a2")
    with Repo(str(repo_path)) as repo:
        _commit_all(repo, b"second")
    assert compare("eq", versioner.head_commit_id(repo_path) != original, True)

    versioner.reset_hard(repo_path, "checkpoint")

    assert compare("eq", versioner.head_commit_id(repo_path), original)
    assert compare("eq", (repo_path / "a.txt").read_text(), "a1")


def test_reset_hard_invalid_unknown_revision_raises(
    versioner: DulwichVersioner, repo_path: Path
) -> None:
    with pytest.raises(VersionerError):
        versioner.reset_hard(repo_path, "no-such-tag")


#
# tags
#


def test_create_tag_valid_lightweight_tag_is_listed(
    versioner: DulwichVersioner, repo_path: Path
) -> None:
    versioner.create_tag(repo_path, "v1.0.0")
    assert compare("eq", versioner.list_tags(repo_path), ["v1.0.0"])


def test_create_tag_valid_annotated_tag_is_listed(
    versioner: DulwichVersioner, repo_path: Path
) -> None:
    versioner.create_tag(repo_path, "v2.0.0", message="release")
    assert compare("eq", versioner.list_tags(repo_path), ["v2.0.0"])


def test_create_tag_invalid_duplicate_raises(
    versioner: DulwichVersioner, repo_path: Path
) -> None:
    versioner.create_tag(repo_path, "dup")
    with pytest.raises(VersionerError, match="already exists"):
        versioner.create_tag(repo_path, "dup")


def test_list_tags_valid_returns_sorted_names(
    versioner: DulwichVersioner, repo_path: Path
) -> None:
    for name in ("zeta", "alpha", "middle"):
        versioner.create_tag(repo_path, name)
    assert compare("eq", versioner.list_tags(repo_path), ["alpha", "middle", "zeta"])


#
# commit
#


def test_commit_valid_returns_commit_id(
    versioner: DulwichVersioner, repo_path: Path
) -> None:
    (repo_path / "a.txt").write_text("a2")
    versioner.add(repo_path, ["a.txt"])

    commit_id = versioner.commit(repo_path, "update a")

    assert commit_id is not None
    assert compare("eq", len(commit_id), 40)
    assert compare("eq", versioner.head_commit_id(repo_path), commit_id)


def test_commit_valid_without_staged_changes_returns_none(
    versioner: DulwichVersioner, repo_path: Path
) -> None:
    assert compare("eq", versioner.commit(repo_path, "nothing"), None)


def test_commit_valid_uses_per_call_author(
    versioner: DulwichVersioner, repo_path: Path
) -> None:
    (repo_path / "a.txt").write_text("a2")
    versioner.add(repo_path, ["a.txt"])
    author = Author(name="Alice", email="alice@example.com")

    commit_id = versioner.commit(repo_path, "by alice", author=author)

    with Repo(str(repo_path)) as repo:
        commit = repo[commit_id.encode()]
    assert compare("eq", commit.author, b"Alice <alice@example.com>")
    assert compare("eq", commit.committer, b"Alice <alice@example.com>")


def test_commit_valid_falls_back_to_versioner_author(repo_path: Path) -> None:
    author = Author(name="Default", email="default@example.com")
    versioner = DulwichVersioner(author=author)
    (repo_path / "a.txt").write_text("a2")
    versioner.add(repo_path, ["a.txt"])

    commit_id = versioner.commit(repo_path, "by default")

    with Repo(str(repo_path)) as repo:
        commit = repo[commit_id.encode()]
    assert compare("eq", commit.author, b"Default <default@example.com>")


def test_commit_valid_records_deletions_staged_by_remove(
    versioner: DulwichVersioner, repo_path: Path
) -> None:
    versioner.remove(repo_path, ["a.txt"])

    commit_id = versioner.commit(repo_path, "drop a")

    assert commit_id is not None
    assert compare("eq", versioner.status(repo_path).is_clean, True)
    assert compare("eq", (repo_path / "a.txt").exists(), False)
