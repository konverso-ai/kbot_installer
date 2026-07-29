"""Tests for factory module."""

from unittest.mock import ANY, MagicMock, call, patch

import pytest

from git.provider.base import ProviderBase
from git.provider.errors import ProviderError
from git.provider.factory import (
    _build_provider,
    _resolve_auth,
    add_provider,
    add_selector_provider,
    add_storage_provider,
    add_transport_provider,
    basic_bitbucket_provider,
    basic_github_provider,
    build_configured_storage,
    ssh_bitbucket_provider,
    ssh_github_provider,
)


class TestCreateProvider:
    """Test cases for add_provider function."""

    def test_add_provider_storage(self) -> None:
        """Test creating storage provider."""
        with patch("git.provider.factory.factory_method") as mock_factory_method:
            mock_provider = MagicMock(spec=ProviderBase)
            mock_factory_method.return_value = mock_provider

            result = add_provider("storage")

            mock_factory_method.assert_called_once_with(
                "storage",
                "git.provider",
            )
            assert result is mock_provider

    def test_add_provider_github(self) -> None:
        """Test creating github provider."""
        with patch(
            "git.provider.factory.factory_method"
        ) as mock_factory:
            mock_provider = MagicMock(spec=ProviderBase)
            mock_factory.return_value = mock_provider

            result = add_provider("github", account_name="test")

            mock_factory.assert_called_once_with(
                "github", "git.provider", account_name="test"
            )
            assert result is mock_provider

    def test_add_provider_bitbucket(self) -> None:
        """Test creating bitbucket provider."""
        with patch(
            "git.provider.factory.factory_method"
        ) as mock_factory:
            mock_provider = MagicMock(spec=ProviderBase)
            mock_factory.return_value = mock_provider

            result = add_provider("bitbucket", account_name="test")

            mock_factory.assert_called_once_with(
                "bitbucket", "git.provider", account_name="test"
            )
            assert result is mock_provider

    def test_add_provider_handles_import_error(self) -> None:
        """Test that add_provider handles ImportError."""
        with patch(
            "git.provider.factory.factory_method"
        ) as mock_factory:
            mock_factory.side_effect = ImportError("Module not found")

            with pytest.raises(ImportError, match="Module not found"):
                add_provider("unknown", test="value")

    def test_add_provider_handles_attribute_error(self) -> None:
        """Test that add_provider handles AttributeError."""
        with patch(
            "git.provider.factory.factory_method"
        ) as mock_factory:
            mock_factory.side_effect = AttributeError("Class not found")

            with pytest.raises(AttributeError, match="Class not found"):
                add_provider("unknown", test="value")

    def test_add_provider_handles_type_error(self) -> None:
        """Test that add_provider handles TypeError."""
        with patch(
            "git.provider.factory.factory_method"
        ) as mock_factory:
            mock_factory.side_effect = TypeError("Invalid arguments")

            with pytest.raises(TypeError, match="Invalid arguments"):
                add_provider("unknown", test="value")

    def test_add_provider_with_no_kwargs(self) -> None:
        """Test creating provider with no additional arguments."""
        with patch(
            "git.provider.factory.factory_method"
        ) as mock_factory:
            mock_provider = MagicMock(spec=ProviderBase)
            mock_factory.return_value = mock_provider

            result = add_provider("storage")

            mock_factory.assert_called_once_with(
                "storage", "git.provider"
            )
            assert result is mock_provider


