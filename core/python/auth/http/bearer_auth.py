"""Bearer token HTTP authentication."""

from typing import Annotated, TypeAlias

from pydantic import Field

from auth.auth_mixin import AuthMixin
from auth.base import RequiredSecret

BearerPrefix: TypeAlias = Annotated[str, Field(default="Bearer")]


class BearerAuth(AuthMixin):
    """Authentication using a Bearer token."""

    prefix: BearerPrefix
    secret: RequiredSecret
