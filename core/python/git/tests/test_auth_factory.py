"""Tests for URL-driven git authentication selection."""

from pathlib import Path

import pytest

from auth.http.basic_auth import BasicAuth
from auth.ssh.ssh_auth import SshAuth
from git.auth_factory import add_auth_for_scheme, add_auth_for_url
from git.remote_url import RemoteScheme
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


def test_add_auth_for_url_valid_ssh_remote_builds_ssh_auth(ssh_directory: Path) -> None:
    auth = add_auth_for_url(SSH_URL, ssh_directory=ssh_directory)

    assert isinstance(auth, SshAuth)
    kwargs = auth.remote_kwargs()
    compare("eq", kwargs["username"], "git")
    compare("eq", kwargs["key_filename"], str(ssh_directory / "id_ed25519"))


def test_add_auth_for_url_valid_ssh_remote_ignores_http_credentials(
    ssh_directory: Path,
) -> None:
    """HTTP credentials must not turn an SSH remote into a basic-auth remote."""
    auth = add_auth_for_url(
        SSH_URL, username="john", password="secret", ssh_directory=ssh_directory
    )

    assert isinstance(auth, SshAuth)


def test_add_auth_for_url_valid_https_remote_builds_basic_auth() -> None:
    auth = add_auth_for_url(HTTPS_URL, username="john", password="secret")

    assert isinstance(auth, BasicAuth)
    compare(
        "eq",
        auth.remote_kwargs(),
        {"username": "john", "password": "secret"},
    )


def test_add_auth_for_url_valid_local_path_needs_no_auth(tmp_path: Path) -> None:
    compare("eq", add_auth_for_url(str(tmp_path)), None)


def test_add_auth_for_url_valid_anonymous_remote_needs_no_auth() -> None:
    compare("eq", add_auth_for_url("git://github.com/x/y.git"), None)


def test_add_auth_for_url_invalid_https_without_credentials_raises() -> None:
    with pytest.raises(ValueError, match="requires both a username and a password"):
        add_auth_for_url(HTTPS_URL)


def test_add_auth_for_url_invalid_https_without_password_raises() -> None:
    with pytest.raises(ValueError, match="requires both a username and a password"):
        add_auth_for_url(HTTPS_URL, username="john")


def test_add_auth_for_scheme_valid_ssh_agent_mode() -> None:
    auth = add_auth_for_scheme(RemoteScheme.SSH, use_agent=True)

    assert isinstance(auth, SshAuth)
    compare("eq", auth.use_agent, True)


def test_add_auth_for_scheme_valid_local_returns_none() -> None:
    compare("eq", add_auth_for_scheme(RemoteScheme.LOCAL), None)


def test_add_auth_for_url_valid_falls_back_to_agent_without_key(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """With an agent available and no key on disk, use the agent like git does."""
    monkeypatch.setenv("SSH_AUTH_SOCK", "/tmp/agent.sock")
    empty = tmp_path / "empty-ssh"
    empty.mkdir()

    auth = add_auth_for_url(SSH_URL, ssh_directory=empty)

    assert isinstance(auth, SshAuth)
    compare("eq", auth.use_agent, True)


def test_add_auth_for_url_valid_prefers_key_over_agent(
    ssh_directory: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("SSH_AUTH_SOCK", "/tmp/agent.sock")

    auth = add_auth_for_url(SSH_URL, ssh_directory=ssh_directory)

    assert isinstance(auth, SshAuth)
    compare("eq", auth.use_agent, False)


def test_add_auth_for_url_valid_without_agent_keeps_key_lookup(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("SSH_AUTH_SOCK", raising=False)
    empty = tmp_path / "empty-ssh"
    empty.mkdir()

    auth = add_auth_for_url(SSH_URL, ssh_directory=empty)

    assert isinstance(auth, SshAuth)
    compare("eq", auth.use_agent, False)


def test_add_auth_for_scheme_valid_explicit_use_agent_wins(
    ssh_directory: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("SSH_AUTH_SOCK", "/tmp/agent.sock")

    auth = add_auth_for_scheme(
        RemoteScheme.SSH, use_agent=False, ssh_directory=ssh_directory
    )

    assert isinstance(auth, SshAuth)
    compare("eq", auth.use_agent, False)
