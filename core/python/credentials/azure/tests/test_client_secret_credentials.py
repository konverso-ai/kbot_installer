"""Tests for credentials.azure.client_secret_credentials module."""

from unittest.mock import MagicMock, patch

import pytest
from azure.identity import ClientSecretCredential

from credentials.azure.client_secret_credentials import client_secret_credentials


@patch("credentials.azure.client_secret_credentials.ClientSecretCredential")
def test_client_secret_credentials_valid_constructs_credential(
    mock_credential_cls: MagicMock,
) -> None:
    """client_secret_credentials should build a ClientSecretCredential from its args."""
    mock_instance = MagicMock(spec=ClientSecretCredential)
    mock_credential_cls.return_value = mock_instance

    result = client_secret_credentials(
        tenant_id="tenant",
        client_id="client",
        client_secret="secret",
    )

    mock_credential_cls.assert_called_once_with("tenant", "client", "secret")
    assert result is mock_instance


@pytest.mark.parametrize(
    "tenant_id, client_id, client_secret",
    [
        (None, "client", "secret"),
        ("tenant", None, "secret"),
        ("tenant", "client", None),
        ("", "", ""),
    ],
)
def test_client_secret_credentials_invalid_raises_value_error(
    tenant_id: str | None,
    client_id: str | None,
    client_secret: str | None,
) -> None:
    """client_secret_credentials should raise ValueError when any value is missing."""
    with pytest.raises(ValueError, match="tenant_id, client_id, and client_secret"):
        client_secret_credentials(tenant_id, client_id, client_secret)
