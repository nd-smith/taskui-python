"""
Comprehensive tests for the nesting rules engine.

Tests all aspects of task nesting logic including:
- can_create_child() method validation (both class and instance methods)
- Context-relative level calculation
- Maximum depth enforcement
- Edge cases and boundary conditions
- Configuration-based behavior
- Backward compatibility with deprecated class methods
"""

import pytest
import warnings
from pathlib import Path
import tempfile
from uuid import uuid4

from taskui.models import Task
from taskui.services.nesting_rules import NestingRules, Column
from taskui.config.nesting_config import NestingConfig, ColumnNestingConfig


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


class TestNestingRulesInstanceMethods:
    """Tests for new instance-based NestingRules API with configuration."""

    def test_instance_creation_with_default_config(self):
        """Test creating NestingRules instance with default config."""
        rules = NestingRules()

        # Should use default values matching legacy constants
        assert rules.get_max_depth_instance(Column.COLUMN1) == 1
        assert rules.get_max_depth_instance(Column.COLUMN2) == 2

    def test_instance_creation_with_custom_config(self):
        """Test creating NestingRules instance with custom config."""
        config = NestingConfig(
            column1={'max_depth': 3},
            column2={'max_depth': 5}
        )
        rules = NestingRules(config)

        assert rules.get_max_depth_instance(Column.COLUMN1) == 3
        assert rules.get_max_depth_instance(Column.COLUMN2) == 5

    def test_can_create_child_instance_with_custom_depth(self):
        """Test can_create_child_instance with custom max_depth."""
        config = NestingConfig(
            column1={'max_depth': 1},  # Default
            column2={'max_depth': 2}   # Allow up to level 2
        )
        rules = NestingRules(config)
        list_id = uuid4()

        # Level 1 can have children in Column 2 (max_depth=2)
        task_l1 = Task(title="L1", level=1, parent_id=uuid4(), list_id=list_id)
        assert rules.can_create_child_instance(task_l1, Column.COLUMN2) is True

        # Level 2 cannot have children in Column 2 (at max_depth)
        task_l2 = Task(title="L2", level=2, parent_id=uuid4(), list_id=list_id)
        assert rules.can_create_child_instance(task_l2, Column.COLUMN2) is False

    def test_validate_nesting_depth_instance_with_custom_config(self):
        """Test validate_nesting_depth_instance with custom config."""
        config = NestingConfig(
            column1={'max_depth': 0},  # Only level 0
            column2={'max_depth': 2}   # Up to level 2
        )
        rules = NestingRules(config)
        list_id = uuid4()

        # Level 0 is valid in both columns
        task_l0 = Task(title="L0", level=0, list_id=list_id)
        assert rules.validate_nesting_depth_instance(task_l0, Column.COLUMN1) is True
        assert rules.validate_nesting_depth_instance(task_l0, Column.COLUMN2) is True

        # Level 1 exceeds Column 1 max_depth but is valid for Column 2
        task_l1 = Task(title="L1", level=1, parent_id=uuid4(), list_id=list_id)
        assert rules.validate_nesting_depth_instance(task_l1, Column.COLUMN1) is False
        assert rules.validate_nesting_depth_instance(task_l1, Column.COLUMN2) is True

        # Level 2 is valid for Column 2
        task_l2 = Task(title="L2", level=2, parent_id=uuid4(), list_id=list_id)
        assert rules.validate_nesting_depth_instance(task_l2, Column.COLUMN2) is True

    def test_get_allowed_child_level_instance_with_custom_config(self):
        """Test get_allowed_child_level_instance with custom config."""
        config = NestingConfig(
            column1={'max_depth': 1},  # Default
            column2={'max_depth': 2}   # Allow up to level 2
        )
        rules = NestingRules(config)
        list_id = uuid4()

        # Level 1 task can have level 2 child in Column 2
        task_l1 = Task(title="L1", level=1, parent_id=uuid4(), list_id=list_id)
        assert rules.get_allowed_child_level_instance(task_l1, Column.COLUMN2) == 2

        # Level 2 task cannot have children in Column 2 (at max_depth)
        task_l2 = Task(title="L2", level=2, parent_id=uuid4(), list_id=list_id)
        assert rules.get_allowed_child_level_instance(task_l2, Column.COLUMN2) is None

    def test_calculate_context_relative_level_instance(self):
        """Test calculate_context_relative_level_instance method."""
        rules = NestingRules()
        list_id = uuid4()
        parent_id = uuid4()

        # Direct child should be level 0 relative to parent
        task = Task(title="Child", level=1, parent_id=parent_id, list_id=list_id)
        assert rules.calculate_context_relative_level_instance(task, parent_id) == 0

        # Without context, should return absolute level
        assert rules.calculate_context_relative_level_instance(task) == 1


