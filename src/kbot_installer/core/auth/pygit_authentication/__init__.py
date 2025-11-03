"""PyGit authentication package.

This package provides authentication classes for PyGit operations,
including key pair and username/password authentication methods.
"""

from kbot_installer.core.auth.pygit_authentication.factory import (
    create_pygit_authentication,
)
from kbot_installer.core.auth.pygit_authentication.pygit_authentication_base import (
    PyGitAuthenticationBase,
)
from kbot_installer.core.auth.pygit_authentication.remote_callback_mixin import (
    RemoteCallbackMixin,
)

__all__ = [
    "PyGitAuthenticationBase",
    "RemoteCallbackMixin",
    "create_pygit_authentication",
]
