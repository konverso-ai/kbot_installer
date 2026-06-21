"""Bundle publisher implementation."""

from storage.base import StorageBase
from utils.bundle import Bundle


class BundlePublisher:
    """Publish bundles to cloud storage."""

    def __init__(self, storage: StorageBase) -> None:
        """Initialize the bundle publisher.

        Args:
            storage: Storage backend used to persist bundles.
        """
        self._storage = storage

    def publish(self, bundle: Bundle) -> None:
        """Publish a bundle as JSON to storage.

        Args:
            bundle: Bundle to publish.
        """
        self._storage.set(
            f"{bundle.name}-{bundle.version}.json",
            bundle.model_dump_json(),
        )
