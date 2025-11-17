"""
Tests for ListBar and ListTab UI components.

Tests cover:
- ListTab rendering with list information
- Active list highlighting
- Completion percentage display
- ListBar list management
- List selection messaging
- Number key shortcuts
"""

import pytest
from uuid import uuid4
from datetime import datetime

from taskui.models import TaskList
from taskui.ui.components.list_bar import ListBar, ListTab


class TestListTab:
    """Test suite for ListTab widget."""

    def test_list_tab_creation(self, make_task_list):
        """Test basic ListTab creation."""
        task_list = make_task_list(name="Work")
        tab = ListTab(task_list=task_list, shortcut_number=1, is_active=False)

        assert tab.task_list == task_list
        assert tab.shortcut_number == 1
        assert tab.active is False
        assert tab.list_id == task_list.id

    def test_list_tab_active_creation(self, make_task_list):
        """Test ListTab creation with active state."""
        task_list = make_task_list(name="Home")
        tab = ListTab(task_list=task_list, shortcut_number=2, is_active=True)

        assert tab.active is True
        assert "active" in tab.classes

    def test_list_tab_rendering_basic(self, make_task_list):
        """Test basic ListTab rendering without completion."""
        task_list = make_task_list(name="Work")
        tab = ListTab(task_list=task_list, shortcut_number=1, is_active=False)

        rendered = tab.render()
        rendered_str = str(rendered)

        # Should show shortcut number
        assert "[1]" in rendered_str
        # Should show list name
        assert "Work" in rendered_str
        # Should not show percentage when no tasks
        assert "%" not in rendered_str

    def test_list_tab_rendering_with_completion(self, make_task_list):
        """Test ListTab rendering with completion percentage."""
        task_list = make_task_list(name="Personal")
        # Simulate 3 tasks, 2 completed
        task_list.update_counts(task_count=3, completed_count=2)

        tab = ListTab(task_list=task_list, shortcut_number=3, is_active=False)

        rendered = tab.render()
        rendered_str = str(rendered)

        # Should show completion percentage
        assert "67%" in rendered_str or "66%" in rendered_str  # Rounding variations

    def test_list_tab_rendering_100_percent(self, make_task_list):
        """Test ListTab rendering with 100% completion."""
        task_list = make_task_list(name="Done")
        task_list.update_counts(task_count=5, completed_count=5)

        tab = ListTab(task_list=task_list, shortcut_number=1, is_active=False)

        rendered = tab.render()
        rendered_str = str(rendered)

        assert "100%" in rendered_str

    def test_list_tab_watch_active_adds_class(self, make_task_list):
        """Test that watching active state adds CSS class."""
        task_list = make_task_list(name="Work")
        tab = ListTab(task_list=task_list, shortcut_number=1, is_active=False)

        # Initially inactive
        assert "active" not in tab.classes

        # Activate
        tab.active = True

        # Should have active class
        assert "active" in tab.classes

    def test_list_tab_watch_active_removes_class(self, make_task_list):
        """Test that watching active state removes CSS class."""
        task_list = make_task_list(name="Work")
        tab = ListTab(task_list=task_list, shortcut_number=1, is_active=True)

        # Initially active
        assert "active" in tab.classes

        # Deactivate
        tab.active = False

        # Should not have active class
        assert "active" not in tab.classes


