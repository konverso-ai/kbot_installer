"""Tests for storage factory module."""

from unittest.mock import MagicMock, patch

import pytest

from storage.base import StorageBase
from storage.factory import (
    add_azure_storage,
    add_builtin_storage,
    add_oci_storage,
    add_s3_storage,
    add_storage,
)
from utils.utils_for_unit_tests import compare


class TestCreateBucketStorage:
    """Test cases for add_storage function."""

    def test_add_storage_valid_delegates_to_factory(
        self,
    ) -> None:
        """Test add_storage delegates to factory_method."""
        with patch("storage.factory.factory_method") as mock_factory_method:
            mock_storage = MagicMock(spec=StorageBase)
            mock_factory_method.return_value = mock_storage

            result = add_storage("s3", bucket_name="bucket")

            mock_factory_method.assert_called_once_with(
                "s3",
                "storage",
                bucket_name="bucket",
            )
            assert compare("eq", result, mock_storage)

    @pytest.mark.parametrize(
        "name, kwargs",
        [
            ("nexus", {"domain": "example.com", "repository": "raw"}),
            ("azure", {"backend": MagicMock(), "container_name": "container"}),
            ("s3", {"backend": MagicMock(), "bucket_name": "bucket"}),
        ],
    )
    def test_add_storage_valid_passes_kwargs(
        self,
        name: str,
        kwargs: dict,
    ) -> None:
        """Test add_storage forwards keyword arguments."""
        with patch("storage.factory.factory_method") as mock_factory_method:
            mock_storage = MagicMock(spec=StorageBase)
            mock_factory_method.return_value = mock_storage

            result = add_storage(name, **kwargs)

            mock_factory_method.assert_called_once_with(name, "storage", **kwargs)
            assert compare("eq", result, mock_storage)

    @pytest.mark.parametrize(
        "exception",
        [
            ImportError("Cannot import module"),
            AttributeError("Class not found"),
            TypeError("Invalid arguments"),
        ],
    )
    def test_add_storage_invalid_propagates_factory_errors(
        self,
        exception: BaseException,
    ) -> None:
        """Test add_storage propagates factory errors."""
        with patch("storage.factory.factory_method") as mock_factory_method:
            mock_factory_method.side_effect = exception

            with pytest.raises(type(exception), match=str(exception)):
                add_storage("unknown")


class TestAddS3Storage:
    """Test cases for add_s3_storage function."""

    def test_add_s3_storage_builds_backend_and_storage(self) -> None:
        """Test add_s3_storage wires S3 credentials, backend and storage together."""
        mock_backend = MagicMock()
        mock_storage = MagicMock(spec=StorageBase)
        with (
            patch("storage.factory.S3Credentials") as mock_credentials_cls,
            patch("storage.factory.add_backend") as mock_add_backend,
            patch("storage.factory.add_storage") as mock_add_storage,
        ):
            mock_credentials_cls.return_value = "s3-credentials"
            mock_add_backend.return_value = mock_backend
            mock_add_storage.return_value = mock_storage

            result = add_s3_storage(bucket_name="bucket", cluster_name="cluster")

            mock_add_backend.assert_called_once_with(
                name="s3_storage", credentials="s3-credentials"
            )
            mock_add_storage.assert_called_once_with(
                name="s3",
                backend=mock_backend,
                bucket_name="bucket",
                cluster_name="cluster",
            )
            assert compare("eq", result, mock_storage)


class TestAddAzureStorage:
    """Test cases for add_azure_storage function."""

    def test_add_azure_storage_builds_backend_and_storage(self) -> None:
        """Test add_azure_storage wires Azure credentials, backend and storage together."""
        mock_backend = MagicMock()
        mock_storage = MagicMock(spec=StorageBase)
        with (
            patch("storage.factory.AzureCredentials") as mock_credentials_cls,
            patch("storage.factory.add_backend") as mock_add_backend,
            patch("storage.factory.add_storage") as mock_add_storage,
        ):
            mock_credentials_cls.return_value = "azure-credentials"
            mock_add_backend.return_value = mock_backend
            mock_add_storage.return_value = mock_storage

            result = add_azure_storage(container_name="container")

            mock_add_backend.assert_called_once_with(
                name="azure_blob", credentials="azure-credentials"
            )
            mock_add_storage.assert_called_once_with(
                name="azure",
                backend=mock_backend,
                container_name="container",
            )
            assert compare("eq", result, mock_storage)


class TestAddOciStorage:
    """Test cases for add_oci_storage function."""

    def test_add_oci_storage_builds_backend_and_storage(self) -> None:
        """Test add_oci_storage wires OCI credentials, backend and storage together."""
        mock_backend = MagicMock()
        mock_storage = MagicMock(spec=StorageBase)
        with (
            patch("storage.factory.OciCredentials") as mock_credentials_cls,
            patch("storage.factory.add_backend") as mock_add_backend,
            patch("storage.factory.add_storage") as mock_add_storage,
        ):
            mock_credentials_cls.return_value = "oci-credentials"
            mock_add_backend.return_value = mock_backend
            mock_add_storage.return_value = mock_storage

            result = add_oci_storage(bucket_name="bucket", namespace_name="namespace")

            mock_add_backend.assert_called_once_with(
                name="oci_storage", credentials="oci-credentials"
            )
            mock_add_storage.assert_called_once_with(
                name="oci",
                backend=mock_backend,
                bucket_name="bucket",
                namespace_name="namespace",
            )
            assert compare("eq", result, mock_storage)


class TestAddBuiltinStorage:
    """Test cases for add_builtin_storage function."""

    @pytest.mark.parametrize(
        ("name", "kwargs"),
        [
            ("s3", {"bucket_name": "bucket"}),
            ("azure", {"container_name": "container"}),
            ("oci", {"bucket_name": "bucket", "namespace_name": "namespace"}),
        ],
    )
    def test_add_builtin_storage_dispatches_to_matching_helper(
        self,
        name: str,
        kwargs: dict,
    ) -> None:
        """Test add_builtin_storage resolves and calls add_{name}_storage."""
        mock_storage = MagicMock(spec=StorageBase)
        mock_builder = MagicMock(return_value=mock_storage)
        with patch("storage.factory.factory_function") as mock_factory_function:
            mock_factory_function.return_value = mock_builder

            result = add_builtin_storage(name, **kwargs)

            mock_factory_function.assert_called_once_with(
                module_name="storage.factory",
                attribute_name=f"add_{name}_storage",
            )
            mock_builder.assert_called_once_with(**kwargs)
            assert compare("eq", result, mock_storage)

    def test_add_builtin_storage_propagates_lookup_errors(self) -> None:
        """Test add_builtin_storage propagates errors from factory_function."""
        with patch("storage.factory.factory_function") as mock_factory_function:
            mock_factory_function.side_effect = AttributeError("Class not found")

            with pytest.raises(AttributeError, match="Class not found"):
                add_builtin_storage("unknown")
