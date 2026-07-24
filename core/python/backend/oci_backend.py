"""Oracle Cloud Infrastructure (OCI) authentication and client management."""

from __future__ import annotations

from typing import TYPE_CHECKING

import oci
import oci.object_storage

from utils.Logger import logger

if TYPE_CHECKING:
    from oci.object_storage import ObjectStorageClient

    from credentials.oci_credentials import OciCredentials

log = logger.get_package_logger("backend")


class OciBackend:
    """Backend for Oracle Cloud Infrastructure (OCI) Object Storage."""

    _client: ObjectStorageClient

    def __init__(self, credentials: OciCredentials) -> None:
        """Build the OCI Object Storage client from the given credentials.

        Args:
            credentials: OCI connection config used to configure the underlying
                client. Authentication itself is resolved by the OCI SDK's own
                default config file.

        """
        self.__credentials = credentials
        self.__client = oci.object_storage.ObjectStorageClient(
            self.__credentials.to_client_config()
        )

    def get_client(self) -> ObjectStorageClient:
        """Return the OCI Object Storage client."""
        return self.__client
