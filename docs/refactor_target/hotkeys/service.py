"""app/backend/services/hotkeys/service.py — Главный фасад HotkeyService.

Тонкий фасад, делегирующий вызовы менеджерам.
Заменяет монолитный hotkey_service.py (1031 LOC).

Все @Slot-совместимые методы сохраняют сигнатуры для QML:
    set_bindings, set_binding, get_bindings, reset_binding, reset_all,
    unregister_all, is_available, is_mouse_available, is_wheel_available,
    validate_key, debug_status, debug_test_mouse_listener, shutdown
"""

from __future__ import annotations

import logging
from typing import Any

from app.backend.services.hotkeys.bindings import BindingStore
from app.backend.services.hotkeys.dispatcher import HotkeyDispatcher, default_hotkeys
from app.backend.services.hotkeys.handlers import ActionHandlers
from app.backend.services.hotkeys.keyboard_hotkeys import KeyboardHotkeyManager
from app.backend.services.hotkeys.mouse_hotkeys import MouseHotkeyManager
from app.backend.services.hotkeys.validators import KeyValidator

logger = logging.getLogger(__name__)


class HotkeyService:
    """Фасад для всех операций с горячими клавишами.

    Делегирует работу специализированным менеджерам:
        - BindingStore       — хранение bindings
        - KeyValidator       — валидация
        - KeyboardHotkeys    — keyboard bindings
        - MouseHotkeys       — mouse + wheel bindings
        - ActionHandlers     — обработчики действий
        - HotkeyDispatcher   — диспетчер событий
    """

    def __init__(self, api: Any):
        self._api = api

        # Инициализация компонентов
        self._dispatcher = HotkeyDispatcher()
        self._bindings = BindingStore()
        self._keyboard = KeyboardHotkeyManager(self._dispatcher)
        self._mouse = MouseHotkeyManager(self._dispatcher)
        self._handlers = ActionHandlers(api)

        # Устанавливаем dispatcher handler
        self._dispatcher.set_handler(self._on_action_dispatched)

        # Инициализируем дефолтные bindings
        self._bindings.set_all(default_hotkeys())

    def _on_action_dispatched(self, action: str, pressed: bool, hold_mode: bool):
        """Callback от dispatcher при срабатывании горячей клавиши."""
        try:
            if hold_mode:
                handler = (
                    self._handlers.get_start_handler if pressed else self._handlers.get_stop_handler
                )
            else:
                handler = self._handlers.get_handler
            handler(action)()
        except Exception:
            logger.exception("Action handler failed: action=%s pressed=%s", action, pressed)

    # ─── Bindings API ────────────────────────────────────────────
    def set_bindings(self, bindings: dict[str, dict[str, str]]) -> None:
        """Массовая установка bindings (из profile)."""
        self.unregister_all()
        self._bindings.set_all(bindings)
        self._register_all()

    def set_binding(self, action: str, key: str, mode: str) -> dict:
        """Устанавливает binding для action."""
        v = self._bindings.set(action, key, mode)
        if v.get("ok"):
            self._register_action(action, key, mode)
        return v

    def get_bindings(self) -> dict[str, dict[str, str]]:
        return self._bindings.get_all()

    def reset_binding(self, action: str) -> dict:
        result = self._bindings.reset(action)
        if result.get("ok"):
            b = result["binding"]
            self._register_action(action, b["key"], b["mode"])
        return result

    def reset_all(self) -> dict:
        result = self._bindings.reset_all()
        if result.get("ok"):
            self.unregister_all()
            self._register_all()
        return result

    def unregister_all(self) -> None:
        self._keyboard.unregister_all()
        self._mouse.unregister_all()

    def _register_all(self):
        """Регистрирует все bindings из store в keyboard/mouse managers."""
        for action, b in self._bindings.get_all().items():
            self._register_action(action, b["key"], b["mode"])

    def _register_action(self, action: str, key: str, mode: str):
        """Регистрирует один binding в соответствующем менеджере."""
        if not key:
            return
        parsed = KeyValidator.parse_key_string(key)
        on_press = (
            self._handlers.get_start_handler(action)
            if mode == "HOLD"
            else self._handlers.get_handler(action)
        )
        on_release = self._handlers.get_stop_handler(action) if mode == "HOLD" else lambda: None

        if parsed["type"] == "keyboard":
            ok, err = self._keyboard.register(action, key, mode, on_press, on_release)
            if not ok and err:
                logger.warning("Keyboard register failed for %s: %s", action, err)
        elif parsed["type"] == "mouse":
            ok, err = self._mouse.register_mouse(action, key, mode, on_press, on_release)
            if not ok and err:
                logger.warning("Mouse register failed for %s: %s", action, err)
        elif parsed["type"] == "wheel":
            ok, err = self._mouse.register_wheel(action, key, mode, on_press)
            if not ok and err:
                logger.warning("Wheel register failed for %s: %s", action, err)

    # ─── Status API ──────────────────────────────────────────────
    def is_available(self) -> bool:
        return self._keyboard.is_available()

    def is_mouse_available(self) -> bool:
        return self._mouse.is_mouse_available()

    def is_wheel_available(self) -> bool:
        return self._mouse.is_wheel_available()

    def validate_key(self, key: str, mode: str = "TOGGLE") -> dict:
        return KeyValidator.validate_key(key, mode)

    def debug_status(self) -> dict:
        """Возвращает детальный статус для отладки."""
        return {
            "keyboard_available": self._keyboard.is_available(),
            "mouse_available": self._mouse.is_mouse_available(),
            "wheel_available": self._mouse.is_wheel_available(),
            "bindings_count": len(self._bindings.get_all()),
            "bindings": self._bindings.get_all(),
        }

    def debug_test_mouse_listener(self) -> dict:
        """Тестирует mouse listener (для Diagnostics)."""
        try:
            return {
                "ok": True,
                "mouse_listener_active": self._mouse._mouse_listener is not None,
                "mouse_bindings_count": len(self._mouse._mouse_bindings),
                "wheel_bindings_count": len(self._mouse._wheel_bindings),
            }
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def shutdown(self) -> None:
        """Корректное завершение работы (вызывается при выходе из приложения)."""
        try:
            self.unregister_all()
        except Exception:
            logger.exception("HotkeyService shutdown failed")
