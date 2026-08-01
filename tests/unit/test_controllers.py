# tests/unit/test_controllers.py — Controller unit tests for Phase 3.6
# Target: ≥80% coverage on 4 controllers
from unittest.mock import Mock

import pytest


class TestWindowController:
    """Tests for WindowController slots and signals."""

    def test_panic_stop(self):
        from app.backend.controllers.window_controller import WindowController
        from app.backend.models.runtime_state import RuntimeState

        state = RuntimeState()
        controller = WindowController(
            state, Mock(), Mock(), Mock(), Mock(), Mock(), Mock()
        )

        result = controller.panicStop()
        assert isinstance(result, dict)
        assert "ok" in result
        assert result["ok"] is True

    def test_get_overlay_visible(self):
        from app.backend.controllers.window_controller import WindowController
        from app.backend.models.runtime_state import RuntimeState

        state = RuntimeState()
        controller = WindowController(
            state, Mock(), Mock(), Mock(), Mock(), Mock(), Mock()
        )

        result = controller.getOverlayVisible()
        assert isinstance(result, bool)

    def test_set_overlay_visible(self):
        from app.backend.controllers.window_controller import WindowController
        from app.backend.models.runtime_state import RuntimeState

        state = RuntimeState()
        controller = WindowController(
            state, Mock(), Mock(), Mock(), Mock(), Mock(), Mock()
        )

        result = controller.setOverlayVisible(False)
        assert result is None
        assert controller.overlayVisible is False

    def test_get_performance_profile(self):
        from app.backend.controllers.window_controller import WindowController
        from app.backend.models.runtime_state import RuntimeState

        state = RuntimeState()
        controller = WindowController(
            state, Mock(), Mock(), Mock(), Mock(), Mock(), Mock()
        )

        result = controller.getPerformanceProfile()
        assert isinstance(result, dict)
        assert "ok" in result

    def test_detect_system_theme(self):
        from app.backend.controllers.window_controller import WindowController
        from app.backend.models.runtime_state import RuntimeState

        state = RuntimeState()
        controller = WindowController(
            state, Mock(), Mock(), Mock(), Mock(), Mock(), Mock()
        )

        result = controller.detectSystemTheme()
        assert isinstance(result, dict)
        assert "ok" in result

    def test_export_import_profile_dialog(self):
        from unittest.mock import patch

        from app.backend.controllers.window_controller import WindowController
        from app.backend.models.runtime_state import RuntimeState

        state = RuntimeState()
        controller = WindowController(
            state, Mock(), Mock(), Mock(), Mock(), Mock(), Mock()
        )

        # Mock QFileDialog to avoid GUI interaction
        with patch(
            "PySide6.QtWidgets.QFileDialog.getSaveFileName",
            return_value=("test_profile.json", "JSON Files (*.json)"),
        ):
            with patch(
                "app.backend.profile_io.export_profile",
                return_value={"ok": True, "path": "test_profile.json"},
            ):
                result = controller.exportProfileDialog()
                assert isinstance(result, dict)
                assert "ok" in result

        with patch(
            "PySide6.QtWidgets.QFileDialog.getOpenFileName",
            return_value=("test_profile.json", "JSON Files (*.json)"),
        ):
            with patch(
                "app.backend.profile_io.import_profile",
                return_value={"ok": True, "applied": True},
            ):
                result = controller.importProfileDialog()
                assert isinstance(result, dict)
                assert "ok" in result

    def test_crash_report_methods(self):
        from app.backend.controllers.window_controller import WindowController
        from app.backend.models.runtime_state import RuntimeState

        state = RuntimeState()
        controller = WindowController(
            state, Mock(), Mock(), Mock(), Mock(), Mock(), Mock()
        )

        result = controller.setCrashReportSending(True)
        assert isinstance(result, bool)

        result = controller.listCrashReports()
        assert isinstance(result, dict)
        assert "ok" in result

        result = controller.clearAllCrashReports()
        assert isinstance(result, dict)
        assert "ok" in result

    def test_monitor_methods(self):
        from app.backend.controllers.window_controller import WindowController
        from app.backend.models.runtime_state import RuntimeState

        state = RuntimeState()
        controller = WindowController(
            state, Mock(), Mock(), Mock(), Mock(), Mock(), Mock()
        )

        result = controller.getMonitors()
        assert isinstance(result, dict)
        assert "ok" in result

        result = controller.getWorkArea()
        assert isinstance(result, dict)
        assert "ok" in result

    def test_get_work_area_for_monitor(self):
        from app.backend.controllers.window_controller import WindowController
        from app.backend.models.runtime_state import RuntimeState

        state = RuntimeState()
        controller = WindowController(
            state, Mock(), Mock(), Mock(), Mock(), Mock(), Mock()
        )

        result = controller.getWorkAreaForMonitor(0)
        assert isinstance(result, dict)
        assert "ok" in result

    def test_clamp_overlay_position(self):
        from app.backend.controllers.window_controller import WindowController
        from app.backend.models.runtime_state import RuntimeState

        state = RuntimeState()
        controller = WindowController(
            state, Mock(), Mock(), Mock(), Mock(), Mock(), Mock()
        )

        result = controller.clampOverlayPosition(100, 100, 200, 200)
        assert isinstance(result, dict)
        assert "ok" in result

    def test_toggle_window_pin(self):
        from app.backend.controllers.window_controller import WindowController
        from app.backend.models.runtime_state import RuntimeState

        state = RuntimeState()
        controller = WindowController(
            state, Mock(), Mock(), Mock(), Mock(), Mock(), Mock()
        )

        result = controller.toggleWindowPin()
        assert isinstance(result, bool)

    def test_show_app_window(self):
        from app.backend.controllers.window_controller import WindowController
        from app.backend.models.runtime_state import RuntimeState

        state = RuntimeState()
        controller = WindowController(
            state, Mock(), Mock(), Mock(), Mock(), Mock(), Mock()
        )

        result = controller.showAppWindow()
        assert result is None

    def test_toggle_overlay_hud(self):
        from app.backend.controllers.window_controller import WindowController
        from app.backend.models.runtime_state import RuntimeState

        state = RuntimeState()
        controller = WindowController(
            state, Mock(), Mock(), Mock(), Mock(), Mock(), Mock()
        )

        result = controller.toggleOverlayHUD()
        assert result is None

    def test_reassert_overlay_topmost(self):
        from app.backend.controllers.window_controller import WindowController
        from app.backend.models.runtime_state import RuntimeState

        state = RuntimeState()
        controller = WindowController(
            state, Mock(), Mock(), Mock(), Mock(), Mock(), Mock()
        )

        result = controller.reassertOverlayTopmost()
        assert result is None

    def test_set_crash_report_sending(self):
        from app.backend.controllers.window_controller import WindowController
        from app.backend.models.runtime_state import RuntimeState

        state = RuntimeState()
        controller = WindowController(
            state, Mock(), Mock(), Mock(), Mock(), Mock(), Mock()
        )

        result = controller.setCrashReportSending(True)
        assert isinstance(result, bool)

    def test_log_method(self):
        from app.backend.controllers.window_controller import WindowController
        from app.backend.models.runtime_state import RuntimeState

        state = RuntimeState()
        controller = WindowController(
            state, Mock(), Mock(), Mock(), Mock(), Mock(), Mock()
        )

        # Should not raise
        controller.log("INFO", "TEST", "test message")


