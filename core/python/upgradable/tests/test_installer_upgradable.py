"""Tests for InstallerUpgradable.

Git working copies are real dulwich clones of a local ``origin`` repository,
so status/fetch/checkout/pull run the actual code path without any authentication.
"""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from dulwich import porcelain
from dulwich.repo import Repo

from downloadable.product_downloadable import ProductDownloadable
from git.versioner.dulwich_versioner import DulwichVersioner
from storage.base import StorageBackendEnum
from upgradable.errors import UpgradeError
from upgradable.installer_upgradable import InstallerUpgradable
from utils.product.build import Build
from utils.product.product import Product
from utils.utils_for_unit_tests import compare

AUTHOR = b"Tester <tester@example.com>"


def _xml(name: str, version: str, parents: tuple[str, ...] = ()) -> str:
    parents_xml = "".join(f'<parent name="{parent}"/>' for parent in parents)
    return f'<product name="{name}" version="{version}" type="solution"><parents>{parents_xml}</parents></product>'


def _commit_all(repo: Repo, message: bytes) -> bytes:
    porcelain.add(repo, paths=".")
    return porcelain.commit(repo, message=message, author=AUTHOR, committer=AUTHOR)


def _make_upstream(path: Path, branch: str, description_xml: str) -> None:
    """Create an upstream repository with an initial commit on branch."""
    path.mkdir(parents=True)
    (path / "description.xml").write_text(description_xml, encoding="utf-8")
    (path / "README").write_text("a", encoding="utf-8")
    with porcelain.init(str(path)) as repo:
        repo.refs.set_symbolic_ref(b"HEAD", b"refs/heads/" + branch.encode())
        _commit_all(repo, b"initial")


def _branch_upstream(upstream: Path, base: str, branch: str, description_xml: str) -> bytes:
    """Create branch upstream from base with a new description.xml; base is left unchanged."""
    base_ref = b"refs/heads/" + base.encode()
    with Repo(str(upstream)) as repo:
        old = repo.refs[base_ref]
        (upstream / "description.xml").write_text(description_xml, encoding="utf-8")
        commit = _commit_all(repo, b"new release")
        repo.refs[b"refs/heads/" + branch.encode()] = commit
        repo.refs[base_ref] = old
    return commit


def _clone(upstream: Path, target: Path, branch: str) -> None:
    """Clone upstream on branch, with a local branch tracking it."""
    ref = b"refs/heads/" + branch.encode()
    with porcelain.clone(str(upstream), str(target), branch=branch.encode()) as repo:
        repo.refs[ref] = repo.head()
        repo.refs.set_symbolic_ref(b"HEAD", ref)


def _head(path: Path) -> bytes:
    with Repo(str(path)) as repo:
        return repo.head()


def _write_download(path: Path, name: str, version: str = "2025.03") -> None:
    """Write a storage download: description.xml plus a description.json with build info."""
    path.mkdir(parents=True, exist_ok=True)
    product = Product(name=name, build=Build(branch=f"release-{version}-dev", commit="c0ffee"))
    (path / "description.xml").write_text(_xml(name, version), encoding="utf-8")
    (path / "description.json").write_text(json.dumps(product.to_json()), encoding="utf-8")


@pytest.fixture
def installer(tmp_path: Path) -> Path:
    """Create an empty installer directory."""
    path = tmp_path / "installer"
    path.mkdir()
    return path


def _product_upgrade(installer: Path, product: str = "demo", version: str = "2026.01") -> InstallerUpgradable:
    return InstallerUpgradable(
        installer_path=installer,
        storage_backend=StorageBackendEnum.NEXUS,
        product=product,
        version=version,
    )


class TestCheck:
    """check() reports every blocking problem and modifies nothing."""

    def test_dirty_git_copy_and_local_build_are_all_reported(self, tmp_path: Path, installer: Path) -> None:
        """A tracked modification and a manual build both cancel the upgrade; nothing is touched."""
        upstream = tmp_path / "up"
        _make_upstream(upstream, "release-2025.03-dev", _xml("demo", "2025.03"))
        _branch_upstream(upstream, "release-2025.03-dev", "release-2026.01-dev", _xml("demo", "2026.01"))
        demo = installer / "demo"
        _clone(upstream, demo, "release-2025.03-dev")
        (demo / "README").write_text("local edit", encoding="utf-8")
        head = _head(demo)
        local = installer / "local"
        local.mkdir()
        (local / "description.xml").write_text(_xml("local", "2025.03"), encoding="utf-8")

        with pytest.raises(UpgradeError) as excinfo:
            _product_upgrade(installer).check()

        message = str(excinfo.value)
        assert "demo: Uncommitted changes: README" in message
        assert "local: local build cannot be upgraded" in message
        assert compare("eq", (demo / "README").read_text(encoding="utf-8"), "local edit")
        assert compare("eq", _head(demo), head)
        assert compare("eq", DulwichVersioner().current_branch(demo), "release-2025.03-dev")

    def test_missing_release_branch_is_reported(self, tmp_path: Path, installer: Path) -> None:
        """A clean working copy whose origin lacks the release branch cancels the upgrade."""
        upstream = tmp_path / "up"
        _make_upstream(upstream, "release-2025.03-dev", _xml("demo", "2025.03"))
        _clone(upstream, installer / "demo", "release-2025.03-dev")

        with pytest.raises(UpgradeError, match=r"demo: branch 'release-2026\.01-dev' not found"):
            _product_upgrade(installer).check()

    def test_target_not_newer_is_reported(self, installer: Path) -> None:
        """Upgrading a product to its own major.minor is refused."""
        _write_download(installer / "demo", "demo", "2026.01")

        with pytest.raises(UpgradeError, match=r"'demo' is at version 2026\.01: 2026\.01 is not newer"):
            _product_upgrade(installer).check()


