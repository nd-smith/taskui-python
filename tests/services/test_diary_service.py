"""
Tests for DiaryService - CRUD operations for task diary entries.

Tests cover creation, reading, updating, and deleting diary entries,
as well as task relationship validation and cascade deletion.
"""

import pytest
from uuid import UUID, uuid4
from datetime import datetime

from taskui.services.diary_service import (
    DiaryService,
    DiaryEntryNotFoundError,
    TaskNotFoundError,
)
from taskui.database import DiaryEntryORM, TaskORM


class TestDiaryServiceCreate:
    """Tests for diary entry creation operations."""

    @pytest.mark.asyncio
    async def test_create_entry_basic(self, db_session, sample_task, sample_task_id):
        """Test creating a basic diary entry."""
        service = DiaryService(db_session)

        entry = await service.create_entry(
            task_id=sample_task_id,
            content="First diary entry for this task"
        )

        assert entry.task_id == sample_task_id
        assert entry.content == "First diary entry for this task"
        assert entry.id is not None
        assert entry.created_at is not None
        assert isinstance(entry.created_at, datetime)

    @pytest.mark.asyncio
    async def test_create_entry_saves_to_database(self, db_session, sample_task, sample_task_id):
        """Test that created entries are persisted to database."""
        service = DiaryService(db_session)

        entry = await service.create_entry(
            task_id=sample_task_id,
            content="Persisted diary entry"
        )

        # Verify in database
        retrieved = await service.get_entry_by_id(entry.id)
        assert retrieved is not None
        assert retrieved.content == "Persisted diary entry"
        assert retrieved.id == entry.id
        assert retrieved.task_id == sample_task_id

    @pytest.mark.asyncio
    async def test_create_entry_invalid_task(self, db_session):
        """Test creating an entry with non-existent task raises error."""
        service = DiaryService(db_session)
        fake_task_id = uuid4()

        with pytest.raises(TaskNotFoundError):
            await service.create_entry(
                task_id=fake_task_id,
                content="Entry for non-existent task"
            )

    @pytest.mark.asyncio
    async def test_create_entry_with_long_content(self, db_session, sample_task, sample_task_id):
        """Test creating an entry with maximum length content."""
        service = DiaryService(db_session)
        long_content = "A" * 2000  # Max length is 2000

        entry = await service.create_entry(
            task_id=sample_task_id,
            content=long_content
        )

        assert len(entry.content) == 2000
        assert entry.content == long_content

    @pytest.mark.asyncio
    async def test_create_multiple_entries_for_same_task(self, db_session, sample_task, sample_task_id):
        """Test creating multiple entries for the same task."""
        service = DiaryService(db_session)

        entry1 = await service.create_entry(sample_task_id, "First entry")
        entry2 = await service.create_entry(sample_task_id, "Second entry")
        entry3 = await service.create_entry(sample_task_id, "Third entry")

        assert entry1.task_id == sample_task_id
        assert entry2.task_id == sample_task_id
        assert entry3.task_id == sample_task_id
        assert entry1.id != entry2.id != entry3.id


class TestDiaryServiceRead:
    """Tests for diary entry reading operations."""

    @pytest.mark.asyncio
    async def test_get_entries_for_task_empty(self, db_session, sample_task, sample_task_id):
        """Test getting entries for a task with no entries."""
        service = DiaryService(db_session)

        entries = await service.get_entries_for_task(sample_task_id)

        assert entries == []

    @pytest.mark.asyncio
    async def test_get_entries_for_task_with_entries(self, db_session, sample_task, sample_task_id):
        """Test getting entries for a task with multiple entries."""
        service = DiaryService(db_session)

        # Create entries in sequence
        entry1 = await service.create_entry(sample_task_id, "First entry")
        entry2 = await service.create_entry(sample_task_id, "Second entry")
        entry3 = await service.create_entry(sample_task_id, "Third entry")

        # Get entries (should be newest first)
        entries = await service.get_entries_for_task(sample_task_id)

        assert len(entries) == 3
        # Verify newest first ordering
        assert entries[0].content == "Third entry"
        assert entries[1].content == "Second entry"
        assert entries[2].content == "First entry"

    @pytest.mark.asyncio
    async def test_get_entries_for_task_with_limit(self, db_session, sample_task, sample_task_id):
        """Test getting entries with limit parameter."""
        service = DiaryService(db_session)

        # Create 5 entries
        for i in range(5):
            await service.create_entry(sample_task_id, f"Entry {i+1}")

        # Get only 3 most recent
        entries = await service.get_entries_for_task(sample_task_id, limit=3)

        assert len(entries) == 3
        # Should get entries 5, 4, 3 (newest first)
        assert entries[0].content == "Entry 5"
        assert entries[1].content == "Entry 4"
        assert entries[2].content == "Entry 3"

    @pytest.mark.asyncio
    async def test_get_entries_for_task_default_limit(self, db_session, sample_task, sample_task_id):
        """Test that default limit is 3."""
        service = DiaryService(db_session)

        # Create 10 entries
        for i in range(10):
            await service.create_entry(sample_task_id, f"Entry {i+1}")

        # Get with default limit
        entries = await service.get_entries_for_task(sample_task_id)

        assert len(entries) == 3  # Default limit

    @pytest.mark.asyncio
    async def test_get_entries_for_invalid_task(self, db_session):
        """Test getting entries for non-existent task raises error."""
        service = DiaryService(db_session)
        fake_task_id = uuid4()

        with pytest.raises(TaskNotFoundError):
            await service.get_entries_for_task(fake_task_id)

    @pytest.mark.asyncio
    async def test_get_entry_by_id_exists(self, db_session, sample_task, sample_task_id):
        """Test getting a specific entry by ID."""
        service = DiaryService(db_session)

        entry = await service.create_entry(sample_task_id, "Test entry")
        retrieved = await service.get_entry_by_id(entry.id)

        assert retrieved is not None
        assert retrieved.id == entry.id
        assert retrieved.content == "Test entry"
        assert retrieved.task_id == sample_task_id

    @pytest.mark.asyncio
    async def test_get_entry_by_id_not_exists(self, db_session):
        """Test getting a non-existent entry by ID returns None."""
        service = DiaryService(db_session)
        fake_entry_id = uuid4()

        retrieved = await service.get_entry_by_id(fake_entry_id)

        assert retrieved is None


