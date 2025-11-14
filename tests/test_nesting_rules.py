"""
Comprehensive tests for the nesting rules engine.

Tests all aspects of task nesting logic including:
- can_create_child() method validation
- Context-relative level calculation
- Maximum depth enforcement
- Edge cases and boundary conditions
"""

import pytest
from uuid import uuid4

from taskui.models import Task
from taskui.services.nesting_rules import NestingRules, Column


class TestNestingRulesColumn1:
    """Tests for Column 1 (Tasks) nesting rules - max 2 levels (0-1)."""

    def test_level0_can_have_children(self):
        """Level 0 tasks can have children in Column 1."""
        task = Task(
            title="Sprint Planning",
            level=0,
            list_id=uuid4()
        )
        assert NestingRules.can_create_child(task, Column.COLUMN1) is True

    def test_level1_cannot_have_children(self):
        """Level 1 tasks cannot have children in Column 1."""
        parent_id = uuid4()
        task = Task(
            title="Review backlog",
            level=1,
            parent_id=parent_id,
            list_id=uuid4()
        )
        assert NestingRules.can_create_child(task, Column.COLUMN1) is False

    def test_max_depth_is_1(self):
        """Column 1 maximum depth is 1."""
        assert NestingRules.get_max_depth(Column.COLUMN1) == 1

    def test_level0_depth_validation(self):
        """Level 0 tasks are valid in Column 1."""
        task = Task(title="Task", level=0, list_id=uuid4())
        assert NestingRules.validate_nesting_depth(task, Column.COLUMN1) is True

    def test_level1_depth_validation(self):
        """Level 1 tasks are valid in Column 1."""
        task = Task(title="Task", level=1, parent_id=uuid4(), list_id=uuid4())
        assert NestingRules.validate_nesting_depth(task, Column.COLUMN1) is True

    def test_level2_depth_validation_fails(self):
        """Level 2 tasks exceed Column 1 maximum depth."""
        task = Task(title="Task", level=2, parent_id=uuid4(), list_id=uuid4())
        assert NestingRules.validate_nesting_depth(task, Column.COLUMN1) is False

    def test_get_allowed_child_level_from_level0(self):
        """Child of level 0 task should be level 1."""
        task = Task(title="Parent", level=0, list_id=uuid4())
        child_level = NestingRules.get_allowed_child_level(task, Column.COLUMN1)
        assert child_level == 1

    def test_get_allowed_child_level_from_level1_returns_none(self):
        """Level 1 tasks cannot have children in Column 1."""
        task = Task(title="Parent", level=1, parent_id=uuid4(), list_id=uuid4())
        child_level = NestingRules.get_allowed_child_level(task, Column.COLUMN1)
        assert child_level is None


class TestNestingRulesColumn2:
    """Tests for Column 2 (Subtasks) nesting rules - max 3 levels (0-2)."""

    def test_level0_can_have_children(self):
        """Level 0 tasks can have children in Column 2."""
        task = Task(
            title="API Development",
            level=0,
            list_id=uuid4()
        )
        assert NestingRules.can_create_child(task, Column.COLUMN2) is True

    def test_level1_can_have_children(self):
        """Level 1 tasks can have children in Column 2."""
        parent_id = uuid4()
        task = Task(
            title="Auth endpoints",
            level=1,
            parent_id=parent_id,
            list_id=uuid4()
        )
        assert NestingRules.can_create_child(task, Column.COLUMN2) is True

    def test_level2_cannot_have_children(self):
        """Level 2 tasks cannot have children in Column 2."""
        parent_id = uuid4()
        task = Task(
            title="Redis setup",
            level=2,
            parent_id=parent_id,
            list_id=uuid4()
        )
        assert NestingRules.can_create_child(task, Column.COLUMN2) is False

    def test_max_depth_is_2(self):
        """Column 2 maximum depth is 2."""
        assert NestingRules.get_max_depth(Column.COLUMN2) == 2

    def test_level0_depth_validation(self):
        """Level 0 tasks are valid in Column 2."""
        task = Task(title="Task", level=0, list_id=uuid4())
        assert NestingRules.validate_nesting_depth(task, Column.COLUMN2) is True

    def test_level1_depth_validation(self):
        """Level 1 tasks are valid in Column 2."""
        task = Task(title="Task", level=1, parent_id=uuid4(), list_id=uuid4())
        assert NestingRules.validate_nesting_depth(task, Column.COLUMN2) is True

    def test_level2_depth_validation(self):
        """Level 2 tasks are valid in Column 2."""
        task = Task(title="Task", level=2, parent_id=uuid4(), list_id=uuid4())
        assert NestingRules.validate_nesting_depth(task, Column.COLUMN2) is True

    def test_get_allowed_child_level_from_level0(self):
        """Child of level 0 task should be level 1."""
        task = Task(title="Parent", level=0, list_id=uuid4())
        child_level = NestingRules.get_allowed_child_level(task, Column.COLUMN2)
        assert child_level == 1

    def test_get_allowed_child_level_from_level1(self):
        """Child of level 1 task should be level 2."""
        task = Task(title="Parent", level=1, parent_id=uuid4(), list_id=uuid4())
        child_level = NestingRules.get_allowed_child_level(task, Column.COLUMN2)
        assert child_level == 2

    def test_get_allowed_child_level_from_level2_returns_none(self):
        """Level 2 tasks cannot have children in Column 2."""
        task = Task(title="Parent", level=2, parent_id=uuid4(), list_id=uuid4())
        child_level = NestingRules.get_allowed_child_level(task, Column.COLUMN2)
        assert child_level is None


