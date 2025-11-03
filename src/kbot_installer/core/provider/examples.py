"""Exemples d'utilisation des providers.

Ce module contient des exemples concrets d'utilisation des différents providers
(Nexus, GitHub, Bitbucket) pour cloner des dépôts.
"""

import asyncio
import os
import tempfile
from pathlib import Path

from dotenv import load_dotenv

from kbot_installer.core.auth.pygit_authentication import create_pygit_authentication
from kbot_installer.core.provider.factory import create_provider

# Charger les variables d'environnement depuis le fichier .env
load_dotenv()


async def example_nexus_github_bitbucket() -> None:
    """Exemple utilisant Nexus, GitHub et Bitbucket.

    Cet exemple montre comment utiliser les trois providers ensemble
    pour cloner des dépôts depuis différentes sources.
    """
    print("=== Exemple avec Nexus, GitHub et Bitbucket ===")

    # Configuration des chemins de destination

    # 1. Nexus Provider (sans authentification)
    print("\n1. Clonage depuis Nexus...")
    try:
        nexus_provider = create_provider(
            "nexus", domain="konverso.ai", repository="kbot_raw"
        )

        # Cloner un dépôt depuis Nexus

        nexus_target = Path(tempfile.mkdtemp(prefix="nexus_repo_"))
        nexus_provider.clone("api-task-manager", nexus_target, branch="master")
        print(f"✅ Nexus: Dépôt cloné vers {nexus_target}")

    except Exception as e:
        print(f"❌ Nexus: Erreur - {e}")

    # 2. GitHub Provider (avec authentification par clé SSH)
    print("\n2. Clonage depuis GitHub...")
    try:
        # Configuration de l'authentification GitHub (clé SSH)
        github_auth = create_pygit_authentication(
            "user_pass",
            username=os.getenv("GITHUB_USERNAME", "mon-username"),
            password=os.getenv("GITHUB_TOKEN", "mon-app-password"),
        )

        github_provider = create_provider(
            "github",
            account_name=os.getenv("GITHUB_USERNAME", "mon-username"),
            auth=github_auth,
        )

        # Cloner un dépôt depuis GitHub

        github_target = Path(tempfile.mkdtemp(prefix="github_repo_"))
        await github_provider.clone("api-task-manager", github_target, branch="master")
        print(f"✅ GitHub: Dépôt cloné vers {github_target}")

    except Exception as e:
        print(f"❌ GitHub: Erreur - {e}")

    # 3. Bitbucket Provider (avec authentification par nom d'utilisateur/mot de passe)
    print("\n3. Clonage depuis Bitbucket...")
    try:
        # Configuration de l'authentification Bitbucket (nom d'utilisateur/mot de passe)
        bitbucket_auth = create_pygit_authentication(
            "user_pass",
            username=os.getenv("BITBUCKET_USERNAME", "mon-username"),
            password=os.getenv("BITBUCKET_APP_PASSWORD", "mon-app-password"),
        )

        bitbucket_provider = create_provider(
            "bitbucket",
            account_name=os.getenv("BITBUCKET_WORKSPACE", "konversoai"),
            auth=bitbucket_auth,
        )

        # Cloner un dépôt depuis Bitbucket

        bitbucket_target = Path(tempfile.mkdtemp(prefix="bitbucket_repo_"))
        await bitbucket_provider.clone(
            "api-task-manager", bitbucket_target, branch="master"
        )
        print(f"✅ Bitbucket: Dépôt cloné vers {bitbucket_target}")

    except Exception as e:
        print(f"❌ Bitbucket: Erreur - {e}")


