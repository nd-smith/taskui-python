"""
Diary service for TaskUI application.

Implements CRUD operations for task diary entries with database persistence.
Provides functionality for creating, reading, updating, and deleting diary entries
associated with tasks.
"""

from datetime import datetime, timezone
from typing import List, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from taskui.database import DiaryEntryORM, TaskORM
from taskui.logging_config import get_logger
from taskui.models import DiaryEntry

logger = get_logger(__name__)


class DiaryServiceError(Exception):
    """Base exception for diary service errors."""
    pass


class DiaryEntryNotFoundError(DiaryServiceError):
    """Raised when a diary entry is not found."""
    pass


class TaskNotFoundError(DiaryServiceError):
    """Raised when a task is not found."""
    pass


class DiaryService:
    """
    Service layer for diary entry operations.

    Handles CRUD operations for diary entries with database persistence
    and task relationship management.
    """

    def __init__(self, session: AsyncSession) -> None:
        """
        Initialize diary service with database session.

        Args:
            session: Active async database session
        """
        self.session = session

    # ==============================================================================
    # CONVERSION HELPERS
    # ==============================================================================

    def _orm_to_pydantic(self, entry_orm: DiaryEntryORM) -> DiaryEntry:
        """
        Convert DiaryEntryORM to Pydantic DiaryEntry model.

        Args:
            entry_orm: SQLAlchemy ORM diary entry instance

        Returns:
            Pydantic DiaryEntry instance
        """
        return DiaryEntry.model_validate(
            {
                "id": UUID(entry_orm.id),
                "task_id": UUID(entry_orm.task_id),
                "content": entry_orm.content,
                "created_at": entry_orm.created_at,
            }
        )

    @staticmethod
    def _pydantic_to_orm(entry: DiaryEntry) -> DiaryEntryORM:
        """
        Convert Pydantic DiaryEntry to DiaryEntryORM model.

        Args:
            entry: Pydantic DiaryEntry instance

        Returns:
            SQLAlchemy ORM diary entry instance
        """
        return DiaryEntryORM(
            id=str(entry.id),
            task_id=str(entry.task_id),
            content=entry.content,
            created_at=entry.created_at,
        )

    # ==============================================================================
    # VALIDATION HELPERS
    # ==============================================================================

    async def _verify_task_exists(self, task_id: UUID) -> None:
        """
        Verify that a task exists.

        Args:
            task_id: UUID of the task

        Raises:
            TaskNotFoundError: If task does not exist
        """
        result = await self.session.execute(
            select(TaskORM).where(TaskORM.id == str(task_id))
        )
        task = result.scalar_one_or_none()
        if not task:
            raise TaskNotFoundError(f"Task with id {task_id} not found")

    async def _get_entry_or_raise(self, entry_id: UUID) -> DiaryEntryORM:
        """
        Get a diary entry by ID or raise an exception.

        Args:
            entry_id: UUID of the diary entry

        Returns:
            DiaryEntryORM instance

        Raises:
            DiaryEntryNotFoundError: If diary entry does not exist
        """
        result = await self.session.execute(
            select(DiaryEntryORM).where(DiaryEntryORM.id == str(entry_id))
        )
        entry_orm = result.scalar_one_or_none()
        if not entry_orm:
            raise DiaryEntryNotFoundError(f"Diary entry with id {entry_id} not found")
        return entry_orm

    # ==============================================================================
    # CREATE OPERATIONS
    # ==============================================================================

    async def create_entry(
        self,
        task_id: UUID,
        content: str,
    ) -> DiaryEntry:
        """
        Create a new diary entry for a task.

        Args:
            task_id: UUID of the task
            content: Entry content/text

        Returns:
            Created DiaryEntry instance

        Raises:
            TaskNotFoundError: If task does not exist
        """
        try:
            logger.debug(f"Creating diary entry for task {task_id}")

            # Verify task exists
            await self._verify_task_exists(task_id)

            # Create diary entry
            entry = DiaryEntry(
                task_id=task_id,
                content=content,
            )

            # Convert to ORM and save
            entry_orm = self._pydantic_to_orm(entry)
            self.session.add(entry_orm)
            await self.session.flush()

            logger.info(f"Created diary entry: id={entry.id}, task_id={task_id}")
            return entry
        except TaskNotFoundError as e:
            logger.error(f"Failed to create diary entry - task not found: {e}", exc_info=True)
            raise
        except Exception as e:
            logger.error(f"Failed to create diary entry: {e}", exc_info=True)
            raise

    # ==============================================================================
    # READ OPERATIONS
    # ==============================================================================

    async def get_entries_for_task(
        self,
        task_id: UUID,
        limit: int = 3,
    ) -> List[DiaryEntry]:
        """
        Get diary entries for a task, ordered by creation time (newest first).

        Args:
            task_id: UUID of the task
            limit: Maximum number of entries to return (default: 3)

        Returns:
            List of DiaryEntry instances ordered by created_at DESC

        Raises:
            TaskNotFoundError: If task does not exist
        """
        try:
            # Verify task exists
            await self._verify_task_exists(task_id)

            # Build query
            query = (
                select(DiaryEntryORM)
                .where(DiaryEntryORM.task_id == str(task_id))
                .order_by(DiaryEntryORM.created_at.desc())
                .limit(limit)
            )

            # Execute query
            result = await self.session.execute(query)
            entry_orms = result.scalars().all()

            # Convert to Pydantic
            entries = [self._orm_to_pydantic(entry_orm) for entry_orm in entry_orms]

            logger.debug(f"Retrieved {len(entries)} diary entries for task {task_id}")
            return entries
        except TaskNotFoundError as e:
            logger.error(f"Failed to get diary entries - task not found: {e}", exc_info=True)
            raise
        except Exception as e:
            logger.error(f"Failed to get diary entries for task {task_id}: {e}", exc_info=True)
            raise

    async def get_entry_by_id(self, entry_id: UUID) -> Optional[DiaryEntry]:
        """
        Get a diary entry by its ID.

        Args:
            entry_id: UUID of the diary entry

        Returns:
            DiaryEntry instance or None if not found
        """
        result = await self.session.execute(
            select(DiaryEntryORM).where(DiaryEntryORM.id == str(entry_id))
        )
        entry_orm = result.scalar_one_or_none()

        if not entry_orm:
            return None

        return self._orm_to_pydantic(entry_orm)

    # ==============================================================================
    # UPDATE OPERATIONS
    # ==============================================================================

    async def update_entry(
        self,
        entry_id: UUID,
        content: str,
    ) -> DiaryEntry:
        """
        Update a diary entry's content.

        Args:
            entry_id: UUID of the diary entry to update
            content: New content text

        Returns:
            Updated DiaryEntry instance

        Raises:
            DiaryEntryNotFoundError: If diary entry does not exist
        """
        try:
            logger.debug(f"Updating diary entry {entry_id}")

            # Get existing entry
            entry_orm = await self._get_entry_or_raise(entry_id)

            # Update content
            entry_orm.content = content

            # Flush changes to database
            await self.session.flush()

            # Convert back to Pydantic
            entry = self._orm_to_pydantic(entry_orm)

            logger.info(f"Updated diary entry: id={entry_id}")
            return entry
        except DiaryEntryNotFoundError as e:
            logger.error(f"Failed to update diary entry - not found: {e}", exc_info=True)
            raise
        except Exception as e:
            logger.error(f"Failed to update diary entry {entry_id}: {e}", exc_info=True)
            raise

    # ==============================================================================
    # DELETE OPERATIONS
    # ==============================================================================

    async def delete_entry(self, entry_id: UUID) -> None:
        """
        Delete a diary entry.

        Args:
            entry_id: UUID of the diary entry to delete

        Raises:
            DiaryEntryNotFoundError: If diary entry does not exist
        """
        try:
            logger.debug(f"Deleting diary entry {entry_id}")

            # Get entry to delete
            entry_orm = await self._get_entry_or_raise(entry_id)

            # Delete the entry
            await self.session.delete(entry_orm)

            # Flush the deletion
            await self.session.flush()

            logger.info(f"Deleted diary entry: id={entry_id}")
        except DiaryEntryNotFoundError as e:
            logger.error(f"Failed to delete diary entry - not found: {e}", exc_info=True)
            raise
        except Exception as e:
            logger.error(f"Failed to delete diary entry {entry_id}: {e}", exc_info=True)
            raise
