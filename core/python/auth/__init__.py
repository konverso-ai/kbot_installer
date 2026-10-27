"""Authentication module."""

from auth.factory import add_auth
from auth.http.base import HttpAuthBase
from auth.http.factory import add_http_auth
from auth.ssh.factory import add_ssh_auth

__all__ = [
    "HttpAuthBase",
    "add_auth",
    "add_http_auth",
    "add_ssh_auth",
]