class TestSshGithubProvider:
    """Test cases for ssh_github_provider function."""

    def test_builds_provider_with_ssh_auth(self) -> None:
        """Test that it builds a github provider using SSH credentials/auth."""
        mock_credentials = MagicMock()
        mock_credentials.auth_kwargs.return_value = {"key": "value"}
        mock_auth = MagicMock()
        mock_versioner = MagicMock()
        mock_provider = MagicMock(spec=ProviderBase)

        with (
            patch(
                "git.provider.factory.SshGithubCredentials",
                return_value=mock_credentials,
            ),
            patch(
                "git.provider.factory.add_ssh_auth", return_value=mock_auth
            ) as mock_add_ssh_auth,
            patch(
                "git.provider.factory.add_versioner", return_value=mock_versioner
            ) as mock_add_versioner,
            patch(
                "git.provider.factory.add_provider", return_value=mock_provider
            ) as mock_add_provider,
        ):
            result = ssh_github_provider()

            mock_credentials.auth_kwargs.assert_called_once_with()
            mock_add_ssh_auth.assert_called_once_with(name="ssh", key="value")
            mock_add_versioner.assert_called_once_with("dulwich", auth=mock_auth)
            mock_add_provider.assert_called_once_with(
                name="github", account_name="konverso-ai", versioner=mock_versioner
            )
            assert result is mock_provider


class TestSshBitbucketProvider:
    """Test cases for ssh_bitbucket_provider function."""

    def test_builds_provider_with_ssh_auth(self) -> None:
        """Test that it builds a bitbucket provider using SSH credentials/auth."""
        mock_credentials = MagicMock()
        mock_credentials.auth_kwargs.return_value = {"key": "value"}
        mock_auth = MagicMock()
        mock_versioner = MagicMock()
        mock_provider = MagicMock(spec=ProviderBase)

        with (
            patch(
                "git.provider.factory.SshBitbucketCredentials",
                return_value=mock_credentials,
            ),
            patch(
                "git.provider.factory.add_ssh_auth", return_value=mock_auth
            ) as mock_add_ssh_auth,
            patch(
                "git.provider.factory.add_versioner", return_value=mock_versioner
            ) as mock_add_versioner,
            patch(
                "git.provider.factory.add_provider", return_value=mock_provider
            ) as mock_add_provider,
        ):
            result = ssh_bitbucket_provider()

            mock_credentials.auth_kwargs.assert_called_once_with()
            mock_add_ssh_auth.assert_called_once_with(name="ssh", key="value")
            mock_add_versioner.assert_called_once_with("dulwich", auth=mock_auth)
            mock_add_provider.assert_called_once_with(
                name="bitbucket", account_name="konversoai", versioner=mock_versioner
            )
            assert result is mock_provider


class TestBasicGithubProvider:
    """Test cases for basic_github_provider function."""

    def test_builds_provider_with_basic_auth(self) -> None:
        """Test that it builds a github provider using basic credentials/auth."""
        mock_credentials = MagicMock()
        mock_credentials.auth_kwargs.return_value = {"key": "value"}
        mock_auth = MagicMock()
        mock_versioner = MagicMock()
        mock_provider = MagicMock(spec=ProviderBase)

        with (
            patch(
                "git.provider.factory.BasicGithubCredentials",
                return_value=mock_credentials,
            ),
            patch(
                "git.provider.factory.add_http_auth", return_value=mock_auth
            ) as mock_add_http_auth,
            patch(
                "git.provider.factory.add_versioner", return_value=mock_versioner
            ) as mock_add_versioner,
            patch(
                "git.provider.factory.add_provider", return_value=mock_provider
            ) as mock_add_provider,
        ):
            result = basic_github_provider()

            mock_credentials.auth_kwargs.assert_called_once_with()
            mock_add_http_auth.assert_called_once_with(name="basic", key="value")
            mock_add_versioner.assert_called_once_with("dulwich", auth=mock_auth)
            mock_add_provider.assert_called_once_with(
                name="github", account_name="konverso-ai", versioner=mock_versioner
            )
            assert result is mock_provider


