"""
Tests for export/import service (Sync V2 foundation).

Tests the core export/import functionality that forms the basis of V2 sync.
"""

import pytest
import pytest_asyncio
from datetime import datetime, timezone
from uuid import uuid4

from taskui.export_schema import (
    ConflictStrategy,
    ExportedList,
    ExportedState,
    ExportedTask,
    CURRENT_SCHEMA_VERSION,
    migrate_data,
)
from taskui.services.export_import import ExportImportService
from taskui.services.list_service import ListService
from taskui.services.task_service import TaskService


# ==============================================================================
# SCHEMA TESTS
# ==============================================================================


class TestExportSchema:
    """Tests for export schema models."""

    def test_exported_task_basic(self):
        """ExportedTask can be created with minimal fields."""
        task = ExportedTask(
            id=uuid4(),
            title="Test Task",
            is_completed=False,
            position=0,
            created_at=datetime.now(timezone.utc),
        )
        assert task.title == "Test Task"
        assert task.children == []

    def test_exported_task_with_children(self):
        """ExportedTask can contain nested children."""
        child = ExportedTask(
            id=uuid4(),
            title="Child Task",
            is_completed=False,
            position=0,
            created_at=datetime.now(timezone.utc),
        )
        parent = ExportedTask(
            id=uuid4(),
            title="Parent Task",
            is_completed=False,
            position=0,
            created_at=datetime.now(timezone.utc),
            children=[child],
        )
        assert len(parent.children) == 1
        assert parent.children[0].title == "Child Task"

    def test_exported_list_basic(self):
        """ExportedList can be created with minimal fields."""
        task_list = ExportedList(
            id=uuid4(),
            name="Work",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        assert task_list.name == "Work"
        assert task_list.tasks == []

    def test_exported_state_basic(self):
        """ExportedState can be created with minimal fields."""
        state = ExportedState(
            client_id="test-client",
        )
        assert state.schema_version == CURRENT_SCHEMA_VERSION
        assert state.client_id == "test-client"
        assert state.lists == []

    def test_schema_version(self):
        """Current schema version is set correctly."""
        assert CURRENT_SCHEMA_VERSION == 1


class TestMigration:
    """Tests for schema migration."""

    def test_migrate_data_preserves_unknown_fields(self):
        """Migration preserves unknown fields for forward compatibility."""
        data = {
            "schema_version": 1,
            "client_id": "test",
            "lists": [],
            "unknown_field": "preserved",
        }
        migrated = migrate_data(data)
        assert migrated["unknown_field"] == "preserved"

    def test_migrate_data_updates_version(self):
        """Migration updates schema version to current."""
        data = {
            "schema_version": 0,
            "client_id": "test",
            "lists": [],
        }
        migrated = migrate_data(data)
        assert migrated["schema_version"] == CURRENT_SCHEMA_VERSION


# ==============================================================================
# EXPORT TESTS
# ==============================================================================


class TestExport:
    """Tests for export functionality."""

    @pytest_asyncio.fixture
    async def export_service(self, db_session):
        """Create export service with test database."""
        return ExportImportService(db_session, "test-client")

    @pytest_asyncio.fixture
    async def populated_db(self, db_session, sample_list_id):
        """Create a database with sample data for export tests."""
        list_service = ListService(db_session)
        task_service = TaskService(db_session)

        # Create a list
        await list_service.create_list("Work", list_id=sample_list_id)

        # Create some tasks
        task1 = await task_service.create_task(
            title="Task 1",
            list_id=sample_list_id,
            notes="First task",
        )
        task2 = await task_service.create_task(
            title="Task 2",
            list_id=sample_list_id,
        )

        # Create a child task
        child = await task_service.create_task(
            title="Child Task",
            list_id=sample_list_id,
            parent_id=task1.id,
        )

        return {
            "list_id": sample_list_id,
            "task1_id": task1.id,
            "task2_id": task2.id,
            "child_id": child.id,
        }

    async def test_export_empty_database(self, export_service):
        """Export returns empty state for empty database."""
        state = await export_service.export_all_lists()

        assert state.schema_version == CURRENT_SCHEMA_VERSION
        assert state.client_id == "test-client"
        assert state.lists == []

    async def test_export_list_with_tasks(self, export_service, populated_db):
        """Export includes tasks as nested tree."""
        exported_list = await export_service.export_list(populated_db["list_id"])

        assert exported_list.name == "Work"
        assert len(exported_list.tasks) == 2  # Only top-level tasks

        # Find the task with children
        task_with_child = next(
            (t for t in exported_list.tasks if t.title == "Task 1"),
            None
        )
        assert task_with_child is not None
        assert len(task_with_child.children) == 1
        assert task_with_child.children[0].title == "Child Task"

    async def test_export_all_lists(self, export_service, populated_db):
        """Export all lists returns complete state."""
        state = await export_service.export_all_lists()

        assert len(state.lists) == 1
        assert state.lists[0].name == "Work"

    async def test_export_preserves_task_fields(self, export_service, populated_db):
        """Export preserves all task fields."""
        exported_list = await export_service.export_list(populated_db["list_id"])

        task1 = next(t for t in exported_list.tasks if t.title == "Task 1")
        assert task1.notes == "First task"
        assert task1.is_completed is False
        assert task1.created_at is not None


# ==============================================================================
# IMPORT TESTS
# ==============================================================================


class TestImport:
    """Tests for import functionality."""

    @pytest_asyncio.fixture
    async def import_service(self, db_session):
        """Create import service with test database."""
        return ExportImportService(db_session, "test-client")

    def make_export_data(self, lists=None):
        """Create valid export data for testing."""
        return {
            "schema_version": CURRENT_SCHEMA_VERSION,
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "client_id": "remote-client",
            "lists": lists or [],
        }

    def make_list_data(self, name="Work", tasks=None):
        """Create valid list data for testing."""
        return {
            "id": str(uuid4()),
            "name": name,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "tasks": tasks or [],
        }

    def make_task_data(self, title="Task", children=None):
        """Create valid task data for testing."""
        return {
            "id": str(uuid4()),
            "title": title,
            "notes": None,
            "url": None,
            "is_completed": False,
            "position": 0,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "completed_at": None,
            "children": children or [],
        }

    async def test_import_empty_state(self, import_service):
        """Import empty state completes without error."""
        data = self.make_export_data([])
        imported, skipped, conflicts = await import_service.import_all_lists(data)

        assert imported == 0
        assert skipped == 0
        assert conflicts == []

    async def test_import_single_list(self, import_service, db_session):
        """Import creates new list."""
        list_data = self.make_list_data("Work")
        data = self.make_export_data([list_data])

        imported, skipped, conflicts = await import_service.import_all_lists(data)

        assert imported == 1
        assert skipped == 0

        # Verify list was created
        list_service = ListService(db_session)
        lists = await list_service.get_all_lists()
        assert len(lists) == 1
        assert lists[0].name == "Work"

    async def test_import_list_with_tasks(self, import_service, db_session):
        """Import creates tasks with hierarchy."""
        child_task = self.make_task_data("Child")
        parent_task = self.make_task_data("Parent", children=[child_task])
        list_data = self.make_list_data("Work", tasks=[parent_task])
        data = self.make_export_data([list_data])

        imported, skipped, conflicts = await import_service.import_all_lists(data)

        assert imported == 1

        # Verify tasks were created
        list_service = ListService(db_session)
        task_service = TaskService(db_session)

        lists = await list_service.get_all_lists()
        tasks = await task_service.get_all_tasks_for_list(lists[0].id)

        assert len(tasks) == 2
        parent = next(t for t in tasks if t.title == "Parent")
        child = next(t for t in tasks if t.title == "Child")
        assert child.parent_id == parent.id

    async def test_import_conflict_newer_wins_remote_newer(
        self, import_service, db_session
    ):
        """NEWER_WINS imports when remote is newer."""
        # Create local list first
        list_service = ListService(db_session)
        local_list = await list_service.create_list("Work")

        # Create import data with newer timestamp
        from datetime import timedelta
        remote_updated = datetime.now(timezone.utc) + timedelta(hours=1)

        list_data = {
            "id": str(local_list.id),
            "name": "Work Updated",
            "created_at": local_list.created_at.isoformat(),
            "updated_at": remote_updated.isoformat(),
            "tasks": [],
        }
        data = self.make_export_data([list_data])

        imported, skipped, conflicts = await import_service.import_all_lists(
            data, ConflictStrategy.NEWER_WINS
        )

        assert imported == 1

    async def test_import_conflict_local_wins(self, import_service, db_session):
        """LOCAL_WINS skips import when list exists."""
        # Create local list first
        list_service = ListService(db_session)
        local_list = await list_service.create_list("Work")

        # Create import data with same list ID
        list_data = {
            "id": str(local_list.id),
            "name": "Work Remote",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "tasks": [],
        }
        data = self.make_export_data([list_data])

        imported, skipped, conflicts = await import_service.import_all_lists(
            data, ConflictStrategy.LOCAL_WINS
        )

        assert imported == 0
        assert skipped == 1
        assert len(conflicts) == 1

        # Verify local list unchanged
        lists = await list_service.get_all_lists()
        assert lists[0].name == "Work"

    async def test_import_conflict_remote_wins(self, import_service, db_session):
        """REMOTE_WINS always imports."""
        # Create local list first
        list_service = ListService(db_session)
        local_list = await list_service.create_list("Work Local")

        # Create import data with same list ID
        list_data = {
            "id": str(local_list.id),
            "name": "Work Remote",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "tasks": [],
        }
        data = self.make_export_data([list_data])

        imported, skipped, conflicts = await import_service.import_all_lists(
            data, ConflictStrategy.REMOTE_WINS
        )

        assert imported == 1

        # Verify remote list imported
        lists = await list_service.get_all_lists()
        assert lists[0].name == "Work Remote"


# ==============================================================================
# ROUND-TRIP TESTS
# ==============================================================================


class TestRoundTrip:
    """Tests for export/import round-trip."""

    @pytest_asyncio.fixture
    async def services(self, db_session):
        """Create services for round-trip testing."""
        return {
            "export_import": ExportImportService(db_session, "test-client"),
            "list": ListService(db_session),
            "task": TaskService(db_session),
        }

    async def test_round_trip_preserves_data(self, services, db_session):
        """Export then import preserves all data."""
        # Create original data
        task_list = await services["list"].create_list("Work")
        task1 = await services["task"].create_task(
            title="Task 1",
            list_id=task_list.id,
            notes="Notes for task 1",
        )
        child = await services["task"].create_task(
            title="Child",
            list_id=task_list.id,
            parent_id=task1.id,
        )

        # Export
        state = await services["export_import"].export_all_lists()
        export_data = state.model_dump(mode="json")

        # Clear database (simulate importing to different client)
        await services["list"].delete_list(task_list.id)

        # Import
        await services["export_import"].import_all_lists(export_data)

        # Verify data preserved
        lists = await services["list"].get_all_lists()
        assert len(lists) == 1
        assert lists[0].name == "Work"

        tasks = await services["task"].get_all_tasks_for_list(lists[0].id)
        assert len(tasks) == 2

        imported_task1 = next(t for t in tasks if t.title == "Task 1")
        assert imported_task1.notes == "Notes for task 1"

        imported_child = next(t for t in tasks if t.title == "Child")
        assert imported_child.parent_id == imported_task1.id

    async def test_round_trip_preserves_hierarchy(self, services, db_session):
        """Round-trip preserves multi-level hierarchy."""
        # Create 3-level hierarchy
        task_list = await services["list"].create_list("Work")
        level0 = await services["task"].create_task(
            title="Level 0",
            list_id=task_list.id,
        )
        level1 = await services["task"].create_task(
            title="Level 1",
            list_id=task_list.id,
            parent_id=level0.id,
        )
        level2 = await services["task"].create_task(
            title="Level 2",
            list_id=task_list.id,
            parent_id=level1.id,
        )

        # Export and import
        state = await services["export_import"].export_all_lists()
        export_data = state.model_dump(mode="json")

        await services["list"].delete_list(task_list.id)
        await services["export_import"].import_all_lists(export_data)

        # Verify hierarchy
        lists = await services["list"].get_all_lists()
        tasks = await services["task"].get_all_tasks_for_list(lists[0].id)

        imported_l0 = next(t for t in tasks if t.title == "Level 0")
        imported_l1 = next(t for t in tasks if t.title == "Level 1")
        imported_l2 = next(t for t in tasks if t.title == "Level 2")

        assert imported_l0.level == 0
        assert imported_l0.parent_id is None

        assert imported_l1.level == 1
        assert imported_l1.parent_id == imported_l0.id

        assert imported_l2.level == 2
        assert imported_l2.parent_id == imported_l1.id
