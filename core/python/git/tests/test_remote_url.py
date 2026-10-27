"""Tests for git remote URL transport detection."""

import pytest

from git.remote_url import RemoteScheme, detect_remote_scheme
from utils.utils_for_unit_tests import compare


@pytest.mark.parametrize(
    "url",
    [
        "git@github.com:konverso-ai/kbot.git",
        "git@bitbucket.org:konversoai/kbot_installer.git",
        "github.com:konverso-ai/kbot.git",
        "ssh://git@github.com/konverso-ai/kbot.git",
        "ssh://git@altssh.bitbucket.org:443/konversoai/kbot.git",
        "git+ssh://git@github.com/konverso-ai/kbot.git",
    ],
)
def test_detect_remote_scheme_valid_ssh(url: str) -> None:
    compare("eq", detect_remote_scheme(url), RemoteScheme.SSH)


@pytest.mark.parametrize(
    "url",
    [
        "https://bitbucket.org/konversoai/kbot.git",
        "http://internal.example.com/git/kbot.git",
        "https://user@bitbucket.org/konversoai/kbot.git",
        "HTTPS://bitbucket.org/konversoai/kbot.git",
    ],
)
def test_detect_remote_scheme_valid_http(url: str) -> None:
    compare("eq", detect_remote_scheme(url), RemoteScheme.HTTP)


@pytest.mark.parametrize(
    "url",
    [
        "/home/konverso/dev/git/kbot",
        "./relative/repo",
        "~/dev/git/kbot",
        "file:///home/konverso/dev/git/kbot",
    ],
)
def test_detect_remote_scheme_valid_local(url: str) -> None:
    compare("eq", detect_remote_scheme(url), RemoteScheme.LOCAL)


def test_detect_remote_scheme_valid_anonymous() -> None:
    compare("eq", detect_remote_scheme("git://github.com/x/y.git"), RemoteScheme.ANONYMOUS)


def test_detect_remote_scheme_valid_strips_surrounding_whitespace() -> None:
    compare(
        "eq",
        detect_remote_scheme("  git@github.com:konverso-ai/kbot.git\n"),
        RemoteScheme.SSH,
    )


def test_detect_remote_scheme_invalid_empty_url_raises() -> None:
    with pytest.raises(ValueError, match="empty remote URL"):
        detect_remote_scheme("   ")


def test_detect_remote_scheme_invalid_unknown_scheme_raises() -> None:
    with pytest.raises(ValueError, match="Unsupported git remote scheme 'ftp'"):
        detect_remote_scheme("ftp://example.com/repo.git")


def test_needs_auth_valid_only_for_ssh_and_http() -> None:
    compare("eq", RemoteScheme.SSH.needs_auth, True)
    compare("eq", RemoteScheme.HTTP.needs_auth, True)
    compare("eq", RemoteScheme.LOCAL.needs_auth, False)
    compare("eq", RemoteScheme.ANONYMOUS.needs_auth, False)