class TestProductUpgrade:
    """Product mode moves the product and its new dependency closure, and drops the rest."""

    def test_git_copies_move_and_products_follow_new_parents(self, tmp_path: Path, installer: Path) -> None:
        """demo moves to the release branch, its new parent is downloaded, the others are removed."""
        up_demo = tmp_path / "up_demo"
        _make_upstream(up_demo, "release-2025.03-dev", _xml("demo", "2025.03"))
        new_head = _branch_upstream(
            up_demo, "release-2025.03-dev", "release-2026.01-dev", _xml("demo", "2026.01", ("newdep",))
        )
        demo = installer / "demo"
        _clone(up_demo, demo, "release-2025.03-dev")
        up_extra = tmp_path / "up_extra"
        _make_upstream(up_extra, "release-2026.01-dev", _xml("extra", "2026.01"))
        _clone(up_extra, installer / "extra", "release-2026.01-dev")
        _write_download(installer / "old", "old")

        provider = MagicMock()
        provider.get_name.return_value = "fake"
        provider.clone_and_checkout.side_effect = lambda name, target, **_: _write_download(
            Path(target), name, "2026.01"
        )

        def _build_downloadable(**kwargs: object) -> ProductDownloadable:
            return ProductDownloadable(
                product=Product(name=str(kwargs["product"]), build=Build(branch="release-2026.01-dev")),
                provider=provider,
            )

        upgradable = _product_upgrade(installer)
        with patch(
            "upgradable.installer_upgradable.build_downloadable", side_effect=_build_downloadable
        ) as build_downloadable:
            upgradable.check()
            outcome = upgradable.apply()

        assert compare("eq", build_downloadable.call_args.kwargs["version"], "2026.01")
        assert compare("eq", DulwichVersioner().current_branch(demo), "release-2026.01-dev")
        assert compare("eq", _head(demo), new_head)
        assert compare("eq", [c.args[0] for c in provider.clone_and_checkout.call_args_list], ["newdep"])
        assert compare("eq", outcome.added, ["newdep"])
        assert compare("eq", outcome.removed, ["extra", "old"])
        assert outcome.moved_dir is not None
        assert compare("eq", (outcome.moved_dir / "extra" / ".git").is_dir(), True)
        assert compare("eq", outcome.moved_dir.name.startswith(".removed_"), True)
        assert compare("eq", (installer / "old").exists(), False)


class TestBundleUpgrade:
    """Bundle mode moves to the latest bundle of the target version and drops products outside it."""

    def test_latest_bundle_of_version_is_installed(self, installer: Path) -> None:
        """'-v 2026.01' picks the highest 2026.01 bundle; storage products outside it are deleted."""
        current = {"name": "ev-basic", "version": "2025.03.0016", "versions": []}
        bundle_json = installer / "bundle.json"
        bundle_json.write_text(json.dumps(current), encoding="utf-8")
        _write_download(installer / "gone", "gone")
        new_bundle = {
            "name": "ev-basic",
            "version": "2026.01.0003",
            "versions": [{"name": "acme", "build": {"branch": "release-2026.01-dev", "commit": "abc"}}],
        }
        storage = MagicMock()
        storage.list.side_effect = lambda _prefix: iter(
            ["ev-basic-2025.03.0016.json", "ev-basic-2026.01.0001.json", "ev-basic-2026.01.0003.json"]
        )
        storage.get.return_value = json.dumps(new_bundle)

        upgradable = InstallerUpgradable(
            installer_path=installer, storage_backend=StorageBackendEnum.NEXUS, version="2026.01"
        )
        with (
            patch("upgradable.installer_upgradable.build_configured_storage", return_value=storage),
            patch("upgradable.installer_upgradable.BundleDownloadable") as bundle_downloadable,
        ):
            bundle_downloadable.return_value.download.side_effect = lambda path: _write_download(
                path / "acme", "acme", "2026.01"
            )
            upgradable.check()
            assert compare("eq", json.loads(bundle_json.read_text(encoding="utf-8")), current)
            outcome = upgradable.apply()

        storage.get.assert_called_once_with("ev-basic-2026.01.0003.json")
        bundle_downloadable.assert_called_once_with(
            storage_name=StorageBackendEnum.NEXUS,
            name="ev-basic-2026.01.0003",
            installer_dir=installer,
            verbose=False,
        )
        assert compare("eq", outcome.added, ["acme"])
        assert compare("eq", outcome.removed, ["gone"])
        assert outcome.moved_dir is None
