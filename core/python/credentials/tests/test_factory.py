"""Tests for credentials.factory module."""

from unittest.mock import MagicMock, patch

from credentials.base import CredentialsBase
from credentials.factory import add_credentials
from utils.utils_for_unit_tests import compare


def test_addcredentials_valid_delegates_to_factory_method() -> None:
    """Test add_credentials delegates to factory_method with name/package."""
    with patch("credentials.factory.factory_method") as mock_factory_method:
        mock_credentials = MagicMock(spec=CredentialsBase)
        mock_factory_method.return_value = mock_credentials

        result = add_credentials("nexus", username="user")

        mock_factory_method.assert_called_once_with("nexus", "credentials", username="user")
        assert compare("eq", result, mock_credentials)