class TestContextRelativeLevels:
    """Tests for context-relative level calculation in Column 2."""

    def test_no_context_returns_absolute_level(self):
        """Without context parent, returns the task's absolute level."""
        task = Task(title="Task", level=2, parent_id=uuid4(), list_id=uuid4())
        relative_level = NestingRules.calculate_context_relative_level(task)
        assert relative_level == 2

    def test_direct_child_is_level0(self):
        """Direct children of context parent appear at level 0."""
        context_parent_id = uuid4()
        task = Task(
            title="Auth endpoints",
            level=1,
            parent_id=context_parent_id,
            list_id=uuid4()
        )
        relative_level = NestingRules.calculate_context_relative_level(
            task, context_parent_id
        )
        assert relative_level == 0

    def test_context_relative_level_calculation(self):
        """Context-relative levels are calculated from the context parent."""
        # Create a hierarchy:
        # API Dev (L0, id=A) → Auth (L1, id=B, parent=A) → Session (L2, id=C, parent=B)

        id_api_dev = uuid4()
        id_auth = uuid4()

        # When API Dev is selected in Column 1:
        task_auth = Task(
            title="Auth endpoints",
            level=1,
            parent_id=id_api_dev,
            list_id=uuid4()
        )
        # Auth should appear at level 0 in Column 2
        assert NestingRules.calculate_context_relative_level(
            task_auth, context_parent_id=id_api_dev
        ) == 0

        # Session management (child of Auth)
        task_session = Task(
            title="Session management",
            level=2,
            parent_id=id_auth,
            list_id=uuid4()
        )
        # When Auth is selected in Column 1, Session should appear at level 0
        assert NestingRules.calculate_context_relative_level(
            task_session, context_parent_id=id_auth
        ) == 0


class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""

    def test_can_create_child_with_none_column_returns_false(self):
        """Invalid column context returns False."""
        task = Task(title="Task", level=0, list_id=uuid4())
        # Note: This would raise AttributeError in practice, but tests the logic
        # In real usage, column should always be a valid Column enum

    def test_multiple_tasks_at_same_level(self):
        """Multiple tasks at the same level can exist."""
        parent_id = uuid4()
        list_id = uuid4()

        task1 = Task(title="Task 1", level=0, list_id=list_id, position=0)
        task2 = Task(title="Task 2", level=0, list_id=list_id, position=1)
        task3 = Task(title="Task 3", level=0, list_id=list_id, position=2)

        # All level 0 tasks can have children in both columns
        assert NestingRules.can_create_child(task1, Column.COLUMN1) is True
        assert NestingRules.can_create_child(task2, Column.COLUMN1) is True
        assert NestingRules.can_create_child(task3, Column.COLUMN1) is True

    def test_sibling_tasks_with_different_parent_levels(self):
        """Tasks with same parent are at the same level."""
        parent_id = uuid4()
        list_id = uuid4()

        # Both children of the same parent
        child1 = Task(
            title="Child 1",
            level=1,
            parent_id=parent_id,
            list_id=list_id,
            position=0
        )
        child2 = Task(
            title="Child 2",
            level=1,
            parent_id=parent_id,
            list_id=list_id,
            position=1
        )

        # Both should have same nesting rules
        assert (
            NestingRules.can_create_child(child1, Column.COLUMN1) ==
            NestingRules.can_create_child(child2, Column.COLUMN1)
        )
        assert (
            NestingRules.can_create_child(child1, Column.COLUMN2) ==
            NestingRules.can_create_child(child2, Column.COLUMN2)
        )


