"""Furl URL manager implementation following factory naming convention.

This module provides a FurlUrlManager class that follows the factory naming convention
for the url_manager package.
"""

from __future__ import annotations

from typing import Self

from furl import furl

from kbot_installer.core.url_manager.url_manager_base import URLManagerBase


class FurlUrlManager(URLManagerBase):
    """Furl URL manager implementation following factory naming convention.

    This class provides URL management functionality using the furl library
    for robust URL parsing and manipulation.
    """

    def __init__(self, base_url: str) -> None:
        """Initialize the FurlUrlManager.

        Args:
            base_url (str): The base URL for the manager.

        """
        super().__init__(base_url)
        self._furl = furl(base_url)

    def from_string(self, url: str) -> FurlUrlManager:
        """Create a new FurlUrlManager instance from a URL string.

        Args:
            url (str): The URL string to parse.

        Returns:
            FurlUrlManager: A new FurlUrlManager instance.

        Example:
            >>> manager = FurlUrlManager("https://api.example.com")
            >>> new_manager = manager.from_string("https://api.github.com/repos/user/repo")
            >>> print(new_manager)
            https://api.github.com/repos/user/repo

        """
        return FurlUrlManager(url)

    def add_params(self, **params: str | float | bool | None) -> FurlUrlManager:
        """Add parameters to the URL.

        Args:
            **params (str | float | bool | None): Parameters to add to the URL.

        Returns:
            FurlUrlManager: A new FurlUrlManager instance with added parameters.

        Example:
            >>> manager = FurlUrlManager("https://api.example.com/users")
            >>> new_manager = manager.add_params(page=1, limit=10)
            >>> print(new_manager)
            https://api.example.com/users?page=1&limit=10

        """
        new_furl = self._furl.copy()
        for key, value in params.items():
            if value is not None:
                new_furl.add({key: value})

        return FurlUrlManager(str(new_furl))

    def __str__(self) -> str:
        """Return the URL as a string.

        Returns:
            str: The URL string representation.

        Example:
            >>> manager = FurlUrlManager("https://api.example.com/users?page=1")
            >>> print(str(manager))
            https://api.example.com/users?page=1

        """
        return str(self._furl)

    def __truediv__(self, path_segment: str) -> FurlUrlManager:
        """Add a path segment to the URL using the / operator.

        Args:
            path_segment (str): The path segment to append.

        Returns:
            FurlUrlManager: A new FurlUrlManager instance with the added path segment.

        Example:
            >>> manager = FurlUrlManager("https://api.example.com")
            >>> new_manager = manager / "api" / "v1"
            >>> print(new_manager)
            https://api.example.com/api/v1

        """
        new_furl = self._furl.copy()
        new_furl.path.add(path_segment)
        return FurlUrlManager(str(new_furl))

    def __itruediv__(self, path_segment: str) -> Self:
        """Add a path segment to the URL using the /= operator.

        Args:
            path_segment (str): The path segment to append.

        Returns:
            FurlUrlManager: A new FurlUrlManager instance with the added path segment.

        Example:
            >>> manager = FurlUrlManager("https://api.example.com")
            >>> manager /= "api"
            >>> manager /= "v1"
            >>> print(manager)
            https://api.example.com/api/v1

        """
        new_furl = self._furl.copy()
        new_furl.path.add(path_segment)
        return FurlUrlManager(str(new_furl))
