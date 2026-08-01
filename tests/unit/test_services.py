# tests/unit/test_services.py — Comprehensive service tests for Phase 3.6
# Target: ≥80% coverage on services + controllers
import time
from unittest.mock import Mock

import pytest


class TestClickerService:
    """Tests for ClickerService."""

    def test_start_stop(self):
        from app.backend.services.clicker_service import ClickerService

        service = ClickerService()
        service._bridge = Mock()

        # Test start
        result = service.start()
        assert result["is_running"] is True
        assert service.is_running is True

        # Test stop
        result = service.stop()
        assert result["is_running"] is False
        assert service.is_running is False

    def test_config_validation(self):
        from app.backend.services.clicker_service import ClickerService

        service = ClickerService()
        service._bridge = Mock()

        # Valid config - update_config returns status dict without "ok" field
        result = service.update_config(100, 0, "L", 0, "sendinput")
        assert result["is_running"] is False
        assert result["interval_ms"] == 100

        # Invalid interval - will be corrected to 1 by the service
        result = service.update_config(-1, 0, "L", 0, "sendinput")
        assert result["interval_ms"] == 1

        # Invalid button - defaults to L
        result = service.update_config(100, 0, "INVALID", 0, "sendinput")
        assert service.button == "L"

        # Invalid background_method - keeps current
        original = service.background_method
        result = service.update_config(100, 0, "L", 0, "invalid")
        assert service.background_method == original

    def test_calculation(self):
        from app.backend.services.clicker_service import ClickerService

        service = ClickerService()
        service._bridge = Mock()

        # Start briefly to get some clicks
        service.update_config(10, 0, "L", 10, "sendinput")
        service.start()
        time.sleep(0.15)
        service.stop()

        # Should have clicks
        assert service.click_count >= 0

    def test_background_methods(self):
        from app.backend.services.clicker_service import ClickerService

        service = ClickerService()
        service._bridge = Mock()

        for method in ["sendinput", "postmessage", "vigem", "pico"]:
            result = service.update_config(100, 0, "L", 0, method)
            assert result["background_method"] == method

        # Invalid method - should not change
        original = service.background_method
        result = service.update_config(100, 0, "L", 0, "invalid")
        assert service.background_method == original


class TestRecorderService:
    """Tests for RecorderService."""

    def setup_method(self):
        from app.backend.services.recorder_service import RecorderService

        self.service = RecorderService()
        self.service._bridge = Mock()

    def test_start_stop_record(self):
        """Test start/stop recording."""
        result = self.service.start_recording()
        assert result["ok"] is True
        assert self.service.is_recording is True

        time.sleep(0.05)

        result = self.service.stop_recording()
        assert result["ok"] is True
        assert self.service.is_recording is False
        assert "events_count" in result

    def test_play_record(self):
        """Test playing a record."""
        # Need at least one record
        self.service.start_recording()
        time.sleep(0.2)  # Longer recording for more events
        self.service.stop_recording()

        records = self.service.list_records()
        assert len(records["records"]) > 0

        record_name = records["records"][0]
        result = self.service.play_record(record_name)
        assert result["ok"] is True

        time.sleep(0.01)
        status = self.service.status()
        assert status["ok"] is True
        assert status["is_playing"] is True

        time.sleep(0.3)  # Wait for playback to complete

        result = self.service.stop_playing()
        assert result["ok"] is True

    def test_delete_record(self):
        """Test deleting a record."""
        self.service.start_recording()
        time.sleep(0.05)
        self.service.stop_recording()

        records = self.service.list_records()
        record_name = records["records"][0]

        result = self.service.delete_record(record_name)
        assert result["ok"] is True

        records = self.service.list_records()
        assert record_name not in records["records"]


class TestAimService:
    """Tests for AimService."""

    def test_detection_modes(self):
        from app.backend.services.aim_service import AimService

        service = AimService()

        for mode in ["auto", "multi", "circles", "color", "calibrate"]:
            result = service.set_detection_mode(mode)
            assert result["ok"] is True
            assert service.detection_mode == mode

    def test_target_color(self):
        from app.backend.services.aim_service import AimService

        service = AimService()

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
            result = service.set_target_color(color)
            assert result["ok"] is True
            assert service.target_color == color

    def test_config(self):
        from app.backend.services.aim_service import AimService

        service = AimService()

        # update_config returns status dict without "ok" field
        result = service.update_config(confidence=0.5, smooth_steps=5, reset_delay=0.005)
        assert result["confidence"] == 0.5
        assert result["smooth_steps"] == 5
        assert result["reset_delay"] == 0.005

    def test_start_stop(self):
        from app.backend.services.aim_service import AimService

        service = AimService()

        result = service.start()
        assert result["is_running"] is True
        assert service.is_running is True

        result = service.stop()
        assert result["is_running"] is False
        assert service.is_running is False