class TestBasicBitbucketProvider:
    """Test cases for basic_bitbucket_provider function."""

    def test_builds_provider_with_basic_auth(self) -> None:
        """Test that it builds a bitbucket provider using basic credentials/auth."""
        mock_credentials = MagicMock()
        mock_credentials.auth_kwargs.return_value = {"key": "value"}
        mock_auth = MagicMock()
        mock_versioner = MagicMock()
        mock_provider = MagicMock(spec=ProviderBase)

        with (
            patch(
                "git.provider.factory.BasicBitbucketCredentials",
                return_value=mock_credentials,
            ),
            patch(
                "git.provider.factory.add_http_auth", return_value=mock_auth
            ) as mock_add_http_auth,
            patch(
                "git.provider.factory.add_versioner", return_value=mock_versioner
            ) as mock_add_versioner,
            patch(
                "git.provider.factory.add_provider", return_value=mock_provider
            ) as mock_add_provider,
        ):
            result = basic_bitbucket_provider()

            mock_credentials.auth_kwargs.assert_called_once_with()
            mock_add_http_auth.assert_called_once_with(name="basic", key="value")
            mock_add_versioner.assert_called_once_with("dulwich", auth=mock_auth)
            mock_add_provider.assert_called_once_with(
                name="bitbucket", account_name="konversoai", versioner=mock_versioner
            )
            assert result is mock_provider


class TestAddTransportProvider:
    """Test cases for add_transport_provider function."""

    def test_dispatches_to_matching_builder(self) -> None:
        """Test that it resolves and calls the {transport}_{provider}_provider function."""
        mock_provider = MagicMock(spec=ProviderBase)
        mock_builder = MagicMock(return_value=mock_provider)

        with patch(
            "git.provider.factory.factory_function", return_value=mock_builder
        ) as mock_factory_function:
            result = add_transport_provider("ssh", "github")

            mock_factory_function.assert_called_once_with(
                module_name="git.provider.factory",
                attribute_name="ssh_github_provider",
            )
            mock_builder.assert_called_once_with()
            assert result is mock_provider

    def test_propagates_attribute_error_when_builder_missing(self) -> None:
        """Test that it propagates AttributeError when no matching builder exists."""
        with patch(
            "git.provider.factory.factory_function",
            side_effect=AttributeError("No such attribute"),
        ):
            with pytest.raises(AttributeError, match="No such attribute"):
                add_transport_provider("unknown", "unknown")


class TestAddStorageProvider:
    """Test cases for add_storage_provider function."""

    def test_builds_storage_backend_and_wraps_in_provider(self) -> None:
        """Test that it builds the named storage backend and wraps it in a StorageProvider."""
        mock_storage = MagicMock()
        mock_provider = MagicMock(spec=ProviderBase)

        with (
            patch(
                "git.provider.factory.add_builtin_storage", return_value=mock_storage
            ) as mock_add_builtin_storage,
            patch(
                "git.provider.factory.add_provider", return_value=mock_provider
            ) as mock_add_provider,
        ):
            result = add_storage_provider("s3", bucket_name="test")

            mock_add_builtin_storage.assert_called_once_with(name="s3", bucket_name="test")
            mock_add_provider.assert_called_once_with(name="storage", storage=mock_storage)
            assert result is mock_provider


class TestBuildConfiguredStorage:
    """Test cases for build_configured_storage function."""

    def test_delegates_to_backend_settings_with_area(self) -> None:
        """It resolves the backend settings and forwards the area."""
        mock_storage = MagicMock()
        settings = MagicMock()
        settings.build_storage.return_value = mock_storage
        config = MagicMock()
        config.storage.azure = settings

        result = build_configured_storage("azure", area="bundles", config=config)

        settings.build_storage.assert_called_once_with("bundles", None)
        assert result is mock_storage

    def test_resolves_auth_only_for_nexus(self) -> None:
        """Auth is resolved and forwarded for nexus, and skipped for others."""
        mock_auth = MagicMock()
        settings = MagicMock()
        config = MagicMock()
        config.storage.nexus = settings

        with patch(
            "git.provider.factory._resolve_auth", return_value=mock_auth
        ) as mock_resolve_auth:
            build_configured_storage("nexus", area="artifacts", config=config)

        mock_resolve_auth.assert_called_once_with("storage", config)
        settings.build_storage.assert_called_once_with("artifacts", mock_auth)

    def test_does_not_resolve_auth_for_non_nexus(self) -> None:
        """Non-nexus backends must not attempt to resolve nexus auth."""
        settings = MagicMock()
        config = MagicMock()
        config.storage.s3 = settings

        with patch("git.provider.factory._resolve_auth") as mock_resolve_auth:
            build_configured_storage("s3", area="bundles", config=config)

        mock_resolve_auth.assert_not_called()
        settings.build_storage.assert_called_once_with("bundles", None)