class TestDiaryServiceUpdate:
    """Tests for diary entry update operations."""

    @pytest.mark.asyncio
    async def test_update_entry_success(self, db_session, sample_task, sample_task_id):
        """Test updating an entry's content."""
        service = DiaryService(db_session)

        # Create entry
        entry = await service.create_entry(sample_task_id, "Original content")

        # Update content
        updated = await service.update_entry(entry.id, "Updated content")

        assert updated.id == entry.id
        assert updated.content == "Updated content"
        assert updated.task_id == sample_task_id

        # Verify in database
        retrieved = await service.get_entry_by_id(entry.id)
        assert retrieved.content == "Updated content"

    @pytest.mark.asyncio
    async def test_update_entry_not_found(self, db_session):
        """Test updating a non-existent entry raises error."""
        service = DiaryService(db_session)
        fake_entry_id = uuid4()

        with pytest.raises(DiaryEntryNotFoundError):
            await service.update_entry(fake_entry_id, "New content")

    @pytest.mark.asyncio
    async def test_update_entry_empty_content(self, db_session, sample_task, sample_task_id):
        """Test updating entry with empty content raises validation error."""
        service = DiaryService(db_session)

        entry = await service.create_entry(sample_task_id, "Original content")

        # Empty content should fail Pydantic validation when converting back
        with pytest.raises(Exception):  # ValidationError from Pydantic
            updated = await service.update_entry(entry.id, "")


class TestDiaryServiceDelete:
    """Tests for diary entry deletion operations."""

    @pytest.mark.asyncio
    async def test_delete_entry_success(self, db_session, sample_task, sample_task_id):
        """Test deleting an entry."""
        service = DiaryService(db_session)

        # Create entry
        entry = await service.create_entry(sample_task_id, "Entry to delete")

        # Verify exists
        assert await service.get_entry_by_id(entry.id) is not None

        # Delete entry
        await service.delete_entry(entry.id)
        await db_session.commit()

        # Verify deleted
        assert await service.get_entry_by_id(entry.id) is None

    @pytest.mark.asyncio
    async def test_delete_entry_not_found(self, db_session):
        """Test deleting a non-existent entry raises error."""
        service = DiaryService(db_session)
        fake_entry_id = uuid4()

        with pytest.raises(DiaryEntryNotFoundError):
            await service.delete_entry(fake_entry_id)

    @pytest.mark.asyncio
    async def test_delete_entry_does_not_affect_others(self, db_session, sample_task, sample_task_id):
        """Test deleting one entry doesn't affect other entries."""
        service = DiaryService(db_session)

        # Create multiple entries
        entry1 = await service.create_entry(sample_task_id, "Entry 1")
        entry2 = await service.create_entry(sample_task_id, "Entry 2")
        entry3 = await service.create_entry(sample_task_id, "Entry 3")

        # Delete middle entry
        await service.delete_entry(entry2.id)
        await db_session.commit()

        # Verify others still exist
        assert await service.get_entry_by_id(entry1.id) is not None
        assert await service.get_entry_by_id(entry2.id) is None
        assert await service.get_entry_by_id(entry3.id) is not None


