"""
Tests for TaskService - task creation and reading operations.

Tests cover CRUD operations, nesting validation, and hierarchy management.
"""

import pytest
from uuid import UUID, uuid4

from taskui.services.task_service import (
    TaskService,
    NestingLimitError,
    TaskNotFoundError,
    TaskListNotFoundError,
)
from taskui.database import TaskORM


class TestTaskServiceCreate:
    """Tests for task creation operations."""

    @pytest.mark.asyncio
    async def test_create_task_basic(self, db_session, sample_task_list, sample_list_id):
        """Test creating a basic top-level task."""
        service = TaskService(db_session)

        task = await service.create_task(
            title="Test Task",
            list_id=sample_list_id,
            notes="Test notes"
        )

        assert task.title == "Test Task"
        assert task.notes == "Test notes"
        assert task.level == 0
        assert task.parent_id is None
        assert task.list_id == sample_list_id
        assert task.position == 0
        assert not task.is_completed

    @pytest.mark.asyncio
    async def test_create_task_saves_to_database(self, db_session, sample_task_list, sample_list_id):
        """Test that created tasks are persisted to database."""
        service = TaskService(db_session)

        task = await service.create_task(
            title="Persisted Task",
            list_id=sample_list_id
        )

        # Verify in database
        retrieved = await service.get_task_by_id(task.id)
        assert retrieved is not None
        assert retrieved.title == "Persisted Task"
        assert retrieved.id == task.id

    @pytest.mark.asyncio
    async def test_create_task_invalid_list(self, db_session):
        """Test creating a task with non-existent list raises error."""
        service = TaskService(db_session)
        fake_list_id = uuid4()

        with pytest.raises(TaskListNotFoundError):
            await service.create_task(
                title="Orphan Task",
                list_id=fake_list_id
            )

    @pytest.mark.asyncio
    async def test_create_task_position_increments(self, db_session, sample_task_list, sample_list_id):
        """Test that positions increment for sibling tasks."""
        service = TaskService(db_session)

        task1 = await service.create_task("Task 1", sample_list_id)
        task2 = await service.create_task("Task 2", sample_list_id)
        task3 = await service.create_task("Task 3", sample_list_id)

        assert task1.position == 0
        assert task2.position == 1
        assert task3.position == 2


class TestTaskServiceCreateChild:
    """Tests for child task creation with nesting validation."""

    @pytest.mark.asyncio
    async def test_create_child_in_column1(self, db_session, sample_task_list, sample_list_id):
        """Test creating a child task."""
        service = TaskService(db_session)

        # Create parent (level 0)
        parent = await service.create_task("Parent Task", sample_list_id)

        # Create child
        child = await service.create_child_task(
            parent_id=parent.id,
            title="Child Task",
            notes="Child notes"
        )

        assert child.title == "Child Task"
        assert child.notes == "Child notes"
        assert child.parent_id == parent.id
        assert child.level == 1
        assert child.list_id == sample_list_id
        assert child.position == 0

    @pytest.mark.asyncio
    async def test_create_child_in_column2(self, db_session, sample_task_list, sample_list_id):
        """Test creating nested children."""
        service = TaskService(db_session)

        # Create parent (level 0)
        parent = await service.create_task("Parent Task", sample_list_id)

        # Create level 1 child
        child = await service.create_child_task(
            parent_id=parent.id,
            title="Level 1 Child"
        )

        assert child.level == 1
        assert child.parent_id == parent.id

        # Create level 2 grandchild
        grandchild = await service.create_child_task(
            parent_id=child.id,
            title="Level 2 Grandchild"
        )

        assert grandchild.level == 2
        assert grandchild.parent_id == child.id

    @pytest.mark.asyncio
    async def test_create_child_exceeds_global_limit(self, db_session, sample_task_list, sample_list_id):
        """Test that global nesting limit (max depth 4) is enforced."""
        service = TaskService(db_session)

        # Create full depth hierarchy (levels 0-4)
        level0 = await service.create_task("Level 0", sample_list_id)
        level1 = await service.create_child_task(level0.id, "Level 1")
        level2 = await service.create_child_task(level1.id, "Level 2")
        level3 = await service.create_child_task(level2.id, "Level 3")
        level4 = await service.create_child_task(level3.id, "Level 4")

        # Try to create level 5 (should fail - exceeds max depth of 4)
        with pytest.raises(NestingLimitError) as exc_info:
            await service.create_child_task(level4.id, "Level 5")

        assert "maximum nesting depth" in str(exc_info.value).lower() or "max depth" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_create_child_nonexistent_parent(self, db_session, sample_task_list):
        """Test creating child with non-existent parent raises error."""
        service = TaskService(db_session)
        fake_parent_id = uuid4()

        with pytest.raises(TaskNotFoundError):
            await service.create_child_task(
                parent_id=fake_parent_id,
                title="Orphan Child"
            )

    @pytest.mark.asyncio
    async def test_create_multiple_children_positions(self, db_session, sample_task_list, sample_list_id):
        """Test that child positions increment correctly."""
        service = TaskService(db_session)

        parent = await service.create_task("Parent", sample_list_id)

        child1 = await service.create_child_task(parent.id, "Child 1")
        child2 = await service.create_child_task(parent.id, "Child 2")
        child3 = await service.create_child_task(parent.id, "Child 3")

        assert child1.position == 0
        assert child2.position == 1
        assert child3.position == 2


