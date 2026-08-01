"""Unit tests for MacroService undo/redo functionality (v1.0.0 UX upgrade).

NOTE: MacroService is a @singleton, so we need to bypass the singleton
to create a fresh instance per test. We use the reset_instance() method
added by the @singleton decorator, or access the original class.
"""

from unittest.mock import MagicMock

import pytest

pytestmark = pytest.mark.unit


@pytest.fixture
def macro_service():
    """Get a fresh MacroService instance per test (bypassing singleton)."""
    from app.backend.services.macro_service import MacroService

    # Reset the singleton cache first (useful for test isolation, especially with xdist)
    if hasattr(MacroService, "reset_instance"):
        MacroService.reset_instance()

    # Access the original class (stored by @singleton decorator as attribute on wrapper)
    # In multiprocessing/xdist environments, the wrapper may be different, so try multiple approaches
    original_cls = getattr(MacroService, "_original_class", None)
    if original_cls is None:
        # Fallback: try to get from the underlying class attribute
        original_cls = getattr(MacroService, "cls", None)

    if original_cls is None:
        # Last resort: import the class directly from the module (bypassing decorator)
        from app.backend.services.macro_service import (
            MacroService as DirectMacroService,
        )

        original_cls = DirectMacroService

    # Create a fresh instance, bypassing the singleton cache
    service = original_cls()
    service.set_bridge(MagicMock())
    return service


class TestUndoRedoBasics:
    def test_initial_state_no_undo_no_redo(self, macro_service):
        status = macro_service.get_undo_redo_status()
        assert status["can_undo"] is False
        assert status["can_redo"] is False
        assert status["undo_count"] == 0
        assert status["redo_count"] == 0

    def test_add_action_enables_undo(self, macro_service):
        macro_service.add_action("a", 0.1, 0.05)
        status = macro_service.get_undo_redo_status()
        assert status["can_undo"] is True
        assert status["can_redo"] is False

    def test_undo_after_add_removes_action(self, macro_service):
        macro_service.add_action("a", 0.1, 0.05)
        assert macro_service.get_status()["actions_count"] == 1
        result = macro_service.undo()
        assert result["ok"] is True
        assert macro_service.get_status()["actions_count"] == 0

    def test_undo_enables_redo(self, macro_service):
        macro_service.add_action("a", 0.1, 0.05)
        macro_service.undo()
        status = macro_service.get_undo_redo_status()
        assert status["can_undo"] is False
        assert status["can_redo"] is True

    def test_redo_after_undo_restores_action(self, macro_service):
        macro_service.add_action("a", 0.1, 0.05)
        macro_service.undo()
        result = macro_service.redo()
        assert result["ok"] is True
        assert macro_service.get_status()["actions_count"] == 1

    def test_undo_with_empty_stack_returns_error(self, macro_service):
        result = macro_service.undo()
        assert result["ok"] is False
        assert "Nothing to undo" in result["error"]

    def test_redo_with_empty_stack_returns_error(self, macro_service):
        result = macro_service.redo()
        assert result["ok"] is False
        assert "Nothing to redo" in result["error"]


class TestUndoRedoMultipleActions:
    def test_multiple_undoes(self, macro_service):
        macro_service.add_action("a", 0.1, 0.05)
        macro_service.add_action("b", 0.2, 0.1)
        macro_service.add_action("c", 0.3, 0.15)
        assert macro_service.get_status()["actions_count"] == 3

        macro_service.undo()
        assert macro_service.get_status()["actions_count"] == 2
        assert macro_service.get_status()["actions"][1]["key"] == "b"

        macro_service.undo()
        assert macro_service.get_status()["actions_count"] == 1
        assert macro_service.get_status()["actions"][0]["key"] == "a"

        macro_service.undo()
        assert macro_service.get_status()["actions_count"] == 0

    def test_multiple_redoes(self, macro_service):
        macro_service.add_action("a", 0.1, 0.05)
        macro_service.add_action("b", 0.2, 0.1)
        macro_service.undo()
        macro_service.undo()
        assert macro_service.get_status()["actions_count"] == 0

        macro_service.redo()
        assert macro_service.get_status()["actions_count"] == 1
        assert macro_service.get_status()["actions"][0]["key"] == "a"

        macro_service.redo()
        assert macro_service.get_status()["actions_count"] == 2
        assert macro_service.get_status()["actions"][1]["key"] == "b"

    def test_new_action_after_undo_clears_redo(self, macro_service):
        macro_service.add_action("a", 0.1, 0.05)
        macro_service.add_action("b", 0.2, 0.1)
        macro_service.undo()
        assert macro_service.get_undo_redo_status()["can_redo"] is True

        macro_service.add_action("c", 0.3, 0.15)
        assert macro_service.get_undo_redo_status()["can_redo"] is False


