"""Tests for credentials.oci_credentials module."""

from unittest.mock import patch

import pytest

from credentials.oci_credentials import OciCredentials
from utils.utils_for_unit_tests import compare


def test_missingenvvars_valid_always_empty(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test missing_env_vars always reports nothing missing (default credentials)."""
    monkeypatch.delenv("OCI_REGION", raising=False)
    monkeypatch.delenv("OCI_CONFIG_PROFILE", raising=False)

    creds = OciCredentials()
    assert compare("eq", creds.missing_env_vars(), [])


def test_region_valid_defaults_to_none() -> None:
    """Test region defaults to None when OCI_REGION is unset."""
    creds = OciCredentials()
    assert creds.region is None


def test_region_valid_reads_env_var(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test region is read from OCI_REGION when set."""
    monkeypatch.setenv("OCI_REGION", "eu-paris-1")
    creds = OciCredentials()
    assert compare("eq", creds.region, "eu-paris-1")


def test_configprofile_valid_defaults_to_default() -> None:
    """Test config_profile defaults to DEFAULT when OCI_CONFIG_PROFILE is unset."""
    creds = OciCredentials()
    assert compare("eq", creds.config_profile, "DEFAULT")


def test_toclientconfig_valid_loads_from_file_and_applies_region(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test to_client_config loads the OCI config file and overrides region."""
    monkeypatch.setenv("OCI_REGION", "eu-paris-1")
    monkeypatch.setenv("OCI_CONFIG_PROFILE", "CUSTOM")
    with patch("credentials.oci_credentials.oci.config.from_file") as mock_from_file:
        mock_from_file.return_value = {"region": "eu-frankfurt-1", "user": "ocid1.user"}

        creds = OciCredentials()
        config = creds.to_client_config()

        mock_from_file.assert_called_once_with(profile_name="CUSTOM")
        assert compare("eq", config["region"], "eu-paris-1")
        assert compare("eq", config["user"], "ocid1.user")


def test_toclientconfig_valid_keeps_file_region_when_unset() -> None:
    """Test to_client_config keeps the config file's region when none is configured."""
    with patch("credentials.oci_credentials.oci.config.from_file") as mock_from_file:
        mock_from_file.return_value = {"region": "eu-frankfurt-1"}

        creds = OciCredentials()
        config = creds.to_client_config()

        assert compare("eq", config["region"], "eu-frankfurt-1")