class TestTaskServiceRead:
    """Tests for task reading and retrieval operations."""

    @pytest.mark.asyncio
    async def test_get_tasks_for_list(self, db_session, sample_task_list, sample_list_id):
        """Test retrieving all top-level tasks for a list."""
        service = TaskService(db_session)

        # Create multiple tasks
        task1 = await service.create_task("Task 1", sample_list_id)
        task2 = await service.create_task("Task 2", sample_list_id)
        task3 = await service.create_task("Task 3", sample_list_id)

        # Retrieve all tasks
        tasks = await service.get_tasks_for_list(sample_list_id)

        assert len(tasks) == 3
        assert tasks[0].id == task1.id
        assert tasks[1].id == task2.id
        assert tasks[2].id == task3.id

    @pytest.mark.asyncio
    async def test_get_tasks_for_list_ordered_by_position(self, db_session, sample_task_list, sample_list_id):
        """Test that tasks are returned in position order."""
        service = TaskService(db_session)

        # Create tasks
        await service.create_task("First", sample_list_id)
        await service.create_task("Second", sample_list_id)
        await service.create_task("Third", sample_list_id)

        tasks = await service.get_tasks_for_list(sample_list_id)

        assert tasks[0].position == 0
        assert tasks[1].position == 1
        assert tasks[2].position == 2

    @pytest.mark.asyncio
    async def test_get_tasks_for_list_excludes_children(self, db_session, sample_task_list, sample_list_id):
        """Test that get_tasks_for_list only returns top-level tasks."""
        service = TaskService(db_session)

        # Create parent and children
        parent = await service.create_task("Parent", sample_list_id)
        await service.create_child_task(parent.id, "Child 1")
        await service.create_child_task(parent.id, "Child 2")

        # Should only return parent
        tasks = await service.get_tasks_for_list(sample_list_id)
        assert len(tasks) == 1
        assert tasks[0].id == parent.id

    @pytest.mark.asyncio
    async def test_get_tasks_for_nonexistent_list(self, db_session):
        """Test getting tasks for non-existent list raises error."""
        service = TaskService(db_session)
        fake_list_id = uuid4()

        with pytest.raises(TaskListNotFoundError):
            await service.get_tasks_for_list(fake_list_id)

    @pytest.mark.asyncio
    async def test_get_children(self, db_session, sample_task_list, sample_list_id):
        """Test retrieving direct children of a task."""
        service = TaskService(db_session)

        parent = await service.create_task("Parent", sample_list_id)
        child1 = await service.create_child_task(parent.id, "Child 1")
        child2 = await service.create_child_task(parent.id, "Child 2")

        children = await service.get_children(parent.id)

        assert len(children) == 2
        assert children[0].id == child1.id
        assert children[1].id == child2.id
        assert all(child.parent_id == parent.id for child in children)

    @pytest.mark.asyncio
    async def test_get_children_ordered_by_position(self, db_session, sample_task_list, sample_list_id):
        """Test that children are returned in position order."""
        service = TaskService(db_session)

        parent = await service.create_task("Parent", sample_list_id)
        await service.create_child_task(parent.id, "First")
        await service.create_child_task(parent.id, "Second")
        await service.create_child_task(parent.id, "Third")

        children = await service.get_children(parent.id)

        assert children[0].position == 0
        assert children[1].position == 1
        assert children[2].position == 2

    @pytest.mark.asyncio
    async def test_get_children_excludes_grandchildren(self, db_session, sample_task_list, sample_list_id):
        """Test that get_children only returns direct children."""
        service = TaskService(db_session)

        parent = await service.create_task("Parent", sample_list_id)
        child = await service.create_child_task(parent.id, "Child")
        grandchild = await service.create_child_task(child.id, "Grandchild")

        children = await service.get_children(parent.id)

        assert len(children) == 1
        assert children[0].id == child.id

    @pytest.mark.asyncio
    async def test_get_children_nonexistent_parent(self, db_session):
        """Test getting children of non-existent parent raises error."""
        service = TaskService(db_session)
        fake_parent_id = uuid4()

        with pytest.raises(TaskNotFoundError):
            await service.get_children(fake_parent_id)

    @pytest.mark.asyncio
    async def test_get_all_descendants(self, db_session, sample_task_list, sample_list_id):
        """Test retrieving all descendants (children, grandchildren, etc.)."""
        service = TaskService(db_session)

        # Create hierarchy
        parent = await service.create_task("Parent", sample_list_id)
        child1 = await service.create_child_task(parent.id, "Child 1")
        child2 = await service.create_child_task(parent.id, "Child 2")
        grandchild1 = await service.create_child_task(child1.id, "Grandchild 1")
        grandchild2 = await service.create_child_task(child1.id, "Grandchild 2")

        descendants = await service.get_all_descendants(parent.id)

        # Should return all 4 descendants
        assert len(descendants) == 4
        descendant_ids = [d.id for d in descendants]
        assert child1.id in descendant_ids
        assert child2.id in descendant_ids
        assert grandchild1.id in descendant_ids
        assert grandchild2.id in descendant_ids

    @pytest.mark.asyncio
    async def test_get_all_descendants_hierarchical_order(self, db_session, sample_task_list, sample_list_id):
        """Test that descendants are returned in hierarchical (depth-first) order."""
        service = TaskService(db_session)

        # Create hierarchy
        parent = await service.create_task("Parent", sample_list_id)
        child1 = await service.create_child_task(parent.id, "Child 1")
        grandchild1 = await service.create_child_task(child1.id, "Grandchild 1")
        child2 = await service.create_child_task(parent.id, "Child 2")

        descendants = await service.get_all_descendants(parent.id)

        # Should be depth-first: child1, grandchild1, child2
        assert descendants[0].id == child1.id
        assert descendants[1].id == grandchild1.id
        assert descendants[2].id == child2.id

    @pytest.mark.asyncio
    async def test_get_all_descendants_no_children(self, db_session, sample_task_list, sample_list_id):
        """Test getting descendants for task with no children returns empty list."""
        service = TaskService(db_session)

        parent = await service.create_task("Parent", sample_list_id)
        descendants = await service.get_all_descendants(parent.id)

        assert len(descendants) == 0

    @pytest.mark.asyncio
    async def test_get_task_by_id(self, db_session, sample_task_list, sample_list_id):
        """Test retrieving a specific task by ID."""
        service = TaskService(db_session)

        created_task = await service.create_task("Test Task", sample_list_id, notes="Test notes")
        retrieved_task = await service.get_task_by_id(created_task.id)

        assert retrieved_task is not None
        assert retrieved_task.id == created_task.id
        assert retrieved_task.title == "Test Task"
        assert retrieved_task.notes == "Test notes"

    @pytest.mark.asyncio
    async def test_get_task_by_id_nonexistent(self, db_session):
        """Test getting non-existent task returns None."""
        service = TaskService(db_session)
        fake_id = uuid4()

        task = await service.get_task_by_id(fake_id)
        assert task is None


