"""Factory for Azure service-principal (client-secret) credentials."""

from azure.identity import ClientSecretCredential


def client_secret_credentials(
    tenant_id: str | None,
    client_id: str | None,
    client_secret: str | None,
) -> ClientSecretCredential:
    """Return a credential authenticating as an Azure AD service principal.

    Args:
        tenant_id: Azure AD tenant ID.
        client_id: Azure AD application (client) ID.
        client_secret: Azure AD application client secret.

    Returns:
        A ``ClientSecretCredential`` instance built from the given values.

    Raises:
        ValueError: If ``tenant_id``, ``client_id``, or ``client_secret`` is
            missing.

    """
    if not tenant_id or not client_id or not client_secret:
        msg = "tenant_id, client_id, and client_secret are required for client_secret credential"
        raise ValueError(msg)
    return ClientSecretCredential(tenant_id, client_id, client_secret)