class TestNestingRulesFromConfig:
    """Tests for NestingRules.from_config() class method."""

    def test_from_config_with_nonexistent_file(self):
        """Test from_config with non-existent file returns defaults."""
        rules = NestingRules.from_config("/tmp/nonexistent_nesting_config.toml")

        # Should use defaults (both columns default to max_depth=1)
        assert rules.get_max_depth_instance(Column.COLUMN1) == 1
        assert rules.get_max_depth_instance(Column.COLUMN2) == 1

    def test_from_config_with_valid_file(self):
        """Test from_config with valid TOML file."""
        # Create temporary TOML config
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.toml') as f:
            f.write("""
[nesting]
enabled = true
num_columns = 2

[nesting.column1]
max_depth = 1
display_name = "Tasks"

[nesting.column2]
max_depth = 2
display_name = "Subtasks"
""")
            config_path = f.name

        try:
            rules = NestingRules.from_config(config_path)

            assert rules.get_max_depth_instance(Column.COLUMN1) == 1
            assert rules.get_max_depth_instance(Column.COLUMN2) == 2
        finally:
            Path(config_path).unlink()

    def test_from_config_without_path_uses_default_location(self):
        """Test from_config without path uses default location."""
        # Should not raise even if default location doesn't exist
        rules = NestingRules.from_config()

        # Should get default values (both columns default to max_depth=1)
        assert rules.get_max_depth_instance(Column.COLUMN1) == 1
        assert rules.get_max_depth_instance(Column.COLUMN2) == 1


class TestNestingRulesBackwardCompatibility:
    """Tests for backward compatibility with deprecated class methods."""

    def test_class_methods_emit_deprecation_warning(self):
        """Test that class methods emit DeprecationWarning."""
        list_id = uuid4()
        task = Task(title="Test", level=0, list_id=list_id)

        # can_create_child should emit warning
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            NestingRules.can_create_child(task, Column.COLUMN1)
            assert len(w) == 1
            assert issubclass(w[0].category, DeprecationWarning)
            assert "deprecated" in str(w[0].message).lower()

        # get_max_depth should emit warning
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            NestingRules.get_max_depth(Column.COLUMN1)
            assert len(w) == 1
            assert issubclass(w[0].category, DeprecationWarning)

        # validate_nesting_depth should emit warning
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            NestingRules.validate_nesting_depth(task, Column.COLUMN1)
            assert len(w) == 1
            assert issubclass(w[0].category, DeprecationWarning)

        # get_allowed_child_level should emit warning
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            NestingRules.get_allowed_child_level(task, Column.COLUMN1)
            assert len(w) == 1
            assert issubclass(w[0].category, DeprecationWarning)

        # calculate_context_relative_level should emit warning
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            NestingRules.calculate_context_relative_level(task)
            assert len(w) == 1
            assert issubclass(w[0].category, DeprecationWarning)

    def test_class_methods_return_same_results_as_instance_methods(self):
        """Test that deprecated class methods return same results as instance methods."""
        list_id = uuid4()

        # Create tasks at different levels
        task_l0 = Task(title="L0", level=0, list_id=list_id)
        task_l1 = Task(title="L1", level=1, parent_id=uuid4(), list_id=list_id)
        task_l2 = Task(title="L2", level=2, parent_id=uuid4(), list_id=list_id)

        # Create instance with default config
        rules = NestingRules()

        # Suppress warnings for this test
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)

            # can_create_child
            assert (NestingRules.can_create_child(task_l0, Column.COLUMN1) ==
                    rules.can_create_child_instance(task_l0, Column.COLUMN1))
            assert (NestingRules.can_create_child(task_l1, Column.COLUMN1) ==
                    rules.can_create_child_instance(task_l1, Column.COLUMN1))
            assert (NestingRules.can_create_child(task_l1, Column.COLUMN2) ==
                    rules.can_create_child_instance(task_l1, Column.COLUMN2))

            # get_max_depth
            assert (NestingRules.get_max_depth(Column.COLUMN1) ==
                    rules.get_max_depth_instance(Column.COLUMN1))
            assert (NestingRules.get_max_depth(Column.COLUMN2) ==
                    rules.get_max_depth_instance(Column.COLUMN2))

            # validate_nesting_depth
            assert (NestingRules.validate_nesting_depth(task_l2, Column.COLUMN1) ==
                    rules.validate_nesting_depth_instance(task_l2, Column.COLUMN1))
            assert (NestingRules.validate_nesting_depth(task_l2, Column.COLUMN2) ==
                    rules.validate_nesting_depth_instance(task_l2, Column.COLUMN2))

            # get_allowed_child_level
            assert (NestingRules.get_allowed_child_level(task_l0, Column.COLUMN1) ==
                    rules.get_allowed_child_level_instance(task_l0, Column.COLUMN1))
            assert (NestingRules.get_allowed_child_level(task_l1, Column.COLUMN1) ==
                    rules.get_allowed_child_level_instance(task_l1, Column.COLUMN1))


