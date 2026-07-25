"""Authentication module."""

from auth.http.base import HttpAuthBase
from auth.http.factory import add_http_auth as create_auth

__all__ = [
    "HttpAuthBase",
    "create_auth",
]
