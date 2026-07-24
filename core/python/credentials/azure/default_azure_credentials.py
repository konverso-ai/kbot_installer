"""Factory for Azure's default credential chain."""

from azure.identity import DefaultAzureCredential


def default_azure_credentials(**_kwargs) -> DefaultAzureCredential:
    """Return a credential using Azure's default credential chain.

    Returns:
        A ``DefaultAzureCredential`` instance, resolving credentials from the
        environment, a managed identity, the Azure CLI, or other supported
        sources, in order.

    """
    return DefaultAzureCredential()
