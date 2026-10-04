"""Tests for InstallerUpdatable.

Git working copies are real dulwich clones of a local ``origin`` repository,
so checkout/fetch/pull run the actual code path without any authentication.
"""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from dulwich import porcelain
from dulwich.repo import Repo

from git.versioner.dulwich_versioner import DulwichVersioner
from storage.base import StorageBackendEnum
from updatable.installer_updatable import InstallerUpdatable
from utils.product.build import Build
from utils.product.product import Product
from utils.utils_for_unit_tests import compare

AUTHOR = b"Tester <tester@example.com>"
VERSIONED_XML = '<product name="demo" version="2026.01" type="solution"/>'
UNVERSIONED_XML = '<product name="demo" type="solution"/>'


def _commit_all(repo: Repo, message: bytes) -> bytes:
    """Stage everything and commit."""
    porcelain.add(repo, paths=".")
    return porcelain.commit(repo, message=message, author=AUTHOR, committer=AUTHOR)


def _make_upstream(path: Path, branch: str, description_xml: str = VERSIONED_XML) -> None:
    """Create an upstream repository with an initial commit on branch."""
    path.mkdir(parents=True)
    (path / "description.xml").write_text(description_xml, encoding="utf-8")
    (path / "README").write_text("a", encoding="utf-8")
    with porcelain.init(str(path)) as repo:
        repo.refs.set_symbolic_ref(b"HEAD", b"refs/heads/" + branch.encode())
        _commit_all(repo, b"initial")


def _clone(upstream: Path, target: Path, branch: str) -> None:
    """Clone upstream on branch, with a local branch tracking it."""
    ref = b"refs/heads/" + branch.encode()
    with porcelain.clone(str(upstream), str(target), branch=branch.encode()) as repo:
        repo.refs[ref] = repo.head()
        repo.refs.set_symbolic_ref(b"HEAD", ref)


def _commit_upstream(upstream: Path, branch: str) -> bytes:
    """Commit a README change upstream and point branch at it."""
    (upstream / "README").write_text("b", encoding="utf-8")
    with Repo(str(upstream)) as repo:
        commit = _commit_all(repo, b"upstream change")
        repo.refs[b"refs/heads/" + branch.encode()] = commit
    return commit


def _head(path: Path) -> bytes:
    with Repo(str(path)) as repo:
        return repo.head()


def _updatable(installer: Path) -> InstallerUpdatable:
    return InstallerUpdatable(installer_path=installer, storage_backend=StorageBackendEnum.NEXUS)


@pytest.fixture
def installer(tmp_path: Path) -> Path:
    """Create an empty installer directory."""
    path = tmp_path / "installer"
    path.mkdir()
    return path


class TestGitWorkingCopies:
    """Git working copies are moved to their version branch and pulled."""

    def test_feature_branch_moves_to_dev_release_branch(self, tmp_path: Path, installer: Path) -> None:
        """A clone on an unrelated branch is checked out on the dev release branch, then pulled."""
        upstream = tmp_path / "up"
        _make_upstream(upstream, "master")
        demo = installer / "demo"
        _clone(upstream, demo, "master")
        with Repo(str(demo)) as repo:
            repo.refs[b"refs/heads/feature"] = repo.head()
            repo.refs.set_symbolic_ref(b"HEAD", b"refs/heads/feature")
        new_head = _commit_upstream(upstream, "release-2026.01-dev")

        failed = _updatable(installer)()

        assert compare("eq", failed, [])
        assert compare("eq", DulwichVersioner().current_branch(demo), "release-2026.01-dev")
        assert compare("eq", _head(demo), new_head)
        assert compare("eq", (demo / "README").read_text(encoding="utf-8"), "b")

    def test_prod_release_branch_is_kept_and_pulled(self, tmp_path: Path, installer: Path) -> None:
        """A clone already on the prod release branch stays on it and gets the upstream commit."""
        upstream = tmp_path / "up"
        _make_upstream(upstream, "release-2026.01")
        demo = installer / "demo"
        _clone(upstream, demo, "release-2026.01")
        new_head = _commit_upstream(upstream, "release-2026.01")

        failed = _updatable(installer)()

        assert compare("eq", failed, [])
        assert compare("eq", DulwichVersioner().current_branch(demo), "release-2026.01")
        assert compare("eq", _head(demo), new_head)

    def test_dirty_repository_is_skipped_and_others_updated(self, tmp_path: Path, installer: Path) -> None:
        """A tracked modification fails that product only; the other clone is still pulled."""
        upstream = tmp_path / "up"
        _make_upstream(upstream, "release-2026.01-dev")
        dirty = installer / "dirty"
        clean = installer / "demo"
        _clone(upstream, dirty, "release-2026.01-dev")
        _clone(upstream, clean, "release-2026.01-dev")
        (dirty / "README").write_text("a-local", encoding="utf-8")
        old_dirty_head = _head(dirty)
        new_head = _commit_upstream(upstream, "release-2026.01-dev")

        failed = _updatable(installer)()

        assert compare("eq", failed, ["dirty"])
        assert compare("eq", (dirty / "README").read_text(encoding="utf-8"), "a-local")
        assert compare("eq", _head(dirty), old_dirty_head)
        assert compare("eq", _head(clean), new_head)

    def test_untracked_file_does_not_block_update(self, tmp_path: Path, installer: Path) -> None:
        """Untracked files are not uncommitted changes: the clone is updated."""
        upstream = tmp_path / "up"
        _make_upstream(upstream, "release-2026.01-dev")
        demo = installer / "demo"
        _clone(upstream, demo, "release-2026.01-dev")
        (demo / "notes.txt").write_text("mine", encoding="utf-8")
        new_head = _commit_upstream(upstream, "release-2026.01-dev")

        failed = _updatable(installer)()

        assert compare("eq", failed, [])
        assert compare("eq", _head(demo), new_head)
        assert compare("eq", (demo / "notes.txt").read_text(encoding="utf-8"), "mine")

    def test_detached_head_without_version_fails(self, tmp_path: Path, installer: Path) -> None:
        """Without a version nor a current branch, no branch can be chosen."""
        upstream = tmp_path / "up"
        _make_upstream(upstream, "master", UNVERSIONED_XML)
        demo = installer / "demo"
        _clone(upstream, demo, "master")
        head = _head(demo)
        (demo / ".git" / "HEAD").write_text(head.decode() + "\n", encoding="utf-8")

        failed = _updatable(installer)()

        assert compare("eq", failed, ["demo"])
        assert compare("eq", _head(demo), head)