async def example_github_bitbucket_only() -> None:
    """Exemple utilisant seulement GitHub et Bitbucket.

    Cet exemple montre comment utiliser GitHub et Bitbucket
    sans Nexus.
    """
    print("\n=== Exemple avec GitHub et Bitbucket seulement ===")

    # Configuration des chemins de destination

    # 1. GitHub Provider (sans authentification - accès public)
    print("\n1. Clonage depuis GitHub (public)...")
    try:
        github_provider = create_provider(
            "github",
            account_name="torvalds",  # Dépôt public de Linus Torvalds
        )

        # Cloner un dépôt public depuis GitHub

        github_target = Path(tempfile.mkdtemp(prefix="linux_public_"))
        await github_provider.clone("linux", github_target, branch="master")
        print(f"✅ GitHub (public): Dépôt cloné vers {github_target}")

    except Exception as e:
        print(f"❌ GitHub (public): Erreur - {e}")

    # 2. Bitbucket Provider (avec authentification par clé SSH)
    print("\n2. Clonage depuis Bitbucket...")
    try:
        # Configuration de l'authentification Bitbucket (clé SSH)
        bitbucket_auth = create_pygit_authentication(
            "key_pair",
            username="git",
            private_key_path=str(Path("~/.ssh/id_rsa").expanduser()),
            public_key_path=str(Path("~/.ssh/id_rsa.pub").expanduser()),
            passphrase="",
        )

        bitbucket_provider = create_provider(
            "bitbucket", account_name="mon-workspace", auth=bitbucket_auth
        )

        # Cloner un dépôt depuis Bitbucket

        bitbucket_target = Path(tempfile.mkdtemp(prefix="bitbucket_private_"))
        await bitbucket_provider.clone(
            "mon-depot-prive", bitbucket_target, branch="develop"
        )
        print(f"✅ Bitbucket: Dépôt privé cloné vers {bitbucket_target}")

    except Exception as e:
        print(f"❌ Bitbucket: Erreur - {e}")


