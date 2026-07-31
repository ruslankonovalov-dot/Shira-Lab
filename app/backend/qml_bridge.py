"""
qml_bridge.py — Thin bridge between QML UI and Python backend.
Aggregates signals and delegates to 4 controllers (Window, Gamepad, Hotkey, Profile).
All @Slot methods return native dict/list/str/int/float/bool (QVariantMap compatible).
"""
from __future__ import annotations

import json
import logging
import threading
from typing import TYPE_CHECKING, Any

from PySide6.QtCore import Property, QObject, Signal, Slot

from app.backend.models.runtime_state import RuntimeState
from app.backend.persistence import load_profile, save_profile
from app.backend.services.aim_service import AimService
from app.backend.services.clicker_service import ClickerService
from app.backend.services.hotkey_service import HotkeyService
from app.backend.services.input_validation import (
    AIM_ASPECT_MAX,
    AIM_ASPECT_MIN,
    AIM_BRIGHTNESS_MAX,
    AIM_BRIGHTNESS_MIN,
    AIM_CONFIDENCE_MAX,
    AIM_CONFIDENCE_MIN,
    AIM_FOV_MAX,
    AIM_FOV_MIN,
    AIM_MAX_AREA_MAX,
    AIM_MAX_AREA_MIN,
    AIM_MIN_AREA_MAX,
    AIM_MIN_AREA_MIN,
    AIM_RESET_DELAY_MAX,
    AIM_RESET_DELAY_MIN,
    AIM_SATURATION_MAX,
    AIM_SATURATION_MIN,
    AIM_SMOOTH_MAX,
    AIM_SMOOTH_MIN,
    AIM_SPEED_MAX,
    AIM_SPEED_MIN,
    CLICKER_HOLD_MAX,
    CLICKER_HOLD_MIN,
    CLICKER_INTERVAL_MAX,
    CLICKER_INTERVAL_MIN,
    CLICKER_LIMIT_MAX,
    CLICKER_LIMIT_MIN,
    GAMEPAD_BUTTONS_MASK_MAX,
    GAMEPAD_STICK_MAX,
    GAMEPAD_STICK_MIN,
    GAMEPAD_TARGET_INDEX_MAX,
    GAMEPAD_TARGET_INDEX_MIN,
    GAMEPAD_TRIGGER_MAX,
    GAMEPAD_TRIGGER_MIN,
    MACRO_DELAY_MAX,
    MACRO_DELAY_MIN,
    MACRO_HOLD_MAX,
    MACRO_HOLD_MIN,
    RECORDER_REPEATS_MAX,
    RECORDER_REPEATS_MIN,
    VALID_AIM_DETECTION_MODES,
    VALID_AIM_TARGET_COLORS,
    VALID_BACKGROUND_METHODS,
    VALID_CLICKER_BUTTONS,
    QVariantMap,
    _qvar_map,
    make_error_response,
    validate_enum,
    validate_float,
    validate_int,
    validate_json_array,
    validate_str,
)
from app.backend.services.macro_service import MacroService
from app.backend.services.pico_service import get_pico_service
from app.backend.services.recorder_service import RecorderService
from app.backend.services.vigem_service import get_vigem_service
from app.backend.sound_manager import SoundManager
from app.backend.system_tray import SystemTrayManager
from window_utils import (
    get_visible_windows,
)

# Controllers (Phase 2.1: extracted from god-object)
if TYPE_CHECKING:
    from app.backend.controllers.gamepad_controller import GamepadController
    from app.backend.controllers.hotkey_controller import HotkeyController
    from app.backend.controllers.profile_controller import ProfileController
    from app.backend.controllers.window_controller import WindowController

logger = logging.getLogger(__name__)


