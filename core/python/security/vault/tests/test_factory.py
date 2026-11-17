"""Tests for vault factory module."""

from unittest.mock import MagicMock, patch

import pytest

from utils.utils_for_unit_tests import compare
from security.vault.alias_vault import AliasVault
from security.vault.base import VaultBase
from security.vault.environment_vault import EnvironmentVault
from security.vault.factory import (
    add_azure_vault,
    add_builtin_vault,
    add_oci_vault,
    add_s3_vault,
    add_secret_vault,
    add_vault,
)
from security.vault.secret_vault import SecretVault
from security.vault.value_vault import ValueVault


class TestAddVault:
    """Test cases for add_vault function."""

    def test_add_vault_valid_delegates_to_factory(self) -> None:
        """Test add_vault delegates to factory_method."""
        with patch("security.vault.factory.factory_method") as mock_factory_method:
            mock_vault = MagicMock(spec=VaultBase)
            mock_factory_method.return_value = mock_vault
            mock_backend = MagicMock()

            result = add_vault("s3", backend=mock_backend)

            mock_factory_method.assert_called_once_with(
                "s3",
                "security.vault",
                backend=mock_backend,
            )
            assert compare("eq", result, mock_vault)

    @pytest.mark.parametrize(
        "name, kwargs",
        [
            ("nexus", {"domain": "example.com"}),
            ("azure", {"backend_factory": MagicMock()}),
            ("s3", {"backend": MagicMock()}),
        ],
    )
    def test_add_vault_valid_passes_kwargs(
        self,
        name: str,
        kwargs: dict,
    ) -> None:
        """Test add_vault forwards keyword arguments."""
        with patch("security.vault.factory.factory_method") as mock_factory_method:
            mock_vault = MagicMock(spec=VaultBase)
            mock_factory_method.return_value = mock_vault

            result = add_vault(name, **kwargs)

            mock_factory_method.assert_called_once_with(name, "security.vault", **kwargs)
            assert compare("eq", result, mock_vault)

    @pytest.mark.parametrize(
        "exception",
        [
            ImportError("Cannot import module"),
            AttributeError("Class not found"),
            TypeError("Invalid arguments"),
        ],
    )
    def test_add_vault_invalid_propagates_factory_errors(
        self,
        exception: BaseException,
    ) -> None:
        """Test add_vault propagates factory errors."""
        with patch("security.vault.factory.factory_method") as mock_factory_method:
            mock_factory_method.side_effect = exception

            with pytest.raises(type(exception), match=str(exception)):
                add_vault("unknown")

    @pytest.mark.parametrize(
        ("name", "kwargs", "expected_cls"),
        [
            ("environment", {}, EnvironmentVault),
            ("value", {}, ValueVault),
            ("alias", {"get_config": str}, AliasVault),
            ("secret", {"vault": MagicMock(spec=VaultBase)}, SecretVault),
        ],
    )
    def test_add_vault_valid_resolves_class_by_naming_convention(
        self,
        name: str,
        kwargs: dict,
        expected_cls: type[VaultBase],
    ) -> None:
        """Test add_vault resolves security.vault.{name}_vault.{Name}Vault without mocking."""
        result = add_vault(name, **kwargs)

        assert compare("eq", type(result), expected_cls)


class TestAddS3Vault:
    """Test cases for add_s3_vault function."""

    @pytest.mark.parametrize(
        ("region_name", "credentials_kwargs"),
        [
            (None, {}),
            ("eu-west-3", {"AWS_DEFAULT_REGION": "eu-west-3"}),
        ],
    )
    def test_add_s3_vault_builds_backend_and_vault(
        self, region_name: str | None, credentials_kwargs: dict
    ) -> None:
        """Test add_s3_vault wires S3 credentials (with region), backend and vault."""
        mock_backend = MagicMock()
        mock_vault = MagicMock(spec=VaultBase)
        with (
            patch("credentials.s3_credentials.S3Credentials") as mock_credentials_cls,
            patch("backend.factory.add_backend") as mock_add_backend,
            patch("security.vault.factory.add_vault") as mock_add_vault,
        ):
            mock_credentials_cls.return_value = "s3-credentials"
            mock_add_backend.return_value = mock_backend
            mock_add_vault.return_value = mock_vault

            result = add_s3_vault(region_name=region_name)

            mock_credentials_cls.assert_called_once_with(**credentials_kwargs)
            mock_add_backend.assert_called_once_with(
                name="s3_vault", credentials="s3-credentials"
            )
            mock_add_vault.assert_called_once_with(name="s3", backend=mock_backend)
            assert compare("eq", result, mock_vault)