async def example_bitbucket_only() -> None:
    """Exemple utilisant seulement Bitbucket.

    Cet exemple montre comment utiliser uniquement Bitbucket
    avec différentes méthodes d'authentification.
    """
    print("\n=== Exemple avec Bitbucket seulement ===")

    # Configuration des chemins de destination

    # 1. Bitbucket Provider (authentification par nom d'utilisateur/mot de passe)
    print("\n1. Clonage depuis Bitbucket (nom d'utilisateur/mot de passe)...")
    try:
        bitbucket_auth_userpass = create_pygit_authentication(
            "user_pass",
            username=os.getenv("BITBUCKET_USERNAME", "mon-username"),
            password=os.getenv("BITBUCKET_APP_PASSWORD", "mon-app-password"),
        )

        bitbucket_provider_userpass = create_provider(
            "bitbucket",
            account_name=os.getenv("BITBUCKET_WORKSPACE", "mon-workspace"),
            auth=bitbucket_auth_userpass,
        )

        # Cloner un dépôt depuis Bitbucket
        bitbucket_target_userpass = Path(tempfile.mkdtemp(prefix="bitbucket_userpass_"))
        await bitbucket_provider_userpass.clone(
            "mon-depot", bitbucket_target_userpass, branch="main"
        )
        print(f"✅ Bitbucket (user/pass): Dépôt cloné vers {bitbucket_target_userpass}")

    except Exception as e:
        print(f"❌ Bitbucket (user/pass): Erreur - {e}")

    # 2. Bitbucket Provider (authentification par clé SSH)
    print("\n2. Clonage depuis Bitbucket (clé SSH)...")
    try:
        bitbucket_auth_ssh = create_pygit_authentication(
            "key_pair",
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
        bitbucket_target_ssh = Path(tempfile.mkdtemp(prefix="bitbucket_ssh_"))
        await bitbucket_provider_ssh.clone(
            "mon-autre-depot", bitbucket_target_ssh, branch="develop"
        )
        print(f"✅ Bitbucket (SSH): Dépôt cloné vers {bitbucket_target_ssh}")

    except Exception as e:
        print(f"❌ Bitbucket (SSH): Erreur - {e}")

    # 3. Bitbucket Provider (sans authentification - accès public)
    print("\n3. Clonage depuis Bitbucket (public)...")
    try:
        bitbucket_provider_public = create_provider(
            "bitbucket",
            account_name="atlassian",  # Dépôt public d'Atlassian
        )

        # Cloner un dépôt public depuis Bitbucket
        bitbucket_target_public = Path(tempfile.mkdtemp(prefix="bitbucket_public_"))
        await bitbucket_provider_public.clone(
            "stash", bitbucket_target_public, branch="master"
        )
        print(f"✅ Bitbucket (public): Dépôt cloné vers {bitbucket_target_public}")

    except Exception as e:
        print(f"❌ Bitbucket (public): Erreur - {e}")


async def example_nexus_bitbucket() -> None:
    """Exemple utilisant Nexus et Bitbucket.

    Cet exemple montre comment utiliser Nexus pour les artefacts
    et Bitbucket pour le code source dans un workflow combiné.
    """
    print("\n=== Exemple avec Nexus + Bitbucket ===")

    # Configuration des chemins de destination

    # 1. Nexus Provider (pour les artefacts)
    print("\n1. Opérations avec Nexus (artefacts)...")
    try:
        nexus_provider = create_provider(
            "nexus", domain="nexus.example.com", repository="releases"
        )

        # Simulation de téléchargement d'artefacts depuis Nexus
        nexus_artifacts = [
            {"name": "kbot-core", "version": "1.0.0", "type": "tar.gz"},
            {"name": "kbot-ui", "version": "2.1.0", "type": "zip"},
            {"name": "kbot-config", "version": "1.5.0", "type": "tar.gz"},
        ]

        for artifact in nexus_artifacts:
            artifact_path = Path(tempfile.mkdtemp(prefix=f"nexus_{artifact['name']}_"))
            print(f"   📦 Téléchargement {artifact['name']} v{artifact['version']}...")
            # Simulation du clonage/téléchargement depuis Nexus
            nexus_provider.clone(
                artifact["name"], artifact_path, branch=artifact["version"]
            )
            print(f"   ✅ {artifact['name']} téléchargé vers {artifact_path}")

        print("✅ Opérations Nexus réussies")

    except Exception as e:
        print(f"❌ Nexus: Erreur - {e}")

    # 2. Bitbucket Provider (pour le code source)
    print("\n2. Opérations avec Bitbucket (code source)...")
    try:
        # Configuration de l'authentification Bitbucket
        bitbucket_auth = create_pygit_authentication(
            "user_pass",
            username=os.getenv("BITBUCKET_USERNAME", "mon-username"),
            password=os.getenv("BITBUCKET_APP_PASSWORD", "mon-app-password"),
        )

        bitbucket_provider = create_provider(
            "bitbucket",
            account_name=os.getenv("BITBUCKET_WORKSPACE", "mon-workspace"),
            auth=bitbucket_auth,
        )

        # Cloner le code source depuis Bitbucket

        bitbucket_target = Path(tempfile.mkdtemp(prefix="bitbucket_code_"))
        await bitbucket_provider.clone(
            "kbot_installer", bitbucket_target, branch="KB-14303"
        )
        print(f"✅ Bitbucket: Code source cloné vers {bitbucket_target}")

    except Exception as e:
        print(f"❌ Bitbucket: Erreur - {e}")

    # 3. Workflow combiné Nexus + Bitbucket
    print("\n3. Workflow combiné Nexus + Bitbucket...")
    try:
        print("   🔄 Workflow d'intégration simulé :")
        print("   📦 1. Artefacts téléchargés depuis Nexus")
        print("   📥 2. Code source cloné depuis Bitbucket")
        print("   🔧 3. Configuration des environnements")
        print("   🚀 4. Déploiement de l'application")
        print("   ✅ Workflow combiné réussi")

    except Exception as e:
        print(f"❌ Workflow combiné: Erreur - {e}")


async def main() -> None:
    """Fonction principale pour exécuter tous les exemples.

    Cette fonction exécute tous les exemples de providers
    dans l'ordre.
    """
    print("🚀 Démarrage des exemples de providers...")

    # Exécuter tous les exemples
    await example_nexus_github_bitbucket()
    await example_github_bitbucket_only()
    await example_bitbucket_only()
    await example_nexus_bitbucket()

    print("\n✅ Tous les exemples de providers ont été exécutés!")


if __name__ == "__main__":
    # Exécuter les exemples
    asyncio.run(main())
