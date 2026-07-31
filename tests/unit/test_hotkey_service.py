# tests/unit/test_hotkey_service.py — HotkeyService comprehensive tests for Phase 3.6
import threading
from unittest.mock import MagicMock, Mock

import pytest


class TestHotkeyService:
    """Tests for HotkeyService."""

    def setup_method(self):
        from app.backend.services.hotkey_service import HotkeyService
        # Create a mock API that mimics QmlBridge/HotkeyController
        mock_api = MagicMock()
        mock_api.clicker = MagicMock()
        mock_api.clicker.is_running = False
        mock_api.aim = MagicMock()
        mock_api.aim.is_running = False
        mock_api.macro = MagicMock()
        mock_api.macro.is_running = False
        mock_api.recorder = MagicMock()
        mock_api.recorder.is_recording = False
        mock_api.vigem = MagicMock()
        mock_api.vigem.is_running = False
        mock_api.pico = MagicMock()
        mock_api.pico.is_connected = False

        self.service = HotkeyService(mock_api)
        self.callback = Mock()

    def test_validate_key_keyboard(self):
        """Test keyboard key validation."""
        # Single keys
        assert self.service.validate_key("f6")["ok"] is True
        assert self.service.validate_key("a")["ok"] is True
        assert self.service.validate_key("escape")["ok"] is True
        assert self.service.validate_key("space")["ok"] is True
        assert self.service.validate_key("enter")["ok"] is True
        assert self.service.validate_key("tab")["ok"] is True

        # Modifiers
        assert self.service.validate_key("ctrl+f7")["ok"] is True
        assert self.service.validate_key("shift+ctrl+alt+f8")["ok"] is True
        assert self.service.validate_key("ctrl+shift+a")["ok"] is True

    def test_validate_key_mouse(self):
        """Test mouse button validation."""
        assert self.service.validate_key("mouse:3")["ok"] is True
        assert self.service.validate_key("mouse:4")["ok"] is True
        assert self.service.validate_key("mouse:5")["ok"] is True

    def test_validate_key_wheel(self):
        """Test mouse wheel validation."""
        assert self.service.validate_key("wheel:up")["ok"] is True
        assert self.service.validate_key("wheel:down")["ok"] is True

    def test_validate_key_invalid(self):
        """Test invalid key validation."""
        assert self.service.validate_key("")["ok"] is False
        assert self.service.validate_key("invalid")["ok"] is False
        assert self.service.validate_key("ctrl+invalid")["ok"] is False
        assert self.service.validate_key(None)["ok"] is False

    def test_register_unregister(self):
        """Test hotkey registration and unregistration."""
        result = self.service.set_binding("clicker_toggle", "f6", "TOGGLE")
        assert result["ok"] is True

        # Check via public API
        bindings = self.service.get_bindings()
        assert bindings["clicker_toggle"]["key"] == "f6"
        assert bindings["clicker_toggle"]["mode"] == "TOGGLE"

        # Unregister by setting empty key (clears the binding)
        result = self.service.set_binding("clicker_toggle", "", "TOGGLE")
        assert result["ok"] is True

        # Should clear the binding (reset_binding() resets to default)
        bindings = self.service.get_bindings()
        assert bindings["clicker_toggle"]["key"] == ""

    def test_register_duplicate(self):
        """Test setting duplicate action overwrites."""
        self.service.set_binding("clicker_toggle", "f6", "TOGGLE")
        result = self.service.set_binding("clicker_toggle", "f7", "TOGGLE")
        assert result["ok"] is True
        # Should now be f7
        assert self.service._bindings["clicker_toggle"]["key"] == "f7"

    def test_unregister_nonexistent(self):
        """Test unregistering non-existent action."""
        # Use an invalid action name
        result = self.service.set_binding("nonexistent", "f6", "TOGGLE")
        assert result["ok"] is False

    def test_register_mouse_binding(self):
        """Test mouse button binding."""
        result = self.service.set_binding("clicker_toggle", "mouse:3", "HOLD")
        assert result["ok"] is True
        # For mouse bindings, the binding has 'button' key instead of 'key'
        assert self.service._bindings["clicker_toggle"]["button"] == "mouse:3"
        assert self.service._bindings["clicker_toggle"]["mode"] == "HOLD"

    def test_register_wheel_binding(self):
        """Test mouse wheel binding."""
        result = self.service.set_binding("clicker_toggle", "wheel:up", "TOGGLE")
        assert result["ok"] is True
        assert self.service._bindings["clicker_toggle"]["wheel"] == "wheel:up"
        assert self.service._bindings["clicker_toggle"]["mode"] == "TOGGLE"

    def test_modes(self):
        """Test hotkey modes: TOGGLE, HOLD."""
        # Test setting different modes via public API
        result = self.service.set_binding("clicker_toggle", "f6", "TOGGLE")
        assert result["ok"] is True
        assert self.service._bindings["clicker_toggle"]["mode"] == "TOGGLE"

        result = self.service.set_binding("aim_toggle", "f9", "HOLD")
        assert result["ok"] is True
        assert self.service._bindings["aim_toggle"]["mode"] == "HOLD"

    def test_hold_mode(self):
        """Test HOLD mode can be set."""
        service = self.service
        service.set_binding("aim_toggle", "f7", "HOLD")
        assert service._bindings["aim_toggle"]["mode"] == "HOLD"

    def test_repeat_mode(self):
        """Test REPEAT mode - not in _VALID_MODES, should return error."""
        service = self.service
        # REPEAT is not a valid mode, should return error
        result = service.set_binding("aim_toggle", "f8", "REPEAT")
        assert result["ok"] is False
        assert "Invalid mode" in result["error"]

    def test_set_bindings(self):
        """Test bulk setting bindings."""
        bindings = {
            "clicker_toggle": {"key": "f6", "mode": "TOGGLE"},
            "aim_toggle": {"key": "f7", "mode": "HOLD"},
        }
        self.service.set_bindings(bindings)
        assert self.service._bindings["clicker_toggle"]["key"] == "f6"
        assert self.service._bindings["clicker_toggle"]["mode"] == "TOGGLE"
        assert self.service._bindings["aim_toggle"]["key"] == "f7"
        assert self.service._bindings["aim_toggle"]["mode"] == "HOLD"

    def test_set_binding_single(self):
        """Test setting single binding."""
        result = self.service.set_binding("clicker_toggle", "f6", "TOGGLE")
        assert result["ok"] is True
        assert "clicker_toggle" in self.service._bindings

    def test_get_binding(self):
        """Test getting binding info."""
        self.service.set_binding("clicker_toggle", "f6", "TOGGLE")
        bindings = self.service.get_bindings()
        binding = bindings.get("clicker_toggle")
        assert binding is not None
        assert binding["key"] == "f6"
        assert binding["mode"] == "TOGGLE"

    def test_get_nonexistent_binding(self):
        """Test getting non-existent binding."""
        bindings = self.service.get_bindings()
        binding = bindings.get("nonexistent")
        # Returns None for unknown actions (not in HOTKEY_ACTIONS)
        assert binding is None

    def test_list_bindings(self):
        """Test listing all bindings."""
        self.service.set_binding("clicker_toggle", "f6", "TOGGLE")
        self.service.set_binding("aim_toggle", "f7", "HOLD")

        bindings = self.service.get_bindings()
        assert "clicker_toggle" in bindings
        assert "aim_toggle" in bindings
        assert bindings["clicker_toggle"]["key"] == "f6"
        assert bindings["aim_toggle"]["key"] == "f7"

    def test_unregister_all(self):
        """Test unregistering all bindings."""
        self.service.set_binding("clicker_toggle", "f6", "TOGGLE")
        self.service.set_binding("aim_toggle", "f7", "HOLD")

        self.service.unregister_all()
        # unregister_all unregisters hooks but doesn't clear keyboard binding keys.
        # Mouse/wheel bindings get reset to empty keys.
        # For keyboard, use reset_all() to restore defaults.
        bindings = self.service.get_bindings()
        assert bindings["clicker_toggle"]["key"] == "f6"  # keyboard bindings unchanged
        assert bindings["aim_toggle"]["key"] == "f7"  # keyboard bindings unchanged

    def test_reset_all(self):
        """Test resetting all bindings to defaults."""
        self.service.set_binding("clicker_toggle", "f6", "TOGGLE")
        self.service.set_binding("aim_toggle", "f7", "HOLD")

        result = self.service.reset_all()
        assert result["ok"] is True
        # Should revert to defaults
        bindings = self.service.get_bindings()
        assert bindings["clicker_toggle"]["key"] == "f6"  # default
        assert bindings["aim_toggle"]["key"] == "f9"  # default

    def test_parse_key_combo(self):
        """Test key combination parsing via _parse_key_string."""
        # Test various formats
        parsed = self.service._parse_key_string("f6")
        assert parsed["main"] == "f6"
        assert parsed["type"] == "keyboard"

        parsed = self.service._parse_key_string("ctrl+f7")
        assert parsed["modifiers"] == ["ctrl"]
        assert parsed["main"] == "f7"
        assert parsed["type"] == "keyboard"

        parsed = self.service._parse_key_string("shift+ctrl+alt+f8")
        assert set(parsed["modifiers"]) == {"shift", "ctrl", "alt"}
        assert parsed["main"] == "f8"
        assert parsed["type"] == "keyboard"

    def test_normalize_key(self):
        """Test key normalization via _parse_key_string lowercase handling."""
        # Handle case insensitivity
        parsed = self.service._parse_key_string("F6")
        assert parsed["main"] == "f6"

        parsed = self.service._parse_key_string("CTRL+F7")
        assert parsed["main"] == "f7"
        assert parsed["modifiers"] == ["ctrl"]

    def test_thread_safety(self):
        """Test thread-safe operations."""
        results = []

        def register_keys(start, count):
            for i in range(count):
                action_name = f"action_{start+i}"
                # Only test with valid HOTKEY_ACTIONS - use valid action names cyclically
                valid_actions = ["clicker_toggle", "aim_toggle", "macro_start", "macro_stop",
                                 "recorder_start", "recorder_stop", "app_show", "panic_stop"]
                action = valid_actions[(start + i) % len(valid_actions)]
                # Function keys f1-f12 are valid
                key_num = (start + i) % 12 + 1
                r = self.service.set_binding(action, f"f{key_num}", "TOGGLE")
                results.append(r["ok"])

        threads = []
        for i in range(5):
            t = threading.Thread(target=register_keys, args=(i*10, 10))
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        assert all(results)
        # Some bindings may be overwritten as actions are reused cyclically
        assert len(self.service._bindings) <= 8  # Only 8 valid actions


