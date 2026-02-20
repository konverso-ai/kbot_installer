"""Base URL manager interface.

This module defines the abstract base class for URL management functionality.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Self


class URLManagerBase(ABC):
    """Abstract base class for URL management.

    This class defines the interface that all URL managers must implement.
    It provides methods for creating URLs from strings, adding parameters,
    and converting back to string representation.
    """

    def __init__(self, base_url: str) -> None:
        """Initialize the URL manager.

        Args:
            base_url (str): The base URL for the manager.

        """
        self.base_url = base_url

    @abstractmethod
    def from_string(self, url: str) -> URLManagerBase:
        """Create a new URL manager instance from a URL string.

        Args:
            url (str): The URL string to parse.

        Returns:
            URLManagerBase: A new URL manager instance.

        """

    @abstractmethod
    def add_params(self, **params: str | float | bool | None) -> URLManagerBase:
        """Add parameters to the URL.

        Args:
            **params (Any): Parameters to add to the URL.

        Returns:
            URLManagerBase: A new URL manager instance with added parameters.

        """

    @abstractmethod
    def __str__(self) -> str:
        """Return the URL as a string.

        Returns:
            str: The URL string representation.

        """

    @abstractmethod
    def __truediv__(self, path_segment: str) -> URLManagerBase:
        """Add a path segment to the URL using the / operator.

        Args:
            path_segment (str): The path segment to append.

        Returns:
            URLManagerBase: A new URL manager instance with the added path segment.

        Example:
            >>> manager = URLManager("https://api.example.com")
            >>> new_manager = manager / "api" / "v1"
            >>> print(new_manager)
            https://api.example.com/api/v1

        """

    @abstractmethod
    def __itruediv__(self, path_segment: str) -> Self:
        """Add a path segment to the URL using the /= operator.

        Args:
            path_segment (str): The path segment to append.

        Returns:
            URLManagerBase: A new URL manager instance with the added path segment.

        Example:
            >>> manager = URLManager("https://api.example.com")
            >>> manager /= "api"
            >>> manager /= "v1"
            >>> print(manager)
            https://api.example.com/api/v1

        """

    def __repr__(self) -> str:
        """Return a string representation of the URL manager.

        Returns:
            str: String representation of the URL manager.

        """
        return f"{self.__class__.__name__}({self.__str__()})"
