"""
Pending operations queue for local sync storage.

Stores operations that haven't been synced yet, queued locally
until the user triggers a manual sync.
"""

import json
from typing import List, Dict, Any, Optional, Callable
from datetime import datetime

from sqlalchemy import select, delete, func
from sqlalchemy.ext.asyncio import AsyncSession

from taskui.database import PendingSyncOperationORM
from taskui.logging_config import get_logger

logger = get_logger(__name__)


class PendingOperationsQueue:
    """
    Manages local queue of pending sync operations.

    Operations are stored in SQLite and persist across app restarts.
    """

    def __init__(
        self,
        session: AsyncSession,
        on_change_callback: Optional[Callable[[int], None]] = None
    ):
        """
        Initialize pending operations queue.

        Args:
            session: SQLAlchemy async session for database operations
            on_change_callback: Optional callback called with count when queue changes
        """
        self.session = session
        self.on_change_callback = on_change_callback

    async def add(
        self,
        operation: str,
        list_id: str,
        data: Dict[str, Any]
    ) -> None:
        """
        Queue an operation for next sync.

        Args:
            operation: Operation type (TASK_CREATE, TASK_UPDATE, TASK_DELETE, etc.)
            list_id: UUID of the list this operation affects
            data: Operation-specific payload
        """
        pending_op = PendingSyncOperationORM(
            operation=operation,
            list_id=str(list_id),
            data=json.dumps(data),
            timestamp=datetime.utcnow().isoformat(),
            created_at=datetime.utcnow()
        )

        self.session.add(pending_op)
        await self.session.commit()

        logger.debug(f"Queued operation: {operation} for list {list_id}")

        # Notify callback if set
        if self.on_change_callback:
            count = await self.count()
            self.on_change_callback(count)

    async def get_all(self) -> List[Dict[str, Any]]:
        """
        Get all pending operations in order.

        Returns:
            List of operation dictionaries with id, operation, list_id, data, timestamp
        """
        result = await self.session.execute(
            select(PendingSyncOperationORM)
            .order_by(PendingSyncOperationORM.created_at.asc())
        )
        operations = result.scalars().all()

        return [
            {
                'id': op.id,
                'operation': op.operation,
                'list_id': op.list_id,
                'data': json.loads(op.data),
                'timestamp': op.timestamp
            }
            for op in operations
        ]

    async def clear_all(self) -> int:
        """
        Remove all pending operations (after successful sync).

        Returns:
            Number of operations cleared
        """
        result = await self.session.execute(
            delete(PendingSyncOperationORM)
        )
        await self.session.commit()

        count = result.rowcount
        logger.info(f"Cleared {count} pending operations")

        # Notify callback
        if self.on_change_callback:
            self.on_change_callback(0)

        return count

    async def count(self) -> int:
        """
        Get number of pending operations.

        Returns:
            Count of pending operations
        """
        result = await self.session.execute(
            select(func.count()).select_from(PendingSyncOperationORM)
        )
        return result.scalar() or 0

    async def has_pending(self) -> bool:
        """
        Check if there are any pending operations.

        Returns:
            True if queue is not empty
        """
        return await self.count() > 0

    async def remove_by_ids(self, ids: List[int]) -> int:
        """
        Remove specific operations by their database IDs.

        Useful for removing only successfully sent operations.

        Args:
            ids: List of operation IDs to remove

        Returns:
            Number of operations removed
        """
        if not ids:
            return 0

        result = await self.session.execute(
            delete(PendingSyncOperationORM)
            .where(PendingSyncOperationORM.id.in_(ids))
        )
        await self.session.commit()

        count = result.rowcount
        logger.debug(f"Removed {count} specific operations")

        # Notify callback
        if self.on_change_callback:
            remaining = await self.count()
            self.on_change_callback(remaining)

        return count
