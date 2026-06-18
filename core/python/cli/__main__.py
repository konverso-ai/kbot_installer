"""Main entry point for the kbot-installer CLI.

Allows running the tool with: python -m cli
"""

import sys
from typing import NoReturn

import click

from cli.commands import cli


def main() -> NoReturn:
    """Main CLI entry point."""
    try:
        cli()  # pylint: disable=no-value-for-parameter
    except KeyboardInterrupt:
        click.echo("\nOperation cancelled by the user.")
        sys.exit(1)
    except Exception as e:
        click.echo(f"Error: {e}")
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()