class TestTaskServiceChildCounts:
    """Tests for child count calculations."""

    @pytest.mark.asyncio
    async def test_task_child_counts_updated(self, db_session, sample_task_list, sample_list_id):
        """Test that child counts are populated when retrieving tasks."""
        service = TaskService(db_session)

        parent = await service.create_task("Parent", sample_list_id)
        await service.create_child_task(parent.id, "Child 1")
        await service.create_child_task(parent.id, "Child 2")
        await service.create_child_task(parent.id, "Child 3")

        retrieved_parent = await service.get_task_by_id(parent.id)

        assert retrieved_parent.progress_string == "0/3"
        assert retrieved_parent.completion_percentage == 0.0

    @pytest.mark.asyncio
    async def test_task_completed_child_counts(self, db_session, sample_task_list, sample_list_id):
        """Test that completed child counts are accurate."""
        service = TaskService(db_session)

        parent = await service.create_task("Parent", sample_list_id)
        child1 = await service.create_child_task(parent.id, "Child 1")
        child2 = await service.create_child_task(parent.id, "Child 2")
        child3 = await service.create_child_task(parent.id, "Child 3")

        # Mark two children as completed
        from sqlalchemy import update
        await db_session.execute(
            update(TaskORM)
            .where(TaskORM.id.in_([str(child1.id), str(child2.id)]))
            .values(is_completed=True)
        )
        await db_session.commit()

        retrieved_parent = await service.get_task_by_id(parent.id)

        assert retrieved_parent.progress_string == "2/3"
        assert retrieved_parent.completion_percentage == 66.7

    @pytest.mark.asyncio
    async def test_task_no_children_counts(self, db_session, sample_task_list, sample_list_id):
        """Test that tasks with no children have zero counts."""
        service = TaskService(db_session)

        task = await service.create_task("Childless Task", sample_list_id)
        retrieved_task = await service.get_task_by_id(task.id)

        assert retrieved_task.progress_string == ""
        assert retrieved_task.completion_percentage == 0.0
        assert not retrieved_task.has_children


