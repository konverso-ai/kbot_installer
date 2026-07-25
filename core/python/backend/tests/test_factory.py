"""Tests for backend factory module."""

from unittest.mock import MagicMock, patch

import pytest

from backend.base import BackendBase
from backend.factory import (
    add_azure_blob_backend,
    add_backend,
    add_builtin_backend,
    add_oci_storage_backend,
    add_s3_storage_backend,
)
from utils.utils_for_unit_tests import compare


class TestAddBackend:
    """Test cases for add_backend function."""

    def test_add_backend_valid_delegates_to_factory(self) -> None:
        """Test add_backend delegates to factory_method."""
        with patch("backend.factory.factory_method") as mock_factory_method:
            mock_backend = MagicMock(spec=BackendBase)
            mock_factory_method.return_value = mock_backend

            result = add_backend("s3", bucket_name="bucket")

            mock_factory_method.assert_called_once_with(
                "s3",
                "backend",
                bucket_name="bucket",
            )
            assert compare("eq", result, mock_backend)

    @pytest.mark.parametrize(
        "exception",
        [
            ImportError("Cannot import module"),
            AttributeError("Class not found"),
            TypeError("Invalid arguments"),
        ],
    )
    def test_add_backend_invalid_propagates_factory_errors(
        self,
        exception: BaseException,
    ) -> None:
        """Test add_backend propagates factory errors."""
        with patch("backend.factory.factory_method") as mock_factory_method:
            mock_factory_method.side_effect = exception

            with pytest.raises(type(exception), match=str(exception)):
                add_backend("unknown")


class TestAddS3StorageBackend:
    """Test cases for add_s3_storage_backend function."""

    def test_add_s3_storage_backend_builds_credentials_and_delegates(self) -> None:
        """Test add_s3_storage_backend builds S3Credentials and calls add_backend."""
        mock_backend = MagicMock(spec=BackendBase)
        with (
            patch("backend.factory.S3Credentials") as mock_credentials_cls,
            patch("backend.factory.add_backend") as mock_add_backend,
        ):
            mock_credentials = mock_credentials_cls.return_value
            mock_add_backend.return_value = mock_backend

            result = add_s3_storage_backend()

            mock_credentials_cls.assert_called_once_with()
            mock_add_backend.assert_called_once_with(
                name="s3_storage",
                credentials=mock_credentials,
            )
            assert compare("eq", result, mock_backend)


class TestAddAzureBlobBackend:
    """Test cases for add_azure_blob_backend function."""

    def test_add_azure_blob_backend_builds_credentials_and_delegates(self) -> None:
        """Test add_azure_blob_backend builds AzureCredentials and calls add_backend."""
        mock_backend = MagicMock(spec=BackendBase)
        with (
            patch("backend.factory.AzureCredentials") as mock_credentials_cls,
            patch("backend.factory.add_backend") as mock_add_backend,
        ):
            mock_credentials = mock_credentials_cls.return_value
            mock_add_backend.return_value = mock_backend

            result = add_azure_blob_backend(
                account_url="https://account.blob.core.windows.net",
            )

            mock_credentials_cls.assert_called_once_with()
            mock_add_backend.assert_called_once_with(
                name="azure_blob",
                account_url="https://account.blob.core.windows.net",
                credentials=mock_credentials,
            )
            assert compare("eq", result, mock_backend)


class TestAddOciStorageBackend:
    """Test cases for add_oci_storage_backend function."""

    def test_add_oci_storage_backend_builds_credentials_and_delegates(self) -> None:
        """Test add_oci_storage_backend builds OciCredentials and calls add_backend."""
        mock_backend = MagicMock(spec=BackendBase)
        with (
            patch("backend.factory.OciCredentials") as mock_credentials_cls,
            patch("backend.factory.add_backend") as mock_add_backend,
        ):
            mock_credentials = mock_credentials_cls.return_value
            mock_add_backend.return_value = mock_backend

            result = add_oci_storage_backend()

            mock_credentials_cls.assert_called_once_with()
            mock_add_backend.assert_called_once_with(
                name="oci_storage",
                credentials=mock_credentials,
            )
            assert compare("eq", result, mock_backend)


class TestAddBuiltinBackend:
    """Test cases for add_builtin_backend function."""

    @pytest.mark.parametrize(
        ("name", "kwargs"),
        [
            ("s3_storage", {}),
            ("azure_blob", {"account_url": "https://account.blob.core.windows.net"}),
            ("oci_storage", {}),
        ],
    )
    def test_add_builtin_backend_dispatches_to_matching_helper(
        self,
        name: str,
        kwargs: dict,
    ) -> None:
        """Test add_builtin_backend resolves and calls add_{name}_backend."""
        mock_backend = MagicMock(spec=BackendBase)
        mock_builder = MagicMock(return_value=mock_backend)
        with patch("backend.factory.factory_function") as mock_factory_function:
            mock_factory_function.return_value = mock_builder

            result = add_builtin_backend(name, **kwargs)

            mock_factory_function.assert_called_once_with(
                module_name="backend.factory",
                attribute_name=f"add_{name}_backend",
            )
            mock_builder.assert_called_once_with(**kwargs)
            assert compare("eq", result, mock_backend)

    def test_add_builtin_backend_propagates_lookup_errors(self) -> None:
        """Test add_builtin_backend propagates errors from factory_function."""
        with patch("backend.factory.factory_function") as mock_factory_function:
            mock_factory_function.side_effect = AttributeError("Class not found")

            with pytest.raises(AttributeError, match="Class not found"):
                add_builtin_backend("unknown")
