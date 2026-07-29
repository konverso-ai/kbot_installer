"""Factory functions for creating provider instances."""

from typing import TYPE_CHECKING, cast

from auth.factory import add_auth
from auth.http.factory import add_http_auth
from auth.ssh.factory import add_ssh_auth
from credentials.bitbucket.basic_bitbucket_credentials import (
    BasicBitbucketCredentials,
)
from credentials.bitbucket.ssh_bitbucket_credentials import SshBitbucketCredentials
from credentials.github.basic_github_credentials import BasicGithubCredentials
from credentials.github.ssh_github_credentials import SshGithubCredentials
from git.provider.base import ProviderBase
from git.provider.config import DEFAULT_PROVIDERS_CONFIG, ProvidersConfig
from git.provider.errors import ProviderError
from git.versioner import add_versioner
from storage.factory import add_builtin_storage
from utils.factory import factory_function
from utils.factory.loader import factory_method
from utils.Logger import logger

if TYPE_CHECKING:
    from collections.abc import Callable

    import httpx

    from credentials.base import AuthCredentialsBase
    from git.auth_protocol import GitAuthProtocol
    from storage.base import StorageBase

log = logger.get_package_logger("git.provider")

# Providers that can be used without explicit credentials (public repositories).
_PROVIDERS_ALLOWING_ANONYMOUS_ACCESS = frozenset({"github", "bitbucket"})


def add_provider(name: str, **kwargs: object) -> ProviderBase:
    """Create a provider instance by name.

    Args:
        name: Name of the provider to create (e.g., "storage").
        **kwargs: Additional arguments to pass to the provider constructor.

    Returns:
        An instance of the specified provider.

    Raises:
        ImportError: If the provider cannot be imported.
        AttributeError: If the provider class is not found.
        TypeError: If the provider cannot be instantiated with the provided arguments.

    Example:
        >>> storage = create_provider("storage")
        >>> print(storage)
        StorageProvider()

    """
    return cast("ProviderBase", factory_method(name, "git.provider", **kwargs))


def ssh_github_provider() -> ProviderBase:
    """Create a GitHub provider authenticated via SSH."""
    credentials = SshGithubCredentials()
    auth = add_ssh_auth(name="ssh", **credentials.auth_kwargs())
    versioner = add_versioner("dulwich", auth=auth)
    return add_provider(name="github", account_name="konverso-ai", versioner=versioner)


def ssh_bitbucket_provider() -> ProviderBase:
    """Create a Bitbucket provider authenticated via SSH."""
    credentials = SshBitbucketCredentials()
    auth = add_ssh_auth(name="ssh", **credentials.auth_kwargs())
    versioner = add_versioner("dulwich", auth=auth)
    return add_provider(name="bitbucket", account_name="konversoai", versioner=versioner)


def basic_github_provider() -> ProviderBase:
    """Create a GitHub provider authenticated via HTTP basic auth."""
    credentials = BasicGithubCredentials()
    auth = add_http_auth(name="basic", **credentials.auth_kwargs())
    versioner = add_versioner("dulwich", auth=auth)
    return add_provider(name="github", account_name="konverso-ai", versioner=versioner)


def basic_bitbucket_provider() -> ProviderBase:
    """Create a Bitbucket provider authenticated via HTTP basic auth."""
    credentials = BasicBitbucketCredentials()
    auth = add_http_auth(name="basic", **credentials.auth_kwargs())
    versioner = add_versioner("dulwich", auth=auth)
    return add_provider(name="bitbucket", account_name="konversoai", versioner=versioner)


def add_transport_provider(transport: str, provider: str) -> ProviderBase:
    """Create a provider instance for a given transport and provider name.

    Dispatches to the matching helper defined in this module using the
    naming convention ``{transport}_{provider}_provider`` (e.g.
    ``ssh_github_provider``, ``basic_bitbucket_provider``).

    Args:
        transport: Authentication transport to use (e.g. "ssh", "basic").
        provider: Name of the git provider (e.g. "github", "bitbucket").

    Returns:
        An instance of the provider, authenticated via the given transport.

    Raises:
        ImportError: If the current module cannot be imported.
        AttributeError: If no ``{transport}_{provider}_provider`` function exists.

    Example:
        >>> provider = add_transport_provider("ssh", "github")
        >>> print(provider)
        GithubProvider()

    """
    builder = cast(
        "Callable[[], ProviderBase]",
        factory_function(
            module_name=__name__,
            attribute_name=f"{transport}_{provider}_provider",
        ),
    )
    return builder()


def add_storage_provider(name: str, **kwargs) -> ProviderBase:
    """Create a storage-backed provider by building the named storage backend.

    Args:
        name: Name of the storage backend to build (e.g. "s3", "azure").
        **kwargs: Additional arguments passed to the storage backend constructor.

    Returns:
        A ``StorageProvider`` wrapping the built storage backend.

    """
    storage = add_builtin_storage(name=name, **kwargs)
    return add_provider(name="storage", storage=storage)


def build_configured_storage(
    backend_name: str,
    area: str | None = None,
    config: ProvidersConfig = DEFAULT_PROVIDERS_CONFIG,
) -> "StorageBase":
    """Build a fully-wired storage for a backend and logical area.

    Sources connection settings (account URL, bucket/container/repository,
    namespace, ...) from the providers configuration and credentials from the
    environment, building the underlying backend when required. Unlike the
    low-level ``add_storage``, the returned storage is ready to use.

    Args:
        backend_name: Storage backend to build (e.g. ``"nexus"``, ``"s3"``,
            ``"azure"``, ``"oci"``).
        area: Logical area overriding the backend's configured
            container/bucket/repository (e.g. ``"bundles"`` / ``"artifacts"``).
        config: Providers configuration to read connection settings from.

    Returns:
        A ready-to-use storage instance for the requested backend.

    """
    auth = _resolve_auth("storage", config) if backend_name == "nexus" else None
    settings = getattr(config.storage, backend_name)
    return cast("StorageBase", settings.build_storage(area, cast("httpx.Auth | None", auth)))


