"""Tests for auth.ssh.base module."""

import httpx
import pytest

from auth.ssh.base import SshAuthBase
from utils.utils_for_unit_tests import compare


class _ConcreteSshAuth(SshAuthBase):
    def remote_kwargs(self):
        return {"username": "git"}


def test_authflow_valid_yields_request_unchanged() -> None:
    auth = _ConcreteSshAuth()
    request = httpx.Request("GET", "https://example.com")
    authenticated = next(auth.auth_flow(request))
    assert compare("eq", authenticated, request)


def test_gitclienvironment_valid_defaults_to_none() -> None:
    auth = _ConcreteSshAuth()
    assert compare("eq", auth.git_cli_environment(), None)


def test_sshauthbase_invalid_cannot_instantiate_without_implementations() -> None:
    with pytest.raises(TypeError):
        _ = SshAuthBase()