class TestGamepadController:
    """Tests for GamepadController slots and signals."""

    def setup_method(self):
        from app.backend.controllers.gamepad_controller import GamepadController

        self.controller = GamepadController()

    def test_get_vigem_status(self):
        result = self.controller.getVigemStatus()
        assert isinstance(result, dict)
        assert "ok" in result
        if result["ok"]:
            assert "connected" in result
            assert "targets" in result
            assert "target_count" in result

    def test_detect_physical_gamepads(self):
        result = self.controller.detectPhysicalGamepads()
        assert isinstance(result, dict)
        assert "ok" in result
        if result["ok"]:
            assert "gamepads" in result
            assert isinstance(result["gamepads"], list)

    def test_set_gamepad_controller_type(self):
        for ctrl_type in ["X360", "DS4"]:
            result = self.controller.setGamepadControllerType(ctrl_type)
            assert isinstance(result, dict)
            assert "ok" in result

        # Invalid type
        result = self.controller.setGamepadControllerType("INVALID")
        assert isinstance(result, dict)
        assert result["ok"] is False

    def test_set_gamepad_target_index(self):
        for idx in ["0", "1", "2", "3"]:
            result = self.controller.setGamepadTargetIndex(idx)
            assert isinstance(result, dict)
            assert "ok" in result

        # Invalid index
        result = self.controller.setGamepadTargetIndex("5")
        assert isinstance(result, dict)
        assert result["ok"] is False

    def test_set_gamepad_background_method(self):
        for method in ["sendinput", "postmessage", "vigem", "pico"]:
            result = self.controller.setGamepadBackgroundMethod(method, 0)
            assert isinstance(result, dict)
            assert "ok" in result

        # Invalid method
        result = self.controller.setGamepadBackgroundMethod("invalid", 0)
        assert isinstance(result, dict)
        assert result["ok"] is False

    def test_get_vigem_button_map(self):
        result = self.controller.getVigemButtonMap()
        assert isinstance(result, dict)
        assert "ok" in result

    def test_set_vigem_button_map(self):
        mapping = {"a": "space", "b": "enter"}
        result = self.controller.setVigemButtonMap(mapping)
        assert isinstance(result, dict)
        assert "ok" in result

    def test_send_vigem_test_state(self):
        result = self.controller.sendVigemTestState(
            {
                "target_id": 0,
                "buttons": 0x1000,
                "lt": 0,
                "rt": 0,
                "lx": 0,
                "ly": 0,
                "rx": 0,
                "ry": 0,
            }
        )
        assert isinstance(result, dict)
        assert "ok" in result

    def test_get_background_methods(self):
        clicker = self.controller.getClickerBackgroundMethod()
        assert isinstance(clicker, dict)
        assert "ok" in clicker

        macro = self.controller.getMacroBackgroundMethod()
        assert isinstance(macro, dict)
        assert "ok" in macro

        recorder = self.controller.getRecorderBackgroundMethod()
        assert isinstance(recorder, dict)
        assert "ok" in recorder

        gamepad = self.controller.getGamepadBackgroundMethod()
        assert isinstance(gamepad, dict)
        assert "ok" in gamepad

    def test_get_windows(self):
        result = self.controller.getWindows()
        assert isinstance(result, dict)
        assert "ok" in result
        if result["ok"]:
            assert "windows" in result
            assert isinstance(result["windows"], list)

    def test_log_method(self):
        # Should not raise
        self.controller.log("INFO", "TEST", "test message")


