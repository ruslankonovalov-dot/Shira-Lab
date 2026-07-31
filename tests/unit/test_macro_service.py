# tests/unit/test_macro_service.py — MacroService comprehensive tests for Phase 3.6
import threading
import time
from unittest.mock import Mock

import pytest


class TestMacroService:
    """Tests for MacroService."""

    def setup_method(self):
        from app.backend.services.macro_service import MacroService
        self.service = MacroService._original_class()
        self.service.set_bridge(Mock())

    def test_add_action(self):
        """Test adding action."""
        self.service.clear_actions()
        result = self.service.add_action("a", 0.5, 0.05)
        # get_status doesn't return "ok" - returns full status dict
        assert result["actions_count"] == 1

        status = self.service.get_status()
        assert status["actions_count"] == 1
        assert status["actions"][0]["key"] == "a"

    def test_clear_actions(self):
        """Test clearing actions."""
        self.service.clear_actions()
        self.service.add_action("a", 0.5, 0.05)
        self.service.add_action("b", 0.5, 0.05)

        result = self.service.clear_actions()
        # Clear returns status dict, not {"ok": True}
        assert result["actions_count"] == 0

        status = self.service.get_status()
        assert status["actions_count"] == 0

    def test_run_mode(self):
        """Test run mode setting."""
        for mode in ["SEQUENTIAL", "PARALLEL"]:
            result = self.service.set_run_mode(mode)
            assert result["run_mode"] == mode
            assert self.service.run_mode == mode

        result = self.service.set_run_mode("INVALID")
        assert result["run_mode"] == "SEQUENTIAL"
        assert self.service.run_mode == "SEQUENTIAL"

    def test_background_methods(self):
        """Test background methods."""
        for method in ["sendinput", "postmessage", "vigem", "pico"]:
            result = self.service.set_background_method(method)
            assert result["background_method"] == method
            assert self.service.background_method == method

    def test_background_method_invalid(self):
        """Test invalid background method."""
        original = self.service.background_method
        result = self.service.set_background_method("invalid")
        # Doesn't fail, just keeps current
        assert result["background_method"] == original

    def test_start_stop(self):
        """Test start/stop."""
        self.service.clear_actions()
        self.service.add_action("a", 0.1, 0.05)

        result = self.service.start()
        assert result["is_running"] is True
        assert self.service.is_running is True

        time.sleep(0.3)

        result = self.service.stop()
        assert result["is_running"] is False
        assert self.service.is_running is False

    def test_start_no_actions(self):
        """Test start with no actions."""
        self.service.clear_actions()
        result = self.service.start()
        assert result["is_running"] is False
        assert result["actions_count"] == 0

    def test_get_status(self):
        """Test status structure."""
        status = self.service.get_status()
        assert "is_running" in status
        assert "run_mode" in status
        assert "actions" in status
        assert "actions_count" in status
        assert "background_method" in status
        assert "can_undo" in status
        assert "can_redo" in status
        assert "undo_count" in status
        assert "redo_count" in status


class TestMacroServiceUndoRedo:
    """Tests for undo/redo functionality."""

    def setup_method(self):
        from app.backend.services.macro_service import MacroService
        self.service = MacroService._original_class()
        self.service.set_bridge(Mock())

    def test_initial_state(self):
        """Test initial undo/redo state."""
        status = self.service.get_undo_redo_status()
        assert status["can_undo"] is False
        assert status["can_redo"] is False
        assert status["undo_count"] == 0
        assert status["redo_count"] == 0

    def test_undo_after_add(self):
        """Test undo after adding action."""
        self.service.clear_actions()
        self.service.add_action("a", 0.5, 0.05)

        status = self.service.get_undo_redo_status()
        assert status["can_undo"] is True
        assert status["can_redo"] is False

        result = self.service.undo()
        assert result["ok"] is True

        status = self.service.get_status()
        assert status["actions_count"] == 0

    def test_redo_after_undo(self):
        """Test redo after undo."""
        self.service.clear_actions()
        self.service.add_action("a", 0.5, 0.05)
        self.service.undo()

        status = self.service.get_undo_redo_status()
        assert status["can_redo"] is True

        result = self.service.redo()
        assert result["ok"] is True

        status = self.service.get_status()
        assert status["actions_count"] == 1

    def test_multiple_undo_redo(self):
        """Test multiple undo/redo operations."""
        self.service.clear_actions()
        self.service.add_action("a", 0.1, 0.05)
        self.service.add_action("b", 0.2, 0.1)
        self.service.add_action("c", 0.3, 0.15)

        assert self.service.get_status()["actions_count"] == 3

        self.service.undo()
        assert self.service.get_status()["actions_count"] == 2
        assert self.service.get_status()["actions"][1]["key"] == "b"

        self.service.undo()
        assert self.service.get_status()["actions_count"] == 1
        assert self.service.get_status()["actions"][0]["key"] == "a"

        self.service.undo()
        assert self.service.get_status()["actions_count"] == 0

        self.service.redo()
        assert self.service.get_status()["actions_count"] == 1
        assert self.service.get_status()["actions"][0]["key"] == "a"

        self.service.redo()
        assert self.service.get_status()["actions_count"] == 2
        assert self.service.get_status()["actions"][1]["key"] == "b"

    def test_undo_empty_stack(self):
        """Test undo with empty stack."""
        self.service.clear_actions()
        result = self.service.undo()
        assert result["ok"] is False
        assert "Nothing to undo" in result["error"]

    def test_redo_empty_stack(self):
        """Test redo with empty stack."""
        result = self.service.redo()
        assert result["ok"] is False
        assert "Nothing to redo" in result["error"]

    def test_new_action_clears_redo(self):
        """Test new action clears redo stack."""
        self.service.clear_actions()
        self.service.add_action("a", 0.1, 0.05)
        self.service.add_action("b", 0.2, 0.1)
        self.service.undo()
        assert self.service.get_undo_redo_status()["can_redo"] is True

        self.service.add_action("c", 0.3, 0.15)
        assert self.service.get_undo_redo_status()["can_redo"] is False

    def test_clear_with_undo(self):
        """Test clear actions enables undo."""
        self.service.clear_actions()
        self.service.add_action("a", 0.1, 0.05)
        self.service.add_action("b", 0.2, 0.1)
        self.service.clear_actions()

        assert self.service.get_status()["actions_count"] == 0
        assert self.service.get_undo_redo_status()["can_undo"] is True

        self.service.undo()
        assert self.service.get_status()["actions_count"] == 2

    def test_undo_stack_limit(self):
        """Test undo stack is limited."""
        self.service.clear_actions()
        self.service._MAX_UNDO = 5

        for i in range(10):
            self.service.add_action(f"key{i}", 0.1, 0.05)

        assert self.service.get_undo_redo_status()["undo_count"] <= 5


