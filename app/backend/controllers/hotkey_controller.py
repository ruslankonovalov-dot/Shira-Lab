"""
HotkeyController - handles hotkey bindings, validation, and debug.
Extracted from QmlBridge god-object (Phase 2.1).
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, cast

from PySide6.QtCore import QObject, Signal, Slot

from app.backend.services.hotkey_service import HotkeyService
from app.backend.services.input_validation import (
    VALID_HOTKEY_ACTIONS,
    VALID_HOTKEY_MODES,
    QVariantMap,
    _qvar_map,
    make_error_response,
    validate_enum,
)

if TYPE_CHECKING:
    from app.backend.models.runtime_state import RuntimeState

logger = logging.getLogger(__name__)


class HotkeyController(QObject):
    """
    Hotkey management controller.

    Responsibilities:
    - Hotkey registration/unregistration
    - Hotkey validation
    - Hotkey debug status
    - Bindings management
    """

    # Signals
    hotkeysChanged = Signal()
    logMessage = Signal(str, str, str)  # level, source, message

    def __init__(
        self,
        state: RuntimeState,
        hotkeys_service: HotkeyService,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._state: RuntimeState = state
        self._hotkeys: HotkeyService = hotkeys_service

    @property
    def hotkeys(self) -> HotkeyService:
        """Access to underlying hotkey service."""
        return self._hotkeys

    @Slot(result="QVariantMap")
    def getHotkeys(self) -> QVariantMap:
        """Get all current hotkey bindings."""
        try:
            return _qvar_map(cast(QVariantMap, self._hotkeys.get_bindings()))
        except Exception as e:
            logger.exception("getHotkeys failed")
            return _qvar_map({"ok": False, "error": str(e), "bindings": {}})

    @Slot(str, str, str, result="QVariantMap")
    def setHotkey(self, action: str, key: str, mode: str) -> QVariantMap:
        """Set a hotkey binding."""
        ok, val_action, err = validate_enum(action, VALID_HOTKEY_ACTIONS, name="action")
        if not ok or val_action is None:
            return _qvar_map(make_error_response(err or "Invalid action"))

        # Use HotkeyService's own validate_key method
        validation_result = self._hotkeys.validate_key(key)
        if not validation_result.get("ok", False):
            error_val = validation_result.get("error")
            return _qvar_map(
                make_error_response(str(error_val) if error_val else "Invalid key")
            )

        ok, val_mode, err = validate_enum(mode, VALID_HOTKEY_MODES, name="mode")
        if not ok or val_mode is None:
            return _qvar_map(make_error_response(err or "Invalid mode"))

        try:
            result = self._hotkeys.set_binding(val_action, key, val_mode)
            self.hotkeysChanged.emit()
            return _qvar_map(result)
        except Exception as e:
            logger.exception("setHotkey failed")
            return _qvar_map(make_error_response(str(e)))

    @Slot(str, result="QVariantMap")
    def resetHotkey(self, action: str) -> QVariantMap:
        """Reset a hotkey to default."""
        ok, val_action, err = validate_enum(action, VALID_HOTKEY_ACTIONS, name="action")
        if not ok or val_action is None:
            return _qvar_map(make_error_response(err or "Invalid action"))

        try:
            result = self._hotkeys.reset_binding(val_action)
            self.hotkeysChanged.emit()
            return _qvar_map(result)
        except Exception as e:
            logger.exception("resetHotkey failed")
            return _qvar_map(make_error_response(str(e)))

    @Slot(result="QVariantMap")
    def resetAllHotkeys(self) -> QVariantMap:
        """Reset all hotkeys to defaults."""
        try:
            result = self._hotkeys.reset_all()
            self.hotkeysChanged.emit()
            return _qvar_map(result)
        except Exception as e:
            logger.exception("resetAllHotkeys failed")
            return _qvar_map(make_error_response(str(e)))

    @Slot(str, result="QVariantMap")
    def validateKey(self, key: str) -> QVariantMap:
        """Validate a key string."""
        try:
            validation_result = self._hotkeys.validate_key(key)
            return _qvar_map(validation_result)
        except Exception as e:
            logger.exception("validateKey failed")
            return _qvar_map(make_error_response(str(e)))

    @Slot(result="QVariantMap")
    def hotkeysDebugStatus(self) -> QVariantMap:
        """Get detailed debug status of all hotkeys."""
        try:
            return _qvar_map(self._hotkeys.debug_status())
        except Exception as e:
            logger.exception("hotkeysDebugStatus failed")
            return _qvar_map({"ok": False, "error": str(e), "status": {}})

    @Slot(result="QVariantMap")
    def hotkeysDebugThread(self) -> QVariantMap:
        """Get debug info about hotkey dispatcher thread."""
        try:
            return _qvar_map(self._hotkeys.debug_dispatcher_thread())
        except Exception as e:
            logger.exception("hotkeysDebugThread failed")
            return _qvar_map({"ok": False, "error": str(e), "status": {}})

    # ─── Logging Bridge ──────────────────────────────────────────────────

    def log(self, level: str, source: str, message: str) -> None:
        """Log message to console via signal."""
        self.logMessage.emit(level, source, message)

    # ─── _HotkeyApi Protocol Implementation ──────────────────────────────

    @property
    def clicker(self) -> Any:
        """Accessor for clicker controller."""
        return self._state.clicker if hasattr(self._state, "clicker") else None

    @property
    def aim(self) -> Any:
        """Accessor for aim controller."""
        return self._state.aim if hasattr(self._state, "aim") else None

    @property
    def macro(self) -> Any:
        """Accessor for macro controller."""
        return self._state.macro if hasattr(self._state, "macro") else None

    @property
    def recorder(self) -> Any:
        """Accessor for recorder controller."""
        return self._state.recorder if hasattr(self._state, "recorder") else None

    def stop_clicker(self) -> None:
        """Stop the clicker."""
        if hasattr(self._state, "clicker") and self._state.clicker:
            self._state.clicker.stop_clicker()

    def start_clicker(self) -> None:
        """Start the clicker."""
        if hasattr(self._state, "clicker") and self._state.clicker:
            self._state.clicker.start_clicker()

    def aim_stop(self) -> None:
        """Stop aim."""
        if hasattr(self._state, "aim") and self._state.aim:
            self._state.aim.stop()

    def aim_start(self) -> None:
        """Start aim."""
        if hasattr(self._state, "aim") and self._state.aim:
            self._state.aim.start()

    def start_macro(self) -> None:
        """Start macro."""
        if hasattr(self._state, "macro") and self._state.macro:
            self._state.macro.start_macro()

    def stop_macro(self) -> None:
        """Stop macro."""
        if hasattr(self._state, "macro") and self._state.macro:
            self._state.macro.stop_macro()

    def show_app_window(self) -> None:
        """Show app window."""
        self.hotkeysChanged.emit()  # Signal to show window

    def recorder_stop(self) -> None:
        """Stop recorder."""
        if hasattr(self._state, "recorder") and self._state.recorder:
            self._state.recorder.stop()

    def recorder_stop_play(self) -> None:
        """Stop recorder playback."""
        if hasattr(self._state, "recorder") and self._state.recorder:
            self._state.recorder.stop_play()

    def recorder_start(self) -> None:
        """Start recorder."""
        if hasattr(self._state, "recorder") and self._state.recorder:
            self._state.recorder.start()
