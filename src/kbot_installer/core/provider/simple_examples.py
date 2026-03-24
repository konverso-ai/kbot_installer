"""Exemples simples d'utilisation des providers.

Ce module contient des exemples simples d'utilisation des différents providers
(Nexus, GitHub, Bitbucket) pour cloner des dépôts.
"""

import asyncio
import os
import tempfile
from pathlib import Path

from dotenv import load_dotenv

from kbot_installer.core.auth.pygit_authentication import (
    KeyPairPygitAuthentication,
    UserPassPygitAuthentication,
)
from kbot_installer.core.provider.factory import create_provider

# Charger les variables d'environnement depuis le fichier .env
load_dotenv()


async def example_nexus_github_bitbucket() -> None:
    """Exemple utilisant Nexus, GitHub et Bitbucket.

    Cet exemple montre comment utiliser les trois providers ensemble
    pour cloner des dépôts depuis différentes sources.
    """
    # Configuration des chemins de destination
    base_dir = Path(tempfile.mkdtemp(prefix="kbot_examples_"))

    # 1. Nexus Provider (sans authentification)
    try:
        nexus_provider = create_provider(
            "nexus", domain="example.com", repository="my-repos"
        )

        # Cloner un dépôt depuis Nexus
        nexus_target = base_dir / "nexus_repo"
        nexus_provider.clone("my-project", nexus_target, branch="master")

    except Exception as e:
        # Gestion silencieuse des erreurs pour les exemples
        print(f"Erreur silencieuse: {e}")

    # 2. GitHub Provider (avec authentification par clé SSH)
    try:
        # Configuration de l'authentification GitHub (clé SSH)
        github_auth = KeyPairPygitAuthentication(
            username="git",
            private_key_path=str(Path("~/.ssh/id_rsa").expanduser()),
            public_key_path=str(Path("~/.ssh/id_rsa.pub").expanduser()),
            passphrase="",
        )

        github_provider = create_provider(
            "github",
            account_name=os.getenv("GITHUB_USERNAME", "mon-username"),
            auth=github_auth,
        )

        # Cloner un dépôt depuis GitHub
        github_target = base_dir / "github_repo"
        await github_provider.clone("mon-depot", github_target, branch="main")

    except Exception as e:
        # Gestion silencieuse des erreurs pour les exemples
        print(f"Erreur silencieuse: {e}")

    # 3. Bitbucket Provider (avec authentification par nom d'utilisateur/mot de passe)
    try:
        # Configuration de l'authentification Bitbucket (nom d'utilisateur/mot de passe)
        bitbucket_auth = UserPassPygitAuthentication(
            username=os.getenv("BITBUCKET_USERNAME", "mon-username"),
            password=os.getenv("BITBUCKET_APP_PASSWORD", "mon-app-password"),
        )

        bitbucket_provider = create_provider(
            "bitbucket",
            account_name=os.getenv("BITBUCKET_WORKSPACE", "mon-workspace"),
            auth=bitbucket_auth,
        )

        # Cloner un dépôt depuis Bitbucket
        bitbucket_target = base_dir / "bitbucket_repo"
        await bitbucket_provider.clone("mon-depot", bitbucket_target, branch="main")

    except Exception as e:
        # Gestion silencieuse des erreurs pour les exemples
        print(f"Erreur silencieuse: {e}")


