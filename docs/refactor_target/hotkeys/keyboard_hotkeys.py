"""app/backend/services/hotkeys/keyboard_hotkeys.py — Менеджер keyboard bindings.

Перенесено из hotkey_service.py:
- _ensure_pynput_listener (строки 434–465)
- _register_keyboard (строки 679–706)
- _register_sequence (строки 768–782)
- _check_modifiers_pressed (строки 612–633)
"""

from __future__ import annotations

import importlib.util
import logging
from collections.abc import Callable

from app.backend.services.hotkeys.validators import KeyValidator

logger = logging.getLogger(__name__)


class KeyboardHotkeyManager:
    """Управляет регистрацией keyboard hotkeys через pynput.keyboard."""

    def __init__(self, dispatcher):
        self._dispatcher = dispatcher
        self._listener = None
        self._registered: dict[str, dict] = (
            {}
        )  # action → {modifiers, main, mode, callback}
        self._available = False
        self._check_pynput()

    def _check_pynput(self):
        """Проверяет доступность pynput.keyboard."""
        spec = importlib.util.find_spec("pynput.keyboard")
        if spec is not None:
            self._available = True
        else:
            self._available = False
            logger.warning("pynput.keyboard not available")

    def is_available(self) -> bool:
        return self._available

    def register(
        self, action: str, key: str, mode: str, on_press: Callable, on_release: Callable
    ) -> tuple[bool, str | None]:
        """Регистрирует keyboard binding для action.

        Returns: (success, error_message)
        """
        if not self._available:
            return False, "pynput.keyboard not available"

        parsed = KeyValidator.parse_key_string(key)
        if parsed["type"] not in ("keyboard", "invalid"):
            # Это не keyboard binding — пропускаем
            return True, None
        if parsed["type"] == "invalid":
            return False, f"Invalid key: {key}"

        # Если есть modifiers — это combo
        if parsed["modifiers"]:
            return self._register_combo(action, parsed, mode, on_press, on_release)
        else:
            return self._register_single(action, parsed, mode, on_press, on_release)

    def _register_single(self, action, parsed, mode, on_press, on_release):
        """Регистрирует single key (без modifiers)."""
        try:
            # TODO: полная реализация с GlobalHotKeys или Listener
            self._registered[action] = {
                "parsed": parsed,
                "mode": mode,
                "on_press": on_press,
                "on_release": on_release,
            }
            self._ensure_listener()
            return True, None
        except Exception as e:
            return False, str(e)

    def _register_combo(self, action, parsed, mode, on_press, on_release):
        """Регистрирует combo (с modifiers)."""
        try:
            # TODO: использовать keyboard.GlobalHotKeys
            self._registered[action] = {
                "parsed": parsed,
                "mode": mode,
                "on_press": on_press,
                "on_release": on_release,
            }
            self._ensure_listener()
            return True, None
        except Exception as e:
            return False, str(e)

    def unregister(self, action: str):
        """Удаляет регистрацию binding."""
        if action in self._registered:
            del self._registered[action]

    def unregister_all(self):
        """Удаляет все регистрации."""
        self._registered.clear()
        if self._listener:
            try:
                self._listener.stop()
            except Exception:
                pass
            self._listener = None

    def _ensure_listener(self):
        """Создаёт pynput listener если ещё не создан."""
        if self._listener is not None:
            return
        try:
            from pynput import keyboard

            def on_press(key):
                # TODO: проверить _registered, сопоставить с modifiers state
                pass

            def on_release(key):
                # TODO: аналогично
                pass

            self._listener = keyboard.Listener(on_press=on_press, on_release=on_release)
            self._listener.daemon = True
            self._listener.start()
        except Exception as e:
            logger.exception("Failed to start keyboard listener: %s", e)

    @staticmethod
    def check_modifiers_pressed(modifiers: list) -> bool:
        """Проверяет, нажаты ли все указанные modifiers прямо сейчас."""
        if not modifiers:
            return True
        try:
            import ctypes

            user32 = ctypes.windll.user32
            MOD_MAP = {
                "ctrl": 0x0011,
                "alt": 0x0012,
                "shift": 0x0010,
                "win": 0x005B,
            }
            for mod in modifiers:
                vk = MOD_MAP.get(mod.strip().lower())
                if vk and not user32.GetAsyncKeyState(vk) & 0x8000:
                    return False
            return True
        except Exception:
            return False
