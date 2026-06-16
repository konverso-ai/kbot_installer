"""Username/password login with optional access token refresh."""

from typing import Annotated, TypeAlias

import httpx
from pydantic import Field, PrivateAttr, SecretStr

from auth.auth_mixin import AuthMixin
from auth.base import RequiredSecret

Username: TypeAlias = Annotated[str, Field(min_length=1)]
Password: TypeAlias = RequiredSecret


class LoginRefreshAuth(AuthMixin):
    """Username/password login with optional access token refresh."""

    username: Username
    password: Password

    _refresh_token: str | None = PrivateAttr(default=None)

    async def _login(self, base_url: str) -> None:
        async with httpx.AsyncClient(
            base_url=base_url,
            timeout=30,
            follow_redirects=True,
        ) as client:
            response = await client.post(
                "login",
                data={
                    "username": self.username,
                    "password": self.password.get_secret_value(),
                },
            )
            response.raise_for_status()
            token = response.json()
        self.secret = SecretStr(token["access_token"])
        self._refresh_token = token.get("refresh_token")

    async def _refresh(self, client: httpx.AsyncClient) -> None:
        if not self._refresh_token:
            return

        try:
            response = await client.post(
                "refresh",
                json={"refresh_token": self._refresh_token},
            )
            response.raise_for_status()
            token = response.json()
            self.secret = SecretStr(token["access_token"])
            self._refresh_token = token.get("refresh_token")
        except httpx.HTTPStatusError:
            # If the refresh fails, the next request will fail with 401.
            pass