class TestMacroServiceMoveDelete:
    """Tests for move and delete actions."""

    def setup_method(self):
        from app.backend.services.macro_service import MacroService
        self.service = MacroService._original_class()
        self.service.set_bridge(Mock())

    def test_move_action_forward(self):
        """Test moving action forward."""
        self.service.clear_actions()
        self.service.add_action("a", 0.1, 0.05)
        self.service.add_action("b", 0.2, 0.1)
        self.service.add_action("c", 0.3, 0.15)

        result = self.service.move_action(0, 2)
        assert result["ok"] is True

        actions = self.service.get_status()["actions"]
        assert actions[0]["key"] == "b"
        assert actions[1]["key"] == "c"
        assert actions[2]["key"] == "a"

    def test_move_action_backward(self):
        """Test moving action backward."""
        self.service.clear_actions()
        self.service.add_action("a", 0.1, 0.05)
        self.service.add_action("b", 0.2, 0.1)
        self.service.add_action("c", 0.3, 0.15)

        result = self.service.move_action(2, 0)
        assert result["ok"] is True

        actions = self.service.get_status()["actions"]
        assert actions[0]["key"] == "c"
        assert actions[1]["key"] == "a"
        assert actions[2]["key"] == "b"

    def test_move_invalid_indices(self):
        """Test move with invalid indices."""
        self.service.clear_actions()
        self.service.add_action("a", 0.1, 0.05)

        result = self.service.move_action(0, 0)
        assert result["ok"] is False

        result = self.service.move_action(0, 5)
        assert result["ok"] is False

        result = self.service.move_action(-1, 0)
        assert result["ok"] is False

    def test_delete_action(self):
        """Test deleting action."""
        self.service.clear_actions()
        self.service.add_action("a", 0.1, 0.05)
        self.service.add_action("b", 0.2, 0.1)
        self.service.add_action("c", 0.3, 0.15)

        result = self.service.delete_action(1)
        assert result["ok"] is True

        actions = self.service.get_status()["actions"]
        assert len(actions) == 2
        assert actions[0]["key"] == "a"
        assert actions[1]["key"] == "c"

    def test_delete_invalid_index(self):
        """Test delete with invalid index."""
        self.service.clear_actions()
        self.service.add_action("a", 0.1, 0.05)

        result = self.service.delete_action(5)
        assert result["ok"] is False

        result = self.service.delete_action(-1)
        assert result["ok"] is False

    def test_undo_delete(self):
        """Test undo after delete."""
        self.service.clear_actions()
        self.service.add_action("a", 0.1, 0.05)
        self.service.add_action("b", 0.2, 0.1)
        self.service.delete_action(1)

        self.service.undo()
        actions = self.service.get_status()["actions"]
        assert len(actions) == 2
        assert actions[1]["key"] == "b"

    def test_undo_move(self):
        """Test undo after move."""
        self.service.clear_actions()
        self.service.add_action("a", 0.1, 0.05)
        self.service.add_action("b", 0.2, 0.1)
        self.service.add_action("c", 0.3, 0.15)

        self.service.move_action(0, 2)
        self.service.undo()

        actions = self.service.get_status()["actions"]
        assert actions[0]["key"] == "a"
        assert actions[1]["key"] == "b"
        assert actions[2]["key"] == "c"


class TestMacroServiceThreadSafety:
    """Tests for thread safety."""

    def setup_method(self):
        from app.backend.services.macro_service import MacroService
        self.service = MacroService._original_class()
        self.service.set_bridge(Mock())

    def test_concurrent_add_actions(self):
        """Test concurrent add actions."""
        def add_actions():
            for i in range(20):
                self.service.add_action(f"key{i}", 0.1, 0.05)

        threads = [threading.Thread(target=add_actions) for _ in range(3)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert self.service.get_status()["actions_count"] == 60

    def test_concurrent_undo_redo(self):
        """Test concurrent undo/redo (should be safe)."""
        self.service.clear_actions()
        for i in range(10):
            self.service.add_action(f"key{i}", 0.1, 0.05)

        def undo_redo():
            for _ in range(5):
                self.service.undo()
                self.service.redo()

        threads = [threading.Thread(target=undo_redo) for _ in range(3)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Should not crash


if __name__ == "__main__":
    pytest.main([__file__, "-v"])