class TestDiaryServiceCascade:
    """Tests for cascade deletion when tasks are deleted."""

    @pytest.mark.asyncio
    async def test_cascade_delete_on_task_deletion(self, db_session, sample_task_list, sample_list_id):
        """Test that diary entries are deleted when their task is deleted."""
        from taskui.services.task_service import TaskService

        diary_service = DiaryService(db_session)
        task_service = TaskService(db_session)

        # Create a task
        task = await task_service.create_task("Task with entries", sample_list_id)

        # Create diary entries
        entry1 = await diary_service.create_entry(task.id, "Entry 1")
        entry2 = await diary_service.create_entry(task.id, "Entry 2")
        entry3 = await diary_service.create_entry(task.id, "Entry 3")

        # Verify entries exist
        entries = await diary_service.get_entries_for_task(task.id)
        assert len(entries) == 3

        # Delete the task (this should cascade to diary entries)
        await task_service.delete_task(task.id)
        await db_session.commit()

        # Verify entries are gone
        assert await diary_service.get_entry_by_id(entry1.id) is None
        assert await diary_service.get_entry_by_id(entry2.id) is None
        assert await diary_service.get_entry_by_id(entry3.id) is None


class TestDiaryServiceEdgeCases:
    """Tests for edge cases and validation."""

    @pytest.mark.asyncio
    async def test_create_entry_with_special_characters(self, db_session, sample_task, sample_task_id):
        """Test creating entry with special characters and unicode."""
        service = DiaryService(db_session)

        content = "Special chars: @#$%^&*() 日本語 emoji 🎉 newlines\n\nand tabs\t\there"
        entry = await service.create_entry(sample_task_id, content)

        assert entry.content == content

        # Verify retrieval
        retrieved = await service.get_entry_by_id(entry.id)
        assert retrieved.content == content

    @pytest.mark.asyncio
    async def test_entries_ordered_by_created_at(self, db_session, sample_task, sample_task_id):
        """Test that entries are consistently ordered by created_at desc."""
        service = DiaryService(db_session)

        # Create entries with slight delays to ensure different timestamps
        import asyncio
        entries_created = []
        for i in range(5):
            entry = await service.create_entry(sample_task_id, f"Entry {i}")
            entries_created.append(entry)
            await asyncio.sleep(0.01)  # Small delay to ensure timestamp difference

        # Get all entries
        entries = await service.get_entries_for_task(sample_task_id, limit=10)

        # Verify newest first ordering
        for i in range(len(entries) - 1):
            assert entries[i].created_at >= entries[i + 1].created_at

    @pytest.mark.asyncio
    async def test_update_preserves_task_id_and_created_at(self, db_session, sample_task, sample_task_id):
        """Test that updating content doesn't change task_id or created_at."""
        service = DiaryService(db_session)

        entry = await service.create_entry(sample_task_id, "Original")
        original_task_id = entry.task_id
        # Store as naive datetime for comparison (DB returns naive)
        original_created_at_naive = entry.created_at.replace(tzinfo=None)

        # Update content
        updated = await service.update_entry(entry.id, "Updated")

        assert updated.task_id == original_task_id
        # Compare naive datetimes (DB stores without timezone info)
        assert updated.created_at.replace(tzinfo=None) == original_created_at_naive

    @pytest.mark.asyncio
    async def test_get_entries_with_zero_limit(self, db_session, sample_task, sample_task_id):
        """Test getting entries with limit=0 returns empty list."""
        service = DiaryService(db_session)

        # Create entries
        await service.create_entry(sample_task_id, "Entry 1")
        await service.create_entry(sample_task_id, "Entry 2")

        # Get with limit 0
        entries = await service.get_entries_for_task(sample_task_id, limit=0)

        assert entries == []

    @pytest.mark.asyncio
    async def test_multiple_tasks_with_entries(self, db_session, sample_task_list, sample_list_id):
        """Test that entries are isolated between different tasks."""
        from taskui.services.task_service import TaskService

        diary_service = DiaryService(db_session)
        task_service = TaskService(db_session)

        # Create two tasks
        task1 = await task_service.create_task("Task 1", sample_list_id)
        task2 = await task_service.create_task("Task 2", sample_list_id)

        # Create entries for each task
        await diary_service.create_entry(task1.id, "Task 1 Entry 1")
        await diary_service.create_entry(task1.id, "Task 1 Entry 2")
        await diary_service.create_entry(task2.id, "Task 2 Entry 1")

        # Verify entries are isolated
        task1_entries = await diary_service.get_entries_for_task(task1.id)
        task2_entries = await diary_service.get_entries_for_task(task2.id)

        assert len(task1_entries) == 2
        assert len(task2_entries) == 1
        assert all(e.task_id == task1.id for e in task1_entries)
        assert all(e.task_id == task2.id for e in task2_entries)