class TestClearWithUndo:
    def test_clear_enables_undo(self, macro_service):
        macro_service.add_action("a", 0.1, 0.05)
        macro_service.add_action("b", 0.2, 0.1)
        macro_service.clear_actions()
        assert macro_service.get_status()["actions_count"] == 0
        assert macro_service.get_undo_redo_status()["can_undo"] is True

    def test_undo_clear_restores_actions(self, macro_service):
        macro_service.add_action("a", 0.1, 0.05)
        macro_service.add_action("b", 0.2, 0.1)
        macro_service.clear_actions()
        assert macro_service.get_status()["actions_count"] == 0

        macro_service.undo()
        assert macro_service.get_status()["actions_count"] == 2
        assert macro_service.get_status()["actions"][0]["key"] == "a"
        assert macro_service.get_status()["actions"][1]["key"] == "b"


class TestDeleteAction:
    def test_delete_action_by_index(self, macro_service):
        macro_service.add_action("a", 0.1, 0.05)
        macro_service.add_action("b", 0.2, 0.1)
        macro_service.add_action("c", 0.3, 0.15)

        result = macro_service.delete_action(1)
        assert result["ok"] is True
        assert macro_service.get_status()["actions_count"] == 2
        assert macro_service.get_status()["actions"][0]["key"] == "a"
        assert macro_service.get_status()["actions"][1]["key"] == "c"

    def test_delete_invalid_index_returns_error(self, macro_service):
        macro_service.add_action("a", 0.1, 0.05)
        result = macro_service.delete_action(5)
        assert result["ok"] is False
        assert "Invalid index" in result["error"]

    def test_delete_negative_index_returns_error(self, macro_service):
        macro_service.add_action("a", 0.1, 0.05)
        result = macro_service.delete_action(-1)
        assert result["ok"] is False

    def test_undo_delete_restores_action(self, macro_service):
        macro_service.add_action("a", 0.1, 0.05)
        macro_service.add_action("b", 0.2, 0.1)
        macro_service.delete_action(1)
        assert macro_service.get_status()["actions_count"] == 1

        macro_service.undo()
        assert macro_service.get_status()["actions_count"] == 2
        assert macro_service.get_status()["actions"][1]["key"] == "b"


class TestMoveAction:
    def test_move_action_forward(self, macro_service):
        macro_service.add_action("a", 0.1, 0.05)
        macro_service.add_action("b", 0.2, 0.1)
        macro_service.add_action("c", 0.3, 0.15)

        result = macro_service.move_action(0, 2)
        assert result["ok"] is True
        actions = macro_service.get_status()["actions"]
        assert actions[0]["key"] == "b"
        assert actions[1]["key"] == "c"
        assert actions[2]["key"] == "a"

    def test_move_action_backward(self, macro_service):
        macro_service.add_action("a", 0.1, 0.05)
        macro_service.add_action("b", 0.2, 0.1)
        macro_service.add_action("c", 0.3, 0.15)

        result = macro_service.move_action(2, 0)
        assert result["ok"] is True
        actions = macro_service.get_status()["actions"]
        assert actions[0]["key"] == "c"
        assert actions[1]["key"] == "a"
        assert actions[2]["key"] == "b"

    def test_move_same_index_returns_error(self, macro_service):
        macro_service.add_action("a", 0.1, 0.05)
        result = macro_service.move_action(0, 0)
        assert result["ok"] is False

    def test_move_invalid_index_returns_error(self, macro_service):
        macro_service.add_action("a", 0.1, 0.05)
        result = macro_service.move_action(0, 5)
        assert result["ok"] is False

    def test_undo_move_reverses(self, macro_service):
        macro_service.add_action("a", 0.1, 0.05)
        macro_service.add_action("b", 0.2, 0.1)
        macro_service.add_action("c", 0.3, 0.15)

        macro_service.move_action(0, 2)
        macro_service.undo()

        actions = macro_service.get_status()["actions"]
        assert actions[0]["key"] == "a"
        assert actions[1]["key"] == "b"
        assert actions[2]["key"] == "c"


class TestUndoStackLimit:
    def test_undo_stack_is_trimmed(self, macro_service):
        macro_service._MAX_UNDO = 5
        for i in range(10):
            macro_service.add_action(f"key{i}", 0.1, 0.05)
        assert macro_service.get_undo_redo_status()["undo_count"] <= 5


class TestStatusIncludesUndoRedo:
    def test_status_has_undo_redo_fields(self, macro_service):
        status = macro_service.get_status()
        assert "can_undo" in status
        assert "can_redo" in status
        assert "undo_count" in status
        assert "redo_count" in status

    def test_status_reflects_changes(self, macro_service):
        macro_service.add_action("a", 0.1, 0.05)
        status = macro_service.get_status()
        assert status["can_undo"] is True
        assert status["undo_count"] == 1

        macro_service.undo()
        status = macro_service.get_status()
        assert status["can_undo"] is False
        assert status["can_redo"] is True
        assert status["redo_count"] == 1