class TestResolveAuth:
    """Test cases for _resolve_auth function."""

    def test_returns_none_when_no_credentials(self) -> None:
        """Test that None is returned when the provider has no credentials."""
        config = MagicMock()
        config.get_credentials.return_value = None

        assert _resolve_auth("storage", config) is None

    def test_returns_none_when_env_vars_missing(self) -> None:
        """Test that None is returned when required env vars are missing."""
        config = MagicMock()
        credentials = MagicMock()
        credentials.missing_env_vars.return_value = ["NEXUS_USERNAME"]
        config.get_credentials.return_value = credentials

        assert _resolve_auth("storage", config) is None

    def test_returns_none_when_provider_not_configured(self) -> None:
        """Test that None is returned when there is no provider config."""
        config = MagicMock()
        credentials = MagicMock()
        credentials.missing_env_vars.return_value = []
        config.get_credentials.return_value = credentials
        config.get_provider_config.return_value = None

        assert _resolve_auth("storage", config) is None

    def test_returns_none_when_no_auth_kwargs(self) -> None:
        """Test that None is returned when auth_kwargs is empty."""
        config = MagicMock()
        credentials = MagicMock()
        credentials.missing_env_vars.return_value = []
        credentials.auth_kwargs.return_value = {}
        config.get_credentials.return_value = credentials

        assert _resolve_auth("storage", config) is None

    def test_returns_auth_object_on_success(self) -> None:
        """Test that add_auth is called and its result returned."""
        config = MagicMock()
        credentials = MagicMock()
        credentials.missing_env_vars.return_value = []
        credentials.auth_kwargs.return_value = {"username": "u", "password": "p"}
        config.get_credentials.return_value = credentials
        config.get_provider_config.return_value = MagicMock(auth_type="basic")
        mock_auth = MagicMock()

        with patch(
            "git.provider.factory.add_auth", return_value=mock_auth
        ) as mock_add_auth:
            result = _resolve_auth("storage", config)

            mock_add_auth.assert_called_once_with(
                "basic", username="u", password="p"
            )
            assert result is mock_auth

    def test_returns_none_on_import_error(self) -> None:
        """Test that ImportError from add_auth is swallowed as None."""
        config = MagicMock()
        credentials = MagicMock()
        credentials.missing_env_vars.return_value = []
        credentials.auth_kwargs.return_value = {"username": "u"}
        config.get_credentials.return_value = credentials
        config.get_provider_config.return_value = MagicMock(auth_type="basic")

        with patch(
            "git.provider.factory.add_auth",
            side_effect=ImportError("Module not found"),
        ):
            assert _resolve_auth("storage", config) is None

    def test_returns_none_on_generic_exception(self) -> None:
        """Test that a generic exception from add_auth is swallowed as None."""
        config = MagicMock()
        credentials = MagicMock()
        credentials.missing_env_vars.return_value = []
        credentials.auth_kwargs.return_value = {"username": "u"}
        config.get_credentials.return_value = credentials
        config.get_provider_config.return_value = MagicMock(auth_type="basic")

        with patch(
            "git.provider.factory.add_auth",
            side_effect=RuntimeError("boom"),
        ):
            assert _resolve_auth("storage", config) is None


