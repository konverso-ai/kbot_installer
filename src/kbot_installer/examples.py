"""Exemples complets d'utilisation de kbot_installer.

Ce module contient des exemples complets d'utilisation des providers
et des versioners pour démontrer toutes les fonctionnalités disponibles.
"""

import asyncio

from kbot_installer.core.provider.examples import (
    example_bitbucket_only,
    example_github_bitbucket_only,
    example_nexus_github_bitbucket,
)
from kbot_installer.core.versioner.examples import (
    example_bitbucket_operations,
    example_github_operations,
    example_mixed_authentication,
    example_public_repositories,
)


async def run_all_provider_examples() -> None:
    """Exécuter tous les exemples de providers.

    Cette fonction exécute tous les exemples de providers
    pour démontrer l'utilisation des différents providers.
    """
    print("=" * 60)
    print("🚀 EXEMPLES DE PROVIDERS")
    print("=" * 60)

    await example_nexus_github_bitbucket()
    await example_github_bitbucket_only()
    await example_bitbucket_only()


async def run_all_versioner_examples() -> None:
    """Exécuter tous les exemples de versioners.

    Cette fonction exécute tous les exemples de versioners
    pour démontrer l'utilisation des opérations git.
    """
    print("\n" + "=" * 60)
    print("🚀 EXEMPLES DE VERSIONERS")
    print("=" * 60)

    await example_bitbucket_operations()
    await example_github_operations()
    await example_public_repositories()
    await example_mixed_authentication()


async def run_quick_examples() -> None:
    """Exécuter des exemples rapides pour démonstration.

    Cette fonction exécute des exemples rapides qui ne nécessitent
    pas d'authentification pour une démonstration rapide.
    """
    print("=" * 60)
    print("🚀 EXEMPLES RAPIDES (SANS AUTHENTIFICATION)")
    print("=" * 60)

    # Exemple rapide avec dépôts publics
    print("\n--- Exemple rapide: Dépôts publics ---")
    await example_public_repositories()


async def main() -> None:
    """Fonction principale pour exécuter tous les exemples.

    Cette fonction propose différents modes d'exécution
    des exemples selon les besoins.
    """
    print("🎯 KBOT INSTALLER - EXEMPLES COMPLETS")
    print("=" * 60)

    # Les répertoires temporaires sont créés automatiquement par tempfile.mkdtemp()
    # et seront nettoyés automatiquement par le système

    print("\nChoisissez le mode d'exécution:")
    print("1. Exemples rapides (dépôts publics seulement)")
    print("2. Exemples de providers seulement")
    print("3. Exemples de versioners seulement")
    print("4. Tous les exemples (complet)")

    # Pour la démonstration, exécutons les exemples rapides
    print("\n🔄 Exécution des exemples rapides...")
    await run_quick_examples()

    print("\n" + "=" * 60)
    print("✅ EXEMPLES TERMINÉS")
    print("=" * 60)
    print("\nPour exécuter d'autres exemples, modifiez la fonction main()")
    print("ou exécutez directement les modules d'exemples:")
    print("- uv run python -B src/kbot_installer/core/provider/examples.py")
    print("- uv run python -B src/kbot_installer/core/versioner/examples.py")


if __name__ == "__main__":
    # Exécuter les exemples
    asyncio.run(main())
