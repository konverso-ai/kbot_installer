"""Provider construction from configuration and credentials.

Owns the "does this provider have what it needs to be instantiated" concern,
kept separate from ``SelectorProvider`` which only cares about trying
providers in order.
"""

from git.provider.base import ProviderBase
from git.provider.config import ProvidersConfig
from git.provider.credential_manager import CredentialManager
from git.provider.errors import ProviderError
from git.provider.factory import add_provider
from utils.Logger import logger

log = logger.get_package_logger("git.provider")

# Providers that can be used without explicit credentials (public repositories).
_PROVIDERS_ALLOWING_ANONYMOUS_ACCESS = frozenset({"github", "bitbucket"})


def build_provider(
    provider_name: str,
    config: ProvidersConfig,
    credential_manager: CredentialManager,
    *,
    quiet: bool = False,
) -> ProviderBase | None:
    """Build a provider instance from configuration and available credentials.

    Args:
        provider_name: Name of the provider to build (e.g. ``"github"``).
        config: Full providers configuration.
        credential_manager: Manager used to resolve credentials/auth for the
            provider.
        quiet: Forwarded to the "storage" provider to suppress informational
            output.

    Returns:
        The built provider, or None if it is not configured or is missing
        required credentials.

    Raises:
        ProviderError: If the provider is configured and has credentials but
            fails to instantiate because of invalid configuration.

    """
    provider_config = config.get_provider_config(provider_name)
    if not provider_config:
        log.warning("No configuration found for provider: %s", provider_name)
        return None

    if (
        provider_name not in _PROVIDERS_ALLOWING_ANONYMOUS_ACCESS
        and not credential_manager.has_credentials(provider_name)
    ):
        log.debug(
            "Credentials required for provider '%s' but not available", provider_name
        )
        return None

    params = provider_config.kwargs.copy()
    if provider_name == "storage":
        params["config"] = config
        params["quiet"] = quiet

    auth = credential_manager.get_auth_for_provider(provider_name)
    if auth:
        params["auth"] = auth

    try:
        return add_provider(name=provider_name, **params)
    except ProviderError:
        log.exception("Failed to create provider '%s'", provider_name)
        return None
    except ValueError as e:
        msg = f"Failed to configure provider '{provider_name}': {e}"
        raise ProviderError(msg) from e
    except Exception:
        # Log without exposing sensitive information (e.g. credentials) from
        # a full stack trace.
        log.exception("Failed to create provider '%s'", provider_name)
        return None