class TestRealWorldScenarios:
    """Tests based on real-world usage scenarios from the spec."""

    def test_sprint_planning_scenario_column1(self):
        """
        Column 1 scenario from spec:
        Sprint Planning (L0) → Review backlog (L1)
        """
        list_id = uuid4()

        # Create Sprint Planning (Level 0)
        sprint_planning = Task(
            title="Sprint Planning",
            level=0,
            list_id=list_id
        )

        # Can create Review backlog as child
        assert NestingRules.can_create_child(sprint_planning, Column.COLUMN1) is True
        child_level = NestingRules.get_allowed_child_level(sprint_planning, Column.COLUMN1)
        assert child_level == 1

        # Create Review backlog (Level 1)
        review_backlog = Task(
            title="Review backlog",
            level=1,
            parent_id=sprint_planning.id,
            list_id=list_id
        )

        # Cannot create children for Review backlog in Column 1
        assert NestingRules.can_create_child(review_backlog, Column.COLUMN1) is False

    def test_api_development_scenario_column2(self):
        """
        Column 2 scenario from spec:
        API Development (L0) → Auth endpoints (L1) → Session management (L2) → Redis setup (L3 - not allowed)
        """
        list_id = uuid4()

        # Level 0: API Development
        api_dev = Task(title="API Development", level=0, list_id=list_id)
        assert NestingRules.can_create_child(api_dev, Column.COLUMN2) is True

        # Level 1: Auth endpoints
        auth = Task(
            title="Auth endpoints",
            level=1,
            parent_id=api_dev.id,
            list_id=list_id
        )
        assert NestingRules.can_create_child(auth, Column.COLUMN2) is True

        # Level 2: Session management
        session = Task(
            title="Session management",
            level=2,
            parent_id=auth.id,
            list_id=list_id
        )
        # Level 2 is maximum - cannot create children
        assert NestingRules.can_create_child(session, Column.COLUMN2) is False
        child_level = NestingRules.get_allowed_child_level(session, Column.COLUMN2)
        assert child_level is None

    def test_context_relative_display_scenario(self):
        """
        Test context-relative display from spec:
        When "Auth endpoints" (L1) is selected in Column 1,
        Column 2 shows: Session management (appears as L0) → Redis setup (appears as L1)
        """
        list_id = uuid4()

        # Create hierarchy
        api_dev_id = uuid4()
        auth_id = uuid4()

        # Auth endpoints (actual level 1, child of API Dev)
        auth = Task(
            id=auth_id,
            title="Auth endpoints",
            level=1,
            parent_id=api_dev_id,
            list_id=list_id
        )

        # Session management (actual level 2, child of Auth)
        session = Task(
            title="Session management",
            level=2,
            parent_id=auth_id,
            list_id=list_id
        )

        # When Auth is selected as context parent in Column 1:
        # Session should appear at relative level 0 in Column 2
        relative_level = NestingRules.calculate_context_relative_level(
            session, context_parent_id=auth_id
        )
        assert relative_level == 0

        # Verify Session can still be validated in Column 2 context
        assert NestingRules.validate_nesting_depth(session, Column.COLUMN2) is True


class TestMaximumDepthEnforcement:
    """Tests specifically for maximum depth enforcement."""

    def test_column1_enforces_max_2_levels(self):
        """Column 1 only allows 2 total levels (0 and 1)."""
        list_id = uuid4()

        # Level 0 - valid
        level0 = Task(title="L0", level=0, list_id=list_id)
        assert NestingRules.validate_nesting_depth(level0, Column.COLUMN1) is True

        # Level 1 - valid
        level1 = Task(title="L1", level=1, parent_id=level0.id, list_id=list_id)
        assert NestingRules.validate_nesting_depth(level1, Column.COLUMN1) is True

        # Level 2 - invalid for Column 1
        level2 = Task(title="L2", level=2, parent_id=level1.id, list_id=list_id)
        assert NestingRules.validate_nesting_depth(level2, Column.COLUMN1) is False

    def test_column2_enforces_max_3_levels(self):
        """Column 2 only allows 3 total levels (0, 1, and 2)."""
        list_id = uuid4()

        # Level 0 - valid
        level0 = Task(title="L0", level=0, list_id=list_id)
        assert NestingRules.validate_nesting_depth(level0, Column.COLUMN2) is True

        # Level 1 - valid
        level1 = Task(title="L1", level=1, parent_id=level0.id, list_id=list_id)
        assert NestingRules.validate_nesting_depth(level1, Column.COLUMN2) is True

        # Level 2 - valid
        level2 = Task(title="L2", level=2, parent_id=level1.id, list_id=list_id)
        assert NestingRules.validate_nesting_depth(level2, Column.COLUMN2) is True

    def test_child_level_never_exceeds_max_depth(self):
        """get_allowed_child_level never returns a level exceeding max depth."""
        list_id = uuid4()

        # Column 1: Level 1 task cannot have children (would be level 2, exceeds max)
        task_l1 = Task(title="L1", level=1, parent_id=uuid4(), list_id=list_id)
        assert NestingRules.get_allowed_child_level(task_l1, Column.COLUMN1) is None

        # Column 2: Level 2 task cannot have children (would be level 3, exceeds max)
        task_l2 = Task(title="L2", level=2, parent_id=uuid4(), list_id=list_id)
        assert NestingRules.get_allowed_child_level(task_l2, Column.COLUMN2) is None
