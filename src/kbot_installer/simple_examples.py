"""Exemples simples d'utilisation de kbot_installer.

Ce module contient des exemples simples d'utilisation des providers
et des versioners pour démontrer toutes les fonctionnalités disponibles.
"""

import asyncio

from kbot_installer.core.provider.simple_examples import (
    example_bitbucket_only,
    example_github_bitbucket_only,
    example_nexus_github_bitbucket,
)
from kbot_installer.core.versioner.simple_examples import (
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
    await example_nexus_github_bitbucket()
    await example_github_bitbucket_only()
    await example_bitbucket_only()


async def run_all_versioner_examples() -> None:
    """Exécuter tous les exemples de versioners.

    Cette fonction exécute tous les exemples de versioners
    pour démontrer l'utilisation des opérations git.
    """
    await example_bitbucket_operations()
    await example_github_operations()
    await example_public_repositories()
    await example_mixed_authentication()


async def run_quick_examples() -> None:
    """Exécuter des exemples rapides pour démonstration.

    Cette fonction exécute des exemples rapides qui ne nécessitent
    pas d'authentification pour une démonstration rapide.
    """
    # Exemple rapide avec dépôts publics
    await example_public_repositories()


async def main() -> None:
    """Fonction principale pour exécuter tous les exemples.

    Cette fonction propose différents modes d'exécution
    des exemples selon les besoins.
    """
    # Les répertoires temporaires sont créés automatiquement par tempfile.mkdtemp()
    # et seront nettoyés automatiquement par le système

    # Pour la démonstration, exécutons les exemples rapides
    await run_quick_examples()


if __name__ == "__main__":
    # Exécuter les exemples
    asyncio.run(main())
