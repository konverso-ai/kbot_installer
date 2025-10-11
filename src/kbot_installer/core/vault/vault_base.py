"""Base vault interface for secure key-value storage operations."""

from abc import ABC, abstractmethod
from typing import ClassVar


class VaultError(Exception):
    """Exception for vault operations."""


class VaultBase(ABC):
    """Abstract base class for vault implementations.

    This class defines the common interface for all vault implementations,
    providing methods for secure key-value storage operations.
    """

    # Registry to store all vault implementations
    _registry: ClassVar[dict[str, type["VaultBase"]]] = {}

    def __init_subclass__(cls, **kwargs) -> None:  # noqa: ANN003
        """Register vault subclasses automatically.

        This method is called when a subclass is created and automatically
        registers the vault class in the registry using its _name attribute.

        Args:
            **kwargs: Additional keyword arguments passed to the subclass.

        """
        super().__init_subclass__(**kwargs)

        # Register the class using its get_name method
        VaultBase._registry[cls.get_name()] = cls

    @classmethod
    @abstractmethod
    def get_name(cls) -> str:
        """Get the name of the vault."""

    @abstractmethod
    def get_value(self, key: str) -> str | None:
        """Get the value for a given key from the vault.

        Args:
            key (str): The key to retrieve the value for.

        Returns:
            str | None: The value associated with the key, or None if not found.

        """

    @abstractmethod
    def set_value(self, key: str, value: str) -> bool:
        """Add a key-value pair to the vault.

        Args:
            key (str): The key to store.
            value (str): The value to associate with the key.

        Returns:
            bool: True on success, False on failure.

        """

    @abstractmethod
    def delete_value(self, key: str) -> bool:
        """Delete a given key from the vault.

        Args:
            key (str): The key to delete.

        Returns:
            bool: True on success, False on failure.

        """
