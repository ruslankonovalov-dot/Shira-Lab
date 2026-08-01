# tests/integration/test_bridge_integration.py — Integration tests for Phase 3.6
# Tests QmlBridge + Controllers + Services working together
import os
import time

import pytest

# Disable system tray for tests to avoid segfault
os.environ["DISABLE_SYSTEM_TRAY"] = "1"


class TestBridgeIntegration:
    """Integration tests for QmlBridge with all controllers."""

    def setup_method(self):
        # Create a fresh bridge for each test
        pass

    def test_bridge_creation(self):
        """Test that bridge initializes with all controllers."""
        from app.backend.models.runtime_state import RuntimeState
        from app.backend.qml_bridge import QmlBridge

        state = RuntimeState()
        bridge = QmlBridge(state)

        # Verify all controllers are present
        assert hasattr(bridge, "_window_controller")
        assert hasattr(bridge, "_gamepad_controller")
        assert hasattr(bridge, "_hotkey_controller")
        assert hasattr(bridge, "_profile_controller")

        # Verify services are accessible
        assert hasattr(bridge, "clicker")
        assert hasattr(bridge, "aim")
        assert hasattr(bridge, "macro")
        assert hasattr(bridge, "recorder")
        assert hasattr(bridge, "hotkeys")
        assert hasattr(bridge, "_vigem")
        assert hasattr(bridge, "_pico")

    def test_bridge_signals_connected(self):
        """Test that controller signals are connected to bridge."""
        from app.backend.models.runtime_state import RuntimeState
        from app.backend.qml_bridge import QmlBridge

        state = RuntimeState()
        bridge = QmlBridge(state)

        # Check that signals exist
        assert hasattr(bridge, "statusChanged")
        assert hasattr(bridge, "clickerStatusChanged")
        assert hasattr(bridge, "aimStatusChanged")
        assert hasattr(bridge, "macroStatusChanged")
        assert hasattr(bridge, "recorderStatusChanged")
        assert hasattr(bridge, "hotkeysChanged")
        assert hasattr(bridge, "settingsChanged")
        assert hasattr(bridge, "langChanged")

    def test_bridge_clicker_delegation(self):
        """Test clicker service delegation through bridge."""
        from app.backend.models.runtime_state import RuntimeState
        from app.backend.qml_bridge import QmlBridge

        state = RuntimeState()
        bridge = QmlBridge(state)

        # Test clicker start - returns status dict
        result = bridge.startClicker()
        assert isinstance(result, dict)
        assert "is_running" in result
        assert result["is_running"] is True

        # Test clicker stop - returns status dict
        result = bridge.stopClicker()
        assert isinstance(result, dict)
        assert "is_running" in result
        assert result["is_running"] is False

        # Test clicker config - returns status dict (no "ok" wrapper)
        status = bridge.setClickerConfig(100, 0, "L", 0, "sendinput")
        assert isinstance(status, dict)
        assert "is_running" in status
        assert status["interval_ms"] == 100

        # Test clicker status
        result = bridge.getClickerStatus()
        assert isinstance(result, dict)
        assert "is_running" in result

    def test_bridge_aim_delegation(self):
        """Test aim service delegation through bridge."""
        from app.backend.models.runtime_state import RuntimeState
        from app.backend.qml_bridge import QmlBridge

        state = RuntimeState()
        bridge = QmlBridge(state)

        # Test aim start/stop
        result = bridge.aimStart()
        assert isinstance(result, dict)
        assert "ok" in result

        result = bridge.aimStop()
        assert isinstance(result, dict)
        assert "ok" in result

        # Test aim config
        result = bridge.aimSetConfig(0.5, 5, 0.005)
        assert isinstance(result, dict)
        assert "ok" in result

        # Test detection mode
        result = bridge.setAimDetectionMode("color")
        assert isinstance(result, dict)
        assert "ok" in result

        # Test target color
        result = bridge.setAimTargetColor("red")
        assert isinstance(result, dict)
        assert "ok" in result

        result = bridge.aimStatus()
        assert isinstance(result, dict)
        assert "ok" in result

    def test_bridge_macro_delegation(self):
        """Test macro service delegation through bridge."""
        from app.backend.models.runtime_state import RuntimeState
        from app.backend.qml_bridge import QmlBridge

        state = RuntimeState()
        bridge = QmlBridge(state)

        # Test add action - returns status dict
        result = bridge.addMacroAction("a", 0.5, 0.05)
        assert isinstance(result, dict)
        assert "actions" in result

        # Test start/stop - returns status dict
        result = bridge.startMacro()
        assert isinstance(result, dict)
        assert "is_running" in result
        assert result["is_running"] is True

        result = bridge.stopMacro()
        assert isinstance(result, dict)
        assert "is_running" in result
        assert result["is_running"] is False

        # Test clear actions - returns status dict
        result = bridge.clearMacroActions()
        assert isinstance(result, dict)
        assert "actions" in result
        assert result["actions"] == []

        result = bridge.getMacroStatus()
        assert isinstance(result, dict)
        assert "run_mode" in result

    def test_bridge_recorder_delegation(self):
        """Test recorder service delegation through bridge."""
        from app.backend.models.runtime_state import RuntimeState
        from app.backend.qml_bridge import QmlBridge

        state = RuntimeState()
        bridge = QmlBridge(state)

        # Test record
        result = bridge.recorderStart()
        assert isinstance(result, dict)
        assert "ok" in result

        time.sleep(0.05)

        result = bridge.recorderStop()
        assert isinstance(result, dict)
        assert "ok" in result

        # Test play
        records_result = bridge.recorderList()
        if records_result.get("ok") and records_result.get("data"):
            records = records_result["data"]
            if len(records) > 0:
                result = bridge.recorderPlay(records[0])
                assert isinstance(result, dict)
                assert "ok" in result

                time.sleep(0.05)
                result = bridge.recorderStopPlay()
                assert isinstance(result, dict)
                assert "ok" in result

        result = bridge.recorderStatus()
        assert isinstance(result, dict)
        assert "ok" in result

    def test_bridge_hotkey_delegation(self):
        """Test hotkey service delegation through bridge."""
        from app.backend.models.runtime_state import RuntimeState
        from app.backend.qml_bridge import QmlBridge

        state = RuntimeState()
        bridge = QmlBridge(state)

        # Test register/unregister - returns {"ok": True, ...}
        # Use a valid action that the system recognizes
        result = bridge.registerHotkey("clicker_toggle", "f6", "TOGGLE")
        assert isinstance(result, dict)
        assert "ok" in result
        assert result["ok"] is True

        result = bridge.unregisterHotkey("clicker_toggle")
        assert isinstance(result, dict)
        assert "ok" in result
        assert result["ok"] is True

        # Test validate hotkey - returns validation result (without ok wrapper)
        result = bridge.validateKey("f6")
        assert isinstance(result, dict)
        assert "ok" in result
        assert result["ok"] is True

        result = bridge.validateKey("invalid")
        assert isinstance(result, dict)
        assert result["ok"] is False

        # Test debug - returns raw dict without "ok" wrapper
        result = bridge.hotkeysDebugStatus()
        assert isinstance(result, dict)
        assert "keyboard_lib" in result
        assert "mouse_lib" in result
        assert "pynput" in result

    def test_bridge_gamepad_delegation(self):
        """Test gamepad delegation through bridge."""
        from app.backend.models.runtime_state import RuntimeState
        from app.backend.qml_bridge import QmlBridge

        state = RuntimeState()
        bridge = QmlBridge(state)

        # Test Pico
        result = bridge.listPicoDevices()
        assert isinstance(result, dict)
        assert "ok" in result

        result = bridge.getPicoStatus()
        assert isinstance(result, dict)

        # Test ViGEm
        result = bridge.getVigemStatus()
        assert isinstance(result, dict)

    def test_bridge_profile_delegation(self):
        """Test profile delegation through bridge."""
        from app.backend.models.runtime_state import RuntimeState
        from app.backend.qml_bridge import QmlBridge

        state = RuntimeState()
        bridge = QmlBridge(state)

        # Test palettes - returns raw dict (TERMINAL_PALETTES)
        result = bridge.getPalettes()
        assert isinstance(result, dict)
        assert "matrix" in result

        # Test game profiles - returns {"ok": True, ...}
        result = bridge.listGameProfiles()
        assert isinstance(result, dict)
        assert "ok" in result

        # Test target windows - returns {"ok": True, ...}
        result = bridge.getWindows()
        assert isinstance(result, dict)
        assert "ok" in result

        result = bridge.getModuleTargetWindow("aim")
        assert isinstance(result, dict)
        assert "ok" in result

    def test_bridge_invalid_slot_args(self):
        """Test bridge handles invalid arguments gracefully."""
        from app.backend.models.runtime_state import RuntimeState
        from app.backend.qml_bridge import QmlBridge

        state = RuntimeState()
        bridge = QmlBridge(state)

        # Invalid clicker config
        result = bridge.setClickerConfig(-1, 0, "L", 0, "sendinput")
        assert isinstance(result, dict)
        assert result["ok"] is False

        # Invalid aim detection mode
        result = bridge.setAimDetectionMode("invalid_mode")
        assert isinstance(result, dict)
        assert result["ok"] is False

        # Invalid pico mode
        result = bridge.setPicoMode("INVALID")
        assert isinstance(result, dict)
        assert result["ok"] is False