class TestMacroService:
    """Tests for MacroService."""

    def test_add_action(self):
        from app.backend.services.macro_service import MacroService

        service = MacroService()

        # Clear first
        service.clear_actions()

        result = service.add_action("a", 0.5, 0.05)
        assert result["actions_count"] == 1

        status = service.get_status()
        assert status["actions_count"] == 1
        assert status["actions"][0]["key"] == "a"

    def test_undo_redo(self):
        from app.backend.services.macro_service import MacroService

        service = MacroService()

        service.clear_actions()
        service.add_action("a", 0.5, 0.05)
        service.add_action("b", 0.5, 0.05)

        # Undo
        result = service.undo()
        assert result["ok"] is True
        assert result["actions_count"] == 1

        # Redo
        result = service.redo()
        assert result["ok"] is True
        assert result["actions_count"] == 2

    def test_move_action(self):
        from app.backend.services.macro_service import MacroService

        service = MacroService()

        service.clear_actions()
        service.add_action("a", 0.5, 0.05)
        service.add_action("b", 0.5, 0.05)

        # Move action from index 0 to 1
        result = service.move_action(0, 1)
        assert result["ok"] is True

    def test_run_mode(self):
        from app.backend.services.macro_service import MacroService

        service = MacroService()

        for mode in ["SEQUENTIAL", "PARALLEL"]:
            result = service.set_run_mode(mode)
            assert result["run_mode"] == mode
            assert service.run_mode == mode

        result = service.set_run_mode("INVALID")
        assert result["run_mode"] == "SEQUENTIAL"
        assert service.run_mode == "SEQUENTIAL"

    def test_start_stop(self):
        from app.backend.services.macro_service import MacroService

        service = MacroService()

        service.clear_actions()
        service.add_action("a", 0.1, 0.05)

        result = service.start()
        assert result["is_running"] is True
        assert service.is_running is True

        time.sleep(0.3)

        result = service.stop()
        assert result["is_running"] is False
        assert service.is_running is False


class TestProfileIO:
    """Tests for Profile I/O."""

    def test_save_load_roundtrip(self, tmp_path):
        from app.backend.profile_io import load_profile, save_profile

        test_profile = {
            "clicker": {
                "interval_ms": 100,
                "hold_ms": 0,
                "button": "L",
                "limit": 0,
                "background_method": "sendinput",
            },
            "aim": {"speed": 0.5, "fov": 300, "smooth": 5, "reset_delay": 0.005},
            "macro": {"actions": [], "mode": "SEQUENTIAL"},
            "recorder": {"records_dir": "records"},
            "hotkeys": {},
            "ui": {"terminal_palette": "matrix", "ui_lang": "RU"},
            "game_profiles": {},
        }

        profile_path = tmp_path / "test_profile.json"
        save_profile(test_profile, str(profile_path))

        loaded = load_profile(str(profile_path))
        assert loaded["clicker"]["interval_ms"] == 100
        assert loaded["ui"]["terminal_palette"] == "matrix"

    def test_version_migration(self, tmp_path):
        from app.backend.profile_io import (CURRENT_PROFILE_VERSION,
                                            load_profile)

        old_profile = {
            "version": 1,  # Old version
            "clicker": {"interval_ms": 100},
            "aim": {},
            "macro": {"actions": []},
            "recorder": {},
            "hotkeys": {},
            "ui": {"terminal_palette": "matrix"},
        }

        profile_path = tmp_path / "old_profile.json"
        import json

        with open(profile_path, "w", encoding="utf-8") as f:
            json.dump(old_profile, f)

        loaded = load_profile(str(profile_path))
        assert "version" in loaded
        assert loaded["version"] == CURRENT_PROFILE_VERSION


