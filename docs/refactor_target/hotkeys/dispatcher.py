"""app/backend/services/hotkeys/dispatcher.py — Диспетчер действий.

Перенесено из hotkey_service.py, класс HotkeyDispatcher (строки 43–75)
+ функция default_hotkeys (строки 77–112).
"""
from __future__ import annotations

from typing import Callable, Any

from PySide6.QtCore import QObject, Signal


class HotkeyDispatcher(QObject):
    """Диспетчер: принимает события от keyboard/mouse managers и
    вызывает соответствующие action handlers.

    Сигналы:
        actionTriggered(action, pressed, hold_mode) — emitted при срабатывании
    """

    actionTriggered = Signal(str, bool, bool)

    def __init__(self, parent: QObject | None = None):
        super().__init__(parent)
        self._handler: Callable[[str, bool, bool], None] | None = None

    def set_handler(self, handler: Callable[[str, bool, bool], None]):
        """Устанавливает функцию-обработчик действий."""
        self._handler = handler

    def trigger(self, action: str, pressed: bool, hold_mode: bool = False):
        """Вызывается keyboard/mouse manager при срабатывании горячей клавиши."""
        if self._handler is not None:
            try:
                self._handler(action, pressed, hold_mode)
            except Exception:
                pass  # логируем в HotkeyService
        self.actionTriggered.emit(action, pressed, hold_mode)


def default_hotkeys() -> dict[str, dict[str, str]]:
    """Возвращает дефолтный набор горячих клавиш.

    Используется при первом запуске и при reset_all.
    """
    return {
        "clicker_toggle":   {"key": "f6",              "mode": "TOGGLE"},
        "aim_toggle":       {"key": "f7",              "mode": "TOGGLE"},
        "macro_start":      {"key": "f8",              "mode": "HOLD"},
        "macro_stop":       {"key": "f9",              "mode": "TOGGLE"},
        "recorder_start":   {"key": "f10",             "mode": "TOGGLE"},
        "recorder_stop":    {"key": "ctrl+shift+f10",  "mode": "TOGGLE"},
        "app_show":         {"key": "ctrl+shift+s",    "mode": "TOGGLE"},
        "panic_stop":       {"key": "ctrl+shift+p",    "mode": "TOGGLE"},
    }
