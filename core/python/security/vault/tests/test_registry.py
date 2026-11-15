"""Tests for security.vault.registry: kbot vault names resolved through ``security.vault`` implementations."""

from unittest.mock import patch

import pytest

from security.vault.base import VaultBase
from security.vault.registry import VaultRegistry

SETTINGS = {
    "cloud_provider": "AZUREKEYVAULT",
    "aws_secret_vault_region": "eu-west-3",
    "site_secret_store": "my-key-vault",
    "target": "target-value",
}

CLOUD_FACTORIES = ("add_azure_vault", "add_s3_vault", "add_oci_vault")


class FakeCloudVault(VaultBase):
    """In-memory writable vault standing in for a cloud vault."""

    def __init__(self, fail=False):
        self.secrets = {"my-key-vault::db-password": "s3cr3t"}
        self.fail = fail

    def get(self, key):
        if self.fail:
            raise RuntimeError("cloud unavailable")
        return self.secrets[key]

    def set(self, key, value):
        if self.fail:
            raise RuntimeError("cloud unavailable")
        self.secrets[key] = value


def _expand(value):
    for name, setting in SETTINGS.items():
        value = value.replace(f"%({name})v", setting)
    return value


@pytest.fixture
def cloud_vault():
    """Fake cloud vault returned by every cloud vault factory."""
    return FakeCloudVault()


@pytest.fixture
def cloud_factories(cloud_vault):
    """Patch the cloud vault factories to return the fake cloud vault."""
    with (
        patch("security.vault.factory.add_azure_vault", return_value=cloud_vault) as azure,
        patch("security.vault.factory.add_s3_vault", return_value=cloud_vault) as s3,
        patch("security.vault.factory.add_oci_vault", return_value=cloud_vault) as oci,
    ):
        yield dict(zip(CLOUD_FACTORIES, (azure, s3, oci), strict=True))


@pytest.fixture
def registry(cloud_factories):
    """Registry reading the fake settings, with cloud vaults replaced by the fake."""
    return VaultRegistry(SETTINGS.get, _expand)


def test_variable_reads_environment_and_defaults_to_empty_string(registry, monkeypatch):
    monkeypatch.setenv("KBOT_TEST_VAR", "from-env")
    monkeypatch.delenv("KBOT_TEST_UNSET", raising=False)

    assert registry.get("VARIABLE", "KBOT_TEST_VAR") == "from-env"
    assert registry.get("VARIABLE", "KBOT_TEST_UNSET") == ""


def test_value_and_alias_expand_settings_references(registry):
    assert registry.get("VALUE", "x-%(target)v") == "x-target-value"
    assert registry.get("ALIAS", "target") == "target-value"


def test_alias_to_undefined_setting_returns_none(registry):
    assert registry.get("ALIAS", "undefined") is None


def test_secret_delegates_to_cloud_provider_vault_with_expanded_key(registry, cloud_factories):
    value = registry.get("SECRET", "%(site_secret_store)v::db-password")

    assert value == "s3cr3t"
    cloud_factories["add_azure_vault"].assert_called_once_with()


def test_secret_with_invalid_cloud_provider_returns_none(registry, monkeypatch):
    monkeypatch.setitem(SETTINGS, "cloud_provider", "NOPE")

    assert registry.get("SECRET", "my-key-vault::db-password") is None


def test_cloud_vault_is_built_once(registry, cloud_factories):
    registry.get("AZUREKEYVAULT", "my-key-vault::db-password")
    registry.get("AZUREKEYVAULT", "my-key-vault::db-password")

    cloud_factories["add_azure_vault"].assert_called_once_with()


@pytest.mark.parametrize(
    ("name", "factory_name", "factory_kwargs"),
    [
        ("AZUREKEYVAULT", "add_azure_vault", {}),
        ("AWSSECRETMANAGER", "add_s3_vault", {"region_name": "eu-west-3"}),
        ("OCIVAULT", "add_oci_vault", {"resolve_secret_id": SETTINGS.get}),
    ],
)
def test_cloud_vaults_are_built_with_settings(registry, cloud_factories, name, factory_name, factory_kwargs):
    registry.get(name, "my-key-vault::db-password")

    cloud_factories[factory_name].assert_called_once_with(**factory_kwargs)


def test_cloud_vault_failure_returns_none(registry, cloud_vault):
    cloud_vault.fail = True

    assert registry.get("AZUREKEYVAULT", "my-key-vault::db-password") is None


def test_azure_set_value_stores_secret(registry, cloud_vault):
    assert registry.set("AZUREKEYVAULT", "my-key-vault::token", "t0k3n") is True
    assert cloud_vault.secrets["my-key-vault::token"] == "t0k3n"


def test_set_value_failure_returns_false(registry, cloud_vault):
    cloud_vault.fail = True

    assert registry.set("AZUREKEYVAULT", "my-key-vault::token", "t0k3n") is False


def test_set_value_on_read_only_vault_returns_false(registry):
    assert registry.set("VARIABLE", "KBOT_TEST_VAR", "value") is False


def test_unknown_vault_is_not_registered_and_resolves_to_none(registry):
    assert "UNKNOWN" not in registry
    assert "AZUREKEYVAULT" in registry
    assert registry.get("UNKNOWN", "key") is None


def test_membership_does_not_build_the_vault(registry, cloud_factories):
    assert "AZUREKEYVAULT" in registry

    cloud_factories["add_azure_vault"].assert_not_called()


def test_build_failure_is_retried(registry, cloud_factories, cloud_vault):
    cloud_factories["add_azure_vault"].side_effect = [RuntimeError("boom"), cloud_vault]

    assert registry.get("AZUREKEYVAULT", "my-key-vault::db-password") is None
    assert registry.get("AZUREKEYVAULT", "my-key-vault::db-password") == "s3cr3t"
