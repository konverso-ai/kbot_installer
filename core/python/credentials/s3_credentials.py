"""AWS S3 default credentials, config only."""

from typing import Annotated, TypeAlias

from pydantic import AnyHttpUrl, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

RegionName: TypeAlias = Annotated[
    str,
    Field(default="eu-west-1", validation_alias="AWS_DEFAULT_REGION"),
]


class S3Credentials(BaseSettings):
    """AWS S3 connection config for the default boto3 credential chain.

    This credential type requires nothing beyond connection config: actual
    authentication is resolved by boto3's own default credential chain
    (environment variables, shared config/credentials files, or an attached
    instance/task role).
    """

    model_config = SettingsConfigDict(extra="ignore")

    region_name: RegionName
    endpoint_url: Annotated[AnyHttpUrl | None, Field(default=None)]

    max_pool_connections: Annotated[int, Field(default=10, ge=1)]
    retry_max_attempts: Annotated[int, Field(default=3, ge=1)]

    def missing_env_vars(self) -> list[str]:
        """Return canonical environment variable names that are absent.

        Returns:
            An empty list: this credential type relies on boto3's default
            credential chain and requires nothing from the environment.

        """
        return []

    def storage_kwargs(self) -> dict[str, str | None]:
        """Return credential fields for storage backend construction.

        Returns:
            An empty dict: authentication is resolved entirely by boto3's own
            default credential chain, so no extra fields need to be merged in.

        """
        return {}
