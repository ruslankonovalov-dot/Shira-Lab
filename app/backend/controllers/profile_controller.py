"""
ProfileController - handles profile loading, saving, settings, and palettes.
Extracted from QmlBridge god-object (Phase 2.1).
"""

from __future__ import annotations

import logging
import threading
from typing import Any

from PySide6.QtCore import Property, QObject, Signal, Slot

from app.backend.models.runtime_state import TERMINAL_PALETTES, RuntimeState
from app.backend.profile_manager import ProfileManager
from app.backend.services.input_validation import (
    VALID_BACKGROUND_METHODS,
    VALID_PALETTES,
    _qvar,
    _qvar_map,
    make_error_response,
    make_ok_response,
    validate_bool,
    validate_enum,
    validate_hwnd,
    validate_str,
)

logger = logging.getLogger(__name__)


class ProfileController(QObject):
    """
    Profile and settings controller.

    Responsibilities:
    - Profile load/save/list/delete
    - Settings management (palette, language, etc.)
    - Terminal palettes (single source of truth)
    - Profile import/export dialogs
    - Game profiles (named presets)
    """

    # Signals
    settingsChanged = Signal()
    langChanged = Signal()
    logMessage = Signal(str, str, str)  # level, source, message

    def __init__(
        self,
        state: RuntimeState,
        bridge: Any | None = None,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._state: RuntimeState = state
        self._bridge = bridge
        self._profile_manager: ProfileManager = ProfileManager()
        self._save_timer: threading.Timer | None = None

    @property
    def state(self) -> RuntimeState:
        return self._state

    # ─── Palettes (Single Source of Truth) ────────────────────────────────

    @Slot(result="QVariantMap")
    def getPalettes(self) -> dict[str, Any]:
        """Return TERMINAL_PALETTES as native QVariantMap."""
        return TERMINAL_PALETTES

    @Slot(str, result="QVariantMap")
    def setTerminalPalette(self, palette_id: str) -> dict[str, Any]:
        """Set terminal palette."""
        ok, val, err = validate_enum(palette_id, VALID_PALETTES, name="palette_id")
        if not ok or val is None:
            logger.warning(f"setTerminalPalette: {err}")
            return _qvar_map(make_error_response(err or "Invalid palette"))
        self._state.terminal_palette = val
        self._schedule_save()
        self.settingsChanged.emit()
        return _qvar_map(make_ok_response())

    @Property(str, notify=langChanged)
    def currentLang(self) -> str:
        """Get current UI language."""
        return self._state.ui_lang

    @Slot(str, result="QVariantMap")
    def setUiLang(self, code: str) -> dict[str, Any]:
        """Set UI language and emit signals for QML re-evaluation."""
        code = code.upper()
        if code in ("RU", "EN"):
            self._state.ui_lang = code
            self._schedule_save()
            self.settingsChanged.emit()
            self.langChanged.emit()
            return _qvar_map(make_ok_response())
        return _qvar_map(make_error_response("Invalid language code"))

    # ─── Settings ──────────────────────────────────────────────────────────

    @Slot(result="QVariantMap")
    def getSettings(self) -> dict[str, Any]:
        """Get all settings as native QVariantMap."""
        from config import LANGUAGES, LOGO_SHIRA

        lang = dict(LANGUAGES.get(self._state.ui_lang, LANGUAGES["RU"]))
        return {
            "terminal_palette": self._state.terminal_palette,
            "is_pinned": self._state.is_pinned,
            "ui_lang": self._state.ui_lang,
            "lang": lang,
            "logo_shira": LOGO_SHIRA,
            "palettes": TERMINAL_PALETTES,
            "hotkeys": self._state.hotkeys,
        }

    @Slot(str, "QVariant", result="QVariantMap")
    def setSetting(self, key: str, value: Any) -> dict[str, Any] | None:
        """Set arbitrary setting on runtime state."""
        if not hasattr(self._state, key):
            logger.warning(f"Unknown setting: {key}")
            return _qvar(make_error_response(f"Unknown setting: {key}"))  # type: ignore[return-value]
        setattr(self._state, key, value)
        self._schedule_save()
        self.settingsChanged.emit()
        return _qvar(make_ok_response())  # type: ignore[return-value]

    # ─── Profile I/O ──────────────────────────────────────────────────────

    @Slot(result="QVariantMap")
    def exportProfileDialog(self) -> dict[str, Any]:
        """Open file dialog and export profile."""
        try:
            from app.backend.profile_io import export_profile_dialog

            return _qvar_map(export_profile_dialog(self._state))
        except Exception as e:
            logger.exception("exportProfileDialog failed")
            return _qvar_map(make_error_response(str(e)))

    @Slot(result="QVariantMap")
    def importProfileDialog(self) -> dict[str, Any]:
        """Open file dialog and import profile."""
        try:
            from app.backend.profile_io import import_profile_dialog

            return _qvar_map(import_profile_dialog(self._state))
        except Exception as e:
            logger.exception("importProfileDialog failed")
            return _qvar_map(make_error_response(str(e)))

    @Slot(str, result="QVariantMap")
    def saveProfile(self, name: str = "") -> dict[str, Any]:
        """Save current profile to disk."""
        ok, name_val, err = validate_str(name, max_len=255, default="", name="name")
        if not ok or name_val is None:
            logger.warning(f"saveProfile: {err}")
            return _qvar_map(make_error_response(err or "Invalid name"))
        try:
            from app.backend.profile_io import save_profile_to_file

            return _qvar_map(save_profile_to_file(self._state, name_val))
        except Exception as e:
            logger.exception("saveProfile failed")
            return _qvar_map(make_error_response(str(e)))

    @Slot(str, result="QVariantMap")
    def loadProfile(self, filename: str) -> dict[str, Any]:
        """Load profile from file."""
        ok, filename_val, err = validate_str(filename, min_len=1, max_len=512, name="filename")
        if not ok or filename_val is None:
            logger.warning(f"loadProfile: {err}")
            return _qvar_map(make_error_response(err or "Invalid filename"))
        try:
            from app.backend.profile_io import load_profile_from_file

            result = load_profile_from_file(filename_val, self._state)
            if result.get("ok"):
                self.settingsChanged.emit()
            return _qvar_map(result)
        except Exception as e:
            logger.exception("loadProfile failed")
            return _qvar_map(make_error_response(str(e)))

    @Slot(str, result="QVariantMap")
    def deleteProfile(self, filename: str) -> dict[str, Any]:
        """Delete a profile file."""
        ok, filename_val, err = validate_str(filename, min_len=1, max_len=512, name="filename")
        if not ok or filename_val is None:
            logger.warning(f"deleteProfile: {err}")
            return _qvar_map(make_error_response(err or "Invalid filename"))
        try:
            from app.backend.profile_io import delete_profile_file

            return _qvar_map(delete_profile_file(filename_val))
        except Exception as e:
            logger.exception("deleteProfile failed")
            return _qvar_map(make_error_response(str(e)))

    @Slot(result="QVariantMap")
    def listProfiles(self) -> dict[str, Any]:
        """List available profile files."""
        try:
            from app.backend.profile_io import list_profile_files

            return _qvar_map(list_profile_files())
        except Exception as e:
            logger.exception("listProfiles failed")
            return _qvar_map(make_error_response(str(e)))

    # ─── Game Profiles (Named Presets) ────────────────────────────────────

    @Slot(str, result="QVariantMap")
    def saveGameProfile(self, name: str) -> dict[str, Any]:
        """Save current settings as named game profile."""
        from app.backend.services.input_validation import validate_str

        ok, name_val, err = validate_str(name, min_len=1, max_len=100, name="name")
        if not ok or name_val is None:
            logger.warning(f"saveGameProfile: {err}")
            return _qvar_map(make_error_response(err or "Invalid name"))
        try:
            return _qvar_map(self._profile_manager.save_profile(name_val))
        except Exception as e:
            logger.exception("saveGameProfile failed")
            return _qvar_map(make_error_response(str(e)))

    @Slot(str, result="QVariantMap")
    def loadGameProfile(self, name: str) -> dict[str, Any]:
        """Load a named game profile."""
        from app.backend.services.input_validation import validate_str

        ok, name_val, err = validate_str(name, min_len=1, max_len=100, name="name")
        if not ok or name_val is None:
            logger.warning(f"loadGameProfile: {err}")
            return _qvar_map(make_error_response(err or "Invalid name"))
        try:
            result = self._profile_manager.load_profile(name_val)
            if result.get("ok"):
                self.settingsChanged.emit()
            return _qvar_map(result)
        except Exception as e:
            logger.exception("loadGameProfile failed")
            return _qvar_map(make_error_response(str(e)))

    @Slot(str, result="QVariantMap")
    def deleteGameProfile(self, name: str) -> dict[str, Any]:
        """Delete a named game profile."""
        from app.backend.services.input_validation import validate_str

        ok, name_val, err = validate_str(name, min_len=1, max_len=100, name="name")
        if not ok or name_val is None:
            logger.warning(f"deleteGameProfile: {err}")
            return _qvar_map(make_error_response(err or "Invalid name"))
        try:
            return _qvar_map(self._profile_manager.delete_profile(name_val))
        except Exception as e:
            logger.exception("deleteGameProfile failed")
            return _qvar_map(make_error_response(str(e)))

    @Slot(result="QVariantMap")
    def listGameProfiles(self) -> dict[str, Any]:
        """List all named game profiles."""
        try:
            return _qvar_map(self._profile_manager.list_profiles())
        except Exception as e:
            logger.exception("listGameProfiles failed")
            return _qvar_map(make_error_response(str(e)))

    # ─── Background Methods (per module) ──────────────────────────────────

    @Slot(str, result="QVariantMap")
    def setClickerBackgroundMethod(self, method: str) -> dict[str, Any] | None:
        """Set clicker background method."""
        from app.backend.services.input_validation import validate_enum

        ok, val, err = validate_enum(method, VALID_BACKGROUND_METHODS, name="background_method")
        if not ok or val is None:
            logger.warning(f"setClickerBackgroundMethod: {err}")
            return _qvar(make_error_response(err or "Invalid method"))  # type: ignore[return-value]
        self._state.clicker_background_method = val
        self._schedule_save()
        self.settingsChanged.emit()
        return _qvar_map(make_ok_response())

    @Slot(str, result="QVariantMap")
    def setMacroBackgroundMethod(self, method: str) -> dict[str, Any]:
        """Set macro background method."""
        ok, val, err = validate_enum(method, VALID_BACKGROUND_METHODS, name="background_method")
        if not ok or val is None:
            logger.warning(f"setMacroBackgroundMethod: {err}")
            return _qvar_map(make_error_response(err or "Invalid method"))
        self._state.macro_background_method = val
        self._schedule_save()
        self.settingsChanged.emit()
        return _qvar_map(make_ok_response())

    @Slot(str, result="QVariantMap")
    def setRecorderBackgroundMethod(self, method: str) -> dict[str, Any]:
        """Set recorder background method."""
        ok, val, err = validate_enum(method, VALID_BACKGROUND_METHODS, name="background_method")
        if not ok or val is None:
            logger.warning(f"setRecorderBackgroundMethod: {err}")
            return _qvar_map(make_error_response(err or "Invalid method"))
        self._state.recorder_background_method = val
        self._schedule_save()
        self.settingsChanged.emit()
        return _qvar_map(make_ok_response())

    @Slot(str, result="QVariantMap")
    def setGamepadBackgroundMethod(self, method: str) -> dict[str, Any]:
        """Set gamepad background method."""
        ok, val, err = validate_enum(method, VALID_BACKGROUND_METHODS, name="background_method")
        if not ok or val is None:
            logger.warning(f"setGamepadBackgroundMethod: {err}")
            return _qvar_map(make_error_response(err or "Invalid method"))
        self._state.gamepad_background_method = val
        self._schedule_save()
        self.settingsChanged.emit()
        return _qvar_map(make_ok_response())

    # ─── Module Target Windows ────────────────────────────────────────────
    VALID_TARGET_MODULES = ("clicker", "aim", "macro", "recorder", "gamepad")

    @Slot(str, int, result="QVariantMap")
    def setModuleTargetWindow(self, module: str, hwnd: int) -> dict[str, Any]:
        """Set target window for a module."""
        try:
            ok, module_val, err = validate_str(module, min_len=1, max_len=50, name="module")
            if not ok or module_val is None:
                logger.warning(f"setModuleTargetWindow: {err}")
                return _qvar_map(make_error_response(err or "Invalid module"))
            # Validate module is supported
            if module_val not in self.VALID_TARGET_MODULES:
                logger.warning(f"setModuleTargetWindow: Unsupported module: {module_val}")
                return _qvar_map(make_error_response(f"Unsupported module: {module_val}"))
            ok, val, err = validate_hwnd(hwnd)
            if not ok or val is None:
                logger.warning(f"setModuleTargetWindow: {err}")
                return _qvar_map(make_error_response(err or "Invalid hwnd"))
            self._state.set_module_target(module_val, val)
            self._schedule_save()
            self.settingsChanged.emit()
            return _qvar_map(make_ok_response())
        except Exception as e:
            logger.exception("setModuleTargetWindow failed")
            return _qvar_map(make_error_response(str(e)))

    @Slot(str, result="QVariantMap")
    def getModuleTargetWindow(self, module: str) -> dict[str, Any]:
        """Get target window for a module."""
        ok, module_val, err = validate_str(module, min_len=1, max_len=50, name="module")
        if not ok or module_val is None:
            logger.warning(f"getModuleTargetWindow: {err}")
            return _qvar_map(make_error_response(err or "Invalid module"))
        try:
            result = self._state.get_module_target(module_val)
            return _qvar_map(make_ok_response(data=result))
        except Exception as e:
            logger.exception("getModuleTargetWindow failed")
            return _qvar_map(make_error_response(str(e)))

    # ─── Performance Profile ──────────────────────────────────────────────

    @Slot(result="QVariantMap")
    def getPerformanceProfile(self) -> dict[str, Any]:
        """Get current performance profile."""
        import os
        import time

        import psutil

        try:
            process = psutil.Process(os.getpid())
            cpu = process.cpu_percent(interval=0.1)
            mem = process.memory_info().rss / (1024 * 1024)
            threads = process.num_threads()
            uptime = time.time() - process.create_time()

            return {
                "ok": True,
                "cpu_percent": cpu,
                "memory_mb": mem,
                "threads": threads,
                "uptime_sec": int(uptime),
            }
        except Exception as e:
            logger.exception("getPerformanceProfile failed")
            return {"ok": False, "error": str(e)}

    # ─── System Theme Detection ──────────────────────────────────────────

    @Slot(result="QVariantMap")
    def detectSystemTheme(self) -> dict[str, Any]:
        """Detect system theme (dark/light)."""
        try:
            from app.backend.services.theme_detector import detect_windows_theme

            theme = detect_windows_theme()
            return {"ok": True, "theme": theme}
        except Exception as e:
            logger.exception("detectSystemTheme failed")
            return _qvar_map(make_error_response(str(e)))

    # ─── Crash Reporter ──────────────────────────────────────────────────

    @Slot(bool, result="QVariantMap")
    def setCrashReportSending(self, enabled: bool) -> dict[str, Any] | None:
        """Enable/disable automatic crash report sending."""

        ok, enabled_val, err = validate_bool(enabled, name="enabled")
        if not ok or enabled_val is None:
            logger.warning(f"setCrashReportSending: {err}")
            return _qvar_map(make_error_response(err or "Invalid value"))
        try:
            # The crash reporter module doesn't have a set_crash_report_sending function
            # This is handled at startup via install_crash_handler
            self.logMessage.emit(
                "INFO",
                "SYSTEM",
                f"Crash report sending: {'enabled' if enabled_val else 'disabled'}",
            )
            return _qvar_map(make_ok_response())
        except (OSError, ImportError, RuntimeError) as e:
            logger.error(f"setCrashReportSending failed: {e}")
            return _qvar_map(make_error_response(str(e)))

    @Slot(result="QVariantMap")
    def listCrashReports(self) -> dict[str, Any]:
        """List all crash reports."""
        try:
            from app.backend.services.crash_reporter import list_local_crashes as list_reports

            return _qvar_map({"ok": True, "crashes": list_reports()})
        except (OSError, ImportError, RuntimeError) as e:
            logger.exception("listCrashReports failed")
            return _qvar_map(make_error_response(str(e)))

    @Slot(result="QVariantMap")
    def clearAllCrashReports(self) -> dict[str, Any]:
        """Clear all crash reports."""
        try:
            from app.backend.services.crash_reporter import clear_all_crashes as clear_reports

            count = clear_reports()
            return _qvar_map({"ok": True, "cleared": count})
        except (OSError, ImportError, RuntimeError) as e:
            logger.exception("clearAllCrashReports failed")
            return _qvar_map(make_error_response(str(e)))

    @Slot(result="QVariantMap")
    def checkForUpdates(self) -> dict[str, Any]:
        """Check for updates."""
        try:
            from app.backend.services.update_checker import check_for_updates

            return check_for_updates("0.17.0")
        except (OSError, ImportError, RuntimeError) as e:
            logger.exception("checkForUpdates failed")
            return _qvar_map(make_error_response(str(e)))

    # ─── Monitor Info ────────────────────────────────────────────────────

    @Slot(result="QVariantMap")
    def getMonitors(self) -> dict[str, Any]:
        """Get list of monitors."""
        try:
            from window_utils import get_monitors

            return {"ok": True, "monitors": get_monitors()}
        except Exception as e:
            logger.exception("getMonitors failed")
            return {"ok": False, "error": str(e), "monitors": []}

    # ─── Diagnostics ──────────────────────────────────────────────────────

    @Slot(result="QVariantMap")
    def getDiagnostics(self) -> dict[str, Any]:
        """Get full diagnostics info."""
        import platform
        import sys

        try:
            info = {
                "ok": True,
                "app_version": (
                    self._state.app_version if hasattr(self._state, "app_version") else "1.0.0"
                ),
                "python_version": sys.version,
                "platform": platform.platform(),
                "processor": platform.processor(),
                "state": {
                    "ui_lang": self._state.ui_lang,
                    "terminal_palette": self._state.terminal_palette,
                    "is_pinned": self._state.is_pinned,
                    "clicker_bg_method": getattr(
                        self._state, "clicker_background_method", "sendinput"
                    ),
                    "macro_bg_method": getattr(self._state, "macro_background_method", "sendinput"),
                    "recorder_bg_method": getattr(
                        self._state, "recorder_background_method", "sendinput"
                    ),
                    "gamepad_bg_method": getattr(
                        self._state, "gamepad_background_method", "sendinput"
                    ),
                },
                "profile_dir": (
                    str(self._profile_manager.get_profile_dir())
                    if hasattr(self._profile_manager, "get_profile_dir")
                    else ""
                ),
            }
            return info
        except Exception as e:
            logger.exception("getDiagnostics failed")
            return {"ok": False, "error": str(e)}

    # ─── Helpers ──────────────────────────────────────────────────────────

    def _schedule_save(self) -> None:
        """Debounced profile save."""
        if getattr(self, "_suppress_save", False):
            return
        if hasattr(self, "_save_timer") and self._save_timer:
            self._save_timer.cancel()
        import threading

        self._save_timer = threading.Timer(0.4, self._flush_save)
        self._save_timer.daemon = True
        self._save_timer.start()

    def _flush_save(self) -> None:
        """Flush profile to disk — delegate to bridge if available, else save state only."""
        try:
            # Try to use bridge's save (which has all services: clicker, aim, macro, etc.)
            if hasattr(self, "_bridge") and self._bridge:
                self._bridge._flush_save()
            else:
                # Fallback: save just the state (no service data)
                import json

                from app.backend.persistence import _state_to_dict

                payload = {
                    "version": 5,
                    "state": _state_to_dict(self._state),
                }
                from app.backend.persistence import PROFILE_PATH

                PROFILE_PATH.write_text(
                    json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8"
                )
        except Exception:
            import logging

            logging.getLogger(__name__).exception("Failed to save profile from ProfileController")

    # ─── Logging Bridge ──────────────────────────────────────────────────

    def log(self, level: str, source: str, message: str) -> None:
        """Log message to console via signal."""
        self.logMessage.emit(level, source, message)
