"""Tests for the authenticated Dulwich versioner factory helpers."""

from pathlib import Path

import pytest
from dulwich import porcelain

from auth.http.basic_auth import BasicAuth
from auth.ssh.ssh_auth import SshAuth
from git.versioner.author import Author
from git.versioner.dulwich_versioner import DulwichVersioner
from git.versioner.factory import (
    add_basic_dulwich_versioner,
    add_dulwich_versioner_for_repository,
    add_dulwich_versioner_for_url,
    add_ssh_dulwich_versioner,
)
from utils.utils_for_unit_tests import compare

SSH_URL = "git@github.com:konverso-ai/kbot.git"
HTTPS_URL = "https://bitbucket.org/konversoai/kbot.git"


@pytest.fixture
def ssh_directory(tmp_path: Path) -> Path:
    """Create an SSH directory holding a private key."""
    path = tmp_path / "ssh"
    path.mkdir()
    (path / "id_ed25519").write_text("PRIVATE KEY")
    return path


def _auth_of(versioner: DulwichVersioner) -> object:
    """Read the auth object configured on a versioner."""
    return versioner._get_auth()  # noqa: SLF001


def test_add_basic_dulwich_versioner_valid_builds_basic_auth() -> None:
    versioner = add_basic_dulwich_versioner("john", "secret")

    assert isinstance(versioner, DulwichVersioner)
    assert isinstance(_auth_of(versioner), BasicAuth)


def test_add_basic_dulwich_versioner_invalid_without_credentials_raises() -> None:
    with pytest.raises(TypeError):
        add_basic_dulwich_versioner()  # type: ignore[call-arg]


def test_add_ssh_dulwich_versioner_valid_builds_ssh_auth(ssh_directory: Path) -> None:
    versioner = add_ssh_dulwich_versioner(ssh_directory=ssh_directory)

    assert isinstance(_auth_of(versioner), SshAuth)


def test_add_dulwich_versioner_for_url_valid_ssh_url(ssh_directory: Path) -> None:
    versioner = add_dulwich_versioner_for_url(SSH_URL, ssh_directory=ssh_directory)

    assert isinstance(_auth_of(versioner), SshAuth)


def test_add_dulwich_versioner_for_url_valid_https_url() -> None:
    versioner = add_dulwich_versioner_for_url(
        HTTPS_URL, username="john", password="secret"
    )

    assert isinstance(_auth_of(versioner), BasicAuth)


def test_add_dulwich_versioner_for_url_valid_local_path_has_no_auth(
    tmp_path: Path,
) -> None:
    versioner = add_dulwich_versioner_for_url(str(tmp_path))

    compare("eq", _auth_of(versioner), None)


def test_add_dulwich_versioner_for_url_valid_uses_given_author() -> None:
    author = Author(name="Alice", email="alice@example.com")
    versioner = add_dulwich_versioner_for_url(
        HTTPS_URL, username="john", password="secret", author=author
    )

    compare("eq", versioner._author, author)  # noqa: SLF001


def test_add_dulwich_versioner_for_repository_valid_detects_ssh_remote(
    tmp_path: Path, ssh_directory: Path
) -> None:
    path = tmp_path / "repo"
    path.mkdir()
    with porcelain.init(str(path)) as repo:
        porcelain.remote_add(repo, "origin", SSH_URL)

    versioner = add_dulwich_versioner_for_repository(path, ssh_directory=ssh_directory)

    assert isinstance(_auth_of(versioner), SshAuth)


def test_add_dulwich_versioner_for_repository_valid_detects_https_remote(
    tmp_path: Path,
) -> None:
    path = tmp_path / "repo"
    path.mkdir()
    with porcelain.init(str(path)) as repo:
        porcelain.remote_add(repo, "origin", HTTPS_URL)

    versioner = add_dulwich_versioner_for_repository(
        path, username="john", password="secret"
    )

    assert isinstance(_auth_of(versioner), BasicAuth)


def test_add_dulwich_versioner_for_repository_valid_without_remote_has_no_auth(
    tmp_path: Path,
) -> None:
    path = tmp_path / "repo"
    path.mkdir()
    porcelain.init(str(path)).close()

    versioner = add_dulwich_versioner_for_repository(path)

    compare("eq", _auth_of(versioner), None)