class TestTaskServiceUpdate:
    """Tests for task update operations."""

    @pytest.mark.asyncio
    async def test_update_task_title(self, db_session, sample_task_list, sample_list_id):
        """Test updating a task's title."""
        service = TaskService(db_session)

        # Create task
        task = await service.create_task("Original Title", sample_list_id)

        # Update title
        updated_task = await service.update_task(task.id, title="Updated Title")

        assert updated_task.id == task.id
        assert updated_task.title == "Updated Title"
        assert updated_task.notes == task.notes

        # Verify in database
        retrieved = await service.get_task_by_id(task.id)
        assert retrieved.title == "Updated Title"

    @pytest.mark.asyncio
    async def test_update_task_notes(self, db_session, sample_task_list, sample_list_id):
        """Test updating a task's notes."""
        service = TaskService(db_session)

        # Create task with notes
        task = await service.create_task("Task", sample_list_id, notes="Original notes")

        # Update notes
        updated_task = await service.update_task(task.id, notes="Updated notes")

        assert updated_task.id == task.id
        assert updated_task.title == "Task"
        assert updated_task.notes == "Updated notes"

        # Verify in database
        retrieved = await service.get_task_by_id(task.id)
        assert retrieved.notes == "Updated notes"

    @pytest.mark.asyncio
    async def test_update_task_both_fields(self, db_session, sample_task_list, sample_list_id):
        """Test updating both title and notes."""
        service = TaskService(db_session)

        task = await service.create_task("Original", sample_list_id, notes="Old notes")

        updated_task = await service.update_task(
            task.id,
            title="New Title",
            notes="New notes"
        )

        assert updated_task.title == "New Title"
        assert updated_task.notes == "New notes"

    @pytest.mark.asyncio
    async def test_update_task_nonexistent(self, db_session):
        """Test updating non-existent task raises error."""
        service = TaskService(db_session)
        fake_id = uuid4()

        with pytest.raises(TaskNotFoundError):
            await service.update_task(fake_id, title="New Title")

    @pytest.mark.asyncio
    async def test_update_task_no_fields(self, db_session, sample_task_list, sample_list_id):
        """Test updating with no fields raises error."""
        service = TaskService(db_session)

        task = await service.create_task("Task", sample_list_id)

        with pytest.raises(ValueError, match="At least one"):
            await service.update_task(task.id)

    @pytest.mark.asyncio
    async def test_update_task_preserves_hierarchy(self, db_session, sample_task_list, sample_list_id):
        """Test that updating doesn't affect task hierarchy."""
        service = TaskService(db_session)

        parent = await service.create_task("Parent", sample_list_id)
        child = await service.create_child_task(parent.id, "Child")

        # Update parent
        await service.update_task(parent.id, title="Updated Parent")

        # Verify hierarchy intact
        children = await service.get_children(parent.id)
        assert len(children) == 1
        assert children[0].id == child.id


