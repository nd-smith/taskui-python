"""
Sync status widget for displaying sync state in the UI.

Shows pending operation count, last sync time, and sync progress.
"""

from textual.widgets import Static
from textual.reactive import reactive
from datetime import datetime
from typing import Optional

from taskui.logging_config import get_logger

logger = get_logger(__name__)


class SyncStatus(Static):
    """
    Shows sync status in the UI.

    Displays:
    - Pending operation count
    - Last sync time
    - Syncing indicator
    - Connection status
    """

    # Reactive properties auto-refresh on change
    pending_count: reactive[int] = reactive(0)
    last_sync: reactive[Optional[datetime]] = reactive(None)
    syncing: reactive[bool] = reactive(False)
    connected: reactive[bool] = reactive(False)
    enabled: reactive[bool] = reactive(False)

    def render(self) -> str:
        """Render the sync status text."""
        if not self.enabled:
            return "○ Sync disabled"

        if not self.connected:
            return "⚠ Sync: Not connected"

        if self.syncing:
            return "⏳ Syncing..."

        if self.pending_count > 0:
            return f"📤 {self.pending_count} pending (Ctrl+Shift+S)"

        if self.last_sync:
            time_str = self.last_sync.strftime("%I:%M %p")
            return f"✓ Synced: {time_str}"

        return "○ Not synced yet"

    def watch_pending_count(self, count: int) -> None:
        """Update display when pending count changes."""
        logger.debug(f"Sync status: pending count changed to {count}")
        self.refresh()

    def watch_syncing(self, is_syncing: bool) -> None:
        """Update display during sync."""
        logger.debug(f"Sync status: syncing changed to {is_syncing}")
        self.refresh()

    def watch_connected(self, is_connected: bool) -> None:
        """Update display when connection status changes."""
        logger.debug(f"Sync status: connected changed to {is_connected}")
        self.refresh()

    def watch_enabled(self, is_enabled: bool) -> None:
        """Update display when sync enabled/disabled."""
        logger.debug(f"Sync status: enabled changed to {is_enabled}")
        self.refresh()

    def set_sync_complete(self, sent: int, received: int) -> None:
        """
        Update status after sync completes.

        Args:
            sent: Number of operations sent
            received: Number of operations received
        """
        self.syncing = False
        self.last_sync = datetime.now()
        logger.info(f"Sync complete: {sent} sent, {received} received")
        self.refresh()

    def set_pending_count(self, count: int) -> None:
        """Update pending operation count."""
        self.pending_count = count

    def start_sync(self) -> None:
        """Mark sync as in progress."""
        self.syncing = True

    def set_connected(self, connected: bool) -> None:
        """Update connection status."""
        self.connected = connected

    def set_enabled(self, enabled: bool) -> None:
        """Update enabled status."""
        self.enabled = enabled


# Default CSS for the widget
DEFAULT_CSS = """
SyncStatus {
    dock: bottom;
    height: 1;
    background: $surface;
    color: $text-muted;
    text-align: right;
    padding: 0 1;
}
"""
