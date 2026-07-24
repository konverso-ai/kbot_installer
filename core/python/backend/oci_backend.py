"""Oracle Cloud Infrastructure (OCI) authentication and client management."""

from __future__ import annotations

from typing import TYPE_CHECKING

import oci
import oci.object_storage

from utils.Logger import logger

if TYPE_CHECKING:
    from oci.object_storage import ObjectStorageClient

log = logger.get_package_logger("backend")


class OciBackend:
    """Backend for Oracle Cloud Infrastructure (OCI) Object Storage."""

    _client: ObjectStorageClient

    def __init__(
        self,
        region: str,
        user_ocid: str | None = None,
        tenancy_ocid: str | None = None,
        fingerprint: str | None = None,
        private_key_path: str | None = None,
        pass_phrase: str | None = None,
    ) -> None:
        """Build the OCI Object Storage client from the given credentials.

        Args:
            region: OCI region identifier (e.g. "eu-frankfurt-1").
            user_ocid: OCID of the calling user.
            tenancy_ocid: OCID of the tenancy containing the user.
            fingerprint: Fingerprint of the public key uploaded for the user.
            private_key_path: Path to the PEM-encoded API signing key file.
            pass_phrase: Passphrase protecting the private key, if any.

        """
        self.__config = {
            "user": user_ocid,
            "tenancy": tenancy_ocid,
            "fingerprint": fingerprint,
            "key_file": private_key_path,
            "region": region,
            "pass_phrase": pass_phrase,
        }
        self.__client = oci.object_storage.ObjectStorageClient(self.__config)

    def get_client(self) -> ObjectStorageClient:
        """Return the OCI Object Storage client."""
        return self.__client
