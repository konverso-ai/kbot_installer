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


class OciStorageBackend:
    """Backend for Oracle Cloud Infrastructure (OCI) Object Storage."""

    __client: ObjectStorageClient

    def __init__(self, credentials: OciCredentials) -> None:
        """Build the OCI Object Storage client from the given credentials.

        Args:
            credentials: OCI connection config used to configure the underlying
                client. Authentication is resolved by the OCI SDK's own default
                config file, or by the instance/resource principal signer the
                credentials select.

        """
        self.__credentials = credentials
        config = self.__credentials.to_client_config()
        signer = self.__credentials.to_signer()
        if signer is None:
            self.__client = oci.object_storage.ObjectStorageClient(config)
        else:
            self.__client = oci.object_storage.ObjectStorageClient(config, signer=signer)

    def get_client(self) -> ObjectStorageClient:
        """Return the OCI Object Storage client."""
        return self.__client