class TestBuildProvider:
    """Test cases for _build_provider function."""

    def _config_with(self, **provider_config: MagicMock) -> MagicMock:
        """Build a minimal config mock exposing ``get_provider_config``."""
        config = MagicMock()
        config.get_provider_config.side_effect = provider_config.get
        return config

    def test_returns_none_when_provider_not_configured(self) -> None:
        """Test that an unconfigured provider name returns None."""
        config = self._config_with()

        assert _build_provider("unknown", config) is None

    def test_returns_none_when_credentials_missing(self) -> None:
        """Test that a provider requiring credentials returns None without them."""
        provider_config = MagicMock(kwargs={})
        config = self._config_with(storage=provider_config)

        with patch("git.provider.factory._has_credentials", return_value=False):
            assert _build_provider("storage", config) is None

    def test_github_and_bitbucket_allow_anonymous_access(self) -> None:
        """Test that github/bitbucket can be built even without credentials."""
        provider_config = MagicMock(kwargs={"account_name": "konverso-ai"})
        config = self._config_with(github=provider_config)

        with (
            patch("git.provider.factory._has_credentials", return_value=False),
            patch("git.provider.factory._resolve_auth", return_value=None),
            patch("git.provider.factory.add_provider") as mock_create,
        ):
            mock_create.return_value = MagicMock()
            result = _build_provider("github", config)

        mock_create.assert_called_once_with(
            name="github", account_name="konverso-ai", versioner=ANY
        )
        assert result is mock_create.return_value

    def test_storage_provider_builds_backend_from_config(self) -> None:
        """Test that the storage backend is built from config and forwarded."""
        provider_config = MagicMock(kwargs={}, branches=["master", "dev"])
        config = self._config_with(storage=provider_config)
        mock_storage = MagicMock()
        config.storage.backend = "nexus"
        config.storage.build_storage.return_value = mock_storage

        with (
            patch("git.provider.factory._has_credentials", return_value=True),
            patch("git.provider.factory._resolve_auth", return_value=None),
            patch("git.provider.factory.add_provider") as mock_create,
        ):
            mock_create.return_value = MagicMock()
            _build_provider("storage", config, quiet=True)

        config.storage.build_storage.assert_called_once_with(auth=None)
        mock_create.assert_called_once_with(
            name="storage", storage=mock_storage, branches=["master", "dev"]
        )

    def test_storage_provider_receives_auth_when_available(self) -> None:
        """Test that resolved auth is forwarded to the storage backend builder."""
        provider_config = MagicMock(kwargs={}, branches=["master", "dev"])
        config = self._config_with(storage=provider_config)
        mock_auth = MagicMock()
        mock_storage = MagicMock()
        config.storage.backend = "nexus"
        config.storage.build_storage.return_value = mock_storage

        with (
            patch("git.provider.factory._has_credentials", return_value=True),
            patch("git.provider.factory._resolve_auth", return_value=mock_auth),
            patch("git.provider.factory.add_provider") as mock_create,
        ):
            mock_create.return_value = MagicMock()
            _build_provider("storage", config)

        config.storage.build_storage.assert_called_once_with(auth=mock_auth)
        mock_create.assert_called_once_with(
            name="storage", storage=mock_storage, branches=["master", "dev"]
        )

    def test_versioner_built_with_resolved_auth(self) -> None:
        """Test that the resolved auth is used to build the injected versioner."""
        provider_config = MagicMock(kwargs={"account_name": "acme"})
        config = self._config_with(github=provider_config)
        mock_auth = MagicMock()

        with (
            patch("git.provider.factory._has_credentials", return_value=True),
            patch("git.provider.factory._resolve_auth", return_value=mock_auth),
            patch("git.provider.factory.add_provider") as mock_create,
            patch("git.provider.factory.add_versioner") as mock_add_versioner,
        ):
            mock_create.return_value = MagicMock()
            mock_add_versioner.return_value = MagicMock()
            _build_provider("github", config)

        mock_add_versioner.assert_called_once_with("dulwich", auth=mock_auth)
        mock_create.assert_called_once_with(
            name="github", account_name="acme", versioner=mock_add_versioner.return_value
        )

    def test_returns_none_when_creation_raises_provider_error(self) -> None:
        """Test that a ProviderError during creation is swallowed as None."""
        provider_config = MagicMock(kwargs={})
        config = self._config_with(github=provider_config)

        with (
            patch("git.provider.factory._resolve_auth", return_value=None),
            patch("git.provider.factory.add_provider") as mock_create,
        ):
            mock_create.side_effect = ProviderError("boom")
            result = _build_provider("github", config)

        assert result is None

    def test_returns_none_when_creation_raises_generic_exception(self) -> None:
        """Test that an unexpected exception during creation is swallowed as None."""
        provider_config = MagicMock(kwargs={})
        config = self._config_with(github=provider_config)

        with (
            patch("git.provider.factory._resolve_auth", return_value=None),
            patch("git.provider.factory.add_provider") as mock_create,
        ):
            mock_create.side_effect = RuntimeError("boom")
            result = _build_provider("github", config)

        assert result is None

    def test_raises_provider_error_on_invalid_configuration(self) -> None:
        """Test that a ValueError during creation is wrapped in ProviderError."""
        provider_config = MagicMock(kwargs={})
        config = self._config_with(github=provider_config)

        with (
            patch("git.provider.factory._resolve_auth", return_value=None),
            patch("git.provider.factory.add_provider") as mock_create,
            pytest.raises(ProviderError, match="Failed to configure provider"),
        ):
            mock_create.side_effect = ValueError("bad config")
            _build_provider("github", config)


