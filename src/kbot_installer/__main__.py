"""Point d'entrée principal du package kbot-installer.

Ce module permet d'exécuter le package comme un script Python
avec la commande: python -m kbot_installer
"""

import sys
from typing import NoReturn

import click

from kbot_installer.cli.commands import cli


def main() -> NoReturn:
    """Point d'entrée principal de l'application CLI."""
    try:
        cli()
    except KeyboardInterrupt:
        click.echo("\nOpération annulée par l'utilisateur.")
        sys.exit(1)
    except Exception as e:
        click.echo(f"Erreur: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
