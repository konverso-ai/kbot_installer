"""Base class for interactive prompters."""

import getpass
import sys
from collections.abc import Callable


class InteractivePrompter:
    """Base class for interactive parameter prompting.

    Provides common methods for asking yes/no questions, ports, and text input.
    All prompters should inherit from this class or be instantiated with
    similar behavior.

    Attributes:
        use_defaults: If True, automatically use default values without prompting.
        silent: If True, suppress prompts (for non-interactive use).

    """

    def __init__(self, *, use_defaults: bool = False, silent: bool = False) -> None:
        """Initialize the prompter.

        Args:
            use_defaults: If True, automatically use default values.
            silent: If True, suppress prompts.

        """
        self.use_defaults = use_defaults
        self.silent = silent

    def ask_yn(self, question: str, default: str = "y") -> bool:
        """Ask a yes/no question.

        Args:
            question: Question to ask.
            default: Default answer ('y' or 'n').

        Returns:
            True if 'yes', False if 'no'.

        """
        while True:
            if self.use_defaults:
                answer = "y"
            else:
                answer = input(question).strip().lower() or default
            if answer in ("y", "yes"):
                return True
            if answer in ("n", "no"):
                return False
            print('Answer either "y" or "n".')

    def ask_port(
        self,
        question: str,
        default: str,
        ptype: str,
        *,
        limit: bool = True,
        http_port: str | None = None,
        https_port: str | None = None,
    ) -> str:
        """Ask for a port number.

        Args:
            question: Question to ask.
            default: Default port number.
            ptype: Port type ('http', 'https', 'db', 'redis').
            limit: If True, enforce port range 1024-65535.
            http_port: HTTP port value (for conflict checking).
            https_port: HTTPS port value (for conflict checking).

        Returns:
            Port number as string.

        """
        # Port range constants
        min_port = 1024
        max_port = 65535

        while True:
            answer = input(f"{question} [{default}]: ").strip() or default
            if answer.isdigit():
                port = int(answer)
                if limit and port < min_port:
                    print(
                        "Do not use port number below 1024 as it requires root privileges"
                    )
                elif limit and port > max_port:
                    print("Max port number is 65535.")
                elif (ptype == "http" and answer == https_port) or (
                    ptype == "https" and answer == http_port
                ):
                    print("HTTP and HTTPS ports could not be the same")
                else:
                    return answer
            else:
                print("Wrong port number")

    def ask_input(self, question: str, default: str = "") -> str:
        """Ask for text input.

        Args:
            question: Question to ask.
            default: Default value.

        Returns:
            User input or default value.

        """
        if self.use_defaults and default:
            return default
        answer = input(question).strip()
        return answer or default

    def ask_password(
        self,
        prompt: str,
        *,
        default: str | None = None,
        confirm: bool = True,
        validator: Callable[[str], bool] | None = None,
    ) -> str:
        """Ask for a password with optional confirmation.

        Args:
            prompt: Prompt text.
            default: Default password (if provided, uses it without prompting).
            confirm: If True, ask for confirmation.
            validator: Optional function to validate password strength.

        Returns:
            Password string.

        """
        while True:
            if default:
                password = default
            elif sys.stdin.isatty():
                password = getpass.getpass(prompt)
            else:
                print(prompt)
                password = sys.stdin.readline().rstrip()

            if not password:
                continue

            # Validate password if validator provided
            if validator and not validator(password):
                print("This password is not strong enough")
                continue

            # Confirm password if needed
            if confirm:
                confirm_prompt = prompt.replace("Enter", "Confirm")
                if default:
                    confirm_password = default
                elif sys.stdin.isatty():
                    confirm_password = getpass.getpass(confirm_prompt)
                else:
                    print(confirm_prompt)
                    confirm_password = sys.stdin.readline().rstrip()

                if password != confirm_password:
                    print("Passwords are not the same")
                    sys.stdout.flush()
                    continue

            return password
