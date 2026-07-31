"""app/backend/profile_io.py -- Export/Import profile to JSON.

Allows user to save all settings to a file and load back.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict

logger = logging.getLogger(__name__)

PROFILE_FORMAT_VERSION = "1.0"


def export_profile(bridge: Any, path: str | Path) -> Dict[str, Any]:
    """Export all settings + service states to JSON file.

    Includes:
        - terminal_palette, transparency, blur settings
        - ui_lang, bg_image_path, bg_fit_mode
        - hotkeys
        - clicker config
        - macro actions
        - aim config
        - target window

    Does NOT export:
        - recorder records (separate ZIP via recorderExportAll)
        - secrets/tokens (if added later)
    """
    try:
        # Get app_version safely (avoid MagicMock auto-attr issue)
        app_version = getattr(bridge, "_app_version", None)
        if not isinstance(app_version, str):
            app_version = "0.17.0"

        data: Dict[str, Any] = {
            "version": PROFILE_FORMAT_VERSION,
            "app_version": app_version,
            "settings": {
                "terminal_palette": bridge.state.terminal_palette,
                "global_transparency": bridge.state.global_transparency,
                "interface_transparency": bridge.state.interface_transparency,
                "global_blur_enabled": bridge.state.global_blur_enabled,
                "interface_blur_enabled": bridge.state.interface_blur_enabled,
                "is_pinned": bridge.state.is_pinned,
                "ui_lang": bridge.state.ui_lang,
                "bg_image_path": bridge.state.bg_image_path,
                "bg_fit_mode": bridge.state.bg_fit_mode,
            },
            "hotkeys": bridge.state.hotkeys,
            "clicker": _safe_get(bridge.clicker, "get_status"),
            "macro": _safe_get(bridge.macro, "get_status"),
            "aim": _safe_get(bridge.aim, "get_status"),
            "target": {
                "hwnd": bridge.state.target_hwnd,
                "name": bridge.state.target_name,
            },
        }

        path = Path(path)
        path.write_text(
            json.dumps(data, indent=2, ensure_ascii=False, default=str),
            encoding="utf-8"
        )

        logger.info("Profile exported to %s", path)
        return {"ok": True, "path": str(path), "size_bytes": path.stat().st_size}
    except Exception as e:
        logger.exception("Failed to export profile")
        return {"ok": False, "error": str(e)}


def import_profile(bridge: Any, path: str | Path) -> Dict[str, Any]:
    """Import settings from JSON file, applying them to bridge.

    WARNING: Overwrites current settings!
    """
    try:
        path = Path(path)
        if not path.exists():
            return {"ok": False, "error": f"File not found: {path}"}

        data = json.loads(path.read_text(encoding="utf-8"))

        # Version check
        if data.get("version") != PROFILE_FORMAT_VERSION:
            logger.warning(
                "Profile version mismatch: expected %s, got %s",
                PROFILE_FORMAT_VERSION, data.get("version")
            )
            # Continue but migration may be needed

        # Apply settings
        settings = data.get("settings", {})
        if "terminal_palette" in settings:
            bridge.state.terminal_palette = settings["terminal_palette"]
        if "global_transparency" in settings:
            bridge.state.global_transparency = settings["global_transparency"]
        if "interface_transparency" in settings:
            bridge.state.interface_transparency = settings["interface_transparency"]
        if "global_blur_enabled" in settings:
            bridge.state.global_blur_enabled = settings["global_blur_enabled"]
        if "interface_blur_enabled" in settings:
            bridge.state.interface_blur_enabled = settings["interface_blur_enabled"]
        if "is_pinned" in settings:
            bridge.state.is_pinned = settings["is_pinned"]
        if "ui_lang" in settings:
            bridge.state.ui_lang = settings["ui_lang"]
        if "bg_image_path" in settings:
            bridge.state.bg_image_path = settings["bg_image_path"]
        if "bg_fit_mode" in settings:
            bridge.state.bg_fit_mode = settings["bg_fit_mode"]

        # Apply hotkeys
        if "hotkeys" in data:
            bridge.state.hotkeys = data["hotkeys"]
            try:
                bridge.hotkeys.set_bindings(data["hotkeys"])
            except Exception:
                logger.exception("Failed to apply hotkeys from imported profile")

        # Apply clicker config
        clicker = data.get("clicker", {})
        if clicker:
            try:
                bridge.clicker.update_config(
                    clicker.get("interval_ms", 100),
                    clicker.get("hold_ms", 30),
                    clicker.get("button", "left"),
                    clicker.get("limit", 0),
                    clicker.get("background_method", "sendinput"),
                )
            except Exception:
                logger.exception("Failed to apply clicker config")

        # Apply target
        target = data.get("target", {})
        if target.get("hwnd"):
            bridge.state.target_hwnd = target["hwnd"]
        if target.get("name"):
            bridge.state.target_name = target["name"]

        # Save
        bridge._schedule_save()
        if hasattr(bridge, "_apply_transparency"):
            bridge._apply_transparency()
        if hasattr(bridge, "settingsChanged"):
            bridge.settingsChanged.emit()

        logger.info("Profile imported from %s", path)
        return {"ok": True, "applied": True}
    except Exception as e:
        logger.exception("Failed to import profile")
        return {"ok": False, "error": str(e)}


def _safe_get(obj: Any, method_name: str) -> Dict[str, Any]:
    """Safely call obj.method() and return result or empty dict."""
    try:
        method = getattr(obj, method_name)
        result = method()
        if isinstance(result, dict):
            return result
        return {}
    except Exception:
        return {}


def export_profile_dialog(state: Any) -> Dict[str, Any]:
    """Open file dialog and export profile. Returns result dict."""
    try:
        from PySide6.QtWidgets import QApplication, QFileDialog
        app = QApplication.instance()
        if app is None:
            return {"ok": False, "error": "QApplication not available"}
        path, _ = QFileDialog.getSaveFileName(None, "Export Profile", "", "JSON Files (*.json)")
        if not path:
            return {"ok": False, "error": "Cancelled"}
        return export_profile(state, path)
    except Exception as e:
        logger.exception("export_profile_dialog failed")
        return {"ok": False, "error": str(e)}


def import_profile_dialog(state: Any) -> Dict[str, Any]:
    """Open file dialog and import profile. Returns result dict."""
    try:
        from PySide6.QtWidgets import QApplication, QFileDialog
        app = QApplication.instance()
        if app is None:
            return {"ok": False, "error": "QApplication not available"}
        path, _ = QFileDialog.getOpenFileName(None, "Import Profile", "", "JSON Files (*.json)")
        if not path:
            return {"ok": False, "error": "Cancelled"}
        return import_profile(state, path)
    except Exception as e:
        logger.exception("import_profile_dialog failed")
        return {"ok": False, "error": str(e)}


def save_profile_to_file(state: Any, name: str) -> Dict[str, Any]:
    """Save current state as named profile file."""
    try:
        from pathlib import Path
        profile_dir = Path(__file__).resolve().parent.parent.parent / "data" / "profiles"
        profile_dir.mkdir(parents=True, exist_ok=True)
        path = profile_dir / f"{name}.json"
        return export_profile(state, path)
    except Exception as e:
        logger.exception("save_profile_to_file failed")
        return {"ok": False, "error": str(e)}


def load_profile_from_file(filename: str, state: Any) -> Dict[str, Any]:
    """Load profile from file and apply to state."""
    try:
        from pathlib import Path
        profile_dir = Path(__file__).resolve().parent.parent.parent / "data" / "profiles"
        path = profile_dir / filename
        return import_profile(state, path)
    except Exception as e:
        logger.exception("load_profile_from_file failed")
        return {"ok": False, "error": str(e)}


def delete_profile_file(filename: str) -> Dict[str, Any]:
    """Delete a profile file."""
    try:
        from pathlib import Path
        profile_dir = Path(__file__).resolve().parent.parent.parent / "data" / "profiles"
        path = profile_dir / filename
        if path.exists():
            path.unlink()
        return {"ok": True}
    except Exception as e:
        logger.exception("delete_profile_file failed")
        return {"ok": False, "error": str(e)}


def list_profile_files() -> Dict[str, Any]:
    """List available profile files."""
    try:
        from pathlib import Path
        profile_dir = Path(__file__).resolve().parent.parent.parent / "data" / "profiles"
        if not profile_dir.exists():
            return {"ok": True, "profiles": []}
        files = [f.name for f in profile_dir.glob("*.json")]
        files.sort()
        return {"ok": True, "profiles": files}
    except Exception as e:
        logger.exception("list_profile_files failed")
        return {"ok": False, "error": str(e)}