class TestHotkeyController:
    """Tests for HotkeyController slots and signals."""

    def setup_method(self):
        from unittest.mock import Mock

        from app.backend.controllers.hotkey_controller import HotkeyController
        from app.backend.models.runtime_state import RuntimeState
        from app.backend.services.hotkey_service import HotkeyService

        self.state = RuntimeState()
        mock_api = Mock()
        mock_api.clicker = Mock()
        mock_api.clicker.is_running = False
        mock_api.aim = Mock()
        mock_api.aim.is_running = False
        mock_api.macro = Mock()
        mock_api.macro.is_running = False
        mock_api.recorder = Mock()
        mock_api.recorder.is_running = False
        self.hotkey_service = HotkeyService(mock_api)
        self.controller = HotkeyController(self.state, self.hotkey_service)

    def test_get_hotkeys(self):
        result = self.controller.getHotkeys()
        assert isinstance(result, dict)
        # The result is bindings dict directly
        assert "clicker_toggle" in result
        assert isinstance(result["clicker_toggle"], dict)
        assert "key" in result["clicker_toggle"]
        assert "mode" in result["clicker_toggle"]

    def test_set_hotkey(self):
        result = self.controller.setHotkey("clicker_toggle", "f6", "TOGGLE")
        assert isinstance(result, dict)
        assert "ok" in result

    def test_reset_hotkey(self):
        self.controller.setHotkey("clicker_toggle", "f6", "TOGGLE")
        result = self.controller.resetHotkey("clicker_toggle")
        assert isinstance(result, dict)
        assert "ok" in result

    def test_reset_all_hotkeys(self):
        result = self.controller.resetAllHotkeys()
        assert isinstance(result, dict)
        assert "ok" in result

    def test_validate_key(self):
        # Valid keys
        for key in ["f6", "ctrl+f7", "shift+ctrl+alt+f8"]:
            result = self.controller.validateKey(key)
            assert isinstance(result, dict)
            assert "ok" in result

        # Invalid keys
        for key in ["", "invalid_key"]:
            result = self.controller.validateKey(key)
            assert isinstance(result, dict)
            # Invalid keys return ok=False
            assert result["ok"] is False

    def test_hotkeys_debug_status(self):
        result = self.controller.hotkeysDebugStatus()
        assert isinstance(result, dict)
        # debug_status returns raw dict, not wrapped in ok
        assert "keyboard_lib" in result
        assert "mouse_lib" in result
        assert "pynput" in result

    def test_hotkeys_debug_thread(self):
        result = self.controller.hotkeysDebugThread()
        assert isinstance(result, dict)
        # debug_dispatcher_thread returns raw dict
        assert "dispatcher_connected" in result
        assert "handler_set" in result

    def test_log_method(self):
        # Should not raise
        self.controller.log("INFO", "TEST", "test message")


