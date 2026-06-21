"""Base protocol for environment-backed credentials."""

from __future__ import annotations

from typing import Protocol


class CredentialsBase(Protocol):
    """Protocol for credentials loaded from the environment."""

    def missing_env_vars(self) -> list[str]:
        """Return canonical environment variable names that are absent."""

    def auth_kwargs(self) -> dict[str, str] | None:
        """Return auth constructor kwargs when credentials are complete."""


class StorageCredentialsBase(CredentialsBase, Protocol):
    """Protocol for credentials that expose storage backend kwargs."""

    def storage_kwargs(self) -> dict[str, str | None]:
        """Return credential fields for storage backend construction."""


class ClientSecretCredentialsBase(CredentialsBase, Protocol):
    """Protocol for credentials that expose Azure client-secret kwargs."""

    def client_secret_kwargs(self) -> dict[str, str | None]:
        """Return Azure client-secret fields for backend construction."""