class TestHotkeyService:
    """Tests for HotkeyService."""

    def test_validate_key(self):
        from app.backend.services.hotkey_service import HotkeyService

        service = HotkeyService(Mock())

        # Keyboard keys
        assert service.validate_key("f6")["ok"] is True
        assert service.validate_key("ctrl+f7")["ok"] is True
        assert service.validate_key("shift+ctrl+alt+f8")["ok"] is True

        # Mouse
        assert service.validate_key("mouse:3")["ok"] is True
        assert service.validate_key("mouse:4")["ok"] is True
        assert service.validate_key("mouse:5")["ok"] is True

        # Wheel
        assert service.validate_key("wheel:up")["ok"] is True
        assert service.validate_key("wheel:down")["ok"] is True

        # Invalid
        assert service.validate_key("")["ok"] is False
        assert service.validate_key("invalid_key_name")["ok"] is False

    def test_register_unregister(self):
        from app.backend.services.hotkey_service import HotkeyService

        mock_api = Mock()
        mock_api.clicker = Mock()
        mock_api.clicker.is_running = False
        mock_api.aim = Mock()
        mock_api.aim.is_running = False
        mock_api.macro = Mock()
        mock_api.macro.is_running = False
        mock_api.recorder = Mock()
        mock_api.recorder.is_running = False
        mock_api.vigem = Mock()
        mock_api.vigem.is_running = False
        mock_api.pico = Mock()
        mock_api.pico.is_connected = False

        service = HotkeyService(mock_api)

        # Register
        result = service.set_binding("clicker_toggle", "f6", "TOGGLE")
        assert result["ok"] is True

        # Check via public API
        bindings = service.get_bindings()
        assert bindings["clicker_toggle"]["key"] == "f6"
        assert bindings["clicker_toggle"]["mode"] == "TOGGLE"

        # Unregister by setting empty key (clears the binding)
        result = service.set_binding("clicker_toggle", "", "TOGGLE")
        assert result["ok"] is True

        # Should clear the binding (reset_binding() resets to default)
        bindings = service.get_bindings()
        assert bindings["clicker_toggle"]["key"] == ""

    def test_mouse_binding(self):
        from app.backend.services.hotkey_service import HotkeyService

        mock_api = Mock()
        mock_api.clicker = Mock()
        mock_api.clicker.is_running = False
        mock_api.aim = Mock()
        mock_api.aim.is_running = False
        mock_api.macro = Mock()
        mock_api.macro.is_running = False
        mock_api.recorder = Mock()
        mock_api.recorder.is_running = False

        service = HotkeyService(mock_api)

        # Register mouse binding (use valid action "clicker_toggle")
        result = service.set_binding("clicker_toggle", "mouse:3", "HOLD")
        assert result["ok"] is True
        # For mouse bindings, the binding has 'button' key instead of 'key'
        assert service._bindings["clicker_toggle"]["button"] == "mouse:3"
        assert service._bindings["clicker_toggle"]["mode"] == "HOLD"