class TestStorageArtifacts:
    """Storage downloads are replaced by the latest artifact of their branch."""

    @staticmethod
    def _write_download(path: Path, commit: str) -> None:
        path.mkdir(parents=True, exist_ok=True)
        product = Product(name="acme", build=Build(branch="release-2026.01-dev", commit=commit))
        (path / "description.xml").write_text('<product name="acme"/>', encoding="utf-8")
        (path / "description.json").write_text(json.dumps(product.to_json()), encoding="utf-8")

    def _provider_writing(self, commit: str) -> MagicMock:
        provider = MagicMock()

        def _clone(_name: str, target: Path, **_kwargs: object) -> None:
            self._write_download(Path(target), commit)

        provider.clone_and_checkout.side_effect = _clone
        return provider

    def test_new_commit_replaces_folder(self, installer: Path) -> None:
        """A newer artifact replaces the whole product folder."""
        acme = installer / "acme"
        self._write_download(acme, "old")
        (acme / "marker").write_text("stale", encoding="utf-8")
        provider = self._provider_writing("new")

        with patch("updatable.installer_updatable.build_storage_provider", return_value=provider):
            failed = _updatable(installer)()

        assert compare("eq", failed, [])
        assert compare("eq", provider.clone_and_checkout.call_args.kwargs["branch"], "release-2026.01-dev")
        assert compare("eq", (acme / "marker").exists(), False)
        assert compare("eq", Product.from_json_file(acme / "description.json").build.commit, "new")
        assert compare("eq", [p.name for p in installer.iterdir()], ["acme"])

    def test_same_commit_keeps_folder(self, installer: Path) -> None:
        """An artifact at the installed commit leaves the folder untouched."""
        acme = installer / "acme"
        self._write_download(acme, "old")
        (acme / "marker").write_text("kept", encoding="utf-8")

        with patch(
            "updatable.installer_updatable.build_storage_provider",
            return_value=self._provider_writing("old"),
        ):
            failed = _updatable(installer)()

        assert compare("eq", failed, [])
        assert compare("eq", (acme / "marker").read_text(encoding="utf-8"), "kept")
        assert compare("eq", [p.name for p in installer.iterdir()], ["acme"])

    def test_local_build_never_needs_storage(self, installer: Path) -> None:
        """A manual build (no description.json) is kept without building a storage provider."""
        local = installer / "local"
        local.mkdir()
        (local / "description.xml").write_text('<product name="local"/>', encoding="utf-8")

        with patch("updatable.installer_updatable.build_storage_provider") as build_provider:
            failed = _updatable(installer)()

        assert compare("eq", failed, [])
        build_provider.assert_not_called()


class TestBundleInstall:
    """A bundle install moves to the latest bundle of the same major.minor."""

    def test_bundle_downloads_latest_bundle(self, installer: Path) -> None:
        """The latest bundle is downloaded and the per-product storage loop is not run."""
        bundle = {"name": "ev-basic", "version": "2025.03.0016", "versions": []}
        (installer / "bundle.json").write_text(json.dumps(bundle), encoding="utf-8")
        TestStorageArtifacts._write_download(installer / "acme", "old")  # noqa: SLF001

        with (
            patch("updatable.installer_updatable.build_configured_storage") as build_storage,
            patch(
                "updatable.installer_updatable.find_latest_bundle_name",
                return_value="ev-basic-2025.03.0017",
            ) as find_latest,
            patch("updatable.installer_updatable.BundleDownloadable") as bundle_downloadable,
            patch("updatable.installer_updatable.build_storage_provider") as build_provider,
        ):
            failed = _updatable(installer)()

        assert compare("eq", failed, [])
        build_storage.assert_called_once_with("nexus", area="bundles")
        assert compare("eq", find_latest.call_args.args[1].name, "ev-basic")
        bundle_downloadable.assert_called_once_with(
            storage_name=StorageBackendEnum.NEXUS,
            name="ev-basic-2025.03.0017",
            installer_dir=installer,
            verbose=False,
        )
        bundle_downloadable.return_value.download.assert_called_once_with(installer)
        build_provider.assert_not_called()