class TestRuntimeState:
    """Tests for RuntimeState model."""

    def test_default_values(self):
        from app.backend.models.runtime_state import RuntimeState

        state = RuntimeState()

        # Check all expected attributes exist
        assert hasattr(state, "clicker_running")
        assert hasattr(state, "aim_running")
        assert hasattr(state, "macro_running")
        assert hasattr(state, "recorder_recording")
        assert hasattr(state, "recorder_playing")
        assert hasattr(state, "clicker_config")
        assert hasattr(state, "aim_config")
        assert hasattr(state, "macro_config")
        assert hasattr(state, "recorder_config")
        assert hasattr(state, "hotkeys")
        assert hasattr(state, "palettes")
        assert hasattr(state, "terminal_palette")
        assert hasattr(state, "ui_lang")
        assert hasattr(state, "game_profiles")

    def test_config_defaults(self):
        from app.backend.models.runtime_state import RuntimeState

        state = RuntimeState()

        # Clicker config
        assert state.clicker_config["interval_ms"] == 100
        assert state.clicker_config["button"] == "L"
        assert state.clicker_config["background_method"] == "sendinput"

        # Aim config
        assert state.aim_config["speed"] == 0.5
        assert state.aim_config["fov"] == 300
        assert state.aim_config["background_method"] == "sendinput"

        # Macro config
        assert state.macro_config["mode"] == "SEQUENTIAL"

        # UI
        assert state.terminal_palette == "matrix"
        assert state.ui_lang == "RU"


