"""Shared helpers for handling ``SecretStr`` credential fields."""

from pydantic import SecretStr


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
