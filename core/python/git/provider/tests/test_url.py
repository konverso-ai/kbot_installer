"""Tests for git.provider.url module."""

import pytest

from auth.ssh.ssh_auth import SshAuth
from git.provider.url import build_git_url


class FakeHttpAuth:
    """Minimal stand-in for an HTTPS-style auth object (not SshAuth)."""


def test_build_https_url_with_no_auth() -> None:
    """It builds an HTTPS URL when auth is None."""
    url = build_git_url(
        name="github",
        account_name="acme",
        repository_name="repo",
        base_url="https://{name}.example.com/{account_name}/{repository_name}.git",
        ssh_host="github.example.com",
        auth=None,
    )

    assert url == "https://github.example.com/acme/repo.git"


def test_build_https_url_with_non_ssh_auth() -> None:
    """It builds an HTTPS URL when auth is not an SshAuth instance."""
    url = build_git_url(
        name="bitbucket",
        account_name="acme",
        repository_name="repo",
        base_url="https://{name}.example.com/{account_name}/{repository_name}.git",
        ssh_host="bitbucket.example.com",
        auth=FakeHttpAuth(),
    )

    assert url == "https://bitbucket.example.com/acme/repo.git"


def test_build_ssh_url_with_ssh_auth() -> None:
    """It builds an SSH URL when auth is an SshAuth instance."""
    url = build_git_url(
        name="github",
        account_name="acme",
        repository_name="repo",
        base_url="https://{name}.example.com/{account_name}/{repository_name}.git",
        ssh_host="github.example.com",
        auth=SshAuth(),
    )

    assert url == "git@github.example.com:acme/repo.git"


def test_build_ssh_url_ignores_missing_base_url() -> None:
    """It does not require base_url when authenticating over SSH."""
    url = build_git_url(
        name="github",
        account_name="acme",
        repository_name="repo",
        base_url="",
        ssh_host="github.example.com",
        auth=SshAuth(),
    )

    assert url == "git@github.example.com:acme/repo.git"


def test_missing_account_name_raises_value_error() -> None:
    """It raises ValueError when account_name is empty, regardless of auth."""
    with pytest.raises(ValueError, match="account_name is required"):
        build_git_url(
            name="github",
            account_name="",
            repository_name="repo",
            base_url="https://{name}.example.com/{account_name}/{repository_name}.git",
            ssh_host="github.example.com",
            auth=None,
        )


def test_missing_account_name_raises_before_checking_auth() -> None:
    """It raises ValueError for empty account_name even with SSH auth."""
    with pytest.raises(ValueError, match="account_name is required"):
        build_git_url(
            name="github",
            account_name="",
            repository_name="repo",
            base_url="",
            ssh_host="github.example.com",
            auth=SshAuth(),
        )


def test_missing_base_url_raises_value_error_for_https() -> None:
    """It raises ValueError when base_url is empty and not using SSH auth."""
    with pytest.raises(ValueError, match="base_url is required"):
        build_git_url(
            name="github",
            account_name="acme",
            repository_name="repo",
            base_url="",
            ssh_host="github.example.com",
            auth=None,
        )


def test_build_https_url_uses_all_placeholders() -> None:
    """It substitutes name, account_name and repository_name in base_url."""
    url = build_git_url(
        name="myprovider",
        account_name="myaccount",
        repository_name="myrepo",
        base_url="https://{name}.example.com/{account_name}/{repository_name}",
        ssh_host="ignored.example.com",
        auth=None,
    )

    assert url == "https://myprovider.example.com/myaccount/myrepo"