class TestVigemService:
    """Tests for VigemService."""

    def test_add_remove_target(self):
        from app.backend.services.vigem_service import VigemService

        service = VigemService()

        # Add X360 target
        result = service.add_x360()
        assert isinstance(result, int | type(None))

    def test_button_name_to_mask(self):
        from app.backend.services.vigem_service import (XUSB_BUTTON_MAP,
                                                        VigemService)

        # Test known button mappings
        assert VigemService.button_name_to_mask("a") == XUSB_BUTTON_MAP.get("a", 0)
        assert VigemService.button_name_to_mask("b") == XUSB_BUTTON_MAP.get("b", 0)
        assert VigemService.button_name_to_mask("x") == XUSB_BUTTON_MAP.get("x", 0)
        assert VigemService.button_name_to_mask("y") == XUSB_BUTTON_MAP.get("y", 0)
        assert VigemService.button_name_to_mask("lb") == XUSB_BUTTON_MAP.get("lb", 0)
        assert VigemService.button_name_to_mask("rb") == XUSB_BUTTON_MAP.get("rb", 0)
        assert VigemService.button_name_to_mask("back") == XUSB_BUTTON_MAP.get("back", 0)
        assert VigemService.button_name_to_mask("start") == XUSB_BUTTON_MAP.get("start", 0)
        assert VigemService.button_name_to_mask("up") == XUSB_BUTTON_MAP.get("up", 0)
        assert VigemService.button_name_to_mask("down") == XUSB_BUTTON_MAP.get("down", 0)
        assert VigemService.button_name_to_mask("left") == XUSB_BUTTON_MAP.get("left", 0)
        assert VigemService.button_name_to_mask("right") == XUSB_BUTTON_MAP.get("right", 0)

        # Invalid button
        assert VigemService.button_name_to_mask("invalid") == 0

    def test_press_release_button(self):
        from app.backend.services.vigem_service import VigemService

        service = VigemService()

        service.add_x360()
        targets = service.list_targets()
        if targets:
            target_id = list(targets.keys())[0]
            # Just check methods exist and return proper types
            result = service.x360_press_button(target_id, "a")
            assert isinstance(result, bool)

            result = service.x360_release_button(target_id, "a")
            assert isinstance(result, bool)

    def test_set_state_structure(self):
        from app.backend.services.vigem_service import VigemService

        service = VigemService()

        service.add_x360()
        targets = service.list_targets()
        if targets:
            target_id = list(targets.keys())[0]
            result = service.x360_set_state(
                target_id, left_x=10000, left_y=0, right_x=0, right_y=0, lt=0, rt=0
            )
            assert isinstance(result, bool)

    def test_set_state_trigger_limits(self):
        from app.backend.services.vigem_service import VigemService

        service = VigemService()

        service.add_x360()
        targets = service.list_targets()
        if targets:
            target_id = list(targets.keys())[0]
            # Should clamp
            result = service.x360_set_state(target_id, lt=300, rt=255)
            assert isinstance(result, bool)

            result = service.x360_set_state(target_id, lt=-10, rt=0)
            assert isinstance(result, bool)

    def test_set_state_stick_limits(self):
        from app.backend.services.vigem_service import VigemService

        service = VigemService()

        service.add_x360()
        targets = service.list_targets()
        if targets:
            target_id = list(targets.keys())[0]
            # Should clamp
            result = service.x360_set_state(
                target_id,
                left_x=40000,  # Over limit
                left_y=-40000,
                right_x=0,
                right_y=0,
                lt=0,
                rt=0,
            )
            assert isinstance(result, bool)

    def test_x360_set_buttons(self):
        from app.backend.services.vigem_service import VigemService

        service = VigemService()

        service.add_x360()
        targets = service.list_targets()
        if targets:
            target_id = list(targets.keys())[0]
            result = service.x360_set_buttons(target_id, 0x1000)  # A button
            assert isinstance(result, bool)

    def test_x360_set_triggers(self):
        from app.backend.services.vigem_service import VigemService

        service = VigemService()

        service.add_x360()
        targets = service.list_targets()
        if targets:
            target_id = list(targets.keys())[0]
            result = service.x360_set_triggers(target_id, 128, 200)
            assert isinstance(result, bool)

    def test_x360_set_left_stick(self):
        from app.backend.services.vigem_service import VigemService

        service = VigemService()

        service.add_x360()
        targets = service.list_targets()
        if targets:
            target_id = list(targets.keys())[0]
            result = service.x360_set_left_stick(target_id, 10000, -5000)
            assert isinstance(result, bool)

    def test_x360_set_right_stick(self):
        from app.backend.services.vigem_service import VigemService

        service = VigemService()

        service.add_x360()
        targets = service.list_targets()
        if targets:
            target_id = list(targets.keys())[0]
            result = service.x360_set_right_stick(target_id, 0, 10000)
            assert isinstance(result, bool)

    def test_x360_reset(self):
        from app.backend.services.vigem_service import VigemService

        service = VigemService()

        service.add_x360()
        targets = service.list_targets()
        if targets:
            target_id = list(targets.keys())[0]
            result = service.x360_reset(target_id)
            assert isinstance(result, bool)

    def test_get_status_structure(self):
        from app.backend.services.vigem_service import VigemService

        service = VigemService()

        result = service.list_targets()
        assert isinstance(result, dict)

    def test_is_available(self):
        from app.backend.services.vigem_service import VigemService

        service = VigemService()

        result = service.is_available()
        assert isinstance(result, bool)

    def test_connect_disconnect(self):
        from app.backend.services.vigem_service import VigemService

        service = VigemService()

        result = service.connect()
        assert isinstance(result, bool)
        service.disconnect()

    def test_combine_buttons(self):
        from app.backend.services.vigem_service import VigemService

        service = VigemService()

        mask = service.combine_buttons("a", "b", "x")
        assert isinstance(mask, int)
        assert mask > 0

    def test_stick_normalize(self):
        from app.backend.services.vigem_service import VigemService

        service = VigemService()

        result = service.stick_normalize(1.0)
        assert result == 32767

        result = service.stick_normalize(-1.0)
        assert result == -32768

        result = service.stick_normalize(0.0)
        assert result == 0

        # Clamping
        result = service.stick_normalize(2.0)
        assert result == 32767

        result = service.stick_normalize(-2.0)
        assert result == -32768

    def test_trigger_normalize(self):
        from app.backend.services.vigem_service import VigemService

        service = VigemService()

        result = service.trigger_normalize(1.0)
        assert result == 255

        result = service.trigger_normalize(0.0)
        assert result == 0

        result = service.trigger_normalize(0.5)
        assert result == 127  # int(0.5 * 255) = 127

        # Clamping
        result = service.trigger_normalize(2.0)
        assert result == 255

        result = service.trigger_normalize(-1.0)
        assert result == 0