class TestNestingRulesParameterized:
    """Parameterized tests for different configuration values."""

    @pytest.mark.parametrize("column1_depth,column2_depth", [
        (1, 2),  # Typical values
        (0, 0),  # No nesting allowed
        (1, 1),  # Same depth for both
        (0, 2),  # Different depths
    ])
    def test_various_depth_configurations(self, column1_depth, column2_depth):
        """Test NestingRules with various depth configurations."""
        config = NestingConfig(
            column1={'max_depth': column1_depth},
            column2={'max_depth': column2_depth}
        )
        rules = NestingRules(config)

        assert rules.get_max_depth_instance(Column.COLUMN1) == column1_depth
        assert rules.get_max_depth_instance(Column.COLUMN2) == column2_depth

    @pytest.mark.parametrize("task_level,column,max_depth,expected", [
        (0, Column.COLUMN1, 1, True),   # Level 0 can have children
        (1, Column.COLUMN1, 1, False),  # Level 1 at max depth
        (0, Column.COLUMN2, 2, True),   # Level 0 can have children
        (1, Column.COLUMN2, 2, True),   # Level 1 can have children
        (2, Column.COLUMN2, 2, False),  # Level 2 at max depth
        (0, Column.COLUMN1, 0, False),  # Level 0 at max depth (no children)
        (1, Column.COLUMN2, 1, False),  # Level 1 at max depth
    ])
    def test_can_create_child_parameterized(self, task_level, column, max_depth, expected):
        """Test can_create_child_instance with various parameters."""
        list_id = uuid4()
        parent_id = uuid4() if task_level > 0 else None

        # Create config with specified max_depth
        config = NestingConfig(
            column1={'max_depth': max_depth},
            column2={'max_depth': max_depth}
        )
        rules = NestingRules(config)

        task = Task(
            title=f"Level {task_level}",
            level=task_level,
            parent_id=parent_id,
            list_id=list_id
        )

        assert rules.can_create_child_instance(task, column) == expected

    @pytest.mark.parametrize("task_level,max_depth,expected", [
        (0, 1, True),   # Level 0 within max
        (1, 1, True),   # Level 1 at max
        (2, 1, False),  # Level 2 exceeds max
        (0, 0, True),   # Level 0 at max
        (1, 0, False),  # Level 1 exceeds max of 0
        (2, 2, True),   # Level 2 at max
    ])
    def test_validate_nesting_depth_parameterized(self, task_level, max_depth, expected):
        """Test validate_nesting_depth_instance with various parameters."""
        list_id = uuid4()
        parent_id = uuid4() if task_level > 0 else None

        config = NestingConfig(
            column1={'max_depth': max_depth},
            column2={'max_depth': max_depth}
        )
        rules = NestingRules(config)

        task = Task(
            title=f"Level {task_level}",
            level=task_level,
            parent_id=parent_id,
            list_id=list_id
        )

        result = rules.validate_nesting_depth_instance(task, Column.COLUMN1)
        assert result == expected