async def example_github_bitbucket_only() -> None:
    """Exemple utilisant seulement GitHub et Bitbucket.

    Cet exemple montre comment utiliser GitHub et Bitbucket
    sans Nexus.
    """
    # Configuration des chemins de destination
    base_dir = Path(tempfile.mkdtemp(prefix="kbot_examples_"))

    # 1. GitHub Provider (sans authentification - accès public)
    try:
        github_provider = create_provider(
            "github",
            account_name="torvalds",  # Dépôt public de Linus Torvalds
        )

        # Cloner un dépôt public depuis GitHub
        github_target = base_dir / "linux_public"
        await github_provider.clone("linux", github_target, branch="master")

    except Exception as e:
        # Gestion silencieuse des erreurs pour les exemples
        print(f"Erreur silencieuse: {e}")

    # 2. Bitbucket Provider (avec authentification par clé SSH)
    try:
        # Configuration de l'authentification Bitbucket (clé SSH)
        bitbucket_auth = KeyPairPygitAuthentication(
            username="git",
            private_key_path=str(Path("~/.ssh/id_rsa").expanduser()),
            public_key_path=str(Path("~/.ssh/id_rsa.pub").expanduser()),
            passphrase="",
        )

        bitbucket_provider = create_provider(
            "bitbucket", account_name="mon-workspace", auth=bitbucket_auth
        )

        # Cloner un dépôt depuis Bitbucket
        bitbucket_target = base_dir / "bitbucket_private"
        await bitbucket_provider.clone(
            "mon-depot-prive", bitbucket_target, branch="develop"
        )

    except Exception as e:
        # Gestion silencieuse des erreurs pour les exemples
        print(f"Erreur silencieuse: {e}")


async def example_bitbucket_only() -> None:
    """Exemple utilisant seulement Bitbucket.

    Cet exemple montre comment utiliser uniquement Bitbucket
    avec différentes méthodes d'authentification.
    """
    # Configuration des chemins de destination
    base_dir = Path(tempfile.mkdtemp(prefix="kbot_examples_"))

    # 1. Bitbucket Provider (authentification par nom d'utilisateur/mot de passe)
    try:
        bitbucket_auth_userpass = UserPassPygitAuthentication(
            username=os.getenv("BITBUCKET_USERNAME", "mon-username"),
            password=os.getenv("BITBUCKET_APP_PASSWORD", "mon-app-password"),
        )

        bitbucket_provider_userpass = create_provider(
            "bitbucket",
            account_name=os.getenv("BITBUCKET_WORKSPACE", "mon-workspace"),
            auth=bitbucket_auth_userpass,
        )

        # Cloner un dépôt depuis Bitbucket
        bitbucket_target_userpass = base_dir / "bitbucket_userpass"
        await bitbucket_provider_userpass.clone(
            "mon-depot", bitbucket_target_userpass, branch="main"
        )

    except Exception as e:
        # Gestion silencieuse des erreurs pour les exemples
        print(f"Erreur silencieuse: {e}")

    # 2. Bitbucket Provider (authentification par clé SSH)
    try:
        bitbucket_auth_ssh = KeyPairPygitAuthentication(
            username="git",
            private_key_path=str(Path("~/.ssh/id_rsa").expanduser()),
            public_key_path=str(Path("~/.ssh/id_rsa.pub").expanduser()),
            passphrase="",
        )

        bitbucket_provider_ssh = create_provider(
            "bitbucket",
            account_name=os.getenv("BITBUCKET_WORKSPACE", "mon-workspace"),
            auth=bitbucket_auth_ssh,
        )

        # Cloner un autre dépôt depuis Bitbucket
        bitbucket_target_ssh = base_dir / "bitbucket_ssh"
        await bitbucket_provider_ssh.clone(
            "mon-autre-depot", bitbucket_target_ssh, branch="develop"
        )

    except Exception as e:
        # Gestion silencieuse des erreurs pour les exemples
        print(f"Erreur silencieuse: {e}")

    # 3. Bitbucket Provider (sans authentification - accès public)
    try:
        bitbucket_provider_public = create_provider(
            "bitbucket",
            account_name="atlassian",  # Dépôt public d'Atlassian
        )

        # Cloner un dépôt public depuis Bitbucket
        bitbucket_target_public = base_dir / "bitbucket_public"
        await bitbucket_provider_public.clone(
            "stash", bitbucket_target_public, branch="master"
        )

    except Exception as e:
        # Gestion silencieuse des erreurs pour les exemples
        print(f"Erreur silencieuse: {e}")


async def main() -> None:
    """Fonction principale pour exécuter tous les exemples.

    Cette fonction exécute tous les exemples de providers
    dans l'ordre.
    """
    # Exécuter tous les exemples
    await example_nexus_github_bitbucket()
    await example_github_bitbucket_only()
    await example_bitbucket_only()


if __name__ == "__main__":
    # Exécuter les exemples
    asyncio.run(main())
