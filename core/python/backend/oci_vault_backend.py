"""Oracle Cloud Infrastructure (OCI) Vault authentication and client management."""

from __future__ import annotations

from typing import TYPE_CHECKING

import oci
import oci.auth.signers
import oci.secrets

from utils.Logger import logger

if TYPE_CHECKING:
    from oci.secrets import SecretsClient

log = logger.get_package_logger("backend")


class OciVaultBackend:
    """Backend for Oracle Cloud Infrastructure (OCI) Vault secrets."""

    __client: SecretsClient

    def __init__(self) -> None:
        """Build the OCI Secrets client using instance principal authentication.

        Authentication is resolved via the instance's own identity (instance
        principal), so no explicit credentials are required.
        """
        signer = oci.auth.signers.InstancePrincipalsSecurityTokenSigner()
        self.__client = oci.secrets.SecretsClient(config={}, signer=signer)

    def get_client(self) -> SecretsClient:
        """Return the OCI Secrets client."""
        return self.__client
