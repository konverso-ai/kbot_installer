"""Tests for VaultBase and registry functionality."""

import pytest

from kbot_installer.core.vault.vault_base import VaultBase, VaultError


class TestVaultBase:
    """Test cases for VaultBase abstract class."""

    def test_vault_base_is_abstract(self) -> None:
        """Test that VaultBase cannot be instantiated directly."""
        with pytest.raises(TypeError):
            VaultBase()

    def test_vault_base_has_registry(self) -> None:
        """Test that VaultBase has a registry attribute."""
        assert hasattr(VaultBase, "_registry")
        assert isinstance(VaultBase._registry, dict)

    def test_vault_base_abstract_methods(self) -> None:
        """Test that VaultBase has the required abstract methods."""
        abstract_methods = VaultBase.__abstractmethods__
        expected_methods = {"get_name", "get_value", "set_value", "delete_value"}
        assert abstract_methods == expected_methods


class TestVaultRegistry:
    """Test cases for vault registry functionality."""

    def setup_method(self) -> None:
        """Clear registry before each test."""
        VaultBase._registry.clear()

    def test_registry_starts_empty(self) -> None:
        """Test that registry starts empty."""
        assert len(VaultBase._registry) == 0

    def test_init_subclass_registers_class(self) -> None:
        """Test that __init_subclass__ registers classes automatically."""

        # Create a mock class that inherits from VaultBase
        class MockVault(VaultBase):
            _name = "TEST_VAULT"

            @classmethod
            def get_name(cls) -> str:
                return cls._name

            def get_value(self, key: str) -> str | None:
                return None

            def set_value(self, key: str, value: str) -> bool:
                return False

            def delete_value(self, key: str) -> bool:
                return False

        # Check that the class was registered
        assert "TEST_VAULT" in VaultBase._registry
        assert VaultBase._registry["TEST_VAULT"] == MockVault

    def _create_mock_vault_class(self, name: str) -> type[VaultBase]:
        """Create a mock vault class with the given name."""
        # Create a dynamic class name based on the vault name
        class_name = (
            f"MockVault{name[-1]}"  # Extract the number from VAULT1, VAULT2, etc.
        )

        class MockVault(VaultBase):
            _name = name

            @classmethod
            def get_name(cls) -> str:
                return cls._name

            def get_value(self, key: str) -> str | None:
                return None

            def set_value(self, key: str, value: str) -> bool:
                return False

            def delete_value(self, key: str) -> bool:
                return False

        # Set the class name dynamically
        MockVault.__name__ = class_name
        return MockVault

    @pytest.mark.parametrize(
        ("vault_name", "expected_class"),
        [
            ("VAULT1", "MockVault1"),
            ("VAULT2", "MockVault2"),
            ("VAULT3", "MockVault3"),
        ],
    )
    def test_registry_contains_multiple_classes(
        self, vault_name: str, expected_class: str
    ) -> None:
        """Test that registry contains multiple registered classes."""
        # Create mock classes dynamically
        self._create_mock_vault_class("VAULT1")
        self._create_mock_vault_class("VAULT2")
        self._create_mock_vault_class("VAULT3")

        # Check that the specific class is registered
        assert vault_name in VaultBase._registry
        assert VaultBase._registry[vault_name].__name__ == expected_class

    def test_registry_overwrites_duplicate_names(self) -> None:
        """Test that registry overwrites classes with duplicate names."""

        class MockVault1(VaultBase):
            _name = "DUPLICATE"

            @classmethod
            def get_name(cls) -> str:
                return cls._name

            def get_value(self, key: str) -> str | None:
                return None

            def set_value(self, key: str, value: str) -> bool:
                return False

            def delete_value(self, key: str) -> bool:
                return False

        class MockVault2(VaultBase):
            _name = "DUPLICATE"

            @classmethod
            def get_name(cls) -> str:
                return cls._name

            def get_value(self, key: str) -> str | None:
                return None

            def set_value(self, key: str, value: str) -> bool:
                return False

            def delete_value(self, key: str) -> bool:
                return False

        # Check that only the last class is registered
        assert len(VaultBase._registry) == 1
        assert "DUPLICATE" in VaultBase._registry
        assert VaultBase._registry["DUPLICATE"] == MockVault2


class TestVaultError:
    """Test cases for VaultError exception."""

    def _raise_vault_error(self, message: str) -> None:
        """Raise VaultError with the given message."""
        raise VaultError(message)

    def test_vault_error_inherits_from_exception(self) -> None:
        """Test that VaultError inherits from Exception."""
        assert issubclass(VaultError, Exception)

    @pytest.mark.parametrize(
        "message",
        [
            "Test error message",
            "Another error",
            "",
            "Error with special chars: !@#$%^&*()",
        ],
    )
    def test_vault_error_can_be_raised(self, message: str) -> None:
        """Test that VaultError can be raised and caught."""
        with pytest.raises(VaultError):
            self._raise_vault_error(message)

    @pytest.mark.parametrize(
        "message",
        ["Custom error message", "Error with numbers: 12345", "Unicode error: éàçù"],
    )
    def test_vault_error_with_message(self, message: str) -> None:
        """Test that VaultError can carry a message."""
        with pytest.raises(VaultError, match=message):
            self._raise_vault_error(message)
