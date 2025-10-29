"""Admin password prompter."""

from kbot_installer.core.interactivity.base import InteractivePrompter


class AdminPrompter(InteractivePrompter):
    """Prompter for admin password."""

    def prompt_admin_password(
        self,
        *,
        default_password: str | None = None,
        password_validator: callable[[str], bool] | None = None,
        encrypt_fn: callable[[str], str] | None = None,
    ) -> str:
        """Prompt for admin password with validation.

        Args:
            default_password: Default password (if provided, uses it directly).
            password_validator: Function to validate password strength.
            encrypt_fn: Function to encrypt the password.

        Returns:
            Encrypted password string.

        """
        password = self.ask_password(
            "Enter a password for the default 'admin' user: ",
            default=default_password,
            confirm=True,
            validator=password_validator,
        )

        if encrypt_fn:
            return encrypt_fn(password)
        return password