class TestAddAzureVault:
    """Test cases for add_azure_vault function."""

    def test_add_azure_vault_builds_backends_per_key_vault_on_demand(self) -> None:
        """Test add_azure_vault builds no backend upfront, then one per Key Vault."""
        mock_vault = MagicMock(spec=VaultBase)
        with (
            patch("credentials.azure_credentials.AzureCredentials") as mock_credentials_cls,
            patch("backend.factory.add_backend") as mock_add_backend,
            patch("security.vault.factory.add_vault") as mock_add_vault,
        ):
            mock_credentials_cls.return_value = "azure-credentials"
            mock_add_vault.return_value = mock_vault

            result = add_azure_vault()

            mock_add_backend.assert_not_called()
            backend_factory = mock_add_vault.call_args.kwargs["backend_factory"]
            assert compare("eq", mock_add_vault.call_args.kwargs["name"], "azure")
            assert compare("eq", result, mock_vault)

            backend = backend_factory("my-vault")

            mock_add_backend.assert_called_once_with(
                name="azure_vault",
                credentials="azure-credentials",
                vault_name="my-vault",
            )
            assert compare("eq", backend, mock_add_backend.return_value)


class TestAddOciVault:
    """Test cases for add_oci_vault function."""

    def test_add_oci_vault_builds_backend_and_vault(self) -> None:
        """Test add_oci_vault wires the OCI backend, resolver and vault together."""
        mock_backend = MagicMock()
        mock_vault = MagicMock(spec=VaultBase)
        resolve = MagicMock()
        with (
            patch("backend.factory.add_backend") as mock_add_backend,
            patch("security.vault.factory.add_vault") as mock_add_vault,
        ):
            mock_add_backend.return_value = mock_backend
            mock_add_vault.return_value = mock_vault

            result = add_oci_vault(resolve_secret_id=resolve)

            mock_add_backend.assert_called_once_with(name="oci_vault")
            mock_add_vault.assert_called_once_with(
                name="oci", backend=mock_backend, resolve_secret_id=resolve
            )
            assert compare("eq", result, mock_vault)

class TestAddSecretVault:
    """Test cases for add_secret_vault function."""

    def test_add_secret_vault_wraps_builtin_cloud_vault(self) -> None:
        """Test add_secret_vault builds the cloud vault and wraps it in a secret vault."""
        cloud_vault = MagicMock(spec=VaultBase)
        mock_vault = MagicMock(spec=VaultBase)
        with (
            patch("security.vault.factory.add_builtin_vault") as mock_add_builtin_vault,
            patch("security.vault.factory.add_vault") as mock_add_vault,
        ):
            mock_add_builtin_vault.return_value = cloud_vault
            mock_add_vault.return_value = mock_vault

            result = add_secret_vault("s3", region_name="eu-west-3")

            mock_add_builtin_vault.assert_called_once_with("s3", region_name="eu-west-3")
            mock_add_vault.assert_called_once_with(name="secret", vault=cloud_vault)
            assert compare("eq", result, mock_vault)


class TestAddBuiltinVault:
    """Test cases for add_builtin_vault function."""

    @pytest.mark.parametrize(
        ("name", "kwargs"),
        [
            ("s3", {}),
            ("azure", {}),
            ("oci", {}),
        ],
    )
    def test_add_builtin_vault_dispatches_to_matching_helper(
        self,
        name: str,
        kwargs: dict,
    ) -> None:
        """Test add_builtin_vault resolves and calls add_{name}_vault."""
        mock_vault = MagicMock(spec=VaultBase)
        mock_builder = MagicMock(return_value=mock_vault)
        with patch("security.vault.factory.factory_function") as mock_factory_function:
            mock_factory_function.return_value = mock_builder

            result = add_builtin_vault(name, **kwargs)

            mock_factory_function.assert_called_once_with(
                module_name="security.vault.factory",
                attribute_name=f"add_{name}_vault",
            )
            mock_builder.assert_called_once_with(**kwargs)
            assert compare("eq", result, mock_vault)

    def test_add_builtin_vault_propagates_lookup_errors(self) -> None:
        """Test add_builtin_vault propagates errors from factory_function."""
        with patch("security.vault.factory.factory_function") as mock_factory_function:
            mock_factory_function.side_effect = AttributeError("Class not found")

            with pytest.raises(AttributeError, match="Class not found"):
                add_builtin_vault("unknown")
