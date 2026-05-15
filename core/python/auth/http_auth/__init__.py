"""HTTP authentication package.

This package provides authentication classes for HTTP operations,
including basic and bearer token authentication methods.
"""

from auth.http_auth.factory import create_http_auth
from auth.http_auth.http_auth_base import HttpAuthBase

__all__ = [
    "HttpAuthBase",
    "create_http_auth",
]
