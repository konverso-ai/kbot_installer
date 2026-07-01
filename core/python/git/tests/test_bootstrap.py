"""Tests for git.bootstrap module."""

from pathlib import Path
from unittest.mock import MagicMock

from git.bootstrap import bootstrap_repository
from git.models import GitProtocol, GitProvider, GitRepo, RepoType
from utils.product import Product
from utils.utils_for_unit_tests import compare
from utils.version import Version


class _SettingsStub:
    """Minimal settings object for repository export."""

    def to_conf(self) -> str:
        return "key=value"

    def to_json(self) -> str:
        return "{}"


def test_bootstraprepository_valid_bootstraps_all_versions(tmp_path: Path) -> None:
    repo = GitRepo(
        name="jira",
        protocol=GitProtocol.HTTPS,
        provider=GitProvider.GITHUB,
        type=RepoType.SITE,
        product=Product.from_dict({"name": "jira", "version": "1.0.0"}),
        settings=_SettingsStub(),
    )
    versioner = MagicMock()
    versions = [Version.parse("2025.01"), Version.parse("2025.02")]

    bootstrap_repository(repo, versioner, tmp_path, versions)

    assert compare("eq", versioner.checkout.call_count, 2)
    assert compare("eq", versioner.add.call_count, 2)
    assert compare("eq", versioner.commit.call_count, 2)
    pushed_branches = versioner.push_branches.call_args.args[1]
    assert compare("eq", pushed_branches, ["release-2025.1-dev", "release-2025.2-dev"])
