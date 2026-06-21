"""AWS S3 credentials loaded from the environment."""

from typing import Annotated, TypeAlias

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

AwsAccessKeyId: TypeAlias = Annotated[
    str | None,
    Field(default=None, validation_alias="AWS_ACCESS_KEY_ID"),
]
AwsSecretAccessKey: TypeAlias = Annotated[
    str | None,
    Field(default=None, validation_alias="AWS_SECRET_ACCESS_KEY"),
]


class S3Credentials(BaseSettings):
    """AWS credentials loaded from the environment."""

    model_config = SettingsConfigDict(extra="ignore")

    aws_access_key_id: AwsAccessKeyId
    aws_secret_access_key: AwsSecretAccessKey

    def missing_env_vars(self) -> list[str]:
        missing: list[str] = []
        if not self.aws_access_key_id:
            missing.append("AWS_ACCESS_KEY_ID")
        if not self.aws_secret_access_key:
            missing.append("AWS_SECRET_ACCESS_KEY")
        return missing

    def auth_kwargs(self) -> dict[str, str] | None:
        return None

    def storage_kwargs(self) -> dict[str, str | None]:
        """Return AWS credential fields for storage backend construction."""
        return {
            "aws_access_key_id": self.aws_access_key_id,
            "aws_secret_access_key": self.aws_secret_access_key,
        }
