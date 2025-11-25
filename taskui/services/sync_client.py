"""Client ID management for sync."""
import uuid
from pathlib import Path
from taskui.logging_config import get_logger

logger = get_logger(__name__)


class SyncClient:
    """Manages unique client identifier for sync operations."""

    def __init__(self):
        self.client_id = self._get_or_create_client_id()
        logger.info(f"Sync client ID: {self.client_id}")

    def _get_or_create_client_id(self) -> str:
        """
        Get persistent client ID from file or create new one.

        Returns:
            UUID string for this client
        """
        client_id_file = Path.home() / '.taskui' / 'client_id'

        if client_id_file.exists():
            client_id = client_id_file.read_text().strip()
            logger.debug(f"Loaded existing client ID from {client_id_file}")
            return client_id
        else:
            # Create new client ID
            client_id_file.parent.mkdir(parents=True, exist_ok=True)
            new_id = str(uuid.uuid4())
            client_id_file.write_text(new_id)
            logger.info(f"Created new client ID: {new_id}")
            return new_id