class TestTaskServiceDelete:
    """Tests for task deletion operations."""

    @pytest.mark.asyncio
    async def test_delete_task_simple(self, db_session, sample_task_list, sample_list_id):
        """Test deleting a task with no children."""
        service = TaskService(db_session)

        task = await service.create_task("Task to delete", sample_list_id)
        task_id = task.id

        # Delete task
        await service.delete_task(task_id)
        await db_session.commit()

        # Verify deleted
        retrieved = await service.get_task_by_id(task_id)
        assert retrieved is None

    @pytest.mark.asyncio
    async def test_delete_task_with_children(self, db_session, sample_task_list, sample_list_id):
        """Test deleting a task cascades to children."""
        service = TaskService(db_session)

        parent = await service.create_task("Parent", sample_list_id)
        child1 = await service.create_child_task(parent.id, "Child 1")
        child2 = await service.create_child_task(parent.id, "Child 2")

        # Delete parent
        await service.delete_task(parent.id)
        await db_session.commit()

        # Verify all deleted
        assert await service.get_task_by_id(parent.id) is None
        assert await service.get_task_by_id(child1.id) is None
        assert await service.get_task_by_id(child2.id) is None

    @pytest.mark.asyncio
    async def test_delete_task_with_deep_hierarchy(self, db_session, sample_task_list, sample_list_id):
        """Test deleting cascades through deep hierarchy."""
        service = TaskService(db_session)

        # Create hierarchy
        level0 = await service.create_task("Level 0", sample_list_id)
        level1 = await service.create_child_task(level0.id, "Level 1")
        level2 = await service.create_child_task(level1.id, "Level 2")

        # Delete root
        await service.delete_task(level0.id)
        await db_session.commit()

        # Verify all deleted
        assert await service.get_task_by_id(level0.id) is None
        assert await service.get_task_by_id(level1.id) is None
        assert await service.get_task_by_id(level2.id) is None

    @pytest.mark.asyncio
    async def test_delete_task_nonexistent(self, db_session):
        """Test deleting non-existent task raises error."""
        service = TaskService(db_session)
        fake_id = uuid4()

        with pytest.raises(TaskNotFoundError):
            await service.delete_task(fake_id)

    @pytest.mark.asyncio
    async def test_delete_child_preserves_siblings(self, db_session, sample_task_list, sample_list_id):
        """Test deleting one child doesn't affect siblings."""
        service = TaskService(db_session)

        parent = await service.create_task("Parent", sample_list_id)
        child1 = await service.create_child_task(parent.id, "Child 1")
        child2 = await service.create_child_task(parent.id, "Child 2")
        child3 = await service.create_child_task(parent.id, "Child 3")

        # Delete middle child
        await service.delete_task(child2.id)
        await db_session.commit()

        # Verify parent and siblings remain
        assert await service.get_task_by_id(parent.id) is not None
        assert await service.get_task_by_id(child1.id) is not None
        assert await service.get_task_by_id(child2.id) is None
        assert await service.get_task_by_id(child3.id) is not None


