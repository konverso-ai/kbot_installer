"""Exemples simples d'utilisation des versioners.

Ce module contient des exemples simples d'utilisation des versioners
pour les opérations git (clone, pull, checkout) avec différentes
méthodes d'authentification.
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
from kbot_installer.core.versioner.factory import create_versioner

# Charger les variables d'environnement depuis le fichier .env
load_dotenv()


async def example_bitbucket_operations() -> None:
    """Exemple d'opérations git avec Bitbucket.

    Cet exemple montre comment utiliser le versioner pour effectuer
    des opérations git sur des dépôts Bitbucket avec authentification.
    """
    # Configuration des chemins
    base_dir = Path(tempfile.mkdtemp(prefix="kbot_versioner_examples_"))

    # Configuration de l'authentification Bitbucket (nom d'utilisateur/mot de passe)
    bitbucket_auth = UserPassPygitAuthentication(
        username=os.getenv("BITBUCKET_USERNAME", "mon-username"),
        password=os.getenv("BITBUCKET_APP_PASSWORD", "mon-app-password"),
    )

    # Création du versioner avec authentification
    versioner = create_versioner("pygit", auth=bitbucket_auth)

    # URL du dépôt Bitbucket
    bitbucket_repo_url = f"https://bitbucket.org/{os.getenv('BITBUCKET_WORKSPACE', 'mon-workspace')}/mon-depot.git"
    repo_path = base_dir / "bitbucket_repo"

    try:
        # 1. Cloner le dépôt
        await versioner.clone(bitbucket_repo_url, repo_path, branch="main")

        # 2. Changer de branche (checkout)
        await versioner.checkout(repo_path, "develop")

        # 3. Pull des dernières modifications
        await versioner.pull(repo_path, branch="develop")

        # 4. Retour à la branche principale
        await versioner.checkout(repo_path, "main")

        # 5. Pull final
        await versioner.pull(repo_path, branch="main")

    except Exception as e:
        # Gestion silencieuse des erreurs pour les exemples
        print(f"Erreur silencieuse: {e}")


async def example_github_operations() -> None:
    """Exemple d'opérations git avec GitHub.

    Cet exemple montre comment utiliser le versioner pour effectuer
    des opérations git sur des dépôts GitHub avec authentification SSH.
    """
    # Configuration des chemins
    base_dir = Path(tempfile.mkdtemp(prefix="kbot_versioner_examples_"))

    # Configuration de l'authentification GitHub (clé SSH)
    github_auth = KeyPairPygitAuthentication(
        username="git",
        private_key_path=str(Path("~/.ssh/id_rsa").expanduser()),
        public_key_path=str(Path("~/.ssh/id_rsa.pub").expanduser()),
        passphrase="",
    )

    # Création du versioner avec authentification
    versioner = create_versioner("pygit", auth=github_auth)

    # URL du dépôt GitHub (format SSH)
    github_repo_url = (
        f"git@github.com:{os.getenv('GITHUB_USERNAME', 'mon-username')}/mon-depot.git"
    )
    repo_path = base_dir / "github_repo"

    try:
        # 1. Cloner le dépôt
        await versioner.clone(github_repo_url, repo_path, branch="main")

        # 2. Changer de branche (checkout)
        await versioner.checkout(repo_path, "feature/new-feature")

        # 3. Pull des dernières modifications
        await versioner.pull(repo_path, branch="feature/new-feature")

        # 4. Retour à la branche principale
        await versioner.checkout(repo_path, "main")

        # 5. Pull final
        await versioner.pull(repo_path, branch="main")

    except Exception as e:
        # Gestion silencieuse des erreurs pour les exemples
        print(f"Erreur silencieuse: {e}")


async def example_public_repositories() -> None:
    """Exemple d'opérations git avec des dépôts publics.

    Cet exemple montre comment utiliser le versioner pour effectuer
    des opérations git sur des dépôts publics sans authentification.
    """
    # Configuration des chemins
    base_dir = Path(tempfile.mkdtemp(prefix="kbot_versioner_examples_"))

    # Création du versioner sans authentification
    versioner = create_versioner("pygit")

    # Dépôts publics à tester
    public_repos = [
        {
            "name": "linux",
            "url": "https://github.com/torvalds/linux.git",
            "branch": "master",
        },
        {
            "name": "python",
            "url": "https://github.com/python/cpython.git",
            "branch": "main",
        },
    ]

    for repo_info in public_repos:
        repo_name = repo_info["name"]
        repo_url = repo_info["url"]
        repo_branch = repo_info["branch"]
        repo_path = base_dir / f"{repo_name}_public"

        try:
            # 1. Cloner le dépôt
            await versioner.clone(repo_url, repo_path, branch=repo_branch)

            # 2. Pull des dernières modifications
            await versioner.pull(repo_path, branch=repo_branch)

        except Exception as e:
            # Gestion silencieuse des erreurs pour les exemples
            print(f"Erreur silencieuse: {e}")


async def example_mixed_authentication() -> None:
    """Exemple d'opérations git avec différentes méthodes d'authentification.

    Cet exemple montre comment utiliser le versioner avec différentes
    méthodes d'authentification sur différents dépôts.
    """
    # Configuration des chemins
    base_dir = Path(tempfile.mkdtemp(prefix="kbot_versioner_examples_"))

    # 1. Versioner avec authentification Bitbucket (nom d'utilisateur/mot de passe)
    try:
        bitbucket_auth = UserPassPygitAuthentication(
            username=os.getenv("BITBUCKET_USERNAME", "mon-username"),
            password=os.getenv("BITBUCKET_APP_PASSWORD", "mon-app-password"),
        )

        bitbucket_versioner = create_versioner("pygit", auth=bitbucket_auth)
        bitbucket_repo_url = f"https://bitbucket.org/{os.getenv('BITBUCKET_WORKSPACE', 'mon-workspace')}/mon-depot.git"
        bitbucket_repo_path = base_dir / "bitbucket_mixed"

        await bitbucket_versioner.clone(
            bitbucket_repo_url, bitbucket_repo_path, branch="main"
        )
        await bitbucket_versioner.pull(bitbucket_repo_path, branch="main")

    except Exception as e:
        # Gestion silencieuse des erreurs pour les exemples
        print(f"Erreur silencieuse: {e}")

    # 2. Versioner avec authentification GitHub (clé SSH)
    try:
        github_auth = KeyPairPygitAuthentication(
            username="git",
            private_key_path=str(Path("~/.ssh/id_rsa").expanduser()),
            public_key_path=str(Path("~/.ssh/id_rsa.pub").expanduser()),
            passphrase="",
        )

        github_versioner = create_versioner("pygit", auth=github_auth)
        github_repo_url = f"git@github.com:{os.getenv('GITHUB_USERNAME', 'mon-username')}/mon-depot.git"
        github_repo_path = base_dir / "github_mixed"

        await github_versioner.clone(github_repo_url, github_repo_path, branch="main")
        await github_versioner.pull(github_repo_path, branch="main")

    except Exception as e:
        # Gestion silencieuse des erreurs pour les exemples
        print(f"Erreur silencieuse: {e}")

    # 3. Versioner sans authentification (dépôt public)
    try:
        public_versioner = create_versioner("pygit")
        public_repo_url = "https://github.com/torvalds/linux.git"
        public_repo_path = base_dir / "linux_mixed"

        await public_versioner.clone(public_repo_url, public_repo_path, branch="master")
        await public_versioner.pull(public_repo_path, branch="master")

    except Exception as e:
        # Gestion silencieuse des erreurs pour les exemples
        print(f"Erreur silencieuse: {e}")


async def main() -> None:
    """Fonction principale pour exécuter tous les exemples.

    Cette fonction exécute tous les exemples de versioners
    dans l'ordre.
    """
    # Exécuter tous les exemples
    await example_bitbucket_operations()
    await example_github_operations()
    await example_public_repositories()
    await example_mixed_authentication()


if __name__ == "__main__":
    # Exécuter les exemples
    asyncio.run(main())