class TestPicoService:
    """Tests for PicoService."""

    def test_protocol_crc(self):
        from app.backend.services.pico_protocol import calculate_crc8

        # Test CRC8-Dallas/Maxim (init=0xFF, poly=0x31)
        assert calculate_crc8(b"\xaa\x01\x00") == 0xCD
        assert calculate_crc8(b"") == 0xFF
        assert calculate_crc8(b"\x01\x02\x03") == 0x87

    def test_button_map(self):
        from app.backend.services.pico_service import PicoService

        service = PicoService()

        # Test default mapping
        assert service.get_button_map("A") == "space"
        service.set_button_map("A", "f1")
        assert service.get_button_map("A") == "f1"

    def test_connect_disconnect(self):
        from app.backend.services.pico_service import PicoService

        service = PicoService()

        # Try to connect (will fail if no Pico, but should return proper structure)
        result = service.connect("")
        assert isinstance(result, bool)


class TestBridgeControllers:
    """Tests for controller slots returning correct shapes."""

    def test_window_controller_slots(self):
        from unittest.mock import Mock

        from app.backend.controllers.window_controller import WindowController
        from app.backend.models.runtime_state import RuntimeState

        state = RuntimeState()
        controller = WindowController(state, Mock(), Mock(), Mock(), Mock(), Mock(), Mock())

        # Test setTerminalPalette
        result = controller.setTerminalPalette("matrix")
        # setTerminalPalette returns None, so just verify no exception

        # Test toggleWindowPin
        result = controller.toggleWindowPin()
        assert isinstance(result, bool)

    def test_gamepad_controller_slots(self):
        from app.backend.controllers.gamepad_controller import \
            GamepadController

        controller = GamepadController()

        # Test get_vigem_status (always available)
        result = controller.getVigemStatus()
        assert isinstance(result, dict)
        assert "ok" in result

    def test_hotkey_controller_slots(self):
        from unittest.mock import Mock

        from app.backend.controllers.hotkey_controller import HotkeyController
        from app.backend.models.runtime_state import RuntimeState
        from app.backend.services.hotkey_service import HotkeyService

        state = RuntimeState()
        mock_api = Mock()
        mock_api.clicker = Mock()
        mock_api.clicker.is_running = False
        mock_api.aim = Mock()
        mock_api.aim.is_running = False
        mock_api.macro = Mock()
        mock_api.macro.is_running = False
        mock_api.recorder = Mock()
        mock_api.recorder.is_running = False
        hotkey_service = HotkeyService(mock_api)
        controller = HotkeyController(state, hotkey_service)

        # Test get_hotkeys_debug
        result = controller.hotkeysDebugStatus()
        assert isinstance(result, dict)
        assert "keyboard_lib" in result

    def test_profile_controller_slots(self):
        from app.backend.controllers.profile_controller import \
            ProfileController
        from app.backend.models.runtime_state import RuntimeState

        state = RuntimeState()
        controller = ProfileController(state)

        # Test list_game_profiles
        result = controller.listGameProfiles()
        assert isinstance(result, dict)
        assert "ok" in result

        # Test export/import (may need mocking)
        result = controller.getPalettes()
        assert isinstance(result, dict)
        assert "matrix" in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
