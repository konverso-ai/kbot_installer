"""Tests for storage factory module."""

from unittest.mock import MagicMock, patch

import pytest

from storage.base import StorageBase
from storage.factory import create_bucket_storage
from utils.utils_for_unit_tests import compare


class TestCreateBucketStorage:
    """Test cases for create_bucket_storage function."""

    def test_create_bucket_storage_valid_delegates_to_factory(
        self,
    ) -> None:
        """Test create_bucket_storage delegates to factory_method."""
        with patch("storage.factory.factory_method") as mock_factory_method:
            mock_storage = MagicMock(spec=StorageBase)
            mock_factory_method.return_value = mock_storage

            result = create_bucket_storage("s3", bucket_name="bucket")

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
    def test_create_bucket_storage_valid_passes_kwargs(
        self,
        name: str,
        kwargs: dict,
    ) -> None:
        """Test create_bucket_storage forwards keyword arguments."""
        with patch("storage.factory.factory_method") as mock_factory_method:
            mock_storage = MagicMock(spec=StorageBase)
            mock_factory_method.return_value = mock_storage

            result = create_bucket_storage(name, **kwargs)

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
    def test_create_bucket_storage_invalid_propagates_factory_errors(
        self,
        exception: BaseException,
    ) -> None:
        """Test create_bucket_storage propagates factory errors."""
        with patch("storage.factory.factory_method") as mock_factory_method:
            mock_factory_method.side_effect = exception

            with pytest.raises(type(exception), match=str(exception)):
                create_bucket_storage("unknown")