class TestTaskServiceMove:
    """Tests for task move operations."""

    @pytest.mark.asyncio
    async def test_move_task_to_different_parent(self, db_session, sample_task_list, sample_list_id):
        """Test moving a task to a different parent."""
        service = TaskService(db_session)

        parent1 = await service.create_task("Parent 1", sample_list_id)
        parent2 = await service.create_task("Parent 2", sample_list_id)
        child = await service.create_child_task(parent1.id, "Child")

        # Move child to parent2
        moved_task = await service.move_task(child.id, new_parent_id=parent2.id)

        assert moved_task.parent_id == parent2.id
        assert moved_task.level == 1

        # Verify hierarchy
        parent1_children = await service.get_children(parent1.id)
        parent2_children = await service.get_children(parent2.id)

        assert len(parent1_children) == 0
        assert len(parent2_children) == 1
        assert parent2_children[0].id == child.id

    @pytest.mark.asyncio
    async def test_move_task_to_top_level(self, db_session, sample_task_list, sample_list_id):
        """Test moving a child task to top level."""
        service = TaskService(db_session)

        parent = await service.create_task("Parent", sample_list_id)
        child = await service.create_child_task(parent.id, "Child")

        # Move to top level
        moved_task = await service.move_task(child.id, new_parent_id=None)

        assert moved_task.parent_id is None
        assert moved_task.level == 0

        # Verify hierarchy
        parent_children = await service.get_children(parent.id)
        top_level_tasks = await service.get_tasks_for_list(sample_list_id)

        assert len(parent_children) == 0
        assert len(top_level_tasks) == 2  # parent and moved child
        assert any(t.id == child.id for t in top_level_tasks)

    @pytest.mark.asyncio
    async def test_move_task_reorder_within_parent(self, db_session, sample_task_list, sample_list_id):
        """Test reordering tasks within same parent."""
        service = TaskService(db_session)

        parent = await service.create_task("Parent", sample_list_id)
        child1 = await service.create_child_task(parent.id, "Child 1")
        child2 = await service.create_child_task(parent.id, "Child 2")
        child3 = await service.create_child_task(parent.id, "Child 3")

        # Move child3 to position 0
        await service.move_task(child3.id, new_parent_id=parent.id, new_position=0)

        # Get children and check order
        children = await service.get_children(parent.id)
        assert children[0].id == child3.id
        assert children[1].id == child1.id
        assert children[2].id == child2.id

        # Check positions
        assert children[0].position == 0
        assert children[1].position == 1
        assert children[2].position == 2

    @pytest.mark.asyncio
    async def test_move_task_updates_descendant_levels(self, db_session, sample_task_list, sample_list_id):
        """Test moving updates levels of all descendants."""
        service = TaskService(db_session)

        # Create hierarchy
        level0 = await service.create_task("Level 0", sample_list_id)
        level1 = await service.create_child_task(level0.id, "Level 1")
        level2 = await service.create_child_task(level1.id, "Level 2")

        # Move level1 to top level
        await service.move_task(level1.id, new_parent_id=None)

        # Verify levels updated
        moved_level1 = await service.get_task_by_id(level1.id)
        moved_level2 = await service.get_task_by_id(level2.id)

        assert moved_level1.level == 0
        assert moved_level2.level == 1

    @pytest.mark.asyncio
    async def test_move_task_prevents_self_parent(self, db_session, sample_task_list, sample_list_id):
        """Test cannot move task to be its own parent."""
        service = TaskService(db_session)

        task = await service.create_task("Task", sample_list_id)

        with pytest.raises(ValueError, match="own parent"):
            await service.move_task(task.id, new_parent_id=task.id)

    @pytest.mark.asyncio
    async def test_move_task_prevents_descendant_parent(self, db_session, sample_task_list, sample_list_id):
        """Test cannot move task to be a child of its own descendant."""
        service = TaskService(db_session)

        parent = await service.create_task("Parent", sample_list_id)
        child = await service.create_child_task(parent.id, "Child")
        grandchild = await service.create_child_task(child.id, "Grandchild")

        with pytest.raises(ValueError, match="descendant of itself"):
            await service.move_task(parent.id, new_parent_id=grandchild.id)

    @pytest.mark.asyncio
    async def test_move_task_enforces_nesting_limit(self, db_session, sample_task_list, sample_list_id):
        """Test move enforces maximum nesting depth."""
        service = TaskService(db_session)

        # Create hierarchy with task that has children
        level0 = await service.create_task("Level 0", sample_list_id)
        level1 = await service.create_child_task(level0.id, "Level 1")
        level2a = await service.create_child_task(level1.id, "Level 2a")
        level2b = await service.create_child_task(level1.id, "Level 2b")

        # Create another hierarchy at max depth
        another_level0 = await service.create_task("Another Level 0", sample_list_id)
        another_level1 = await service.create_child_task(another_level0.id, "Another Level 1")

        # Try to move level1 (which has children at level 2) under another_level1
        # This would make level1 -> level 2, and its children -> level 3 (exceeds limit)
        with pytest.raises(NestingLimitError, match="would exceed maximum"):
            await service.move_task(level1.id, new_parent_id=another_level1.id)

    @pytest.mark.asyncio
    async def test_move_task_nonexistent(self, db_session):
        """Test moving non-existent task raises error."""
        service = TaskService(db_session)
        fake_id = uuid4()

        with pytest.raises(TaskNotFoundError):
            await service.move_task(fake_id, new_parent_id=None)

    @pytest.mark.asyncio
    async def test_move_task_nonexistent_parent(self, db_session, sample_task_list, sample_list_id):
        """Test moving to non-existent parent raises error."""
        service = TaskService(db_session)

        task = await service.create_task("Task", sample_list_id)
        fake_parent_id = uuid4()

        with pytest.raises(TaskNotFoundError):
            await service.move_task(task.id, new_parent_id=fake_parent_id)


