"""Tests for security.vault.registry: kbot vault names registered on first request."""

import os
import subprocess
import sys
import threading
from unittest.mock import MagicMock, patch

import pytest

from security.vault.alias_vault import AliasVault
from security.vault.base import VaultBase
from security.vault.environment_vault import EnvironmentVault
from security.vault.registry import VaultRegistry
from security.vault.secret_vault import SecretVault
from security.vault.value_vault import ValueVault


@pytest.fixture(autouse=True)
def fresh_registry(monkeypatch):
    """Give every test its own registry: the singleton is reset, then restored afterwards."""
    monkeypatch.setattr(VaultRegistry, "_instance", None)


def test_registry_is_a_singleton_sharing_its_vaults():
    vault = VaultRegistry().get("VARIABLE")

    assert VaultRegistry() is VaultRegistry()
    assert VaultRegistry().get("VARIABLE") is vault


def test_get_builds_the_vault_on_first_call_then_returns_the_registered_one():
    registry = VaultRegistry()

    vault = registry.get("VARIABLE")

    assert isinstance(vault, EnvironmentVault)
    assert registry.get("VARIABLE") is vault


@pytest.mark.parametrize(
    ("name", "kwargs", "expected_cls"),
    [
        ("VALUE", {}, ValueVault),
        ("ALIAS", {"get_config": {}.get}, AliasVault),
        ("SECRET", {"vault": MagicMock(spec=VaultBase)}, SecretVault),
    ],
)
def test_get_builds_the_matching_vault_with_its_arguments(name, kwargs, expected_cls):
    assert isinstance(VaultRegistry().get(name, **kwargs), expected_cls)


def test_arguments_are_only_used_to_build_the_vault():
    builder = MagicMock()
    with patch.dict("security.vault.registry._BUILDERS", {"OCIVAULT": builder}):
        registry = VaultRegistry()
        vault = registry.get("OCIVAULT", resolve_secret_id=str)
        again = registry.get("OCIVAULT", resolve_secret_id=repr)

    builder.assert_called_once_with(resolve_secret_id=str)
    assert vault is again is builder.return_value


def test_failed_build_registers_nothing_and_is_retried():
    vault = MagicMock(spec=VaultBase)
    builder = MagicMock(side_effect=[RuntimeError("boom"), vault])
    with patch.dict("security.vault.registry._BUILDERS", {"AZUREKEYVAULT": builder}):
        registry = VaultRegistry()
        with pytest.raises(RuntimeError, match="boom"):
            registry.get("AZUREKEYVAULT")

        assert registry.get("AZUREKEYVAULT") is vault
        assert registry.get("AZUREKEYVAULT") is vault
    assert builder.call_count == 2


def test_membership_tells_kbot_vault_names_without_building_them():
    builder = MagicMock()
    with patch.dict("security.vault.registry._BUILDERS", {"AZUREKEYVAULT": builder}):
        registry = VaultRegistry()

        assert "AZUREKEYVAULT" in registry
        assert "UNKNOWN" not in registry
    builder.assert_not_called()


def test_get_unknown_vault_raises_key_error():
    with pytest.raises(KeyError):
        VaultRegistry().get("UNKNOWN")


def test_concurrent_first_requests_build_the_vault_once():
    vault = MagicMock(spec=VaultBase)
    building, release = threading.Event(), threading.Event()

    def slow_builder(**_kwargs):
        building.set()
        release.wait(timeout=5)
        return vault

    builder = MagicMock(side_effect=slow_builder)
    results = []
    with patch.dict("security.vault.registry._BUILDERS", {"OCIVAULT": builder}):
        registry = VaultRegistry()
        first = threading.Thread(target=lambda: results.append(registry.get("OCIVAULT")))
        second = threading.Thread(target=lambda: results.append(registry.get("OCIVAULT")))
        first.start()
        assert building.wait(timeout=5)
        second.start()
        second.join(timeout=0.2)  # the second request reaches the build while the first one is still building
        assert isinstance(registry.get("VALUE"), ValueVault)  # other vaults are not held up by that build
        release.set()
        first.join()
        second.join()

    builder.assert_called_once_with()
    assert results == [vault, vault]


def test_importing_the_registry_loads_no_cloud_credentials():
    code = (
        "import sys, security.vault.registry; "
        "print(sorted(m for m in sys.modules if m.startswith(('credentials.', 'backend.factory'))))"
    )
    env = {**os.environ, "PYTHONPATH": os.pathsep.join(sys.path)}
    result = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, check=True, env=env)

    assert result.stdout.strip() == "[]"