class TestAddSelectorProvider:
    """Test cases for add_selector_provider function."""

    def test_builds_selector_from_successfully_built_providers(self) -> None:
        """Test that it builds every provider and wraps them in a SelectorProvider."""
        mock_config = MagicMock()
        mock_github_provider = MagicMock(spec=ProviderBase)
        mock_storage_provider = MagicMock(spec=ProviderBase)
        mock_selector = MagicMock(spec=ProviderBase)

        with (
            patch(
                "git.provider.factory._build_provider",
                side_effect=[mock_storage_provider, mock_github_provider],
            ) as mock_build_provider,
            patch(
                "git.provider.factory.add_provider", return_value=mock_selector
            ) as mock_add_provider,
        ):
            result = add_selector_provider(["storage", "github"], config=mock_config)

            assert mock_build_provider.call_args_list == [
                call("storage", mock_config, quiet=False),
                call("github", mock_config, quiet=False),
            ]
            mock_add_provider.assert_called_once_with(
                name="selector",
                providers=[mock_storage_provider, mock_github_provider],
                quiet=False,
            )
            assert result is mock_selector

    def test_skips_providers_that_could_not_be_built(self) -> None:
        """Test that providers _build_provider returns None for are skipped."""
        mock_config = MagicMock()
        mock_github_provider = MagicMock(spec=ProviderBase)
        mock_selector = MagicMock(spec=ProviderBase)

        with (
            patch(
                "git.provider.factory._build_provider",
                side_effect=[None, mock_github_provider],
            ),
            patch(
                "git.provider.factory.add_provider", return_value=mock_selector
            ) as mock_add_provider,
        ):
            result = add_selector_provider(["storage", "github"], config=mock_config)

            mock_add_provider.assert_called_once_with(
                name="selector",
                providers=[mock_github_provider],
                quiet=False,
            )
            assert result is mock_selector

    def test_raises_when_no_provider_could_be_built(self) -> None:
        """Test that a ProviderError is raised when every provider build fails."""
        mock_config = MagicMock()

        with patch(
            "git.provider.factory._build_provider",
            return_value=None,
        ):
            with pytest.raises(ProviderError, match="No provider could be built"):
                add_selector_provider(["storage", "github"], config=mock_config)

    def test_forwards_quiet_flag(self) -> None:
        """Test that the quiet flag is forwarded to _build_provider and the selector."""
        mock_config = MagicMock()
        mock_provider = MagicMock(spec=ProviderBase)
        mock_selector = MagicMock(spec=ProviderBase)

        with (
            patch(
                "git.provider.factory._build_provider",
                return_value=mock_provider,
            ) as mock_build_provider,
            patch(
                "git.provider.factory.add_provider", return_value=mock_selector
            ) as mock_add_provider,
        ):
            add_selector_provider(["storage"], config=mock_config, quiet=True)

            mock_build_provider.assert_called_once_with(
                "storage", mock_config, quiet=True
            )
            mock_add_provider.assert_called_once_with(
                name="selector", providers=[mock_provider], quiet=True
            )
