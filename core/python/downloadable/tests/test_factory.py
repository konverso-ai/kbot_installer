"""Tests for the downloadable factory module."""

from unittest.mock import MagicMock, patch

from downloadable.base import DownloadableBase
from downloadable.factory import add_downloadable


class TestAddDownloadable:
    """Test cases for add_downloadable function."""

    def test_add_downloadable_delegates_to_factory(self) -> None:
        """add_downloadable should delegate to factory_method with the package name."""
        with patch("downloadable.factory.factory_method") as mock_factory_method:
            mock_downloadable = MagicMock(spec=DownloadableBase)
            mock_factory_method.return_value = mock_downloadable

            result = add_downloadable("product", foo="bar")

            mock_factory_method.assert_called_once_with(
                name="product",
                package="downloadable",
                foo="bar",
            )
            assert result is mock_downloadable
