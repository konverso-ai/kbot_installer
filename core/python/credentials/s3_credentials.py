"""AWS S3 credentials loaded from the environment."""

from typing import Annotated, TypeAlias

from pydantic import AnyHttpUrl, Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

AwsAccessKeyId: TypeAlias = Annotated[
    SecretStr | None,
    Field(default=None, validation_alias="AWS_ACCESS_KEY_ID"),
]
AwsSecretAccessKey: TypeAlias = Annotated[
    SecretStr | None,
    Field(default=None, validation_alias="AWS_SECRET_ACCESS_KEY"),
]
AwsSessionToken: TypeAlias = Annotated[
    SecretStr | None,
    Field(default=None, validation_alias="AWS_SESSION_TOKEN"),
]
RegionName: TypeAlias = Annotated[
    SecretStr | None,
    Field(default="eu-west-1", validation_alias="AWS_DEFAULT_REGION"),
]


def secret_value(secret: SecretStr | None) -> str | None:
    """Unwrap a ``SecretStr`` to its plain string value.

    Args:
        secret: Secret to unwrap, or None.

    Returns:
        The underlying string value, or None if ``secret`` is None.

    """
    match secret:
        case None:
            return None
        case SecretStr():
            return secret.get_secret_value()


class S3Credentials(BaseSettings):
    """AWS credentials loaded from the environment."""

    model_config = SettingsConfigDict(extra="ignore")

    region_name: RegionName
    endpoint_url: Annotated[AnyHttpUrl | None, Field(default=None)]

    max_pool_connections: Annotated[int, Field(default=10, ge=1)]
    retry_max_attempts: Annotated[int, Field(default=3, ge=1)]

    access_key_id: AwsAccessKeyId
    secret_access_key: AwsSecretAccessKey
    session_token: AwsAccessKeyId

    def missing_env_vars(self) -> list[str]:
        """Return canonical environment variable names that are absent.

        Returns:
            Names of the AWS environment variables that are not set.

        """
        missing: list[str] = []
        if not self.access_key_id:
            missing.append("AWS_ACCESS_KEY_ID")
        if not self.secret_access_key:
            missing.append("AWS_SECRET_ACCESS_KEY")
        if not self.session_token:
            missing.append("AWS_SESSION_TOKEN")
        return missing

    def auth_kwargs(self) -> dict[str, str] | None:
        """Return HTTP auth constructor kwargs.

        Returns:
            None, as AWS credentials are not used for HTTP auth.

        """
        return None

    def storage_kwargs(self) -> dict[str, str | None]:
        """Return AWS credential fields for storage backend construction."""
        return {
            "aws_access_key_id": secret_value(self.access_key_id),
            "aws_secret_access_key": secret_value(self.secret_access_key),
            "aws_session_token": secret_value(self.session_token),
        }
