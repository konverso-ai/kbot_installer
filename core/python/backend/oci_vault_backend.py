"""Oracle Cloud Infrastructure (OCI) Vault authentication and client management."""

from __future__ import annotations

from typing import TYPE_CHECKING

import oci
import oci.auth.signers
import oci.secrets
import oci.vault

from utils.Logger import logger

if TYPE_CHECKING:
    from oci.secrets import SecretsClient
    from oci.vault import VaultsClient

log = logger.get_package_logger("backend")


class OciVaultBackend:
    """Backend for Oracle Cloud Infrastructure (OCI) Vault secrets."""

    __client: SecretsClient
    __vaults_client: VaultsClient

    def __init__(self) -> None:
        """Build the OCI Secrets and Vaults clients using instance principal authentication.

        Authentication is resolved via the instance's own identity (instance
        principal), so no explicit credentials are required.
        """
        signer = oci.auth.signers.InstancePrincipalsSecurityTokenSigner()
        self.__client = oci.secrets.SecretsClient(config={}, signer=signer)
        self.__vaults_client = oci.vault.VaultsClient(config={}, signer=signer)

    def get_client(self) -> SecretsClient:
        """Return the OCI Secrets client, used to read secret contents."""
        return self.__client

    def get_vaults_client(self) -> VaultsClient:
        """Return the OCI Vaults client, used to manage secrets (e.g. write new versions)."""
        return self.__vaults_client
