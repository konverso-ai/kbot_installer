"""Tests for auth.login_refresh_auth module."""

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from pydantic import SecretStr, ValidationError

from auth.login_refresh_auth import LoginRefreshAuth
from utils.utils_for_unit_tests import compare


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "login_response, expected_secret, expected_refresh",
    [
        (
            {"access_token": "access-token", "refresh_token": "refresh-token"},
            "access-token",
            "refresh-token",
        ),
        (
            {"access_token": "access-only"},
            "access-only",
            None,
        ),
    ],
)
async def test_login_valid_stores_tokens(
    login_response: dict[str, str],
    expected_secret: str,
    expected_refresh: str | None,
) -> None:
    """Login should persist access and optional refresh tokens."""
    auth = LoginRefreshAuth(username="user", password=SecretStr("pass"))
    mock_response = MagicMock()
    mock_response.json.return_value = login_response
    mock_response.raise_for_status = MagicMock()
    mock_client = AsyncMock()
    mock_client.post = AsyncMock(return_value=mock_response)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)

    with patch("auth.login_refresh_auth.httpx.AsyncClient", return_value=mock_client):
        await auth._login("https://auth.example.com")

    assert compare("eq", auth.secret.get_secret_value(), expected_secret)
    assert compare("eq", auth._refresh_token, expected_refresh)


@pytest.mark.asyncio
async def test_refresh_valid_updates_access_token() -> None:
    """Refresh should replace the access token when a refresh token exists."""
    auth = LoginRefreshAuth(username="user", password=SecretStr("pass"))
    auth.secret = SecretStr("old-access")
    auth._refresh_token = "refresh-token"
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "access_token": "new-access",
        "refresh_token": "new-refresh",
    }
    mock_response.raise_for_status = MagicMock()
    mock_client = AsyncMock()
    mock_client.post = AsyncMock(return_value=mock_response)

    await auth._refresh(mock_client)

    assert compare("eq", auth.secret.get_secret_value(), "new-access")
    assert compare("eq", auth._refresh_token, "new-refresh")


@pytest.mark.asyncio
async def test_refresh_valid_skips_without_refresh_token() -> None:
    """Refresh should be a no-op when no refresh token was stored."""
    auth = LoginRefreshAuth(username="user", password=SecretStr("pass"))
    auth.secret = SecretStr("unchanged")
    mock_client = AsyncMock()

    await auth._refresh(mock_client)

    assert compare("eq", auth.secret.get_secret_value(), "unchanged")
    assert compare("eq", mock_client.post.called, False)


@pytest.mark.asyncio
async def test_refresh_valid_ignores_http_errors() -> None:
    """Failed refresh should leave tokens unchanged."""
    auth = LoginRefreshAuth(username="user", password=SecretStr("pass"))
    auth.secret = SecretStr("old-access")
    auth._refresh_token = "refresh-token"
    mock_response = MagicMock()
    mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
        "unauthorized",
        request=httpx.Request("POST", "https://auth.example.com/refresh"),
        response=httpx.Response(401),
    )
    mock_client = AsyncMock()
    mock_client.post = AsyncMock(return_value=mock_response)

    await auth._refresh(mock_client)

    assert compare("eq", auth.secret.get_secret_value(), "old-access")
    assert compare("eq", auth._refresh_token, "refresh-token")


@pytest.mark.parametrize(
    "params, expected",
    [
        ({"username": "", "password": SecretStr("pass")}, ValidationError),
        ({"username": "user"}, ValidationError),
    ],
)
def test_loginrefreshauth_invalid_rejects_bad_input(
    params: dict, expected: type[BaseException]
) -> None:
    with pytest.raises(expected):
        _ = LoginRefreshAuth(**params)