class TestListBar:
    """Test suite for ListBar widget."""

    def test_list_bar_creation_empty(self):
        """Test ListBar creation with no lists."""
        list_bar = ListBar(lists=[], active_list_id=None)

        assert list_bar.lists == []
        assert list_bar.active_list_id is None
        assert list_bar.tabs == []

    def test_list_bar_creation_with_lists(self, make_task_list):
        """Test ListBar creation with multiple lists."""
        lists = [
            make_task_list(name="Work"),
            make_task_list(name="Home"),
            make_task_list(name="Personal"),
        ]
        list_bar = ListBar(lists=lists, active_list_id=lists[0].id)

        assert len(list_bar.lists) == 3
        assert list_bar.active_list_id == lists[0].id

    def test_list_bar_creation_defaults_first_list(self, make_task_list):
        """Test that ListBar defaults to first list if no active specified."""
        lists = [
            make_task_list(name="Work"),
            make_task_list(name="Home"),
        ]
        list_bar = ListBar(lists=lists)

        assert list_bar.active_list_id == lists[0].id

    def test_list_bar_update_lists(self, make_task_list):
        """Test updating lists in ListBar."""
        initial_lists = [make_task_list(name="Work")]
        list_bar = ListBar(lists=initial_lists)

        new_lists = [
            make_task_list(name="Work"),
            make_task_list(name="Home"),
            make_task_list(name="Personal"),
        ]

        list_bar.update_lists(new_lists)

        assert len(list_bar.lists) == 3

    def test_list_bar_set_active_list(self, make_task_list):
        """Test setting active list."""
        lists = [
            make_task_list(name="Work"),
            make_task_list(name="Home"),
            make_task_list(name="Personal"),
        ]
        list_bar = ListBar(lists=lists, active_list_id=lists[0].id)

        # Compose to create tabs
        list(list_bar.compose())

        # Set second list as active
        list_bar.set_active_list(lists[1].id)

        assert list_bar.active_list_id == lists[1].id

    def test_list_bar_set_active_updates_tabs(self, make_task_list):
        """Test that setting active list updates tab states."""
        lists = [
            make_task_list(name="Work"),
            make_task_list(name="Home"),
        ]
        list_bar = ListBar(lists=lists, active_list_id=lists[0].id)

        # Compose to create tabs
        list(list_bar.compose())

        # Initially first tab is active
        assert list_bar.tabs[0].active is True
        assert list_bar.tabs[1].active is False

        # Set second list as active
        list_bar.set_active_list(lists[1].id)

        # Now second tab should be active
        assert list_bar.tabs[0].active is False
        assert list_bar.tabs[1].active is True

    def test_list_bar_select_by_number_valid(self, make_task_list):
        """Test selecting list by valid number."""
        lists = [
            make_task_list(name="Work"),
            make_task_list(name="Home"),
            make_task_list(name="Personal"),
        ]
        list_bar = ListBar(lists=lists, active_list_id=lists[0].id)

        # Compose to create tabs
        list(list_bar.compose())

        # Select second list (number 2)
        result = list_bar.select_list_by_number(2)

        assert result is True
        assert list_bar.active_list_id == lists[1].id

    def test_list_bar_select_by_number_invalid(self, make_task_list):
        """Test selecting list by invalid number."""
        lists = [
            make_task_list(name="Work"),
            make_task_list(name="Home"),
        ]
        list_bar = ListBar(lists=lists, active_list_id=lists[0].id)

        # Compose to create tabs
        list(list_bar.compose())

        # Try to select number 5 (out of range)
        result = list_bar.select_list_by_number(5)

        assert result is False
        # Active list should remain unchanged
        assert list_bar.active_list_id == lists[0].id

    def test_list_bar_select_by_number_zero(self, make_task_list):
        """Test selecting list by number 0 (invalid)."""
        lists = [make_task_list(name="Work")]
        list_bar = ListBar(lists=lists, active_list_id=lists[0].id)

        # Compose to create tabs
        list(list_bar.compose())

        # Try to select number 0 (out of range)
        result = list_bar.select_list_by_number(0)

        assert result is False

    def test_list_bar_compose_creates_tabs(self, make_task_list):
        """Test that compose creates correct number of tabs."""
        lists = [
            make_task_list(name="Work"),
            make_task_list(name="Home"),
            make_task_list(name="Personal"),
        ]
        list_bar = ListBar(lists=lists, active_list_id=lists[0].id)

        # Compose tabs
        tabs = list(list_bar.compose())

        assert len(tabs) == 3
        assert all(isinstance(tab, ListTab) for tab in tabs)

    def test_list_bar_compose_assigns_shortcut_numbers(self, make_task_list):
        """Test that compose assigns correct shortcut numbers."""
        lists = [
            make_task_list(name="Work"),
            make_task_list(name="Home"),
            make_task_list(name="Personal"),
        ]
        list_bar = ListBar(lists=lists, active_list_id=lists[0].id)

        # Compose tabs
        tabs = list(list_bar.compose())

        assert tabs[0].shortcut_number == 1
        assert tabs[1].shortcut_number == 2
        assert tabs[2].shortcut_number == 3

    def test_list_bar_compose_marks_active_tab(self, make_task_list):
        """Test that compose marks the correct tab as active."""
        lists = [
            make_task_list(name="Work"),
            make_task_list(name="Home"),
            make_task_list(name="Personal"),
        ]
        # Set second list as active
        list_bar = ListBar(lists=lists, active_list_id=lists[1].id)

        # Compose tabs
        tabs = list(list_bar.compose())

        assert tabs[0].active is False
        assert tabs[1].active is True
        assert tabs[2].active is False

    def test_list_bar_watch_active_list_id(self, make_task_list):
        """Test that watching active_list_id updates tabs."""
        lists = [
            make_task_list(name="Work"),
            make_task_list(name="Home"),
        ]
        list_bar = ListBar(lists=lists, active_list_id=lists[0].id)

        # Compose to create tabs
        list(list_bar.compose())

        # Change active list ID
        list_bar.active_list_id = lists[1].id

        # Tabs should update
        assert list_bar.tabs[0].active is False
        assert list_bar.tabs[1].active is True


class TestListBarIntegration:
    """Integration tests for ListBar with TaskList models."""

    def test_list_bar_displays_completion_info(self, make_task_list):
        """Test that ListBar displays completion percentage from TaskList."""
        task_list = make_task_list(name="Work")
        # Set completion info
        task_list.update_counts(task_count=10, completed_count=7)

        list_bar = ListBar(lists=[task_list], active_list_id=task_list.id)
        tabs = list(list_bar.compose())

        # Tab should show completion percentage
        rendered = tabs[0].render()
        rendered_str = str(rendered)

        assert "70%" in rendered_str

    def test_list_bar_handles_zero_tasks(self, make_task_list):
        """Test that ListBar handles lists with zero tasks gracefully."""
        task_list = make_task_list(name="Empty")
        task_list.update_counts(task_count=0, completed_count=0)

        list_bar = ListBar(lists=[task_list], active_list_id=task_list.id)
        tabs = list(list_bar.compose())

        # Should not crash and should not show percentage
        rendered = tabs[0].render()
        rendered_str = str(rendered)

        assert "%" not in rendered_str
        assert "Empty" in rendered_str

    def test_list_bar_three_default_lists(self, make_task_list):
        """Test ListBar with three default lists (Work, Home, Personal)."""
        lists = [
            make_task_list(name="Work"),
            make_task_list(name="Home"),
            make_task_list(name="Personal"),
        ]

        list_bar = ListBar(lists=lists, active_list_id=lists[0].id)
        tabs = list(list_bar.compose())

        # Should have exactly 3 tabs
        assert len(tabs) == 3

        # Tabs should be in order
        assert tabs[0].task_list.name == "Work"
        assert tabs[1].task_list.name == "Home"
        assert tabs[2].task_list.name == "Personal"

        # First should be active
        assert tabs[0].active is True