class TestTaskServiceIntegration:
    """Integration tests for complex scenarios."""

    @pytest.mark.asyncio
    async def test_full_hierarchy_creation(self, db_session, sample_task_list, sample_list_id):
        """Test creating a complete task hierarchy."""
        service = TaskService(db_session)

        # Create Column 1 hierarchy (max 2 levels)
        sprint = await service.create_task("Sprint Planning", sample_list_id)
        review = await service.create_child_task(sprint.id, "Review backlog")

        # Create Column 2 hierarchy (max 3 levels)
        api = await service.create_task("API Development", sample_list_id)
        auth = await service.create_child_task(api.id, "Auth endpoints")
        session = await service.create_child_task(auth.id, "Session mgmt")

        # Verify hierarchy
        sprint_children = await service.get_children(sprint.id)
        assert len(sprint_children) == 1
        assert sprint_children[0].id == review.id

        api_descendants = await service.get_all_descendants(api.id)
        assert len(api_descendants) == 2
        assert api_descendants[0].id == auth.id
        assert api_descendants[1].id == session.id

    @pytest.mark.asyncio
    async def test_multiple_lists_isolation(self, db_session):
        """Test that tasks from different lists are isolated."""
        from taskui.database import TaskListORM
        from datetime import datetime

        # Create two lists
        list1_id = uuid4()
        list2_id = uuid4()

        list1 = TaskListORM(id=str(list1_id), name="Work", created_at=datetime.utcnow())
        list2 = TaskListORM(id=str(list2_id), name="Personal", created_at=datetime.utcnow())

        db_session.add_all([list1, list2])
        await db_session.commit()

        service = TaskService(db_session)

        # Create tasks in each list
        await service.create_task("Work Task 1", list1_id)
        await service.create_task("Work Task 2", list1_id)
        await service.create_task("Personal Task 1", list2_id)

        # Verify isolation
        work_tasks = await service.get_tasks_for_list(list1_id)
        personal_tasks = await service.get_tasks_for_list(list2_id)

        assert len(work_tasks) == 2
        assert len(personal_tasks) == 1
        assert all(task.list_id == list1_id for task in work_tasks)
        assert all(task.list_id == list2_id for task in personal_tasks)


class TestTaskServiceToggleCompletion:
    """Tests for task completion toggle operations."""

    @pytest.mark.asyncio
    async def test_toggle_completion_incomplete_to_complete(self, db_session, sample_task_list, sample_list_id):
        """Test toggling an incomplete task to complete."""
        service = TaskService(db_session)

        # Create a task
        task = await service.create_task(
            title="Test Task",
            list_id=sample_list_id
        )

        # Verify initial state
        assert not task.is_completed
        assert task.completed_at is None

        # Toggle to complete
        updated_task = await service.toggle_completion(task.id)

        # Verify completion
        assert updated_task.is_completed
        assert updated_task.completed_at is not None

    @pytest.mark.asyncio
    async def test_toggle_completion_complete_to_incomplete(self, db_session, sample_task_list, sample_list_id):
        """Test toggling a complete task to incomplete."""
        service = TaskService(db_session)

        # Create and complete a task
        task = await service.create_task(
            title="Test Task",
            list_id=sample_list_id
        )
        completed_task = await service.toggle_completion(task.id)
        assert completed_task.is_completed

        # Toggle back to incomplete
        updated_task = await service.toggle_completion(task.id)

        # Verify incompletion
        assert not updated_task.is_completed
        assert updated_task.completed_at is None

    @pytest.mark.asyncio
    async def test_toggle_completion_persistence(self, db_session, sample_task_list, sample_list_id):
        """Test that completion status persists to database."""
        service = TaskService(db_session)

        # Create a task
        task = await service.create_task(
            title="Test Task",
            list_id=sample_list_id
        )

        # Toggle to complete
        await service.toggle_completion(task.id)
        await db_session.commit()

        # Retrieve from database
        retrieved_task = await service.get_task_by_id(task.id)

        # Verify persistence
        assert retrieved_task.is_completed
        assert retrieved_task.completed_at is not None

    @pytest.mark.asyncio
    async def test_toggle_completion_nonexistent_task(self, db_session):
        """Test toggling completion on a non-existent task raises error."""
        service = TaskService(db_session)

        # Try to toggle a non-existent task
        with pytest.raises(TaskNotFoundError):
            await service.toggle_completion(uuid4())