class TestHotkeyServiceIntegration:
    """Integration tests with mocked keyboard listeners."""

    def setup_method(self):
        from app.backend.services.hotkey_service import HotkeyService
        mock_api = MagicMock()
        mock_api.clicker = MagicMock()
        mock_api.clicker.is_running = False
        mock_api.aim = MagicMock()
        mock_api.aim.is_running = False
        mock_api.macro = MagicMock()
        mock_api.macro.is_running = False
        mock_api.recorder = MagicMock()
        mock_api.recorder.is_recording = False
        mock_api.recorder.is_playing = False

        self.service = HotkeyService(mock_api)

    def test_get_status(self):
        """Test getting service status."""
        self.service.set_binding("clicker_toggle", "f6", "TOGGLE")
        status = self.service.debug_status()

        assert "keyboard_lib" in status
        assert "mouse_lib" in status
        assert "pynput" in status
        assert status["keyboard_lib"] is True

    def test_is_key_registered(self):
        """Test checking if a key is already registered - not directly available."""
        # There's no is_key_registered method in the API, but we can check bindings
        self.service.set_binding("clicker_toggle", "f6", "TOGGLE")
        bindings = self.service.get_bindings()
        registered_keys = [b["key"] for b in bindings.values() if b["key"]]
        assert "f6" in registered_keys
        assert "f7" not in registered_keys

    def test_get_bindings_by_key(self):
        """Test getting actions bound to a specific key."""
        self.service.set_binding("clicker_toggle", "f6", "TOGGLE")
        self.service.set_binding("aim_toggle", "f9", "TOGGLE")

        bindings = self.service.get_bindings()
        f6_actions = [action for action, b in bindings.items() if b.get("key") == "f6"]
        assert "clicker_toggle" in f6_actions
        assert "aim_toggle" not in f6_actions

    def test_modifier_parsing(self):
        """Test modifier key parsing via _parse_key_string."""
        from app.backend.services.hotkey_service import HotkeyService
        # Test via static method
        parsed = HotkeyService._parse_key_string("ctrl+f7")
        assert parsed["modifiers"] == ["ctrl"]
        assert parsed["main"] == "f7"

        parsed = HotkeyService._parse_key_string("shift+ctrl+alt+f8")
        assert set(parsed["modifiers"]) == {"shift", "ctrl", "alt"}
        assert parsed["main"] == "f8"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])