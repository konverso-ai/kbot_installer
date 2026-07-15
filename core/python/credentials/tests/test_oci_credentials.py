"""Tests for credentials.oci_credentials module."""

import pytest

from credentials.oci_credentials import OciCredentials
from utils.utils_for_unit_tests import compare


def test_missingenvvars_valid_reports_all_when_unset(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    for key in (
        "OCI_USER_OCID",
        "OCI_TENANCY_OCID",
        "OCI_FINGERPRINT",
        "OCI_PRIVATE_KEY_PATH",
    ):
        monkeypatch.delenv(key, raising=False)

    creds = OciCredentials()
    assert compare(
        "eq",
        creds.missing_env_vars(),
        [
            "OCI_USER_OCID",
            "OCI_TENANCY_OCID",
            "OCI_FINGERPRINT",
            "OCI_PRIVATE_KEY_PATH",
        ],
    )


def test_missingenvvars_valid_empty_when_set(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OCI_USER_OCID", "user")
    monkeypatch.setenv("OCI_TENANCY_OCID", "tenancy")
    monkeypatch.setenv("OCI_FINGERPRINT", "fingerprint")
    monkeypatch.setenv("OCI_PRIVATE_KEY_PATH", "/tmp/key.pem")

    creds = OciCredentials()
    assert compare("eq", creds.missing_env_vars(), [])


def test_authkwargs_valid_returns_none() -> None:
    creds = OciCredentials()
    assert compare("eq", creds.auth_kwargs(), None)


def test_storagekwargs_valid_returns_credential_fields(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OCI_USER_OCID", "user")
    monkeypatch.setenv("OCI_TENANCY_OCID", "tenancy")
    monkeypatch.setenv("OCI_FINGERPRINT", "fingerprint")
    monkeypatch.setenv("OCI_PRIVATE_KEY_PATH", "/tmp/key.pem")
    monkeypatch.setenv("OCI_PASS_PHRASE", "secret")

    creds = OciCredentials()
    assert compare(
        "eq",
        creds.storage_kwargs(),
        {
            "user_ocid": "user",
            "tenancy_ocid": "tenancy",
            "fingerprint": "fingerprint",
            "private_key_path": "/tmp/key.pem",
            "pass_phrase": "secret",
        },
    )
