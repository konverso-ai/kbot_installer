"""Base class for HTTP authentication.

This module defines the abstract base class that all HTTP authentication
classes must implement to provide a unified interface for HTTP operations.
"""

from abc import ABC, abstractmethod

import httpx


class HttpAuthBase(ABC):
    """Abstract base class for HTTP authentication.

    This class defines the interface that all HTTP authentication classes must implement.
    It provides a method for getting authentication objects for HTTP operations.

    """

    @abstractmethod
    def get_auth(self) -> httpx.Auth:
        """Get the authentication object for HTTP requests.

        Returns:
            httpx.Auth: The authentication object for HTTP requests.

        """
