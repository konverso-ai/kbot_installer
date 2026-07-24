"""API key HTTP authentication."""

from typing import Annotated, TypeAlias

from pydantic import Field

from auth.auth_mixin import AuthMixin
from auth.base import RequiredSecret

ApikeyPrefix: TypeAlias = Annotated[str, Field(default="APIKey")]
ApikeyHeaderName: TypeAlias = Annotated[str, Field(default="X-Api-Key")]


class ApikeyAuth(AuthMixin):
    """Authentication using an API key."""

    header_name: ApikeyHeaderName
    prefix: ApikeyPrefix
    secret: RequiredSecret