class TestProfileController:
    """Tests for ProfileController slots and signals."""

    def setup_method(self):
        from app.backend.controllers.profile_controller import ProfileController
        from app.backend.models.runtime_state import RuntimeState

        self.state = RuntimeState()
        self.controller = ProfileController(self.state)

    def test_get_palettes(self):
        result = self.controller.getPalettes()
        assert isinstance(result, dict)
        assert "matrix" in result

    def test_set_terminal_palette(self):
        # Valid palette
        result = self.controller.setTerminalPalette("matrix")
        assert isinstance(result, dict)
        assert "ok" in result

        # Invalid palette
        result = self.controller.setTerminalPalette("nonexistent")
        assert isinstance(result, dict)
        assert result["ok"] is False

    def test_set_ui_lang(self):
        for lang in ["RU", "EN"]:
            result = self.controller.setUiLang(lang)
            assert isinstance(result, dict)
            assert "ok" in result

        # Invalid lang
        result = self.controller.setUiLang("INVALID")
        assert isinstance(result, dict)
        assert result["ok"] is False

    def test_current_lang(self):
        result = self.controller.currentLang
        assert isinstance(result, str)
        assert result in ["RU", "EN"]

    def test_get_settings(self):
        result = self.controller.getSettings()
        assert isinstance(result, dict)
        assert "terminal_palette" in result
        assert "is_pinned" in result
        assert "ui_lang" in result

    def test_set_setting(self):
        result = self.controller.setSetting("terminal_palette", "matrix")
        assert isinstance(result, dict)
        assert "ok" in result

        # Unknown setting
        result = self.controller.setSetting("unknown_setting", "value")
        assert isinstance(result, dict)
        assert result["ok"] is False

    def test_profile_io(self):
        import os
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "test_profile.json")

            result = self.controller.saveProfile(path)
            assert isinstance(result, dict)
            assert "ok" in result

            if result["ok"]:
                result = self.controller.loadProfile(path)
                assert isinstance(result, dict)
                assert "ok" in result

    def test_export_import_profile_dialog(self):
        result = self.controller.exportProfileDialog()
        assert isinstance(result, dict)
        assert "ok" in result

        result = self.controller.importProfileDialog()
        assert isinstance(result, dict)
        assert "ok" in result

    def test_list_profiles(self):
        result = self.controller.listProfiles()
        assert isinstance(result, dict)
        assert "ok" in result

    def test_game_profiles(self):
        # Save
        result = self.controller.saveGameProfile("test_profile_123")
        assert isinstance(result, dict)
        assert "ok" in result

        if result["ok"]:
            # List
            result = self.controller.listGameProfiles()
            assert isinstance(result, dict)
            assert "ok" in result

            # Load
            result = self.controller.loadGameProfile("test_profile_123")
            assert isinstance(result, dict)
            assert "ok" in result

            # Delete
            result = self.controller.deleteGameProfile("test_profile_123")
            assert isinstance(result, dict)
            assert "ok" in result

    def test_background_methods(self):
        for method in ["sendinput", "postmessage", "vigem", "pico"]:
            result = self.controller.setClickerBackgroundMethod(method)
            assert isinstance(result, dict)
            assert "ok" in result

            result = self.controller.setMacroBackgroundMethod(method)
            assert isinstance(result, dict)
            assert "ok" in result

            result = self.controller.setRecorderBackgroundMethod(method)
            assert isinstance(result, dict)
            assert "ok" in result

            result = self.controller.setGamepadBackgroundMethod(method)
            assert isinstance(result, dict)
            assert "ok" in result

    def test_module_target_window(self):
        for module in ["clicker", "aim", "macro", "recorder", "gamepad"]:
            result = self.controller.setModuleTargetWindow(module, 0)
            assert isinstance(result, dict)
            assert "ok" in result

            result = self.controller.getModuleTargetWindow(module)
            assert isinstance(result, dict)
            assert "ok" in result

        # Invalid module
        result = self.controller.setModuleTargetWindow("invalid_module", 0)
        assert isinstance(result, dict)
        assert result["ok"] is False

    def test_performance_profile(self):
        result = self.controller.getPerformanceProfile()
        assert isinstance(result, dict)
        assert "ok" in result

    def test_detect_system_theme(self):
        result = self.controller.detectSystemTheme()
        assert isinstance(result, dict)
        assert "ok" in result

    def test_crash_report_methods(self):
        result = self.controller.setCrashReportSending(True)
        assert isinstance(result, dict)
        assert "ok" in result

        result = self.controller.listCrashReports()
        assert isinstance(result, dict)
        assert "ok" in result

        result = self.controller.clearAllCrashReports()
        assert isinstance(result, dict)
        assert "ok" in result

    def test_check_for_updates(self):
        result = self.controller.checkForUpdates()
        assert isinstance(result, dict)
        assert "ok" in result

    def test_get_monitors(self):
        result = self.controller.getMonitors()
        assert isinstance(result, dict)
        assert "ok" in result

    def test_get_diagnostics(self):
        result = self.controller.getDiagnostics()
        assert isinstance(result, dict)
        assert "ok" in result

    def test_log_method(self):
        # Should not raise
        self.controller.log("INFO", "TEST", "test message")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
