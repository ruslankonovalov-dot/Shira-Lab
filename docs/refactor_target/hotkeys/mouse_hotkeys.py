"""app/backend/services/hotkeys/mouse_hotkeys.py — Менеджер mouse + wheel bindings.

Перенесено из hotkey_service.py:
- _ensure_mouse_hook (строки 408–432)
- _handle_mouse_event_safe (строки 467–501)
- _handle_pynput_click (строки 502–534)
- _trigger_mouse_binding (строки 535–570)
- _handle_wheel_delta (строки 571–579)
- _handle_wheel_event (строки 580–597)
- _trigger_wheel (строки 598–611)
- _register_mouse (строки 707–744)
- _register_wheel (строки 745–767)
"""

from __future__ import annotations

import importlib.util
import logging
import time
from collections.abc import Callable

from app.backend.services.hotkeys.validators import KeyValidator

logger = logging.getLogger(__name__)


class MouseHotkeyManager:
    """Управляет mouse click + wheel hotkeys."""

    def __init__(self, dispatcher):
        self._dispatcher = dispatcher
        self._mouse_listener = None
        self._mouse_hook = None
        self._mouse_bindings: dict[
            str, dict
        ] = {}  # button_key → {action, mode, on_press, on_release}
        self._wheel_bindings: dict[str, dict] = {}  # wheel_name → {action, mode}
        self._wheel_cooldown: dict[str, float] = {}  # wheel_name → last_trigger_time
        self._wheel_cooldown_sec = 0.15  # защита от дребезга

        self._mouse_available = False
        self._wheel_available = False
        self._check_pynput()

    def _check_pynput(self):
        spec = importlib.util.find_spec("pynput.mouse")
        if spec is not None:
            self._mouse_available = True
            self._wheel_available = True
        else:
            logger.warning("pynput.mouse not available")

    def is_mouse_available(self) -> bool:
        return self._mouse_available

    def is_wheel_available(self) -> bool:
        return self._wheel_available

    # ─── Mouse button registration ──────────────────────────────
    def register_mouse(
        self, action: str, key: str, mode: str, on_press: Callable, on_release: Callable
    ) -> tuple[bool, str | None]:
        """Регистрирует mouse button binding."""
        if not self._mouse_available:
            return False, "pynput.mouse not available"

        parsed = KeyValidator.parse_key_string(key)
        if parsed["type"] != "mouse":
            return True, None  # это не mouse binding — пропускаем

        button_key = parsed["main"]
        self._mouse_bindings[button_key] = {
            "action": action,
            "mode": mode,
            "on_press": on_press,
            "on_release": on_release,
            "modifiers": parsed["modifiers"],
        }
        self._ensure_mouse_listener()
        return True, None

    def register_wheel(
        self, action: str, key: str, mode: str, on_trigger: Callable
    ) -> tuple[bool, str | None]:
        """Регистрирует wheel binding."""
        if not self._wheel_available:
            return False, "pynput.mouse wheel not available"

        parsed = KeyValidator.parse_key_string(key)
        if parsed["type"] != "wheel":
            return True, None

        wheel_name = parsed["main"]
        self._wheel_bindings[wheel_name] = {
            "action": action,
            "mode": mode,
            "on_trigger": on_trigger,
            "modifiers": parsed["modifiers"],
        }
        self._ensure_mouse_listener()
        return True, None

    def unregister(self, action: str):
        """Удаляет все mouse/wheel bindings для action."""
        for btn_key in list(self._mouse_bindings):
            if self._mouse_bindings[btn_key]["action"] == action:
                del self._mouse_bindings[btn_key]
        for wheel in list(self._wheel_bindings):
            if self._wheel_bindings[wheel]["action"] == action:
                del self._wheel_bindings[wheel]

    def unregister_all(self):
        self._mouse_bindings.clear()
        self._wheel_bindings.clear()
        if self._mouse_listener:
            try:
                self._mouse_listener.stop()
            except Exception:
                pass
            self._mouse_listener = None

    # ─── Listener lifecycle ─────────────────────────────────────
    def _ensure_mouse_listener(self):
        """Создаёт pynput.mouse listener."""
        if self._mouse_listener is not None:
            return
        try:
            from pynput import mouse

            def on_click(_x, _y, button, pressed):
                self._handle_click(button, pressed)

            def on_scroll(_x, _y, dx, dy):
                self._handle_scroll(dx, dy)

            self._mouse_listener = mouse.Listener(
                on_click=on_click, on_scroll=on_scroll
            )
            self._mouse_listener.daemon = True
            self._mouse_listener.start()
        except Exception as e:
            logger.exception("Failed to start mouse listener: %s", e)

    # ─── Event handlers ──────────────────────────────────────────
    def _handle_click(self, button, pressed: bool):
        """Обрабатывает click event от pynput."""
        from pynput.mouse import Button

        button_map = {
            Button.left: "left",
            Button.right: "right",
            Button.middle: "middle",
            Button.x1: "mouse4",
            Button.x2: "mouse5",
        }
        button_key = button_map.get(button)
        if not button_key:
            return

        binding = self._mouse_bindings.get(button_key)
        if not binding:
            return

        # Проверяем modifiers
        from app.backend.services.hotkeys.keyboard_hotkeys import KeyboardHotkeyManager

        if not KeyboardHotkeyManager.check_modifiers_pressed(
            binding.get("modifiers", [])
        ):
            return

        mode = binding["mode"]
        if mode == "TOGGLE" and pressed:
            binding["on_press"]()
        elif mode == "HOLD":
            (binding["on_press"] if pressed else binding["on_release"])()

    def _handle_scroll(self, dx: int, dy: int):
        """Обрабатывает scroll event."""
        now = time.time()
        if dy > 0:
            self._trigger_wheel("wheel_up", now)
        elif dy < 0:
            self._trigger_wheel("wheel_down", now)
        if dx > 0:
            self._trigger_wheel("wheel_right", now)
        elif dx < 0:
            self._trigger_wheel("wheel_left", now)

    def _trigger_wheel(self, wheel_name: str, now: float):
        """Вызывает wheel binding с защитой от дребезга."""
        binding = self._wheel_bindings.get(wheel_name)
        if not binding:
            return

        # Cooldown
        last = self._wheel_cooldown.get(wheel_name, 0)
        if now - last < self._wheel_cooldown_sec:
            return
        self._wheel_cooldown[wheel_name] = now

        # Modifiers check
        from app.backend.services.hotkeys.keyboard_hotkeys import KeyboardHotkeyManager

        if not KeyboardHotkeyManager.check_modifiers_pressed(
            binding.get("modifiers", [])
        ):
            return

        binding["on_trigger"]()