class QmlBridge(QObject):
    """Thin bridge aggregator — delegates to 4 controllers."""

    # Signals (re-exposed from controllers for QML compatibility)
    statusChanged = Signal(str)
    clickerStatusChanged = Signal()
    aimStatusChanged = Signal()
    macroStatusChanged = Signal()
    recorderStatusChanged = Signal()
    hotkeysChanged = Signal()
    settingsChanged = Signal()
    overlayVisibilityChanged = Signal()
    appVisibilityChanged = Signal(bool)
    iconChanged = Signal()
    overlayStatusUpdate = Signal(object)  # Consolidated status for OverlayHUD
    langChanged = Signal()
    windowPinChanged = Signal(bool)  # New signal for pin state
    _iconReady = Signal(object)  # Internal: bg thread → main thread
    logMessage = Signal(str, str, str)
    updateCheckResult = Signal(object)
    crashReportSaved = Signal(str)

    def __init__(self, state: RuntimeState | None = None, parent: QObject | None = None):
        # Handle both old signature (state as parent) and new signature (state as first arg)
        if state is not None and isinstance(state, QObject):
            # Called as QmlBridge(state) where state is actually a QObject (old usage)
            parent = state
            state = None
        elif state is not None and not isinstance(state, QObject):
            # Called as QmlBridge(state) with RuntimeState
            pass
        else:
            state = None

        if state is None:
            state = RuntimeState()

        super().__init__(parent)

        # Core services
        self.clicker: ClickerService = ClickerService()
        self.macro: MacroService = MacroService()
        self.recorder: RecorderService = RecorderService()
        self.aim: AimService = AimService()
        self.hotkeys: HotkeyService = HotkeyService(self)
        self.state: RuntimeState = state  # Use the passed state
        self._save_timer: threading.Timer | None = None
        self._save_lock = threading.Lock()
        self._suppress_save: bool = False
        self._shutdown: bool = False

        # ViGEm and Pico services
        self._vigem = get_vigem_service()
        self._pico = get_pico_service()

        # Sound manager
        self.sounds: SoundManager = SoundManager(self)

        # Init controllers (Phase 2.1) - runtime imports needed since TYPE_CHECKING doesn't import at runtime
        from app.backend.controllers.gamepad_controller import GamepadController
        from app.backend.controllers.hotkey_controller import HotkeyController
        from app.backend.controllers.profile_controller import ProfileController
        from app.backend.controllers.window_controller import WindowController

        # Overlay state - BEFORE controllers/tray so timer sees it
        self._overlayVisible: bool = True

        self._window_controller: WindowController = WindowController(
            self.state,
            self.clicker, self.macro, self.recorder, self.aim, self.hotkeys,
            self.sounds,
            bridge=self,
            parent=self
        )
        self._gamepad_controller: GamepadController = GamepadController(parent=self)
        self._hotkey_controller: HotkeyController = HotkeyController(self.state, self.hotkeys, parent=self)
        self._profile_controller: ProfileController = ProfileController(self.state, bridge=self, parent=self)

        # System tray - AFTER controllers so timer doesn't fire before init
        self.tray: SystemTrayManager | None = None
        # By default, don't create system tray in tests
        import os
        if not os.environ.get("DISABLE_SYSTEM_TRAY"):
            self.tray = SystemTrayManager(self)  # type: ignore[arg-type]
            # Pass tray to WindowController (it was created without tray)
            self._window_controller.set_tray(self.tray)

        # Set bridge references for controllers that need it
        self._gamepad_controller._vigem.set_bridge(self)
        self._gamepad_controller._pico.set_bridge(self)
        self._vigem.set_bridge(self)
        self._pico.set_bridge(self)

        # Add is_app_visible method for HotkeyService protocol
        self.is_app_visible = self._window_controller.is_app_visible

        # Connect internal signals from controllers
        self._connect_controller_signals()

        # Inject bridge into services for logging
        self.clicker.set_bridge(self)
        self.aim.set_bridge(self)
        self.macro.set_bridge(self)
        self.recorder.set_bridge(self)

        # Load profile and init
        load_profile(self)
        self._hotkey_controller.hotkeys.set_bindings(self.state.hotkeys)
        # Emit settingsChanged so QML picks up the loaded palette/lang
        self.settingsChanged.emit()

        # Apply sound settings
        self.sounds.set_enabled(getattr(self.state, 'sounds_enabled', True))
        self.sounds.set_volume(getattr(self.state, 'sounds_volume', 0.5))

        # Start background status poller for OverlayHUD
        self._status_poller: threading.Thread | None = None
        self._start_status_poller()

        # Visibility check is handled by WindowController (wait for tray to be set)
        # Don't start duplicate timer here

    # ─── overlayVisible Property for QML/Tray ───────────────────────────────

    @Property(bool, notify=overlayVisibilityChanged)
    def overlayVisible(self) -> bool:
        return self._overlayVisible

    @Slot(bool)
    def _on_window_pin_changed(self, pinned: bool) -> None:
        self.windowPinChanged.emit(pinned)

    @Slot(bool)
    def _on_overlay_visibility_changed(self, visible: bool) -> None:
        self._overlayVisible = visible
        self.overlayVisibilityChanged.emit(visible)

    @Slot(bool)
    def _on_app_visibility_changed(self, visible: bool) -> None:
        self.appVisibilityChanged.emit(visible)

    def _connect_controller_signals(self) -> None:
        """Forward signals from controllers to bridge signals for QML."""
        # WindowController signals - use slots to bridge Signal -> Signal
        self._window_controller.windowPinChanged.connect(self._on_window_pin_changed)
        self._window_controller.windowVisibilityChanged.connect(lambda v: self.statusChanged.emit("visibility" if v else "hidden"))
        self._window_controller.overlayVisibilityChanged.connect(self._on_overlay_visibility_changed)
        self._window_controller.appVisibilityChanged.connect(self._on_app_visibility_changed)
        self._window_controller.iconChanged.connect(self.iconChanged.emit)
        self._window_controller.iconReady.connect(self._on_icon_generated)
        self._window_controller.crashReportSaved.connect(self.crashReportSaved.emit)
        self._window_controller.logMessage.connect(self.logMessage.emit)

        # HotkeyController signals
        self._hotkey_controller.hotkeysChanged.connect(self.hotkeysChanged.emit)
        self._hotkey_controller.logMessage.connect(self.logMessage.emit)

        # GamepadController signals
        self._gamepad_controller.vigemStatusChanged.connect(lambda: self.statusChanged.emit("vigem"))
        self._gamepad_controller.picoStatusChanged.connect(lambda: self.statusChanged.emit("pico"))
        self._gamepad_controller.physicalGamepadsChanged.connect(lambda: self.statusChanged.emit("physical"))
        self._gamepad_controller.logMessage.connect(self.logMessage.emit)

        # ProfileController signals
        self._profile_controller.settingsChanged.connect(self.settingsChanged.emit)
        self._profile_controller.langChanged.connect(self.langChanged.emit)
        self._profile_controller.logMessage.connect(self.logMessage.emit)

    # ─── Delegated Properties ──────────────────────────────────────────────

    @property
    def window_controller(self) -> WindowController:
        return self._window_controller

    @property
    def gamepad_controller(self) -> GamepadController:
        return self._gamepad_controller

    @property
    def hotkey_controller(self) -> HotkeyController:
        return self._hotkey_controller

    @property
    def profile_controller(self) -> ProfileController:
        return self._profile_controller

    # ─── Background Status Poller (thread-safe for OverlayHUD) ──────────────

    def _start_status_poller(self) -> None:
        """Start background thread that polls service statuses and emits signal."""

        def poll_loop() -> None:
            import time
            while not getattr(self, '_shutdown', False):
                time.sleep(0.3)
                try:
                    status = {
                        "clicker": self.clicker.get_status() if hasattr(self.clicker, 'get_status') else {},
                        "aim": self.aim.get_status() if hasattr(self.aim, 'get_status') else {},
                        "macro": self.macro.get_status() if hasattr(self.macro, 'get_status') else {},
                        "recorder": self.recorder.status() if hasattr(self.recorder, 'status') else {},
                    }
                    self.overlayStatusUpdate.emit(status)
                except (OSError, RuntimeError, AttributeError, ValueError) as e:
                    logger.debug(f"Status poller error: {e}")

        self._status_poller = threading.Thread(target=poll_loop, daemon=True, name="OverlayStatusPoller")
        self._status_poller.start()

    # ─── Visibility Check ──────────────────────────────────────────────────

    # ─── Save ──────────────────────────────────────────────────────────────

    def _schedule_save(self) -> None:
        if self._suppress_save:
            return
        with self._save_lock:
            if self._save_timer is not None:
                self._save_timer.cancel()
            self._save_timer = threading.Timer(0.4, self._flush_save)
            self._save_timer.daemon = True
            self._save_timer.start()

    def _flush_save(self) -> None:
        with self._save_lock:
            try:
                save_profile(self)
            except Exception:
                logger.exception("Failed to save profile")

    # ─── Logging ───────────────────────────────────────────────────────────

    def log(self, level: str, source: str, message: str) -> None:
        """Send a log entry to the QML console. Thread-safe via signal."""
        try:
            self.logMessage.emit(str(level), str(source), str(message))
        except Exception:
            logger.exception("Failed to emit log message")

    @Slot(str, str, str)
    def logMessageSlot(self, level: str, source: str, message: str) -> None:
        """Slot version (can be called from QML too)."""
        self.log(level, source, message)

    # ─── i18n: Translation ─────────────────────────────────────────────────

    @Slot(str, result=str)
    def trKey(self, key: str) -> str:
        """Translate a key to current UI language."""
        try:
            from app.backend.i18n import tr as _tr
            from app.backend.services.input_validation import VALID_LANGUAGES
            lang: str = getattr(self.state, "ui_lang", "RU")
            if lang not in VALID_LANGUAGES:
                lang = "RU"
            return _tr(key, lang)
        except (OSError, RuntimeError, AttributeError, ValueError, KeyError):
            return key

    # Compatibility: QML calls Bridge.tr() — delegate to trKey()
    # Use type: ignore because QObject.tr() has a different signature
    @Slot(str, result=str)
    def tr(self, key: str) -> str:  # type: ignore[override]
        """Translate a key (delegates to trKey)."""
        return self.trKey(key)

    @Slot(str, str, result=str)
    def trLang(self, key: str, lang: str) -> str:
        """Translate a key to specific language."""
        try:
            from app.backend.i18n import tr as _tr
            from app.backend.services.input_validation import VALID_LANGUAGES
            if lang not in VALID_LANGUAGES:
                lang = "RU"
            return _tr(key, lang)
        except (OSError, RuntimeError, AttributeError, ValueError, KeyError):
            return key

    @Slot(result="QVariantMap")
    def getI18nCoverage(self) -> QVariantMap:
        """Returns translation coverage stats per language."""
        try:
            from app.backend.i18n import (
                get_available_languages,
                get_translation_coverage,
            )
            return _qvar_map({
                "ok": True,
                "coverage": get_translation_coverage(),
                "languages": get_available_languages(),
            })
        except (OSError, RuntimeError, AttributeError, ValueError, KeyError) as e:
            return _qvar_map({"ok": False, "error": str(e)})

    # ─── App version for QML ───────────────────────────────────────────────

    @Slot(result=str)
    def getAppVersion(self) -> str:
        return getattr(self.state, 'app_version', '1.0.0')

    # ─── Clicker ───────────────────────────────────────────────────────────

    @Slot(result="QVariantMap")
    def getClickerStatus(self) -> QVariantMap:
        return _qvar_map(self.clicker.get_status())

    @Slot(result=int)
    def getHwnd(self) -> int:
        """Get app window HWND."""
        return self.window_controller._get_app_hwnd()

    @Slot(result=float)
    def getClickerCPS(self) -> float:
        return float(getattr(self.clicker, 'cps', 0.0))

    @Slot(int, int, str, int, str, result="QVariantMap")
    def setClickerConfig(self, interval_ms: int, hold_ms: int, button: str, limit: int, background_method: str) -> QVariantMap:
        ok: bool
        ok, interval_val, err = validate_int(interval_ms, CLICKER_INTERVAL_MIN, CLICKER_INTERVAL_MAX, name="interval_ms")
        if not ok or interval_val is None:
            return _qvar_map(make_error_response(err or "Invalid interval_ms"))
        ok, hold_val, err = validate_int(hold_ms, CLICKER_HOLD_MIN, CLICKER_HOLD_MAX, name="hold_ms")
        if not ok or hold_val is None:
            return _qvar_map(make_error_response(err or "Invalid hold_ms"))
        ok, button_val, err = validate_enum(button, VALID_CLICKER_BUTTONS, case_sensitive=False, name="button")
        if not ok or button_val is None:
            return _qvar_map(make_error_response(err or "Invalid button"))
        ok, limit_val, err = validate_int(limit, CLICKER_LIMIT_MIN, CLICKER_LIMIT_MAX, name="limit")
        if not ok or limit_val is None:
            return _qvar_map(make_error_response(err or "Invalid limit"))
        ok, method_val, err = validate_enum(
            background_method, VALID_BACKGROUND_METHODS, default="sendinput", name="background_method")
        if not ok or method_val is None:
            return _qvar_map(make_error_response(err or "Invalid background_method"))

        self.clicker.background_method = method_val
        status = self.clicker.update_config(interval_val, hold_val, button_val, limit_val)
        self._schedule_save()
        return _qvar_map(status)

    @Slot(result="QVariantMap")
    def startClicker(self) -> QVariantMap:
        status = self.clicker.start(target_hwnd=self.state.clicker_target_hwnd)
        self._schedule_save()
        self.sounds.play("start")
        return _qvar_map(status)

    @Slot(result="QVariantMap")
    def stopClicker(self) -> QVariantMap:
        status = self.clicker.stop()
        self._schedule_save()
        self.sounds.play("stop")
        return _qvar_map(status)

    # ─── Macro ─────────────────────────────────────────────────────────────

    @Slot(result="QVariantMap")
    def getMacroStatus(self) -> QVariantMap:
        return _qvar_map(self.macro.get_status())

    @Slot(str, result="QVariantMap")
    def setMacroMode(self, mode: str) -> QVariantMap:
        ok, val, err = validate_enum(mode, {"sequence", "hold", "toggle"}, case_sensitive=False, name="mode")
        if not ok or val is None:
            return _qvar_map(make_error_response(err or "Invalid mode"))
        out = self.macro.set_run_mode(val)
        self._schedule_save()
        return _qvar_map(out)

    @Slot(str, result="QVariantMap")
    def setMacroBackgroundMethod(self, method: str) -> QVariantMap:
        ok, val, err = validate_enum(method, VALID_BACKGROUND_METHODS, default="sendinput", name="method")
        if not ok or val is None:
            return _qvar_map(make_error_response(err or "Invalid method"))
        out = self.macro.set_background_method(val)
        self._schedule_save()
        return _qvar_map(out)

    @Slot(str, float, float, result="QVariantMap")
    def addMacroAction(self, key: str, delay: float, hold: float) -> QVariantMap:
        ok, key_val, err = validate_str(key, min_len=1, max_len=50, name="key")
        if not ok or key_val is None:
            return _qvar_map(make_error_response(err or "Invalid key"))
        ok, delay_val, err = validate_float(delay, MACRO_DELAY_MIN, MACRO_DELAY_MAX, name="delay")
        if not ok or delay_val is None:
            return _qvar_map(make_error_response(err or "Invalid delay"))
        ok, hold_val, err = validate_float(hold, MACRO_HOLD_MIN, MACRO_HOLD_MAX, name="hold")
        if not ok or hold_val is None:
            return _qvar_map(make_error_response(err or "Invalid hold"))
        out = self.macro.add_action(key_val, delay_val, hold_val)
        self._schedule_save()
        return _qvar_map(out)

    @Slot(result="QVariantMap")
    def clearMacroActions(self) -> QVariantMap:
        out = self.macro.clear_actions()
        self._schedule_save()
        return _qvar_map(out)

    @Slot(result="QVariantMap")
    def startMacro(self) -> QVariantMap:
        out = self.macro.start(target_hwnd=self.state.macro_target_hwnd)
        self._schedule_save()
        self.sounds.play("start")
        return _qvar_map(out)

    @Slot(result="QVariantMap")
    def stopMacro(self) -> QVariantMap:
        out = self.macro.stop()
        self._schedule_save()
        self.sounds.play("stop")
        return _qvar_map(out)

    @Slot(result="QVariantMap")
    def macroUndo(self) -> QVariantMap:
        try:
            result = self.macro.undo()
            self._schedule_save()
            self.macroStatusChanged.emit()
            return _qvar_map(result)
        except (OSError, RuntimeError, AttributeError, ValueError, IndexError) as e:
            return _qvar_map({"ok": False, "error": str(e)})

    @Slot(result="QVariantMap")
    def macroRedo(self) -> QVariantMap:
        try:
            result = self.macro.redo()
            self._schedule_save()
            self.macroStatusChanged.emit()
            return _qvar_map(result)
        except (OSError, RuntimeError, AttributeError, ValueError, IndexError) as e:
            return _qvar_map({"ok": False, "error": str(e)})

    @Slot(int, result="QVariantMap")
    def macroDeleteAction(self, index: int) -> QVariantMap:
        try:
            result = self.macro.delete_action(int(index))
            self._schedule_save()
            self.macroStatusChanged.emit()
            return _qvar_map(result)
        except (OSError, RuntimeError, AttributeError, ValueError, IndexError) as e:
            return _qvar_map({"ok": False, "error": str(e)})

    @Slot(int, int, result="QVariantMap")
    def macroMoveAction(self, from_index: int, to_index: int) -> QVariantMap:
        try:
            result = self.macro.move_action(int(from_index), int(to_index))
            self._schedule_save()
            self.macroStatusChanged.emit()
            return _qvar_map(result)
        except (OSError, RuntimeError, AttributeError, ValueError, IndexError) as e:
            return _qvar_map({"ok": False, "error": str(e)})

    @Slot(result="QVariantMap")
    def macroGetUndoRedoStatus(self) -> QVariantMap:
        try:
            return _qvar_map(self.macro.get_undo_redo_status())
        except (OSError, RuntimeError, AttributeError, ValueError) as e:
            return _qvar_map({"ok": False, "error": str(e)})

    # ─── Recorder ──────────────────────────────────────────────────────────

    @Slot(result="QVariantMap")
    def recorderStatus(self) -> QVariantMap:
        return _qvar_map(self.recorder.status())

    @Slot(result="QVariantMap")
    def recorderList(self) -> QVariantMap:
        return _qvar_map(self.recorder.list_records())

    @Slot(result="QVariantMap")
    def recorderStart(self) -> QVariantMap:
        result = self.recorder.start_recording()
        self.sounds.play("start")
        return _qvar_map(result)

    @Slot(result="QVariantMap")
    def recorderStop(self) -> QVariantMap:
        result = self.recorder.stop_recording()
        self.sounds.play("stop")
        return _qvar_map(result)

    @Slot(str, int, result="QVariantMap")
    def recorderPlay(self, name: str, repeats: int = 1) -> QVariantMap:
        ok, name_val, err = validate_str(name, min_len=1, max_len=255, name="record_name")
        if not ok or name_val is None:
            return _qvar_map(make_error_response(err or "Invalid name"))
        ok, repeats_val, err = validate_int(repeats, RECORDER_REPEATS_MIN, RECORDER_REPEATS_MAX, default=1, name="repeats")
        if not ok or repeats_val is None:
            return _qvar_map(make_error_response(err or "Invalid repeats"))
        result = self.recorder.play_record(name_val, repeats_val)
        self.sounds.play("start")
        return _qvar_map(result)

    @Slot(result="QVariantMap")
    def recorderStopPlay(self) -> QVariantMap:
        result = self.recorder.stop_playing()
        self.sounds.play("stop")
        return _qvar_map(result)

    @Slot(str, result="QVariantMap")
    def setRecorderBackgroundMethod(self, method: str) -> QVariantMap:
        ok, val, err = validate_enum(method, VALID_BACKGROUND_METHODS, default="sendinput", name="method")
        if not ok or val is None:
            return _qvar_map(make_error_response(err or "Invalid method"))
        out = self.recorder.set_background_method(val)
        self._schedule_save()
        return _qvar_map(out)

    @Slot(str)
    def recorderDelete(self, name: str) -> None:
        ok, name_val, err = validate_str(name, min_len=1, max_len=255, name="record_name")
        if not ok or name_val is None:
            logger.warning("recorderDelete: %s", err or "Invalid name")
            return
        self.recorder.delete_record(name_val)

    # ─── Aim ───────────────────────────────────────────────────────────────

    @Slot(result="QVariantMap")
    def aimStatus(self) -> QVariantMap:
        return _qvar_map(self.aim.get_status())

    @Slot(float, int, float, result="QVariantMap")
    def aimSetConfig(self, confidence: float, smooth_steps: int, reset_delay: float) -> QVariantMap:
        ok, conf_val, err = validate_float(confidence, AIM_CONFIDENCE_MIN, AIM_CONFIDENCE_MAX, name="confidence")
        if not ok or conf_val is None:
            return _qvar_map(make_error_response(err or "Invalid confidence"))
        ok, smooth_val, err = validate_int(smooth_steps, AIM_SMOOTH_MIN, AIM_SMOOTH_MAX, name="smooth_steps")
        if not ok or smooth_val is None:
            return _qvar_map(make_error_response(err or "Invalid smooth_steps"))
        ok, reset_val, err = validate_float(reset_delay, AIM_RESET_DELAY_MIN, AIM_RESET_DELAY_MAX, name="reset_delay")
        if not ok or reset_val is None:
            return _qvar_map(make_error_response(err or "Invalid reset_delay"))
        out = self.aim.update_config(conf_val, smooth_val, reset_val)
        self._schedule_save()
        return _qvar_map(out)

    @Slot(int, int, int, int, result="QVariantMap")
    def aimSetRegion(self, top: int, left: int, width: int, height: int) -> QVariantMap:
        ok, top_val, err = validate_int(top, 0, 10000, name="top")
        if not ok or top_val is None:
            return _qvar_map(make_error_response(err or "Invalid top"))
        ok, left_val, err = validate_int(left, 0, 10000, name="left")
        if not ok or left_val is None:
            return _qvar_map(make_error_response(err or "Invalid left"))
        ok, width_val, err = validate_int(width, 0, 10000, name="width")
        if not ok or width_val is None:
            return _qvar_map(make_error_response(err or "Invalid width"))
        ok, height_val, err = validate_int(height, 0, 10000, name="height")
        if not ok or height_val is None:
            return _qvar_map(make_error_response(err or "Invalid height"))
        out = self.aim.set_scan_region(top_val, left_val, width_val, height_val)
        self._schedule_save()
        return _qvar_map(out)

    @Slot(result="QVariantMap")
    def aimStart(self) -> QVariantMap:
        out = self.aim.start()
        self._schedule_save()
        self.sounds.play("start")
        return _qvar_map(out)

    @Slot(result="QVariantMap")
    def aimStop(self) -> QVariantMap:
        out = self.aim.stop()
        self._schedule_save()
        self.sounds.play("stop")
        return _qvar_map(out)

    @Slot(str, result="QVariantMap")
    def setAimBackgroundMethod(self, method: str) -> QVariantMap:
        ok, val, err = validate_enum(method, VALID_BACKGROUND_METHODS, default="sendinput", name="method")
        if not ok or val is None:
            return _qvar_map(make_error_response(err or "Invalid method"))
        out = self.aim.set_background_method(val)
        self._schedule_save()
        return _qvar_map(out)

    @Slot(str, result="QVariantMap")
    def setAimTargetColor(self, color: str) -> QVariantMap:
        ok, val, err = validate_enum(color, VALID_AIM_TARGET_COLORS, name="color")
        if not ok or val is None:
            return _qvar_map(make_error_response(err or "Invalid color"))
        out = self.aim.set_target_color(val)
        self._schedule_save()
        return _qvar_map(out)

    @Slot(int, result="QVariantMap")
    def setAimFov(self, radius: int) -> QVariantMap:
        ok, val, err = validate_int(radius, AIM_FOV_MIN, AIM_FOV_MAX, name="radius")
        if not ok or val is None:
            return _qvar_map(make_error_response(err or "Invalid radius"))
        out = self.aim.set_fov(val)
        self._schedule_save()
        return _qvar_map(out)

    @Slot(float, result="QVariantMap")
    def setAimSpeed(self, speed: float) -> QVariantMap:
        ok, val, err = validate_float(speed, AIM_SPEED_MIN, AIM_SPEED_MAX, name="speed")
        if not ok or val is None:
            return _qvar_map(make_error_response(err or "Invalid speed"))
        out = self.aim.set_aim_speed(val)
        self._schedule_save()
        return _qvar_map(out)

    @Slot(str, result="QVariantMap")
    def setAimDetectionMode(self, mode: str) -> QVariantMap:
        ok, val, err = validate_enum(mode, VALID_AIM_DETECTION_MODES, name="mode")
        if not ok or val is None:
            return _qvar_map(make_error_response(err or "Invalid mode"))
        out = self.aim.set_detection_mode(val)
        self._schedule_save()
        return _qvar_map(out)

    @Slot(str, result="QVariantMap")
    def setAimMultiColors(self, colors_json: str) -> QVariantMap:
        ok, colors_val, err = validate_json_array(colors_json, item_type=str, min_items=1, max_items=10, name="colors")
        if not ok or colors_val is None:
            return _qvar_map(make_error_response(err or "Invalid colors"))
        for c in colors_val:
            if c.lower() not in VALID_AIM_TARGET_COLORS:
                return _qvar_map(make_error_response(f"Invalid color: {c}. Must be one of: {', '.join(sorted(VALID_AIM_TARGET_COLORS))}"))
        out = self.aim.set_multi_colors(colors_val)
        self._schedule_save()
        return _qvar_map(out)

    @Slot(int, int, int, int, int, int, result="QVariantMap")
    def setAimFilters(self, min_area: int, max_area: int, aspect_min_x100: int, aspect_max_x100: int, brightness: int, saturation: int) -> QVariantMap:
        ok, min_val, err = validate_int(min_area, AIM_MIN_AREA_MIN, AIM_MIN_AREA_MAX, name="min_area")
        if not ok or min_val is None:
            return _qvar_map(make_error_response(err or "Invalid min_area"))
        ok, max_val, err = validate_int(max_area, AIM_MAX_AREA_MIN, AIM_MAX_AREA_MAX, name="max_area")
        if not ok or max_val is None:
            return _qvar_map(make_error_response(err or "Invalid max_area"))
        if min_val > max_val:
            return _qvar_map(make_error_response("min_area must be <= max_area"))
        ok, aspect_min_val, err = validate_int(aspect_min_x100, int(AIM_ASPECT_MIN * 100), int(AIM_ASPECT_MAX * 100), name="aspect_min")
        if not ok or aspect_min_val is None:
            return _qvar_map(make_error_response(err or "Invalid aspect_min"))
        ok, aspect_max_val, err = validate_int(aspect_max_x100, int(AIM_ASPECT_MIN * 100), int(AIM_ASPECT_MAX * 100), name="aspect_max")
        if not ok or aspect_max_val is None:
            return _qvar_map(make_error_response(err or "Invalid aspect_max"))
        if aspect_min_val > aspect_max_val:
            return _qvar_map(make_error_response("aspect_min must be <= aspect_max"))
        ok, bright_val, err = validate_int(brightness, AIM_BRIGHTNESS_MIN, AIM_BRIGHTNESS_MAX, name="brightness")
        if not ok or bright_val is None:
            return _qvar_map(make_error_response(err or "Invalid brightness"))
        ok, sat_val, err = validate_int(saturation, AIM_SATURATION_MIN, AIM_SATURATION_MAX, name="saturation")
        if not ok or sat_val is None:
            return _qvar_map(make_error_response(err or "Invalid saturation"))
        out = self.aim.set_filters(min_val, max_val, aspect_min_val / 100.0, aspect_max_val / 100.0, bright_val, sat_val)
        self._schedule_save()
        return _qvar_map(out)

    @Slot(int, int, result="QVariantMap")
    def aimSampleColor(self, x: int, y: int) -> QVariantMap:
        ok, x_val, err = validate_int(x, 0, 10000, name="x")
        if not ok or x_val is None:
            return _qvar_map(make_error_response(err or "Invalid x"))
        ok, y_val, err = validate_int(y, 0, 10000, name="y")
        if not ok or y_val is None:
            return _qvar_map(make_error_response(err or "Invalid y"))
        out = self.aim.sample_color_at(x_val, y_val)
        self._schedule_save()
        return _qvar_map(out)

    # ─── Mouse Position ─────────────────────────────────────────────────────

    @Slot(result="QVariantMap")
    def getMousePosition(self) -> QVariantMap:
        """Get current mouse cursor position. Returns {x, y}."""
        try:
            import ctypes
            class POINT(ctypes.Structure):
                _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]
            pt = POINT()
            user32 = ctypes.windll.user32
            user32.GetCursorPos(ctypes.byref(pt))
            return _qvar_map({"x": int(pt.x), "y": int(pt.y)})
        except (OSError, RuntimeError, AttributeError, ValueError, OverflowError) as e:
            return _qvar_map({"x": 0, "y": 0, "error": str(e)})

    # ─── Hotkeys (delegated to HotkeyController) ───────────────────────────

    @Slot(result="QVariantMap")
    def getHotkeys(self) -> QVariantMap:
        return _qvar_map(self._hotkey_controller.getHotkeys())

    @Slot(str, str, str, result="QVariantMap")
    def setHotkey(self, action: str, key: str, mode: str) -> QVariantMap:
        return _qvar_map(self._hotkey_controller.setHotkey(action, key, mode))

    # Aliases for test compatibility
    @Slot(str, str, str, result="QVariantMap")
    def registerHotkey(self, action: str, key: str, mode: str) -> QVariantMap:
        """Alias for setHotkey (test compatibility)."""
        return self.setHotkey(action, key, mode)

    @Slot(str, result="QVariantMap")
    def unregisterHotkey(self, action: str) -> QVariantMap:
        """Alias for resetHotkey (test compatibility)."""
        return _qvar_map(self._hotkey_controller.resetHotkey(action))

    @Slot(str, result="QVariantMap")
    def resetHotkey(self, action: str) -> QVariantMap:
        return _qvar_map(self._hotkey_controller.resetHotkey(action))

    @Slot(result="QVariantMap")
    def resetAllHotkeys(self) -> QVariantMap:
        return _qvar_map(self._hotkey_controller.resetAllHotkeys())

    @Slot(str, result="QVariantMap")
    def validateKey(self, key: str) -> QVariantMap:
        return _qvar_map(self._hotkey_controller.validateKey(key))

    @Slot(result="QVariantMap")
    def hotkeysDebugStatus(self) -> QVariantMap:
        return _qvar_map(self._hotkey_controller.hotkeysDebugStatus())

    @Slot(result="QVariantMap")
    def hotkeysDebugThread(self) -> QVariantMap:
        return _qvar_map(self._hotkey_controller.hotkeysDebugThread())

    # ─── Diagnostics ───────────────────────────────────────────────────────

    @Slot(result="QVariantMap")
    def getDiagnostics(self) -> QVariantMap:
        import platform
        return _qvar_map({
            "platform": platform.platform(),
            "python": platform.python_version(),
            "is_pinned": self.state.is_pinned,
            "hotkeys_available": self.hotkeys.is_available(),
            "mouse_hotkeys_available": self.hotkeys.is_mouse_available(),
            "terminal_palette": self.state.terminal_palette,
            "ui": "pyside6",
        })

    # ─── Panic Stop ─────────────────────────────────────────────────────────

    @Slot(result="QVariantMap")
    def panicStop(self) -> QVariantMap:
        """Emergency stop - stops ALL modules instantly."""
        logger.warning("PANIC STOP triggered!")
        results = {}
        try:
            results["clicker"] = self.stopClicker()
        except Exception:
            logger.exception("Panic stop: failed to stop clicker")
        try:
            results["aim"] = self.aimStop()
        except Exception:
            logger.exception("Panic stop: failed to stop aim")
        try:
            results["macro"] = self.stopMacro()
        except Exception:
            logger.exception("Panic stop: failed to stop macro")
        try:
            results["recorder"] = self.recorderStopPlay()
        except Exception:
            logger.exception("Panic stop: failed to stop recorder")
        self.sounds.play("panic")
        return _qvar_map({"ok": True, "stopped": results})

    # ─── Aliases for HotkeyService (snake_case) ─────────────────────────────
    # HotkeyService calls these methods on the API object (self)
    # IMPORTANT: These check app visibility - modules won't start if app is hidden!

    def start_clicker(self) -> QVariantMap:
        if not self.is_app_visible():
            logger.warning("Clicker start blocked: app not visible (no window, no tray)")
            return _qvar_map({"ok": False, "error": "App not visible"})
        return self.startClicker()

    def stop_clicker(self) -> QVariantMap:
        return self.stopClicker()

    def aim_start(self) -> QVariantMap:
        if not self.is_app_visible():
            logger.warning("Aim start blocked: app not visible (no window, no tray)")
            return _qvar_map({"ok": False, "error": "App not visible"})
        return self.aimStart()

    def aim_stop(self) -> QVariantMap:
        return self.aimStop()

    def start_macro(self) -> QVariantMap:
        if not self.is_app_visible():
            logger.warning("Macro start blocked: app not visible (no window, no tray)")
            return _qvar_map({"ok": False, "error": "App not visible"})
        return self.startMacro()

    def stop_macro(self) -> QVariantMap:
        return self.stopMacro()

    def recorder_start(self) -> QVariantMap:
        if not self.is_app_visible():
            logger.warning("Recorder start blocked: app not visible (no window, no tray)")
            return _qvar_map({"ok": False, "error": "App not visible"})
        return self.recorderStart()

    def recorder_stop(self) -> QVariantMap:
        return self.recorderStop()

    def recorder_stop_play(self) -> QVariantMap:
        return self.recorderStopPlay()

    def show_app_window(self) -> None:
        return self.showAppWindow()

    # ─── Window/Overlay/Tray (delegated to WindowController) ────────────────

    @Slot(result=bool)
    def toggleWindowPin(self) -> bool:
        return self._window_controller.toggleWindowPin()

    @Slot()
    def showAppWindow(self) -> None:
        self._window_controller.showAppWindow()

    @Slot(int)
    def set_app_hwnd(self, hwnd: int) -> None:
        """Called from main.py after QML window creation to store app HWND."""
        from app.backend.services.input_validation import (
            validate_int,
        )

        ok, hwnd_val, err = validate_int(hwnd, 0, None, name="hwnd")
        if not ok or hwnd_val is None:
            logger.error(f"Invalid hwnd: {err}")
            return
        self._window_controller.set_app_hwnd(hwnd_val)

    @Slot(int)
    def set_overlay_hwnd(self, hwnd: int) -> None:
        """Called from main.py when overlay becomes visible to store overlay HWND."""
        from app.backend.services.input_validation import (
            validate_int,
        )

        ok, hwnd_val, err = validate_int(hwnd, 0, None, name="hwnd")
        if not ok or hwnd_val is None:
            logger.error(f"Invalid overlay hwnd: {err}")
            return
        self._window_controller.set_overlay_hwnd(hwnd_val)

    @Slot()
    def toggleOverlayHUD(self) -> None:
        self._window_controller.toggleOverlayHUD()

    @Slot(result="QVariantMap")
    def panicStop_slot(self) -> dict[str, Any]:
        return self._window_controller.panicStop()

    @Slot(int, int)
    def windowDragMove(self, dx: int, dy: int) -> None:
        pass

    @Slot()
    def windowMinimize(self) -> None:
        import ctypes
        hwnd = self._window_controller._get_app_hwnd()
        if hwnd:
            user32 = ctypes.windll.user32
            user32.ShowWindow(hwnd, 6)

    @Slot()
    def windowToggleMaximize(self) -> None:
        import ctypes
        from ctypes import wintypes
        hwnd = self._window_controller._get_app_hwnd()
        if hwnd:
            user32 = ctypes.windll.user32
            # WINDOWPLACEMENT structure (not in wintypes, define locally)
            class WINDOWPLACEMENT(ctypes.Structure):
                _fields_ = [
                    ("length", ctypes.c_uint),
                    ("flags", ctypes.c_uint),
                    ("showCmd", ctypes.c_uint),
                    ("ptMinPosition", wintypes.POINT),
                    ("ptMaxPosition", wintypes.POINT),
                    ("rcNormalPosition", wintypes.RECT),
                ]
            placement = WINDOWPLACEMENT()
            placement.length = ctypes.sizeof(placement)
            user32.GetWindowPlacement(hwnd, ctypes.byref(placement))
            if placement.showCmd == 3:
                user32.ShowWindow(hwnd, 9)
            else:
                user32.ShowWindow(hwnd, 3)

    @Slot()
    def windowClose(self) -> None:
        self._window_controller._shutdown()

    @Slot(result="QVariantMap")
    def getOverlayVisibility(self) -> QVariantMap:
        return _qvar_map({"visible": self.overlayVisible})

    @Slot(bool)
    def setOverlayVisible(self, visible: bool) -> None:
        self._window_controller.setOverlayVisible(visible)

    @Slot()
    def reassertOverlayTopmost(self) -> None:
        self._window_controller.reassertOverlayTopmost()

    @Slot(result="QVariantMap")
    def getWorkArea(self) -> QVariantMap:
        return _qvar_map(self._window_controller.getWorkArea())

    @Slot(int, int, int, int, result="QVariantMap")
    def clampOverlayPosition(self, x: int, y: int, w: int, h: int) -> QVariantMap:
        return _qvar_map(self._window_controller.clampOverlayPosition(x, y, w, h))

    @Slot(result=bool)
    def isAppVisible(self) -> bool:
        return self._window_controller.is_app_visible()

    # ─── Multi-monitor support (delegated to WindowController) ──────────────

    @Slot(result="QVariantMap")
    def getMonitors(self) -> QVariantMap:
        return _qvar_map(self._window_controller.getMonitors())

    @Slot(int, result="QVariantMap")
    def getMonitorForWindow(self, hwnd: int) -> QVariantMap:
        return _qvar_map(self._window_controller.getMonitorForWindow(hwnd))

    @Slot(int, result="QVariantMap")
    def getWorkAreaForMonitor(self, monitor_index: int) -> QVariantMap:
        return _qvar_map(self._window_controller.getWorkAreaForMonitor(monitor_index))

    # ─── Target window (delegated to ProfileController) ─────────────────────

    @Slot(result="QVariantMap")
    def getWindows(self) -> QVariantMap:
        """Get list of visible windows for target selection."""
        windows = [{"hwnd": 0, "title": "GLOBAL_SCREEN"}]
        for hwnd, title in sorted(get_visible_windows(), key=lambda x: x[1].lower()):
            windows.append({"hwnd": int(hwnd), "title": title})
        return _qvar_map({"ok": True, "windows": windows})

    @Slot(str, int, result="QVariantMap")
    def setModuleTargetWindow(self, module: str, hwnd: int) -> QVariantMap:
        return _qvar_map(self.profile_controller.setModuleTargetWindow(module, hwnd))

    @Slot(str, result="QVariantMap")
    def getModuleTargetWindow(self, module: str) -> QVariantMap:
        return _qvar_map(self.profile_controller.getModuleTargetWindow(module))

    # ─── ViGEm / Pico (delegated to GamepadController) ─────────────────────

    @Slot(result="QVariantMap")
    def getVigemStatus(self) -> QVariantMap:
        return _qvar_map(self.gamepad_controller.getVigemStatus())

    @Slot(str, result="QVariantMap")
    def setVigemControllerType(self, controller_type: str) -> QVariantMap:
        return _qvar_map(self.gamepad_controller.setGamepadControllerType(controller_type))

    @Slot(int, result="QVariantMap")
    def setVigemTargetIndex(self, index: int) -> QVariantMap:
        return _qvar_map(self.gamepad_controller.setGamepadTargetIndex(str(index)))

    @Slot(str, str, result="QVariantMap")
    def setVigemButtonMap(self, key: str, gamepad_btn: str) -> QVariantMap:
        return _qvar_map(self.gamepad_controller.setVigemButtonMap({key.strip().lower(): gamepad_btn.strip().upper()}))

    @Slot(result="QVariantMap")
    def startVigem(self) -> QVariantMap:
        return _qvar_map(self.gamepad_controller.getVigemStatus())

    @Slot(result="QVariantMap")
    def stopVigem(self) -> QVariantMap:
        return _qvar_map(self.gamepad_controller.getVigemStatus())

    @Slot(result="QVariantMap")
    def refreshVigemTargets(self) -> QVariantMap:
        return _qvar_map(self.gamepad_controller.getVigemStatus())

    @Slot(int, int, int, int, int, int, int, int, result="QVariantMap")
    def vigemSetGamepadState(self, target_id: int, buttons: int, lt: int, rt: int, lx: int, ly: int, rx: int, ry: int) -> QVariantMap:
        return _qvar_map(self.gamepad_controller.sendVigemTestState({
            "target_id": target_id,
            "buttons": buttons,
            "lt": lt,
            "rt": rt,
            "lx": lx,
            "ly": ly,
            "rx": rx,
            "ry": ry
        }))

    @Slot(dict, result="QVariantMap")
    def sendVigemTestState(self, state_map: dict[str, Any]) -> QVariantMap:
        """Send test state to virtual gamepad with full input validation."""
        # Validate target_id
        ok, target_id_val, err = validate_int(
            state_map.get("target_id", 0) if state_map else 0,
            GAMEPAD_TARGET_INDEX_MIN, GAMEPAD_TARGET_INDEX_MAX, default=0, name="target_id")
        if not ok or target_id_val is None:
            return _qvar_map(make_error_response(err or "Invalid target_id"))

        # Validate buttons (0..0xFFFFFFFF)
        ok, buttons_val, err = validate_int(
            state_map.get("buttons", 0) if state_map else 0,
            0, GAMEPAD_BUTTONS_MASK_MAX, default=0, name="buttons")
        if not ok or buttons_val is None:
            return _qvar_map(make_error_response(err or "Invalid buttons"))

        # Validate triggers (0..255)
        ok, lt_val, err = validate_int(
            state_map.get("lt", 0) if state_map else 0,
            GAMEPAD_TRIGGER_MIN, GAMEPAD_TRIGGER_MAX, default=0, name="lt")
        if not ok or lt_val is None:
            return _qvar_map(make_error_response(err or "Invalid lt"))
        ok, rt_val, err = validate_int(
            state_map.get("rt", 0) if state_map else 0,
            GAMEPAD_TRIGGER_MIN, GAMEPAD_TRIGGER_MAX, default=0, name="rt")
        if not ok or rt_val is None:
            return _qvar_map(make_error_response(err or "Invalid rt"))

        # Validate sticks (-32768..32767)
        ok, lx_val, err = validate_int(
            state_map.get("lx", 0) if state_map else 0,
            GAMEPAD_STICK_MIN, GAMEPAD_STICK_MAX, default=0, name="lx")
        if not ok or lx_val is None:
            return _qvar_map(make_error_response(err or "Invalid lx"))
        ok, ly_val, err = validate_int(
            state_map.get("ly", 0) if state_map else 0,
            GAMEPAD_STICK_MIN, GAMEPAD_STICK_MAX, default=0, name="ly")
        if not ok or ly_val is None:
            return _qvar_map(make_error_response(err or "Invalid ly"))
        ok, rx_val, err = validate_int(
            state_map.get("rx", 0) if state_map else 0,
            GAMEPAD_STICK_MIN, GAMEPAD_STICK_MAX, default=0, name="rx")
        if not ok or rx_val is None:
            return _qvar_map(make_error_response(err or "Invalid rx"))
        ok, ry_val, err = validate_int(
            state_map.get("ry", 0) if state_map else 0,
            GAMEPAD_STICK_MIN, GAMEPAD_STICK_MAX, default=0, name="ry")
        if not ok or ry_val is None:
            return _qvar_map(make_error_response(err or "Invalid ry"))

        return _qvar_map(self.gamepad_controller.sendVigemTestState({
            "target_id": target_id_val,
            "buttons": buttons_val,
            "lt": lt_val,
            "rt": rt_val,
            "lx": lx_val,
            "ly": ly_val,
            "rx": rx_val,
            "ry": ry_val
        }))

    @Slot(int, int, result="QVariantMap")
    def vigemSetButtons(self, target_id: int, button_mask: int) -> QVariantMap:
        return _qvar_map(self.gamepad_controller.sendVigemTestState({
            "target_id": target_id, "buttons": button_mask
        }))

    @Slot(int, int, int, result="QVariantMap")
    def vigemSetTriggers(self, target_id: int, left: int, right: int) -> QVariantMap:
        return _qvar_map(self.gamepad_controller.sendVigemTestState({
            "target_id": target_id, "lt": left, "rt": right
        }))

    @Slot(int, int, int, result="QVariantMap")
    def vigemSetLeftStick(self, target_id: int, x: int, y: int) -> QVariantMap:
        return _qvar_map(self.gamepad_controller.sendVigemTestState({
            "target_id": target_id, "lx": x, "ly": y
        }))

    @Slot(int, int, int, result="QVariantMap")
    def vigemSetRightStick(self, target_id: int, x: int, y: int) -> QVariantMap:
        return _qvar_map(self.gamepad_controller.sendVigemTestState({
            "target_id": target_id, "rx": x, "ry": y
        }))

    @Slot(int, result="QVariantMap")
    def vigemReset(self, target_id: int) -> QVariantMap:
        return _qvar_map(self.gamepad_controller.sendVigemTestState({
            "target_id": target_id
        }))

    @Slot(str, result="QVariantMap")
    def setGamepadBackgroundMethod(self, method: str) -> QVariantMap:
        return _qvar_map(self.profile_controller.setGamepadBackgroundMethod(method))

    @Slot(result="QVariantMap")
    def getPicoStatus(self) -> QVariantMap:
        return _qvar_map(self.gamepad_controller.getPicoStatus())

    @Slot(result="QVariantMap")
    def listPicoDevices(self) -> QVariantMap:
        return _qvar_map(self.gamepad_controller.listPicoDevices())

    @Slot(str, int, result="QVariantMap")
    def setPicoPort(self, port: str, baudrate: int = 115200) -> QVariantMap:
        # GamepadController doesn't have setPicoPort; use startPico with port
        return _qvar_map(self.gamepad_controller.startPico(port))

    @Slot(str, result="QVariantMap")
    def setPicoMode(self, mode: str) -> QVariantMap:
        return _qvar_map(self.gamepad_controller.setPicoMode(mode))

    @Slot(str, str, result="QVariantMap")
    def setPicoButtonMap(self, key: str, button: str) -> QVariantMap:
        return _qvar_map(self.gamepad_controller.setPicoButtonMap(key, button))

    @Slot(str, result="QVariantMap")
    def startPico(self, port: str = "") -> QVariantMap:
        return _qvar_map(self.gamepad_controller.startPico(port))

    @Slot(result="QVariantMap")
    def stopPico(self) -> QVariantMap:
        return _qvar_map(self.gamepad_controller.stopPico())

    @Slot(str, str, int, result="QVariantMap")
    def picoSendKey(self, key: str, action: str, hold_ms: int = 50) -> QVariantMap:
        return _qvar_map(self.gamepad_controller.picoSendKey(key, action, hold_ms))

    @Slot(int, int, int, int, result="QVariantMap")
    def picoSendMouse(self, dx: int, dy: int, button: int = 0, hold_ms: int = 0) -> QVariantMap:
        return _qvar_map(self.gamepad_controller.picoSendMouse(dx, dy, button, hold_ms))

    @Slot(int, int, int, int, int, int, int, int, result="QVariantMap")
    def picoSendGamepad(self, buttons: int, lt: int, rt: int, lx: int, ly: int, rx: int, ry: int, mask: int = 65535) -> QVariantMap:
        return _qvar_map(self.gamepad_controller.picoSendGamepad(buttons, lt, rt, lx, ly, rx, ry))

    @Slot(int, int, int, result="QVariantMap")
    def picoSetStick(self, stick: int, x: int, y: int) -> QVariantMap:
        return _qvar_map(self.gamepad_controller.picoSetStick(stick, x, y))

    @Slot(int, int, result="QVariantMap")
    def picoSetTriggers(self, lt: int, rt: int) -> QVariantMap:
        # Delegate to sendVigemTestState for triggers
        return _qvar_map(self.gamepad_controller.sendVigemTestState({"lt": lt, "rt": rt}))

    @Slot(result="QVariantMap")
    def picoReset(self) -> QVariantMap:
        return _qvar_map(self.gamepad_controller.picoReset())

    @Slot(result="QVariantMap")
    def detectPhysicalGamepads(self) -> QVariantMap:
        return _qvar_map(self.gamepad_controller.detectPhysicalGamepads())

    # ─── Profile/Config (delegated to ProfileController) ────────────────────

    @Slot(result="QVariantMap")
    def getPalettes(self) -> QVariantMap:
        return _qvar_map(self.profile_controller.getPalettes())

    @Slot(result="QVariantMap")
    def getSettings(self) -> QVariantMap:
        return _qvar_map(self.profile_controller.getSettings())

    @Slot(str)
    def setTerminalPalette(self, palette_id: str) -> None:
        self.profile_controller.setTerminalPalette(palette_id)
        # Regenerate icon for new palette (async, emits iconChanged when done)
        self._regenerate_palette_icon(palette_id)

    @Slot(str)
    def setUiLang(self, code: str) -> None:
        self.profile_controller.setUiLang(code)

    @Property(str, notify=langChanged)
    def currentLang(self) -> str:
        return str(self.profile_controller.currentLang)

    @Slot(str, result="QVariantMap")
    def saveGameProfile(self, name: str) -> QVariantMap:
        return _qvar_map(self.profile_controller.saveGameProfile(name))

    @Slot(str, result="QVariantMap")
    def loadGameProfile(self, name: str) -> QVariantMap:
        return _qvar_map(self.profile_controller.loadGameProfile(name))

    @Slot(result="QVariantMap")
    def listGameProfiles(self) -> QVariantMap:
        return _qvar_map(self.profile_controller.listGameProfiles())

    @Slot(str, result="QVariantMap")
    def deleteGameProfile(self, name: str) -> QVariantMap:
        return _qvar_map(self.profile_controller.deleteGameProfile(name))

    @Slot(str, result="QVariantMap")
    def exportProfile(self, path: str) -> QVariantMap:
        try:
            from app.backend.profile_io import export_profile
            result = export_profile(self, path)
            return _qvar_map(result)
        except (OSError, RuntimeError, AttributeError, ValueError, json.JSONDecodeError) as e:
            return _qvar_map({"ok": False, "error": str(e)})

    @Slot(str, result="QVariantMap")
    def importProfile(self, path: str) -> QVariantMap:
        try:
            from app.backend.profile_io import import_profile
            result = import_profile(self, path)
            return _qvar_map(result)
        except (OSError, RuntimeError, AttributeError, ValueError, json.JSONDecodeError) as e:
            return _qvar_map({"ok": False, "error": str(e)})

    @Slot(result="QVariantMap")
    def exportProfileDialog(self) -> QVariantMap:
        return _qvar_map(self.profile_controller.exportProfileDialog())

    @Slot(result="QVariantMap")
    def importProfileDialog(self) -> QVariantMap:
        return _qvar_map(self.profile_controller.importProfileDialog())

    @Slot(str, result="QVariantMap")
    def saveProfile(self, name: str = "") -> QVariantMap:
        return _qvar_map(self.profile_controller.saveProfile(name))

    @Slot(str, result="QVariantMap")
    def loadProfile(self, filename: str) -> QVariantMap:
        return _qvar_map(self.profile_controller.loadProfile(filename))

    @Slot(str, result="QVariantMap")
    def deleteProfile(self, filename: str) -> QVariantMap:
        return _qvar_map(self.profile_controller.deleteProfile(filename))

    @Slot(result="QVariantMap")
    def listProfiles(self) -> QVariantMap:
        return _qvar_map(self.profile_controller.listProfiles())

    # ─── System Theme / Auto Theme ──────────────────────────────────────────

    @Slot(result="QVariantMap")
    def detectSystemTheme(self) -> QVariantMap:
        return _qvar_map(self.profile_controller.detectSystemTheme())

    @Slot(result="QVariantMap")
    def applyAutoTheme(self) -> QVariantMap:
        try:
            from app.backend.services.theme_detector import (
                detect_windows_theme,
                get_palette_for_theme,
            )
            theme = detect_windows_theme()
            palette = get_palette_for_theme(theme, self.state.terminal_palette)
            self.settingsChanged.emit()
            return _qvar_map({"ok": True, "theme": theme, "palette": palette})
        except (OSError, RuntimeError, AttributeError, ValueError, ImportError) as e:
            return _qvar_map({"ok": False, "error": str(e)})

    # ─── Update Checker ─────────────────────────────────────────────────────

    @Slot(str, result="QVariantMap")
    def checkForUpdates(self, current_version: str = "0.17.0") -> QVariantMap:
        try:
            from app.backend.services.update_checker import check_for_updates
            result = check_for_updates(current_version)
            return _qvar_map(result)
        except (OSError, RuntimeError, AttributeError, ValueError, ImportError) as e:
            return _qvar_map({"ok": False, "error": str(e)})

    @Slot(str, result="QVariantMap")
    def checkForUpdatesAsync(self, current_version: str = "0.17.0") -> QVariantMap:
        try:
            from app.backend.services.update_checker import check_for_updates_async
            def callback(result: str) -> None:
                try:
                    import json as _json
                    self.updateCheckResult.emit(_qvar_map(_json.loads(result)))
                except (json.JSONDecodeError, ValueError):
                    pass
            check_for_updates_async(current_version, callback)
            return _qvar_map({"ok": True, "started": True})
        except (OSError, RuntimeError, AttributeError, ValueError, ImportError) as e:
            return _qvar_map({"ok": False, "error": str(e)})

    # ─── Crash Reporter (delegated to WindowController) ────────────────────

    @Slot(result="QVariantMap")
    def listCrashReports(self) -> QVariantMap:
        return _qvar_map(self._window_controller.listCrashReports())

    @Slot(str, result="QVariantMap")
    def readCrashReport(self, filename: str) -> QVariantMap:
        return _qvar_map(self._window_controller.readCrashReport(filename))

    @Slot(str, result="QVariantMap")
    def deleteCrashReport(self, filename: str) -> QVariantMap:
        return _qvar_map(self._window_controller.deleteCrashReport(filename))

    @Slot(result="QVariantMap")
    def clearAllCrashReports(self) -> QVariantMap:
        return _qvar_map(self._window_controller.clearAllCrashReports())

    @Slot(bool)
    def setCrashReportSending(self, enabled: bool) -> None:
        self._window_controller.setCrashReportSending(enabled)

    # ─── Performance ───────────────────────────────────────────────────────

    @Slot(result="QVariantMap")
    def getPerformanceProfile(self) -> QVariantMap:
        return _qvar_map(self._window_controller.getPerformanceProfile())

    # ─── Icon regeneration (delegate to WindowController) ──────────────────

    def _regenerate_palette_icon(self, palette_id: str) -> None:
        self._window_controller._regenerate_palette_icon(palette_id)

    def _on_icon_generated(self, png_path: str) -> None:
        self._window_controller._on_icon_generated(png_path)

    # ─── hwnd helpers (delegate) ────────────────────────────────────────────
