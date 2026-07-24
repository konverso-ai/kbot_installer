"""Exemples d'utilisation des versioners.

Ce module contient deux exemples concrets d'utilisation de DulwichVersioner :
un exemple avec authentification SSH et un exemple avec authentification
Basic (nom d'utilisateur / mot de passe). Chaque exemple construit une
authentification, construit un versioner puis appelle ``remote_exists``.
"""

import os

from dotenv import load_dotenv

from auth.factory import create_auth
from git.versioner.factory import create_versioner

# Charger les variables d'environnement depuis le fichier .env
load_dotenv()


def example_ssh_auth() -> None:
    """Exemple utilisant une authentification SSH.

    Cet exemple montre comment construire une authentification SSH,
    construire un versioner Dulwich à partir de cette authentification,
    puis vérifier l'existence d'un dépôt distant.
    """
    print("=== Exemple avec authentification SSH ===")
    try:
        ssh_auth = create_auth(
            "ssh",
            username=os.getenv("SSH_AUTH_USERNAME", "git"),
        )

        versioner = create_versioner("dulwich", auth=ssh_auth)

        repository_url = os.getenv("SSH_EXAMPLE_REPOSITORY_URL", "git@github.com:torvalds/linux.git")
        exists = versioner.remote_exists(repository_url)
        print(f"✅ SSH: Le dépôt {repository_url} existe: {exists}")

    except Exception as e:
        print(f"❌ SSH: Erreur - {e}")


def example_basic_auth() -> None:
    """Exemple utilisant une authentification Basic.

    Cet exemple montre comment construire une authentification Basic
    (nom d'utilisateur / mot de passe), construire un versioner Dulwich
    à partir de cette authentification, puis vérifier l'existence d'un
    dépôt distant.
    """
    print("\n=== Exemple avec authentification Basic ===")
    try:
        basic_auth = create_auth(
            "basic",
            username=os.getenv("BASIC_AUTH_USERNAME", "mon-username"),
            password=os.getenv("BASIC_AUTH_PASSWORD", "mon-mot-de-passe"),
        )

        versioner = create_versioner("dulwich", auth=basic_auth)

        repository_url = os.getenv(
            "BASIC_EXAMPLE_REPOSITORY_URL",
            "https://github.com/torvalds/linux.git",
        )
        exists = versioner.remote_exists(repository_url)
        print(f"✅ Basic: Le dépôt {repository_url} existe: {exists}")

    except Exception as e:
        print(f"❌ Basic: Erreur - {e}")


def main() -> None:
    """Fonction principale pour exécuter les deux exemples.

    Cette fonction exécute successivement l'exemple SSH puis l'exemple
    Basic.
    """
    print("🚀 Démarrage des exemples de versioners...")

    example_ssh_auth()
    example_basic_auth()

    print("\n✅ Tous les exemples de versioners ont été exécutés!")


if __name__ == "__main__":
    main()
