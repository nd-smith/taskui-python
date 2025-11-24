"""
Database layer for TaskUI application.

Provides SQLAlchemy ORM models, async engine/session management, and database
initialization for SQLite persistence.
"""

from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import AsyncGenerator, Optional
from uuid import UUID

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, select
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from taskui.logging_config import get_logger

logger = get_logger(__name__)

# Database path in config directory
_PROJECT_ROOT = Path(__file__).parent.parent
_CONFIG_DIR = _PROJECT_ROOT / "config"
_DEFAULT_DB_PATH = _CONFIG_DIR / "taskui.db"
_DEFAULT_DB_URL = f"sqlite+aiosqlite:///{_DEFAULT_DB_PATH}"


class Base(DeclarativeBase):
    """Base class for all ORM models."""
    pass


class TaskListORM(Base):
    """
    SQLAlchemy ORM model for task lists.

    Corresponds to the TaskList Pydantic model, storing list metadata
    in the database.
    """
    __tablename__ = "task_lists"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    # Relationship to tasks
    tasks: Mapped[list["TaskORM"]] = relationship(
        "TaskORM",
        back_populates="task_list",
        cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<TaskListORM(id={self.id}, name={self.name})>"


class TaskORM(Base):
    """
    SQLAlchemy ORM model for tasks.

    Corresponds to the Task Pydantic model, storing task data with support
    for hierarchical nesting through parent_id foreign key.
    """
    __tablename__ = "tasks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    url: Mapped[Optional[str]] = mapped_column(String(2083), nullable=True)

    # Status flags
    is_completed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Hierarchy
    parent_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True, index=True)
    level: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    position: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # Relationships
    list_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("task_lists.id"), nullable=False, index=True
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Relationship to task list
    task_list: Mapped["TaskListORM"] = relationship("TaskListORM", back_populates="tasks")

    # Relationship to diary entries
    diary_entries: Mapped[list["DiaryEntryORM"]] = relationship(
        "DiaryEntryORM",
        back_populates="task",
        cascade="all, delete-orphan",
        order_by="DiaryEntryORM.created_at.desc()"
    )

    def __repr__(self) -> str:
        return f"<TaskORM(id={self.id}, title={self.title}, level={self.level})>"


class DiaryEntryORM(Base):
    """
    SQLAlchemy ORM model for diary entries.

    Stores task diary entries with timestamp tracking and content.
    Linked to tasks via foreign key with CASCADE delete.
    """
    __tablename__ = "diary_entries"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    task_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("tasks.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)

    # Relationship to task
    task: Mapped["TaskORM"] = relationship("TaskORM", back_populates="diary_entries")

    def __repr__(self) -> str:
        return f"<DiaryEntryORM(id={self.id}, task_id={self.task_id})>"


class DatabaseManager:
    """
    Manages database connections and session lifecycle.

    Handles async engine creation, session management, and database
    initialization for both production and testing scenarios.
    """

    def __init__(self, database_url: str = _DEFAULT_DB_URL):
        """
        Initialize database manager with connection URL.

        Args:
            database_url: SQLAlchemy database URL (default: local SQLite file)
        """
        self.database_url = database_url
        self.engine: Optional[AsyncEngine] = None
        self.session_maker: Optional[async_sessionmaker[AsyncSession]] = None

    async def initialize(self) -> None:
        """
        Initialize the database engine and create tables.

        Creates the async engine, session maker, and all tables defined
        in the Base metadata.
        """
        try:
            logger.info(f"Initializing database: {self.database_url}")
            self.engine = create_async_engine(
                self.database_url,
                echo=False,  # Set to True for SQL query logging
                future=True,
            )

            self.session_maker = async_sessionmaker(
                self.engine,
                class_=AsyncSession,
                expire_on_commit=False,
            )

            # Create all tables
            async with self.engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)

            logger.info("Database initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}", exc_info=True)
            raise

    async def close(self) -> None:
        """
        Close the database engine and cleanup resources.
        """
        if self.engine:
            logger.info("Closing database connection")
            try:
                await self.engine.dispose()
                self.engine = None
                self.session_maker = None
                logger.info("Database connection closed successfully")
            except Exception as e:
                logger.error(f"Error closing database connection: {e}", exc_info=True)
                raise

    @asynccontextmanager
    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        """
        Get an async database session with automatic transaction management.

        Yields:
            AsyncSession for database operations

        Example:
            async with db_manager.get_session() as session:
                result = await session.execute(select(TaskORM))
                tasks = result.scalars().all()
        """
        if not self.session_maker:
            raise RuntimeError("DatabaseManager not initialized. Call initialize() first.")

        async with self.session_maker() as session:
            try:
                yield session
                await session.commit()
            except Exception as e:
                logger.error(f"Database session error, rolling back: {e}", exc_info=True)
                await session.rollback()
                raise


# Global database manager instance
_db_manager: Optional[DatabaseManager] = None


def get_database_manager(database_url: str = _DEFAULT_DB_URL) -> DatabaseManager:
    """
    Get or create the global database manager instance.

    Args:
        database_url: SQLAlchemy database URL

    Returns:
        DatabaseManager instance
    """
    global _db_manager
    if _db_manager is None:
        _db_manager = DatabaseManager(database_url)
    return _db_manager


async def init_database(database_url: str = _DEFAULT_DB_URL) -> DatabaseManager:
    """
    Initialize the database and return the manager instance.

    Convenience function for application startup.

    Args:
        database_url: SQLAlchemy database URL

    Returns:
        Initialized DatabaseManager instance
    """
    db_manager = get_database_manager(database_url)
    await db_manager.initialize()
    return db_manager
