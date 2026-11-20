"""Tests for backend base module."""

from backend.base import BackendBase
from utils.utils_for_unit_tests import compare


class _DummyBackend:
    """Minimal concrete BackendBase used to exercise the protocol interface."""

    def __init__(self, client: object) -> None:
        """Store the client to be returned by get_client."""
        self._client = client

    def get_client(self) -> object | None:
        """Return the stored client."""
        return self._client


class TestBackendBase:
    """Test cases for the BackendBase protocol."""

    def test_get_client_valid_returns_stored_client(self) -> None:
        """Test a BackendBase-shaped class returns its client via get_client."""
        client = object()
        backend: BackendBase = _DummyBackend(client)

        assert compare("eq", backend.get_client(), client)

    def test_get_client_valid_can_return_none(self) -> None:
        """Test a BackendBase-shaped class can return None from get_client."""
        backend: BackendBase = _DummyBackend(None)

        assert backend.get_client() is None