class TestInputValidation:
    """Tests for input validation helpers."""

    def test_validate_interval_ms(self):
        from app.backend.services.input_validation import validate_interval_ms

        # Valid
        ok, err = validate_interval_ms(100)
        assert ok is True
        assert err == ""

        ok, err = validate_interval_ms(1)
        assert ok is True

        # Invalid
        ok, err = validate_interval_ms(0)
        assert ok is False

        ok, err = validate_interval_ms(-1)
        assert ok is False

        ok, err = validate_interval_ms("invalid")
        assert ok is False

    def test_validate_button(self):
        from app.backend.services.input_validation import validate_button

        for btn in ["L", "R", "M", "X1", "X2"]:
            ok, err = validate_button(btn)
            assert ok is True

        ok, err = validate_button("INVALID")
        assert ok is False

    def test_validate_detection_mode(self):
        from app.backend.services.input_validation import \
            validate_detection_mode

        for mode in ["auto", "multi", "circles", "color", "calibrate"]:
            ok, err = validate_detection_mode(mode)
            assert ok is True

        ok, err = validate_detection_mode("invalid")
        assert ok is False

    def test_validate_target_color(self):
        from app.backend.services.input_validation import validate_target_color

        for color in [
            "red",
            "blue",
            "green",
            "purple",
            "yellow",
            "cyan",
            "orange",
            "pink",
        ]:
            ok, err = validate_target_color(color)
            assert ok is True

        ok, err = validate_target_color("invalid")
        assert ok is False

    def test_validate_background_method(self):
        from app.backend.services.input_validation import \
            validate_background_method

        for method in ["sendinput", "postmessage", "vigem", "pico"]:
            ok, err = validate_background_method(method)
            assert ok is True

        ok, err = validate_background_method("invalid")
        assert ok is False

    def test_validate_hotkey_key(self):
        from app.backend.services.input_validation import validate_hotkey_key

        # Keyboard
        for key in ["f6", "ctrl+f7", "shift+ctrl+alt+f8", "a", "1", "escape"]:
            ok, err = validate_hotkey_key(key)
            assert ok is True

        # Mouse
        for key in ["m1", "m2", "m3"]:
            ok, err = validate_hotkey_key(key)
            assert ok is True

        # Wheel
        for key in ["wheel_up", "wheel_down"]:
            ok, err = validate_hotkey_key(key)
            assert ok is True

        # Invalid
        for key in ["", "invalid_key", "ctrl+invalid"]:
            ok, err = validate_hotkey_key(key)
            assert ok is False

    def test_validate_hotkey_mode(self):
        from app.backend.services.input_validation import validate_hotkey_mode

        for mode in ["TOGGLE", "HOLD", "REPEAT"]:
            ok, err = validate_hotkey_mode(mode)
            assert ok is True

        ok, err = validate_hotkey_mode("INVALID")
        assert ok is False

    def test_validate_pico_mode(self):
        from app.backend.services.input_validation import validate_pico_mode

        for mode in ["COMPOSITE", "KEYBOARD", "MOUSE", "GAMEPAD"]:
            ok, err = validate_pico_mode(mode)
            assert ok is True

        ok, err = validate_pico_mode("INVALID")
        assert ok is False

    def test_validate_vigem_target_type(self):
        from app.backend.services.input_validation import \
            validate_vigem_target_type

        for ttype in ["X360", "DS4"]:
            ok, err = validate_vigem_target_type(ttype)
            assert ok is True

        ok, err = validate_vigem_target_type("INVALID")
        assert ok is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
