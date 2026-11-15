"""Tests for oci_vault_backend module."""

from unittest.mock import MagicMock, patch

from backend.oci_vault_backend import OciVaultBackend
from utils.utils_for_unit_tests import compare


class TestOciVaultBackend:
    """Test cases for OciVaultBackend class."""

    def test_init_valid_builds_client_with_instance_principal_signer(self) -> None:
        """Test OciVaultBackend builds Secrets and Vaults clients using instance principal auth."""
        with patch("backend.oci_vault_backend.oci") as mock_oci:
            mock_signer = MagicMock()
            mock_oci.auth.signers.InstancePrincipalsSecurityTokenSigner.return_value = (
                mock_signer
            )
            mock_client = MagicMock()
            mock_oci.secrets.SecretsClient.return_value = mock_client
            mock_vaults_client = MagicMock()
            mock_oci.vault.VaultsClient.return_value = mock_vaults_client

            backend = OciVaultBackend()

            mock_oci.auth.signers.InstancePrincipalsSecurityTokenSigner.assert_called_once_with()
            mock_oci.secrets.SecretsClient.assert_called_once_with(
                config={}, signer=mock_signer
            )
            assert compare("eq", backend.get_client(), mock_client)
            mock_oci.vault.VaultsClient.assert_called_once_with(
                config={}, signer=mock_signer
            )
            assert compare("eq", backend.get_vaults_client(), mock_vaults_client)
