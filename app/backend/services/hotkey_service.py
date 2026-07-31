from __future__ import annotations

import logging
import threading
import time
from collections.abc import Callable
from typing import (
    TYPE_CHECKING,
    Any,
    Protocol,
    TypedDict,
    cast,
)

if TYPE_CHECKING:
    from app.backend.services.input_validation import QVariantMap
else:
    QVariantMap = dict[str, Any]


class _HotkeyApi(Protocol):
    """Protocol defining the API that HotkeyService expects from its host."""
    clicker: Any
    aim: Any
    macro: Any
    recorder: Any
    def stop_clicker(self) -> None | QVariantMap: ...
    def start_clicker(self) -> None | QVariantMap: ...
    def aim_stop(self) -> None | QVariantMap: ...
    def aim_start(self) -> None | QVariantMap: ...
    def start_macro(self) -> None | QVariantMap: ...
    def stop_macro(self) -> None | QVariantMap: ...
    def show_app_window(self) -> None | QVariantMap: ...
    def recorder_stop(self) -> None | QVariantMap: ...
    def recorder_stop_play(self) -> None | QVariantMap: ...
    def recorder_start(self) -> None | QVariantMap: ...

try:
    import keyboard
    _HAS_KEYBOARD = True
except Exception:  # noqa: BLE001
    _HAS_KEYBOARD = False
    keyboard = None

# mouse lib — основной для кнопок (int 1-N)
try:
    import mouse as mouse_lib
    _HAS_MOUSE_LIB = True
except Exception:  # noqa: BLE001
    _HAS_MOUSE_LIB = False
    mouse_lib = None

# pynput — fallback для кнопок + основной для wheel
try:
    from pynput import mouse as pynput_mouse
    _HAS_PYNPUT = True
except Exception:  # noqa: BLE001
    _HAS_PYNPUT = False
    pynput_mouse = None

# Qt signal for thread-safe hotkey action dispatch
try:
    from PySide6.QtCore import QObject
    from PySide6.QtCore import Signal as QtSignal
    _HAS_PYSIDE = True
except Exception:  # noqa: BLE001
    _HAS_PYSIDE = False
    QObject = object  # type: ignore[assignment, misc]
    # Signal is not callable in this context, use a dummy
    def _DummyQtSignal(*args: Any, **kwargs: Any) -> Any:
        class DummySignal:
            def connect(self, *a: Any, **kw: Any) -> None: pass
            def emit(self, *a: Any, **kw: Any) -> None: pass
        return DummySignal()
    QtSignal = _DummyQtSignal  # type: ignore[assignment, misc]

# ─── TypedDicts for proper type narrowing ──────────────────────────────────

class ParsedKeyEmpty(TypedDict):
    type: str
    modifiers: list[str]
    main: str
    sequence: list[str]


class ParsedKeySequence(TypedDict):
    type: str
    modifiers: list[str]
    main: str
    sequence: list[str]


class ParsedKeyMouse(TypedDict):
    type: str
    modifiers: list[str]
    main: str
    sequence: list[str]


class ParsedKeyWheel(TypedDict):
    type: str
    modifiers: list[str]
    main: str
    sequence: list[str]


class ParsedKeyKeyboard(TypedDict):
    type: str
    modifiers: list[str]
    main: str
    sequence: list[str]


_ParsedKey = (
    ParsedKeyEmpty
    | ParsedKeySequence
    | ParsedKeyMouse
    | ParsedKeyWheel
    | ParsedKeyKeyboard
)


class BindingBase(TypedDict, total=False):
    mode: str


class KeyboardBinding(BindingBase):
    type: str
    modifiers: list[str]
    main: str


class MouseBinding(BindingBase):
    type: str
    modifiers: list[str]
    button: str
    button_n: int


class WheelBinding(BindingBase):
    type: str
    modifiers: list[str]
    wheel: str


class SequenceBinding(BindingBase):
    type: str
    sequence: list[str]


class EmptyBinding(BindingBase):
    type: str
    key: str


_BindingDict = (
    KeyboardBinding
    | MouseBinding
    | WheelBinding
    | SequenceBinding
    | EmptyBinding
)

_BindingMap = dict[str, _BindingDict | dict[str, str]]
_RegisteredMap = dict[str, list[Any]]
_HookHandle = Any

logger = logging.getLogger(__name__)


# ─── HotkeyDispatcher for Qt thread safety ──────────────────────────────────


class HotkeyDispatcher(QObject):
    """Thread-safe dispatcher for hotkey actions to Qt main thread."""

    # Signal: action_name (str), is_pressed (bool), is_hold_mode (bool)
    actionTriggered = QtSignal(str, bool, bool)

    def __init__(self) -> None:
        super().__init__()
        self._handler: Callable[[str, bool, bool], None] | None = None

    def set_handler(self, handler: Callable[[str, bool, bool], None]) -> None:
        """Set the handler to be called on main thread."""
        self._handler = handler
        if self._handler is not None:
            self.actionTriggered.connect(self._handler)

    def trigger(self, action: str, pressed: bool, hold_mode: bool = False) -> None:
        """Emit signal from any thread - Qt delivers to main thread."""
        self.actionTriggered.emit(action, pressed, hold_mode)


# Действия, поддерживающие горячие клавиши
HOTKEY_ACTIONS = (
    "clicker_toggle",
    "aim_toggle",
    "macro_start",
    "macro_stop",
    "recorder_start",
    "recorder_stop",
    "app_show",
    "panic_stop",
)

