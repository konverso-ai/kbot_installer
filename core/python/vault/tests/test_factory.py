"""Tests for vault factory module."""

from unittest.mock import MagicMock, patch

import pytest

from utils.utils_for_unit_tests import compare
from vault.base import VaultBase
from vault.factory import (
    add_azure_vault,
    add_builtin_vault,
    add_oci_vault,
    add_s3_vault,
    add_vault,
)


class TestAddVault:
    """Test cases for add_vault function."""

    def test_add_vault_valid_delegates_to_factory(self) -> None:
        """Test add_vault delegates to factory_method."""
        with patch("vault.factory.factory_method") as mock_factory_method:
            mock_vault = MagicMock(spec=VaultBase)
            mock_factory_method.return_value = mock_vault
            mock_backend = MagicMock()

            result = add_vault("s3", backend=mock_backend)

            mock_factory_method.assert_called_once_with(
                "s3",
                "vault",
                backend=mock_backend,
            )
            assert compare("eq", result, mock_vault)

    @pytest.mark.parametrize(
        "name, kwargs",
        [
            ("nexus", {"domain": "example.com"}),
            ("azure", {"backend": MagicMock(), "vault_name": "my-vault"}),
            ("s3", {"backend": MagicMock()}),
        ],
    )
    def test_add_vault_valid_passes_kwargs(
        self,
        name: str,
        kwargs: dict,
    ) -> None:
        """Test add_vault forwards keyword arguments."""
        with patch("vault.factory.factory_method") as mock_factory_method:
            mock_vault = MagicMock(spec=VaultBase)
            mock_factory_method.return_value = mock_vault

            result = add_vault(name, **kwargs)

            mock_factory_method.assert_called_once_with(name, "vault", **kwargs)
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
        with patch("vault.factory.factory_method") as mock_factory_method:
            mock_factory_method.side_effect = exception

            with pytest.raises(type(exception), match=str(exception)):
                add_vault("unknown")


class TestAddS3Vault:
    """Test cases for add_s3_vault function."""

    def test_add_s3_vault_builds_backend_and_vault(self) -> None:
        """Test add_s3_vault wires S3 credentials, backend and vault together."""
        mock_backend = MagicMock()
        mock_vault = MagicMock(spec=VaultBase)
        with (
            patch("vault.factory.S3Credentials") as mock_credentials_cls,
            patch("vault.factory.add_backend") as mock_add_backend,
            patch("vault.factory.add_vault") as mock_add_vault,
        ):
            mock_credentials_cls.return_value = "s3-credentials"
            mock_add_backend.return_value = mock_backend
            mock_add_vault.return_value = mock_vault

            result = add_s3_vault()

            mock_add_backend.assert_called_once_with(
                name="s3_vault", credentials="s3-credentials"
            )
            mock_add_vault.assert_called_once_with(name="s3", backend=mock_backend)
            assert compare("eq", result, mock_vault)


class TestAddAzureVault:
    """Test cases for add_azure_vault function."""

    def test_add_azure_vault_builds_backend_and_vault(self) -> None:
        """Test add_azure_vault wires Azure credentials, backend and vault together."""
        mock_backend = MagicMock()
        mock_vault = MagicMock(spec=VaultBase)
        with (
            patch("vault.factory.AzureCredentials") as mock_credentials_cls,
            patch("vault.factory.add_backend") as mock_add_backend,
            patch("vault.factory.add_vault") as mock_add_vault,
        ):
            mock_credentials_cls.return_value = "azure-credentials"
            mock_add_backend.return_value = mock_backend
            mock_add_vault.return_value = mock_vault

            result = add_azure_vault(vault_name="my-vault")

            mock_add_backend.assert_called_once_with(
                name="azure_vault",
                credentials="azure-credentials",
                vault_name="my-vault",
            )
            mock_add_vault.assert_called_once_with(name="azure", backend=mock_backend)
            assert compare("eq", result, mock_vault)


class TestAddOciVault:
    """Test cases for add_oci_vault function."""

    def test_add_oci_vault_builds_backend_and_vault(self) -> None:
        """Test add_oci_vault wires the OCI backend and vault together."""
        mock_backend = MagicMock()
        mock_vault = MagicMock(spec=VaultBase)
        with (
            patch("vault.factory.add_backend") as mock_add_backend,
            patch("vault.factory.add_vault") as mock_add_vault,
        ):
            mock_add_backend.return_value = mock_backend
            mock_add_vault.return_value = mock_vault

            result = add_oci_vault()

            mock_add_backend.assert_called_once_with(name="oci_vault")
            mock_add_vault.assert_called_once_with(name="oci", backend=mock_backend)
            assert compare("eq", result, mock_vault)


class TestAddBuiltinVault:
    """Test cases for add_builtin_vault function."""

    @pytest.mark.parametrize(
        ("name", "kwargs"),
        [
            ("s3", {}),
            ("azure", {"vault_name": "my-vault"}),
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
        with patch("vault.factory.factory_function") as mock_factory_function:
            mock_factory_function.return_value = mock_builder

            result = add_builtin_vault(name, **kwargs)

            mock_factory_function.assert_called_once_with(
                module_name="vault.factory",
                attribute_name=f"add_{name}_vault",
            )
            mock_builder.assert_called_once_with(**kwargs)
            assert compare("eq", result, mock_vault)

    def test_add_builtin_vault_propagates_lookup_errors(self) -> None:
        """Test add_builtin_vault propagates errors from factory_function."""
        with patch("vault.factory.factory_function") as mock_factory_function:
            mock_factory_function.side_effect = AttributeError("Class not found")

            with pytest.raises(AttributeError, match="Class not found"):
                add_builtin_vault("unknown")
