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
        cli()
    except KeyboardInterrupt:
        click.echo("\nOperation cancelled by the user.")
        sys.exit(1)
    except Exception as e:
        click.echo(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
