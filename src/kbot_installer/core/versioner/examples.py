"""Exemples d'utilisation des versioners.

Ce module contient des exemples concrets d'utilisation des versioners
pour les opérations git (clone, pull, checkout) avec différentes
méthodes d'authentification.
"""

import asyncio
import os
import tempfile
import uuid
from pathlib import Path

from dotenv import load_dotenv

from kbot_installer.core.auth.pygit_authentication.factory import create_pygit_authentication
from kbot_installer.core.versioner.factory import create_versioner

# Charger les variables d'environnement depuis le fichier .env
load_dotenv()


async def example_bitbucket_operations() -> None:
    """Exemple d'opérations git avec Bitbucket.

    Cet exemple montre comment utiliser le versioner pour effectuer
    des opérations git sur des dépôts Bitbucket avec authentification.
    """
    print("=== Exemple d'opérations Bitbucket ===")

    # Configuration des chemins

    # Configuration de l'authentification Bitbucket (nom d'utilisateur/mot de passe)
    bitbucket_auth = create_pygit_authentication(
        "user_pass",
        username=os.getenv("BITBUCKET_USERNAME", "mon-username"),
        password=os.getenv("BITBUCKET_APP_PASSWORD", "mon-app-password"),
    )

    # Création du versioner avec authentification
    versioner = create_versioner("pygit", auth=bitbucket_auth)

    # URL du dépôt Bitbucket
    bitbucket_repo_url = "https://bitbucket.org/konversoai/kbot_installer.git"
    repo_path = Path(tempfile.mkdtemp(prefix=f"bitbucket_repo_{uuid.uuid4().hex[:8]}_"))

    try:
        # 1. Cloner le dépôt
        print("\n1. Clonage du dépôt Bitbucket...")
        await versioner.clone(bitbucket_repo_url, repo_path)
        print(f"✅ Dépôt cloné vers {repo_path}")

        # 2. Changer de branche (checkout)
        print("\n2. Changement vers la branche 'CS-1875'...")
        await versioner.checkout(repo_path, "CS-1875")
        print("✅ Changement vers la branche 'CS-1875' réussi")

        # 3. Pull des dernières modifications
        print("\n3. Pull des dernières modifications...")
        await versioner.pull(repo_path, branch="CS-1875")
        print("✅ Pull réussi")

        # 4. Retour à la branche principale
        print("\n4. Retour à la branche 'master'...")
        await versioner.checkout(repo_path, "master")
        print("✅ Retour à la branche 'master' réussi")

        # 5. Pull final
        print("\n5. Pull final sur 'master'...")
        await versioner.pull(repo_path, branch="master")
        print("✅ Pull final réussi")

    except Exception as e:
        print(f"❌ Erreur lors des opérations Bitbucket: {e}")


async def example_github_operations() -> None:
    """Exemple d'opérations git avec GitHub.

    Cet exemple montre comment utiliser le versioner pour effectuer
    des opérations git sur des dépôts GitHub avec authentification SSH.
    """
    print("\n=== Exemple d'opérations GitHub ===")

    # Configuration des chemins

    # Configuration de l'authentification GitHub (clé SSH)
    github_auth = create_pygit_authentication(
        "key_pair",
        username="git",
        private_key_path=str(Path("~/.ssh/bitbucket").expanduser()),
        public_key_path=str(Path("~/.ssh/bitbucket.pub").expanduser()),
        passphrase="",  # Ajoutez la passphrase si nécessaire
    )

    # Création du versioner avec authentification
    versioner = create_versioner("pygit", auth=github_auth)

    # URL du dépôt GitHub (format SSH)
    github_repo_url = f"git@github.com:{os.getenv('GITHUB_USERNAME', 'mon-username')}/api-task-manager.git"
    repo_path = Path(tempfile.mkdtemp(prefix=f"github_repo_{uuid.uuid4().hex[:8]}_"))

    try:
        # 1. Cloner le dépôt
        print("\n1. Clonage du dépôt GitHub...")
        await versioner.clone(github_repo_url, repo_path)
        print(f"✅ Dépôt cloné vers {repo_path}")

        # 2. Changer de branche (checkout)
        print("\n2. Changement vers la branche 'KB-20228'...")
        await versioner.checkout(repo_path, "KB-20228")
        print("✅ Changement vers la branche 'KB-20228' réussi")

        # 3. Pull des dernières modifications
        print("\n3. Pull des dernières modifications...")
        await versioner.pull(repo_path, branch="KB-20228")
        print("✅ Pull réussi")

        # 4. Retour à la branche principale
        print("\n4. Retour à la branche 'dev'...")
        await versioner.checkout(repo_path, "dev")
        print("✅ Retour à la branche 'dev' réussi")

        # 5. Pull final
        print("\n5. Pull final sur 'dev'...")
        await versioner.pull(repo_path, branch="dev")
        print("✅ Pull final réussi")

    except Exception as e:
        print(f"❌ Erreur lors des opérations GitHub: {e}")


async def example_public_repositories() -> None:
    """Exemple d'opérations git avec des dépôts publics.

    Cet exemple montre comment utiliser le versioner pour effectuer
    des opérations git sur des dépôts publics sans authentification.
    """
    print("\n=== Exemple d'opérations sur dépôts publics ===")

    # Configuration des chemins

    # Création du versioner sans authentification
    versioner = create_versioner("pygit")

    # Dépôts publics à tester
    public_repos = [
        {
            "name": "kbot-py-client",
            "url": "https://github.com/konverso-ai/kbot-py-client.git",
            "branch": "main",
        },
        {
            "name": "kbot_installer",
            "url": "https://bitbucket.org/konversoai/kbot_installer.git",
            "branch": "KB-14303",
        },
    ]

    for repo_info in public_repos:
        repo_name = repo_info["name"]
        repo_url = repo_info["url"]
        repo_branch = repo_info["branch"]
        repo_path = Path(
            tempfile.mkdtemp(prefix=f"{repo_name}_public_{uuid.uuid4().hex[:8]}_")
        )

        try:
            print(f"\n--- Dépôt public: {repo_name} ---")

            # 1. Cloner le dépôt
            print(f"1. Clonage du dépôt {repo_name}...")
            await versioner.clone(repo_url, repo_path)
            print(f"✅ Dépôt {repo_name} cloné vers {repo_path}")

            # 2. Pull des dernières modifications
            print(f"2. Pull des dernières modifications de {repo_name}...")
            await versioner.pull(repo_path, branch=repo_branch)
            print(f"✅ Pull de {repo_name} réussi")

            # 3. Lister les branches disponibles (simulation)
            print(f"3. Dépôt {repo_name} prêt pour utilisation")

        except Exception as e:
            print(f"❌ Erreur avec le dépôt {repo_name}: {e}")


async def main() -> None:
    """Fonction principale pour exécuter tous les exemples.

    Cette fonction exécute tous les exemples de versioners
    dans l'ordre.
    """
    print("🚀 Démarrage des exemples de versioners...")

    # Exécuter tous les exemples
    await example_bitbucket_operations()
    await example_github_operations()
    await example_public_repositories()

    print("\n✅ Tous les exemples de versioners ont été exécutés!")


if __name__ == "__main__":
    # Exécuter les exemples
    asyncio.run(main())