def _has_credentials(provider_name: str, config: ProvidersConfig) -> bool:
    """Check whether all required credentials are available for a provider.

    Args:
        provider_name: Name of the provider to check credentials for.
        config: Full providers configuration.

    Returns:
        True if all required environment variables are set, False otherwise.

    """
    credentials = config.get_credentials(provider_name)
    if credentials is None:
        log.warning("Unknown provider: %s", provider_name)
        return False

    missing_vars = credentials.missing_env_vars()
    if missing_vars:
        log.debug(
            "Missing environment variables for %s: %s",
            provider_name,
            missing_vars,
        )
        return False

    return True


def _resolve_auth(
    provider_name: str,
    config: ProvidersConfig,
) -> "GitAuthProtocol | None":
    """Resolve the authentication object for a provider, if credentials allow it.

    Args:
        provider_name: Name of the provider to resolve authentication for.
        config: Full providers configuration.

    Returns:
        An authentication object, or None if credentials are unavailable/incomplete.

    """
    if not _has_credentials(provider_name, config):
        return None

    credentials = config.get_credentials(provider_name)
    provider_config = config.get_provider_config(provider_name)
    if credentials is None or not provider_config:
        return None

    auth_kwargs = cast("AuthCredentialsBase", credentials).auth_kwargs()
    if not auth_kwargs:
        return None

    try:
        return add_auth(provider_config.auth_type, **auth_kwargs)
    except ImportError as e:
        log.error(  # noqa: TRY400
            "Failed to import authentication module for auth_type '%s': %s",
            provider_config.auth_type,
            type(e).__name__,
        )
        return None
    except Exception as e:
        log.error(  # noqa: TRY400
            "Failed to create authentication object for auth_type '%s': %s",
            provider_config.auth_type,
            type(e).__name__,
        )
        return None


def _build_provider(
    provider_name: str,
    config: ProvidersConfig,
    *,
    quiet: bool = False,
) -> ProviderBase | None:
    """Build a single provider instance from configuration and available credentials.

    Args:
        provider_name: Name of the provider to build (e.g. ``"github"``).
        config: Full providers configuration.
        quiet: Currently unused for the "storage" provider (it no longer
            supports a quiet mode); kept for signature compatibility with
            :func:`add_selector_provider`.

    Returns:
        The built provider, or None if it is not configured or is missing
        required credentials.

    Raises:
        ProviderError: If the provider is configured and has credentials but
            fails to instantiate because of invalid configuration.

    """
    _ = quiet
    provider_config = config.get_provider_config(provider_name)
    if not provider_config:
        log.warning("No configuration found for provider: %s", provider_name)
        return None

    if provider_name not in _PROVIDERS_ALLOWING_ANONYMOUS_ACCESS and not _has_credentials(
        provider_name, config
    ):
        log.debug("Missing credentials for provider '%s'", provider_name)
        return None

    auth = _resolve_auth(provider_name, config)
    params = provider_config.kwargs.copy()
    if provider_name == "storage":
        # All GitAuthProtocol implementations (auth.http, auth.ssh) also
        # subclass httpx.Auth at runtime; the storage backend kwargs only
        # need the httpx.Auth-compatible surface. build_storage builds the
        # backend for non-nexus stores instead of instantiating the storage
        # class with a missing backend argument.
        storage = config.storage.build_storage(auth=cast("httpx.Auth | None", auth))
        params["storage"] = storage
        params["branches"] = provider_config.branches
    else:
        # Git providers (github, bitbucket) don't build their own Versioner:
        # it is constructed here, already configured with the resolved auth,
        # and injected into the provider.
        params["versioner"] = add_versioner("dulwich", auth=auth)

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


def add_selector_provider(
    provider_names: list[str],
    config: ProvidersConfig = DEFAULT_PROVIDERS_CONFIG,
    *,
    quiet: bool = False,
) -> ProviderBase:
    """Build a selector provider that tries each named provider in order.

    Each provider is built via :func:`_build_provider`, which resolves
    credentials/authentication and skips providers that are not configured or
    lack the required credentials, rather than failing outright.

    Args:
        provider_names: Names of providers to try, in order (e.g.
            ``["storage", "github", "bitbucket"]``).
        config: Full providers configuration used to build each provider.
            Defaults to :data:`git.provider.config.DEFAULT_PROVIDERS_CONFIG`.
        quiet: Forwarded to the resulting selector provider to suppress
            informational clone output.

    Returns:
        A ``SelectorProvider`` wrapping every provider that could be built.

    Raises:
        ProviderError: If none of the requested providers could be built
            (e.g. all are unconfigured, missing credentials, or fail to
            instantiate).

    Example:
        >>> provider = add_selector_provider(["storage", "github", "bitbucket"])
        >>> print(provider)
        SelectorProvider(providers=[...])

    """
    providers = [
        provider
        for name in provider_names
        if (provider := _build_provider(name, config, quiet=quiet)) is not None
    ]
    if not providers:
        msg = f"No provider could be built from: {provider_names}"
        raise ProviderError(msg)

    return add_provider(name="selector", providers=providers, quiet=quiet)
