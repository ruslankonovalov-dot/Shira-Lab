"""Unit tests for app.backend.profile_io module."""
import pytest
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

from app.backend.profile_io import (
    export_profile, import_profile, _safe_get, PROFILE_FORMAT_VERSION,
)

pytestmark = pytest.mark.unit


@pytest.fixture
def mock_bridge():
    """Mock bridge with all needed attributes for export/import."""
    bridge = MagicMock()
    # Use plain attributes (not MagicMock) for primitive values
    bridge.state = MagicMock()
    bridge.state.terminal_palette = "matrix"
    bridge.state.global_transparency = 0.3
    bridge.state.interface_transparency = 0.2
    bridge.state.global_blur_enabled = True
    bridge.state.interface_blur_enabled = False
    bridge.state.is_pinned = False
    bridge.state.ui_lang = "RU"
    bridge.state.bg_image_path = None
    bridge.state.bg_fit_mode = "COVER"
    bridge.state.target_hwnd = None
    bridge.state.target_name = "GLOBAL_SCREEN"
    bridge.state.hotkeys = {
        "clicker_toggle": {"key": "f6", "mode": "TOGGLE"}
    }

    # Make get_status return real dict (MagicMock returns MagicMock by default)
    bridge.clicker = MagicMock()
    bridge.clicker.get_status = MagicMock(return_value={
        "interval_ms": 100, "hold_ms": 30, "button": "left",
        "limit": 0, "background_method": "sendinput",
    })
    bridge.macro = MagicMock()
    bridge.macro.get_status = MagicMock(return_value={"actions": []})
    bridge.aim = MagicMock()
    bridge.aim.get_status = MagicMock(return_value={"confidence": 0.7})

    bridge._schedule_save = MagicMock()
    bridge._apply_transparency = MagicMock()
    bridge.settingsChanged = MagicMock()
    bridge.settingsChanged.emit = MagicMock()
    bridge.hotkeys = MagicMock()
    bridge.hotkeys.set_bindings = MagicMock()

    return bridge


class TestExportProfile:

    def test_export_creates_json_file(self, mock_bridge, tmp_path):
        out = tmp_path / "profile.json"
        result = export_profile(mock_bridge, out)

        assert result["ok"] is True
        assert out.exists()

        data = json.loads(out.read_text(encoding="utf-8"))
        assert data["version"] == PROFILE_FORMAT_VERSION
        assert data["settings"]["terminal_palette"] == "matrix"
        assert data["hotkeys"]["clicker_toggle"]["key"] == "f6"

    def test_export_includes_service_states(self, mock_bridge, tmp_path):
        out = tmp_path / "profile.json"
        export_profile(mock_bridge, out)

        data = json.loads(out.read_text(encoding="utf-8"))
        assert "clicker" in data
        assert data["clicker"]["interval_ms"] == 100
        assert "macro" in data
        assert "aim" in data

    def test_export_returns_size_bytes(self, mock_bridge, tmp_path):
        out = tmp_path / "profile.json"
        result = export_profile(mock_bridge, out)
        assert result["size_bytes"] > 0

    def test_export_handles_path_string(self, mock_bridge, tmp_path):
        out = str(tmp_path / "profile.json")
        result = export_profile(mock_bridge, out)
        assert result["ok"] is True


class TestImportProfile:

    def test_import_applies_settings(self, mock_bridge, tmp_path):
        # First export
        out = tmp_path / "profile.json"
        export_profile(mock_bridge, out)

        # Modify state
        mock_bridge.state.terminal_palette = "cyberpunk"
        mock_bridge.state.ui_lang = "EN"

        # Import back
        result = import_profile(mock_bridge, out)
        assert result["ok"] is True

        # Settings should be restored
        assert mock_bridge.state.terminal_palette == "matrix"
        assert mock_bridge.state.ui_lang == "RU"

    def test_import_nonexistent_file_returns_error(self, mock_bridge, tmp_path):
        result = import_profile(mock_bridge, tmp_path / "nonexistent.json")
        assert result["ok"] is False
        assert "error" in result

    def test_import_invalid_json_returns_error(self, mock_bridge, tmp_path):
        out = tmp_path / "bad.json"
        out.write_text("{ invalid json }", encoding="utf-8")

        result = import_profile(mock_bridge, out)
        assert result["ok"] is False

    def test_import_triggers_save(self, mock_bridge, tmp_path):
        out = tmp_path / "profile.json"
        export_profile(mock_bridge, out)

        import_profile(mock_bridge, out)
        mock_bridge._schedule_save.assert_called_once()

    def test_import_applies_hotkeys(self, mock_bridge, tmp_path):
        out = tmp_path / "profile.json"
        export_profile(mock_bridge, out)

        # Reset mock
        mock_bridge.hotkeys.set_bindings.reset_mock()

        import_profile(mock_bridge, out)
        mock_bridge.hotkeys.set_bindings.assert_called_once()


class TestSafeGet:

    def test_returns_method_result(self):
        obj = MagicMock()
        obj.get_status.return_value = {"running": True}
        result = _safe_get(obj, "get_status")
        assert result == {"running": True}

    def test_returns_empty_on_exception(self):
        obj = MagicMock()
        obj.get_status.side_effect = RuntimeError("fail")
        result = _safe_get(obj, "get_status")
        assert result == {}

    def test_returns_empty_on_missing_method(self):
        obj = MagicMock()
        # MagicMock returns another MagicMock for any attr — let's use a real object
        class Empty:
            pass
        result = _safe_get(Empty(), "nonexistent")
        assert result == {}