MODE_TOGGLE = "TOGGLE"
MODE_HOLD = "HOLD"
_VALID_MODES = (MODE_TOGGLE, MODE_HOLD)

MODIFIER_NAMES = {
    "ctrl", "control", "left ctrl", "right ctrl",
    "shift", "left shift", "right shift",
    "alt", "menu", "left alt", "right alt", "left menu", "right menu",
    "win", "windows", "left windows", "right windows",
}

# Кнопки мыши 1 и 2 (left/right) игнорируем при записи — слишком частые в UI
_IGNORED_MOUSE_BUTTONS: set[int | str] = {1, 2, "1", "2", "left", "right"}

# Pynput Button name → mouse lib number (для fallback)
_PYNPUT_BUTTON_TO_NUM: dict[str, int] = {}
if _HAS_PYNPUT and pynput_mouse:
    _PYNPUT_BUTTON_TO_NUM = {
        str(pynput_mouse.Button.middle): 3,
        str(pynput_mouse.Button.x1): 4,
        str(pynput_mouse.Button.x2): 5,
    }


class HotkeyService:
    """
    Управляет глобальными горячими клавишами.

    Поддерживает:
    - Одиночные клавиши: f6, space, enter
    - Комбинации модификаторов: ctrl+shift+a
    - Кнопки мыши: mouse:3 (middle), mouse:4 (x1), mouse:5 (x2), mouse:N (extra)
    - Клавиша+мышь: ctrl+mouse:4
    - Wheel: wheel:up, wheel:down, wheel:left, wheel:right
    - Последовательности: f6,f7 (до 3 клавиш)

    Использует ОДНОВРЕМЕННО mouse lib + pynput для надёжности:
    - mouse lib — основной (видит все кнопки как int)
    - pynput — fallback (видит middle/x1/x2, и unknown для extra)

    Все вызовы действий диспетчеризуются через HotkeyDispatcher
    в главный Qt-поток для потокобезопасности.
    """

    __slots__ = (
        "_api",
        "_bindings",
        "_dispatcher",
        "_last_mouse_event",
        "_last_mouse_event_time",
        "_lock",
        "_mouse_events_count",
        "_mouse_hook",
        "_mouse_hook_last_error",
        "_mouse_hook_started",
        "_mouse_triggers_count",
        "_pynput_listener",
        "_pynput_started",
        "_registered",
    )

    def __init__(self, api: _HotkeyApi) -> None:
        self._api: _HotkeyApi = api
        self._lock = threading.RLock()
        self._bindings: dict[str, _BindingDict | dict[str, str]] = {}
        self._registered: _RegisteredMap = {}

        # mouse lib hook
        self._mouse_hook: _HookHandle | None = None
        self._mouse_hook_started: bool = False
        self._mouse_hook_last_error: str | None = None

        # pynput listener (для wheel + fallback для кнопок)
        self._pynput_listener: Any | None = None
        self._pynput_started: bool = False

        # Диагностика
        self._last_mouse_event: dict[str, Any] | None = None  # последнее событие мыши (для отладки)
        self._last_mouse_event_time: float = 0.0
        self._mouse_events_count: int = 0
        self._mouse_triggers_count: int = 0

        # Thread-safe dispatcher for hotkey actions (Qt main thread)
        self._dispatcher = HotkeyDispatcher()
        self._dispatcher.set_handler(self._on_action_dispatched)

        # Запускаем listeners сразу при инициализации
        self._ensure_all_listeners()

    def _on_action_dispatched(self, action: str, pressed: bool, hold_mode: bool) -> None:
        """Called on Qt main thread via HotkeyDispatcher signal."""
        try:
            if hold_mode:
                if pressed:
                    self._action_start_handler(action)()
                else:
                    self._action_stop_handler(action)()
            else:
                if pressed:  # TOGGLE mode only triggers on press
                    self._action_handler(action)()
        except (OSError, RuntimeError, ValueError, AttributeError) as e:
            logger.warning("Dispatched hotkey action %s error: %s", action, e)

    # ─── Привязка обработчиков к действиям ────────────────────────────────
    def _action_handler(self, action: str) -> Callable[[], None]:
        api = self._api

        def _clicker_toggle() -> None:
            try:
                if api.clicker.is_running:
                    api.stop_clicker()
                else:
                    api.start_clicker()
            except (OSError, RuntimeError, ValueError, AttributeError) as e:
                logger.warning("clicker_toggle hotkey error: %s", e)

        def _aim_toggle() -> None:
            try:
                if api.aim.is_running:
                    api.aim_stop()
                else:
                    api.aim_start()
            except (OSError, RuntimeError, ValueError, AttributeError) as e:
                logger.warning("aim_toggle hotkey error: %s", e)

        def _macro_start() -> None:
            try:
                api.start_macro()
            except (OSError, RuntimeError, ValueError, AttributeError) as e:
                logger.warning("macro_start hotkey error: %s", e)

        def _macro_stop() -> None:
            try:
                api.stop_macro()
            except (OSError, RuntimeError, ValueError, AttributeError) as e:
                logger.warning("macro_stop hotkey error: %s", e)

        def _recorder_start() -> None:
            try:
                if api.recorder.is_recording:
                    api.recorder_stop()
                else:
                    api.recorder_start()
            except (OSError, RuntimeError, ValueError, AttributeError) as e:
                logger.warning("recorder_start hotkey error: %s", e)

        def _recorder_stop() -> None:
            try:
                api.recorder_stop_play()
            except (OSError, RuntimeError, ValueError, AttributeError) as e:
                logger.warning("recorder_stop hotkey error: %s", e)

        def _app_show() -> None:
            try:
                api.show_app_window()
            except (OSError, RuntimeError, ValueError, AttributeError) as e:
                logger.warning("app_show hotkey error: %s", e)

        def _panic_stop() -> None:
            try:
                # Stop everything immediately
                if api.clicker.is_running:
                    api.stop_clicker()
                if api.aim.is_running:
                    api.aim_stop()
                if api.macro.is_running:
                    api.stop_macro()
                if api.recorder.is_playing:
                    api.recorder_stop_play()
                if api.recorder.is_recording:
                    api.recorder_stop()
            except (OSError, RuntimeError, ValueError, AttributeError) as e:
                logger.warning("panic_stop hotkey error: %s", e)

        mapping: dict[str, Callable[[], None]] = {
            "clicker_toggle":   _clicker_toggle,
            "aim_toggle":       _aim_toggle,
            "macro_start":      _macro_start,
            "macro_stop":       _macro_stop,
            "recorder_start":   _recorder_start,
            "recorder_stop":    _recorder_stop,
            "app_show":         _app_show,
            "panic_stop":       _panic_stop,
        }
        return mapping.get(action, lambda: None)

    def _action_start_handler(self, action: str) -> Callable[[], None]:
        api = self._api

        def _clicker_start() -> None:
            try:
                if not api.clicker.is_running:
                    api.start_clicker()
            except (OSError, RuntimeError, ValueError, AttributeError) as e:
                logger.warning("clicker HOLD start error: %s", e)

        def _aim_start() -> None:
            try:
                if not api.aim.is_running:
                    api.aim_start()
            except (OSError, RuntimeError, ValueError, AttributeError) as e:
                logger.warning("aim HOLD start error: %s", e)

        def _macro_start() -> None:
            try:
                api.start_macro()
            except (OSError, RuntimeError, ValueError, AttributeError) as e:
                logger.warning("macro HOLD start error: %s", e)

        def _recorder_start() -> None:
            try:
                if not api.recorder.is_recording:
                    api.recorder_start()
            except (OSError, RuntimeError, ValueError, AttributeError) as e:
                logger.warning("recorder HOLD start error: %s", e)

        mapping: dict[str, Callable[[], None]] = {
            "clicker_toggle":   _clicker_start,
            "aim_toggle":       _aim_start,
            "macro_start":      _macro_start,
            "recorder_start":   _recorder_start,
        }
        return mapping.get(action, lambda: None)

    def _action_stop_handler(self, action: str) -> Callable[[], None]:
        api = self._api

        def _clicker_stop() -> None:
            try:
                if api.clicker.is_running:
                    api.stop_clicker()
            except (OSError, RuntimeError, ValueError, AttributeError) as e:
                logger.warning("clicker HOLD stop error: %s", e)

        def _aim_stop() -> None:
            try:
                if api.aim.is_running:
                    api.aim_stop()
            except (OSError, RuntimeError, ValueError, AttributeError) as e:
                logger.warning("aim HOLD stop error: %s", e)

        def _macro_stop() -> None:
            try:
                api.stop_macro()
            except (OSError, RuntimeError, ValueError, AttributeError) as e:
                logger.warning("macro HOLD stop error: %s", e)

        def _recorder_stop() -> None:
            try:
                if api.recorder.is_recording:
                    api.recorder_stop()
            except (OSError, RuntimeError, ValueError, AttributeError) as e:
                logger.warning("recorder HOLD stop error: %s", e)

        mapping: dict[str, Callable[[], None]] = {
            "clicker_toggle":   _clicker_stop,
            "aim_toggle":       _aim_stop,
            "macro_start":      _macro_stop,
            "recorder_start":   _recorder_stop,
        }
        return mapping.get(action, lambda: None)

    # ─── Парсинг key string ──────────────────────────────────────────────
    @staticmethod
    def _parse_key_string(key: str) -> _ParsedKey:
        key = (key or "").strip().lower()
        if not key:
            return cast(ParsedKeyEmpty, {"type": "empty", "modifiers": [], "main": "", "sequence": []})

        if "," in key:
            parts = [p.strip() for p in key.split(",") if p.strip()]
            if len(parts) >= 2:
                return cast(
                    ParsedKeySequence,
                    {"type": "sequence", "modifiers": [], "main": "", "sequence": parts},
                )

        if "+" in key:
            parts = [p.strip() for p in key.split("+") if p.strip()]
            if len(parts) >= 2:
                main = parts[-1]
                mods = parts[:-1]
                if main.startswith("mouse:"):
                    return cast(
                        ParsedKeyMouse,
                        {"type": "mouse", "modifiers": mods, "main": main, "sequence": []},
                    )
                if main.startswith("wheel:"):
                    return cast(
                        ParsedKeyWheel,
                        {"type": "wheel", "modifiers": mods, "main": main, "sequence": []},
                    )
                return cast(
                    ParsedKeyKeyboard,
                    {"type": "keyboard", "modifiers": mods, "main": main, "sequence": []},
                )

        if key.startswith("mouse:"):
            return cast(ParsedKeyMouse, {"type": "mouse", "modifiers": [], "main": key, "sequence": []})
        if key.startswith("wheel:"):
            return cast(ParsedKeyWheel, {"type": "wheel", "modifiers": [], "main": key, "sequence": []})
        return cast(
            ParsedKeyKeyboard, {"type": "keyboard", "modifiers": [], "main": key, "sequence": []}
        )

    @staticmethod
    def _is_modifier(key: str) -> bool:
        return key.lower() in MODIFIER_NAMES

    @staticmethod
    def _parse_mouse_button(main: str) -> int | None:
        """Парсит 'mouse:N' -> N (int). None если невалидно."""
        if not main.startswith("mouse:"):
            return None
        try:
            n = int(main[6:])
            if n < 1:
                return None
            return n
        except (ValueError, IndexError):
            return None

    @staticmethod
    def _is_valid_wheel(main: str) -> bool:
        return main in ("wheel:up", "wheel:down", "wheel:left", "wheel:right")

    @staticmethod
    def _normalize_button_n(button_n: int | str | None) -> int | None:
        """
        Нормализует button_n к int.
        mouse lib может вернуть int или (в редких версиях) str.
        """
        if button_n is None or button_n in ("left", "right", "1", "2"):
            return None
        try:
            return int(button_n)
        except (ValueError, TypeError):
            return None

    # ─── Listeners ────────────────────────────────────────────────────────
    def _ensure_all_listeners(self) -> None:
        """Запускает все listeners сразу при инициализации."""
        self._ensure_mouse_hook()
        self._ensure_pynput_listener()

    def _ensure_mouse_hook(self) -> None:
        """Запускает mouse lib hook."""
        if not _HAS_MOUSE_LIB:
            self._mouse_hook_last_error = "mouse lib not installed (pip install mouse)"
            return

        with self._lock:
            if self._mouse_hook_started:
                return

            try:
                def on_event(event: Any) -> None:
                    try:
                        self._handle_mouse_event_safe(event)
                    except Exception:
                        logger.exception("mouse hook callback crashed")
                        self._mouse_hook_last_error = "callback crashed"

                self._mouse_hook = mouse_lib.hook(on_event)
                self._mouse_hook_started = True
                self._mouse_hook_last_error = None
                logger.info("mouse lib hook started successfully")
            except (OSError, RuntimeError, ValueError, AttributeError) as e:
                self._mouse_hook_last_error = f"Failed to start mouse hook: {e}"
                logger.error("Failed to start mouse hook: %s", e)

    def _ensure_pynput_listener(self) -> None:
        """Запускает pynput listener (fallback для кнопок + wheel)."""
        if not _HAS_PYNPUT:
            return

        with self._lock:
            if self._pynput_started:
                return

            try:
                def on_click(x: float, y: float, button: Any, pressed: bool) -> None:
                    try:
                        self._handle_pynput_click(button, pressed)
                    except Exception:
                        logger.exception("pynput click callback crashed")

                def on_scroll(x: float, y: float, dx: int, dy: int) -> None:
                    try:
                        self._handle_wheel_event(dx, dy)
                    except Exception:
                        logger.exception("pynput scroll callback crashed")

                self._pynput_listener = pynput_mouse.Listener(
                    on_click=on_click,
                    on_scroll=on_scroll,
                )
                self._pynput_listener.daemon = True
                self._pynput_listener.start()
                self._pynput_started = True
                logger.info("pynput listener started successfully")
            except (OSError, RuntimeError, ValueError, AttributeError) as e:
                logger.error("Failed to start pynput listener: %s", e)

    def _handle_mouse_event_safe(self, event: Any) -> None:
        """Обрабатывает событие от mouse lib (с защитой от падений)."""
        # Диагностика
        with self._lock:
            self._mouse_events_count += 1
            self._last_mouse_event_time = time.time()
            self._last_mouse_event = {
                "source": "mouse_lib",
                "type": type(event).__name__,
                "repr": repr(event)[:200],
            }

        if not _HAS_KEYBOARD:
            return

        # Проверяем что это ButtonEvent
        if not hasattr(event, 'button') or not hasattr(event, 'event_type'):
            # WheelEvent или MoveEvent
            if hasattr(event, 'delta'):
                self._handle_wheel_delta(event.delta)
            return

        # Нормализуем button_n к int
        button_n = self._normalize_button_n(event.button)
        # Безусловно игнорируем left/right (в любом формате) БЕЗ логирования
        if button_n is None or button_n in _IGNORED_MOUSE_BUTTONS:
            return

        pressed = (event.event_type == 'down')

        logger.debug("mouse lib event: button=%d, pressed=%s", button_n, pressed)

        button_key = f"mouse:{button_n}"
        self._trigger_mouse_binding(button_key, pressed)

    def _handle_pynput_click(self, button: Any, pressed: bool) -> None:
        """Fallback обработка кликов через pynput."""
        if not _HAS_KEYBOARD:
            return

        # Конвертируем pynput Button в номер
        button_n = _PYNPUT_BUTTON_TO_NUM.get(str(button))
        if button_n is None or button_n in _IGNORED_MOUSE_BUTTONS:
            # Неизвестная кнопка (например extra) — pynput вернёт Button.unknown
            # В этом случае мы не знаем номер, пропускаем
            logger.debug("pynput: unknown button %r, skipping", button)
            return

        # Диагностика
        with self._lock:
            self._mouse_events_count += 1
            self._last_mouse_event_time = time.time()
            self._last_mouse_event = {
                "source": "pynput",
                "type": "click",
                "button": button_n,
                "pressed": pressed,
            }

        logger.debug("pynput click: button=%d, pressed=%s", button_n, pressed)

        button_key = f"mouse:{button_n}"
        self._trigger_mouse_binding(button_key, pressed)

    def _trigger_mouse_binding(self, button_key: str, pressed: bool) -> None:
        """Триггерит действия с mouse binding для данной кнопки.

        Thread-safe: copies bindings under lock, then dispatches via Qt signal.
        """
        with self._lock:
            # Snapshot matching bindings to avoid holding lock during dispatch
            matching = [
                (action, binding.get("mode", MODE_TOGGLE))
                for action, binding in self._bindings.items()
                if binding.get("type") == "mouse"
                and binding.get("button") == button_key
                and self._check_modifiers_pressed(cast(list[str], binding.get("modifiers", [])))
            ]

        for action, mode in matching:
            if mode == MODE_TOGGLE:
                if pressed:
                    with self._lock:
                        self._mouse_triggers_count += 1
                    logger.info("mouse hotkey triggered: %s (button=%s)",
                                action, button_key)
                    self._dispatcher.trigger(action, pressed=True, hold_mode=False)
            else:
                # HOLD mode
                if pressed:
                    with self._lock:
                        self._mouse_triggers_count += 1
                    logger.info("mouse HOLD start: %s (button=%s)",
                                action, button_key)
                    self._dispatcher.trigger(action, pressed=True, hold_mode=True)
                else:
                    logger.info("mouse HOLD stop: %s (button=%s)",
                                action, button_key)
                    self._dispatcher.trigger(action, pressed=False, hold_mode=True)

    def _handle_wheel_delta(self, delta: float) -> None:
        """Wheel-событие от mouse lib."""
        if not _HAS_KEYBOARD:
            return
        if delta == 0:
            return
        wheel_name = "wheel:up" if delta > 0 else "wheel:down"
        self._trigger_wheel(wheel_name)

    def _handle_wheel_event(self, dx: int, dy: int) -> None:
        """Wheel-событие от pynput."""
        if not _HAS_KEYBOARD:
            return
        wheel_name: str | None = None
        if dy > 0:
            wheel_name = "wheel:up"
        elif dy < 0:
            wheel_name = "wheel:down"
        elif dx > 0:
            wheel_name = "wheel:right"
        elif dx < 0:
            wheel_name = "wheel:left"

        if not wheel_name:
            return
        self._trigger_wheel(wheel_name)

    def _trigger_wheel(self, wheel_name: str) -> None:
        with self._lock:
            matching = [
                action for action, binding in self._bindings.items()
                if binding.get("type") == "wheel"
                and binding.get("wheel") == wheel_name
                and self._check_modifiers_pressed(cast(list[str], binding.get("modifiers", [])))
            ]

        for action in matching:
            logger.info("wheel hotkey triggered: %s (%s)", action, wheel_name)
            self._dispatcher.trigger(action, pressed=True, hold_mode=False)

    @staticmethod
    def _check_modifiers_pressed(modifiers: list[str]) -> bool:
        if not _HAS_KEYBOARD:
            return False
        if not modifiers:
            return True
        for mod in modifiers:
            mod = mod.lower()
            check_key = mod
            if mod in ("ctrl", "control"):
                check_key = "ctrl"
            elif mod in ("win", "windows"):
                check_key = "windows"
            elif mod in ("alt", "menu"):
                check_key = "alt"
            try:
                if not keyboard.is_pressed(check_key):
                    return False
            except (OSError, RuntimeError, ValueError, AttributeError):
                logger.exception("Failed to check key state")
                return False
        return True

    # ─── Управление регистрацией ──────────────────────────────────────────
    def _unregister_action(self, action: str) -> None:
        if not _HAS_KEYBOARD:
            return
        handles = self._registered.pop(action, [])
        for h in handles:
            try:
                # remove_hotkey works for add_hotkey, but on_press_key/on_release_key
                # return hook IDs that need unhook
                if hasattr(keyboard, "unhook"):
                    keyboard.unhook(h)
                elif hasattr(keyboard, "remove_hotkey"):
                    keyboard.remove_hotkey(h)
            except (KeyError, ValueError, OSError, RuntimeError, AttributeError):
                pass

    def _register_action(self, action: str, key: str, mode: str) -> tuple[bool, str | None]:
        if not _HAS_KEYBOARD:
            return False, "keyboard lib not available"
        if not key:
            return False, "empty key"
        if mode not in _VALID_MODES:
            mode = MODE_TOGGLE

        try:
            self._unregister_action(action)
            parsed = self._parse_key_string(key)

            if parsed["type"] == "sequence":
                return self._register_sequence(action, parsed["sequence"], mode)
            elif parsed["type"] == "mouse":
                return self._register_mouse(action, parsed["modifiers"],
                                             parsed["main"], mode)
            elif parsed["type"] == "wheel":
                return self._register_wheel(action, parsed["modifiers"],
                                              parsed["main"], mode)
            else:
                return self._register_keyboard(action, parsed["modifiers"],
                                                parsed["main"], mode)
        except (OSError, RuntimeError, ValueError, AttributeError, ImportError) as e:
            logger.error("Failed to register hotkey %s=%s: %s", action, key, e)
            return False, str(e)

    def _register_keyboard(self, action: str, modifiers: list[str], main: str,
                            mode: str) -> tuple[bool, str | None]:
        try:
            if mode == MODE_TOGGLE:
                # Use dispatcher for thread-safe execution on Qt main thread
                handler = lambda: self._dispatcher.trigger(action, pressed=True, hold_mode=False)
                combo = "+".join(modifiers + [main]) if modifiers else main
                h = keyboard.add_hotkey(combo, handler, suppress=False)
                self._registered[action] = [h]
            else:
                # HOLD mode - use dispatcher
                start_handler = lambda: self._dispatcher.trigger(action, pressed=True, hold_mode=True)
                stop_handler = lambda: self._dispatcher.trigger(action, pressed=False, hold_mode=True)
                combo = "+".join(modifiers + [main]) if modifiers else main
                if not modifiers:
                    h1 = keyboard.on_press_key(main, lambda e: start_handler())  # type: ignore[no-untyped-call]
                    h2 = keyboard.on_release_key(main, lambda e: stop_handler())  # type: ignore[no-untyped-call]
                    self._registered[action] = [h1, h2]
                else:
                    logger.warning("HOLD mode not supported for combinations, "
                                   "falling back to TOGGLE for %s", action)
                    handler = lambda: self._dispatcher.trigger(action, pressed=True, hold_mode=False)
                    h = keyboard.add_hotkey(combo, handler, suppress=False)
                    self._registered[action] = [h]
            return True, None
        except (OSError, RuntimeError, ValueError, AttributeError, ImportError) as e:
            return False, str(e)

    def _register_mouse(self, action: str, modifiers: list[str], button_key: str,
                         mode: str) -> tuple[bool, str | None]:
        """
        Регистрирует мышиный хоткей.

        Запускает mouse lib hook + pynput listener (если ещё не запущены).
        Binding сохраняется в self._bindings — listeners проверят его в callback.
        """
        if not _HAS_MOUSE_LIB and not _HAS_PYNPUT:
            return False, "neither mouse lib nor pynput available (pip install mouse pynput)"
        if not _HAS_KEYBOARD:
            return False, "keyboard lib not available (required for modifier check)"

        button_n = self._parse_mouse_button(button_key)
        if button_n is None:
            return False, f"Invalid mouse button format: {button_key}"
        if button_n in _IGNORED_MOUSE_BUTTONS:
            return False, f"Mouse button {button_n} (left/right) ignored — too common in UI"

        # Убеждаемся что listeners запущены
        self._ensure_mouse_hook()
        self._ensure_pynput_listener()

        try:
            with self._lock:
                self._bindings[action] = {
                    "type": "mouse",
                    "modifiers": list(modifiers),
                    "button": button_key,
                    "button_n": button_n,
                    "mode": mode,
                }
            logger.info("Registered mouse hotkey: %s = %s [%s]",
                        action, button_key, mode)
            return True, None
        except (OSError, RuntimeError, ValueError, AttributeError) as e:
            return False, str(e)

    def _register_wheel(self, action: str, modifiers: list[str], wheel_key: str,
                         mode: str) -> tuple[bool, str | None]:
        if not _HAS_PYNPUT:
            return False, "pynput not available (pip install pynput)"
        if not _HAS_KEYBOARD:
            return False, "keyboard lib not available"
        if not self._is_valid_wheel(wheel_key):
            return False, f"Invalid wheel: {wheel_key}"

        self._ensure_pynput_listener()

        try:
            with self._lock:
                self._bindings[action] = {
                    "type": "wheel",
                    "modifiers": list(modifiers),
                    "wheel": wheel_key,
                    "mode": mode,
                }
            return True, None
        except (OSError, RuntimeError, ValueError, AttributeError) as e:
            return False, str(e)

    def _register_sequence(self, action: str, keys: list[str], mode: str) -> tuple[bool, str | None]:
        if len(keys) > 3:
            return False, "Sequence too long (max 3 keys)"
        try:
            # Use dispatcher for thread-safe execution
            handler = lambda: self._dispatcher.trigger(action, pressed=True, hold_mode=False)
            combo = ",".join(keys)
            h = keyboard.add_hotkey(combo, handler, suppress=False,
                                     timeout=0.5)
            self._registered[action] = [h]
            return True, None
        except (OSError, RuntimeError, ValueError, AttributeError, ImportError) as e:
            return False, str(e)

    # ─── Публичный API ────────────────────────────────────────────────────
    def set_bindings(self, bindings: dict[str, dict[str, str]]) -> None:
        with self._lock:
            self.unregister_all()
            self._bindings = {}
            for action in HOTKEY_ACTIONS:
                b = bindings.get(action)
                if not b:
                    continue
                key = str(b.get("key", "")).strip().lower()
                mode = str(b.get("mode", MODE_TOGGLE)).upper()
                if mode not in _VALID_MODES:
                    mode = MODE_TOGGLE
                # Store as simple dict.compat with _BindingDict typing
                self._bindings[action] = cast(_BindingDict, {"key": key, "mode": mode})
                if key:
                    self._register_action(action, key, mode)

    def set_binding(self, action: str, key: str, mode: str) -> dict[str, Any]:
        if action not in HOTKEY_ACTIONS:
            return {"ok": False, "error": f"Unknown action: {action}"}
        mode = str(mode or MODE_TOGGLE).upper()
        if mode not in _VALID_MODES:
            return {"ok": False, "error": f"Invalid mode: {mode}"}
        key = str(key or "").strip().lower()

        with self._lock:
            prev_binding: dict[str, Any] = dict(self._bindings.get(action, {"key": "", "mode": "TOGGLE"}))
            self._bindings[action] = cast(_BindingDict, {"key": key, "mode": mode})
            if key:
                ok, err = self._register_action(action, key, mode)
                if not ok:
                    self._bindings[action] = cast(_BindingDict, prev_binding)
                    if prev_binding.get("key"):
                        try:
                            self._register_action(action, str(prev_binding["key"]),
                                                   str(prev_binding["mode"]))
                        except (OSError, RuntimeError, ValueError, AttributeError):
                            logger.exception("Failed to restore previous hotkey binding")
                    return {
                        "ok": False,
                        "error": err or "Failed to register hotkey",
                        "bindings": self.get_bindings(),
                    }
            else:
                self._unregister_action(action)
                if action in self._bindings:
                    self._bindings[action] = cast(_BindingDict, {"key": "", "mode": mode})
            return {"ok": True, "bindings": self.get_bindings()}

    def get_bindings(self) -> dict[str, dict[str, str]]:
        with self._lock:
            out: dict[str, dict[str, str]] = {}
            for a in HOTKEY_ACTIONS:
                b = self._bindings.get(a)
                if b and "type" in b:
                    mods = cast(list[str], b.get("modifiers", []))
                    if b.get("type") == "mouse":
                        main = b.get("button", "")
                    elif b.get("type") == "wheel":
                        main = b.get("wheel", "")
                    else:
                        main = ""
                    if mods:
                        combined = cast(list[str], mods + [main])
                        out[a] = {"key": "+".join(combined),
                                  "mode": str(b.get("mode", "TOGGLE"))}
                    else:
                        out[a] = {"key": str(main), "mode": str(b.get("mode", "TOGGLE"))}
                else:
                    # Handle the simple dict case
                    kb = str(b.get("key", "") if b else "")
                    mb = str(b.get("mode", "TOGGLE") if b else "TOGGLE")
                    out[a] = {"key": kb, "mode": mb}
            return out

    def reset_binding(self, action: str) -> dict[str, Any]:
        if action not in HOTKEY_ACTIONS:
            return {"ok": False, "error": f"Unknown action: {action}"}
        d = default_hotkeys()[action]
        return self.set_binding(action, d["key"], d["mode"])

    def reset_all(self) -> dict[str, Any]:
        self.set_bindings(default_hotkeys())
        return {"ok": True, "bindings": self.get_bindings()}

    def unregister_all(self) -> None:
        if not _HAS_KEYBOARD:
            return
        with self._lock:
            for action in list(self._registered.keys()):
                self._unregister_action(action)
            for action in list(self._bindings.keys()):
                b = self._bindings[action]
                if b.get("type") in ("mouse", "wheel"):
                    self._bindings[action] = cast(_BindingDict, {"key": "", "mode": "TOGGLE"})

    def is_available(self) -> bool:
        return _HAS_KEYBOARD

    def is_mouse_available(self) -> bool:
        return _HAS_MOUSE_LIB or _HAS_PYNPUT

    def is_wheel_available(self) -> bool:
        return _HAS_PYNPUT

    def validate_key(self, key: str, mode: str = "TOGGLE") -> dict[str, bool | str]:
        if not _HAS_KEYBOARD:
            return {"ok": False, "error": "keyboard lib not available"}
        if not key:
            return {"ok": False, "error": "empty key"}
        key = str(key).strip().lower()
        mode = str(mode or "TOGGLE").upper()

        parsed: _ParsedKey = self._parse_key_string(key)

        if parsed["type"] == "sequence":
            seq = parsed["sequence"]
            if not isinstance(seq, list):
                return {"ok": False, "error": "Invalid sequence format"}
            if len(seq) > 3:
                return {"ok": False, "error": "Sequence too long (max 3 keys)"}
            if len(seq) < 2:
                return {"ok": False, "error": "Sequence must have at least 2 keys"}
            for k in seq:
                sub_parsed: _ParsedKey = self._parse_key_string(k)
                if sub_parsed["type"] == "mouse":
                    if not (_HAS_MOUSE_LIB or _HAS_PYNPUT):
                        return {"ok": False, "error": f"mouse libs not available for '{k}'"}
                    n = self._parse_mouse_button(sub_parsed["main"])
                    if n is None or n in _IGNORED_MOUSE_BUTTONS:
                        return {"ok": False, "error": f"Invalid mouse button '{k}'"}
                elif sub_parsed["type"] == "wheel":
                    if not _HAS_PYNPUT:
                        return {"ok": False, "error": f"pynput not available for '{k}'"}
                    if not self._is_valid_wheel(sub_parsed["main"]):
                        return {"ok": False, "error": f"Invalid wheel '{k}'"}
                else:
                    try:
                        if hasattr(keyboard, "parse_hotkey"):
                            keyboard.parse_hotkey(k)
                    except ValueError as e:
                        return {"ok": False, "error": f"Invalid key '{k}': {e}"}
                    except (OSError, RuntimeError, AttributeError) as e:
                        return {"ok": False, "error": f"Invalid key '{k}': {e}"}
            return {"ok": True, "type": "sequence"}

        if parsed["type"] == "mouse":
            if not (_HAS_MOUSE_LIB or _HAS_PYNPUT):
                return {"ok": False, "error": "mouse libs not available (pip install mouse pynput)"}
            for mod in parsed["modifiers"]:
                if mod not in MODIFIER_NAMES:
                    return {"ok": False, "error": f"Unknown modifier: {mod}"}
            n = self._parse_mouse_button(parsed["main"])
            if n is None:
                return {"ok": False, "error": f"Invalid mouse button: {parsed['main']}"}
            if n in _IGNORED_MOUSE_BUTTONS:
                return {"ok": False, "error": f"Mouse button {n} (left/right) ignored — too common in UI"}
            return {"ok": True, "type": "mouse"}

        if parsed["type"] == "wheel":
            if not _HAS_PYNPUT:
                return {"ok": False, "error": "pynput not available for wheel (pip install pynput)"}
            for mod in parsed["modifiers"]:
                if mod not in MODIFIER_NAMES:
                    return {"ok": False, "error": f"Unknown modifier: {mod}"}
            if not self._is_valid_wheel(parsed["main"]):
                return {"ok": False, "error": f"Invalid wheel: {parsed['main']}"}
            return {"ok": True, "type": "wheel"}

        try:
            if hasattr(keyboard, "parse_hotkey"):
                keyboard.parse_hotkey(key)
                return {"ok": True, "type": "keyboard"}
            return {"ok": True, "type": "keyboard"}
        except ValueError as e:
            return {"ok": False, "error": str(e)}
        except (OSError, RuntimeError, AttributeError) as e:
            return {"ok": False, "error": str(e)}

    # ─── Диагностика ──────────────────────────────────────────────────────
    def debug_status(self) -> dict[str, Any]:
        """Возвращает диагностическую информацию о состоянии hotkey service."""
        with self._lock:
            mouse_bindings: list[dict[str, Any]] = []
            for action, b in self._bindings.items():
                if b.get("type") == "mouse":
                    mouse_bindings.append({
                        "action": action,
                        "button": b.get("button"),
                        "button_n": b.get("button_n"),
                        "modifiers": b.get("modifiers", []),
                        "mode": b.get("mode"),
                    })

            return {
                "keyboard_lib": _HAS_KEYBOARD,
                "mouse_lib": _HAS_MOUSE_LIB,
                "pynput": _HAS_PYNPUT,
                "mouse_hook_started": self._mouse_hook_started,
                "mouse_hook_error": self._mouse_hook_last_error,
                "pynput_started": self._pynput_started,
                "mouse_events_count": self._mouse_events_count,
                "mouse_triggers_count": self._mouse_triggers_count,
                "last_mouse_event": self._last_mouse_event,
                "last_mouse_event_age_s": round(time.time() - self._last_mouse_event_time, 2)
                                          if self._last_mouse_event_time else None,
                "mouse_bindings": mouse_bindings,
                "all_bindings": self.get_bindings(),
            }

    def debug_test_mouse_listener(self) -> dict[str, int | dict[str, Any] | None]:
        """
        Тест: ожидает 3 секунды, считает mouse events.
        Пользователь должен кликать/скроллить в это время.
        Возвращает сколько событий пришло.
        """
        with self._lock:
            events_before = self._mouse_events_count
        time.sleep(3.0)
        with self._lock:
            events_after = self._mouse_events_count
            last_event = self._last_mouse_event
        return {
            "events_before": events_before,
            "events_after": events_after,
            "events_during_test": events_after - events_before,
            "last_event": last_event,
        }

    def debug_dispatcher_status(self) -> dict[str, bool]:
        """Get debug status of the hotkey dispatcher."""
        return {
            "dispatcher_connected": self._dispatcher is not None,
            "handler_set": self._dispatcher._handler is not None if self._dispatcher else False,
        }

    def debug_dispatcher_thread(self) -> dict[str, Any]:
        """Get debug info about hotkey dispatcher thread."""
        return self.debug_dispatcher_status()

    def shutdown(self) -> None:
        """Clean up all hooks and listeners. Thread-safe."""
        with self._lock:
            # Unregister all keyboard hotkeys
            self.unregister_all()

            # Stop mouse lib hook
            if self._mouse_hook_started and _HAS_MOUSE_LIB:
                try:
                    if self._mouse_hook:
                        mouse_lib.unhook(self._mouse_hook)
                        self._mouse_hook = None
                    self._mouse_hook_started = False
                    logger.info("mouse lib hook stopped")
                except (OSError, RuntimeError, AttributeError) as e:
                    logger.warning("Failed to stop mouse hook: %s", e)

            # Stop pynput listener
            if self._pynput_started and _HAS_PYNPUT:
                try:
                    if self._pynput_listener:
                        self._pynput_listener.stop()
                        self._pynput_listener = None
                    self._pynput_started = False
                    logger.info("pynput listener stopped")
                except (OSError, RuntimeError, AttributeError) as e:
                    logger.warning("Failed to stop pynput listener: %s", e)


# ─── Helper functions ───────────────────────────────────────────────────────


def default_hotkeys() -> dict[str, dict[str, str]]:
    return {
        "clicker_toggle":  {"key": "f6",         "mode": "TOGGLE"},
        "aim_toggle":      {"key": "f9",         "mode": "TOGGLE"},
        "macro_start":     {"key": "right ctrl", "mode": "TOGGLE"},
        "macro_stop":      {"key": "enter",      "mode": "TOGGLE"},
        "recorder_start":  {"key": "f7",         "mode": "TOGGLE"},
        "recorder_stop":   {"key": "f8",         "mode": "TOGGLE"},
        "app_show":        {"key": "f10",        "mode": "TOGGLE"},
        "panic_stop":      {"key": "f12",        "mode": "TOGGLE"},
    }


# For typing cast
