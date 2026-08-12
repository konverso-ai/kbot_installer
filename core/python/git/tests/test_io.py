"""Tests for git.io module."""

from pathlib import Path

from git.io import write_repository
from git.models import GitProtocol, GitProvider, GitRepo, RepoType
from utils.product import Product
from utils.utils_for_unit_tests import compare


class _SettingsStub:
    """Minimal settings object for repository export."""

    def to_conf(self) -> str:
        return "key=value"

    def to_json(self) -> str:
        return "{}"


def test_writerepository_valid_writes_exported_files(tmp_path: Path) -> None:
    repo = GitRepo(
        name="jira",
        protocol=GitProtocol.HTTPS,
        provider=GitProvider.GITHUB,
        type=RepoType.SITE,
        product=Product.from_dict({"name": "jira", "version": "1.0.0"}),
        settings=_SettingsStub(),
    )

    write_repository(repo, tmp_path)

    assert compare("eq", (tmp_path / "description.xml").exists(), True)
    assert compare("eq", (tmp_path / "pyproject.toml").exists(), True)
    assert compare("eq", (tmp_path / "conf" / "kbot.conf").exists(), True)
    assert compare("eq", (tmp_path / "conf" / "kbot.json").exists(), True)
