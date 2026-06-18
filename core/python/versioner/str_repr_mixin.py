"""Mixin for string representation methods.

This module provides mixin classes that implement __str__ and __repr__ methods
for versioner classes using the _get_auth() method.
"""

from versioner.base import VersionerBase
from typing_extensions import override


class StrReprMixin(VersionerBase):
    """Mixin class for string representation methods.

    This mixin provides __str__ and __repr__ methods that use the _get_auth()
    method to display authentication information. Classes that inherit from this
    mixin must implement the _get_auth() method.

    """

    @override
    def __str__(self) -> str:
        """Return string representation of the versioner.

        Returns:
            String representation of the versioner with authentication status.

        """
        auth = self._get_auth()
        auth_status = auth is not None
        return f"{self.__class__.__name__}(auth={auth_status})"

    @override
    def __repr__(self) -> str:
        """Return detailed string representation of the versioner.

        Returns:
            Detailed string representation of the versioner with authentication object.

        """
        auth = self._get_auth()
        return f"{self.__class__.__name__}(auth={auth})"
