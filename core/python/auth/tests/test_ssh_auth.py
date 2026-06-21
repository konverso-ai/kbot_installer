"""Tests for auth.ssh_auth module."""

from pathlib import Path

import pytest
from pydantic import SecretStr

from auth.ssh_auth import SshAuth
from utils.utils_for_unit_tests import compare


@pytest.mark.parametrize(
    "params, expected",
    [
        (
            {"private_key": SecretStr("inline-key"), "use_agent": True},
            ValueError,
        ),
    ],
)
def test_validatesource_invalid_mutually_exclusive_options(
    params: dict, expected: type[BaseException]
) -> None:
    with pytest.raises(expected):
        _ = SshAuth(**params)


def test_remotekwargs_valid_uses_forwarded_agent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SSH_AUTH_SOCK", "/tmp/fake-agent.sock")
    auth = SshAuth(use_agent=True)
    kwargs = auth.remote_kwargs()
    assert compare("eq", kwargs["username"], "git")
    assert compare("eq", kwargs["ssh_command"], "ssh -o StrictHostKeyChecking=accept-new")
    assert compare("not_in", "key_filename", kwargs)


def test_remotekwargs_valid_uses_local_key_file(tmp_path: Path) -> None:
    ssh_dir = tmp_path / "ssh"
    ssh_dir.mkdir()
    key_file = ssh_dir / "id_ed25519"
    key_file.write_text("fake-private-key")
    auth = SshAuth(ssh_directory=ssh_dir)
    kwargs = auth.remote_kwargs()
    assert compare("eq", kwargs["key_filename"], str(key_file))
    assert compare("eq", kwargs["username"], "git")


def test_remotekwargs_valid_uses_inline_private_key() -> None:
    auth = SshAuth(private_key=SecretStr("inline-private-key"))
    with auth:
        kwargs = auth.remote_kwargs()
    assert compare("in", "key_filename", kwargs)
    assert compare("eq", kwargs["username"], "git")


def test_remotekwargs_invalid_without_agent_socket(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SSH_AUTH_SOCK", raising=False)
    auth = SshAuth(use_agent=True)
    with pytest.raises(RuntimeError):
        _ = auth.remote_kwargs()


def test_remotekwargs_invalid_when_no_local_key(tmp_path: Path) -> None:
    empty_ssh_dir = tmp_path / "empty"
    empty_ssh_dir.mkdir()
    auth = SshAuth(ssh_directory=empty_ssh_dir, key_filenames=("missing_key",))
    with pytest.raises(FileNotFoundError):
        _ = auth.remote_kwargs()


def test_keypath_valid_resolves_local_key_without_remote_kwargs(tmp_path: Path) -> None:
    ssh_dir = tmp_path / "ssh"
    ssh_dir.mkdir()
    key_file = ssh_dir / "id_ed25519"
    key_file.write_text("fake-private-key")
    auth = SshAuth(ssh_directory=ssh_dir)
    assert compare("eq", auth.key_path, key_file)


def test_keypath_invalid_in_agent_mode() -> None:
    auth = SshAuth(use_agent=True)
    with pytest.raises(RuntimeError):
        _ = auth.key_path


def test_authflow_valid_yields_request_unchanged() -> None:
    import httpx

    auth = SshAuth(use_agent=True)
    request = httpx.Request("GET", "https://example.com")
    authenticated = next(auth.auth_flow(request))
    assert compare("eq", authenticated, request)


def test_gitsshcommand_valid_includes_key_file(tmp_path: Path) -> None:
    ssh_dir = tmp_path / "ssh"
    ssh_dir.mkdir()
    key_file = ssh_dir / "id_ed25519"
    key_file.write_text("fake-private-key")
    auth = SshAuth(ssh_directory=ssh_dir)
    assert compare(
        "eq",
        auth.git_ssh_command(),
        f"ssh -o StrictHostKeyChecking=accept-new -i {key_file}",
    )


def test_gitsshcommand_valid_uses_agent_without_key_file(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SSH_AUTH_SOCK", "/tmp/fake-agent.sock")
    auth = SshAuth(use_agent=True)
    assert compare(
        "eq",
        auth.git_ssh_command(),
        "ssh -o StrictHostKeyChecking=accept-new",
    )


def test_gitclienvironment_valid_sets_git_ssh_command(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    ssh_dir = tmp_path / "ssh"
    ssh_dir.mkdir()
    key_file = ssh_dir / "id_ed25519"
    key_file.write_text("fake-private-key")
    auth = SshAuth(ssh_directory=ssh_dir)
    monkeypatch.setenv("CUSTOM_MARKER", "keep-me")
    env = auth.git_cli_environment(base_env={"CUSTOM_MARKER": "keep-me"})
    assert compare("eq", env["CUSTOM_MARKER"], "keep-me")
    assert compare(
        "eq",
        env["GIT_SSH_COMMAND"],
        f"ssh -o StrictHostKeyChecking=accept-new -i {key_file}",
    )


def test_contextmanager_valid_cleans_up_temp_key() -> None:
    auth = SshAuth(private_key=SecretStr("temp-key-content"))
    with auth:
        key_path = auth.key_path
        temp_dir = key_path.parent
        assert compare("eq", key_path.exists(), True)
    assert compare("eq", key_path.exists(), False)
    assert compare("eq", temp_dir.exists(), False)
