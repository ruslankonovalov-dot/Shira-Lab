"""app/backend/services/hotkeys/__init__.py — Пакет модулей горячих клавиш.

Результат рефакторинга God Object `hotkey_service.py` (1031 LOC).

Архитектура:
    HotkeyService (главный фасад)
      ↑ использует
      ├── HotkeyDispatcher   (QObject, dispatches actions → handlers)
      ├── BindingStore       (CRUD для bindings: set/get/reset)
      ├── KeyValidator       (validate_key, parse_key_string, _is_modifier, ...)
      ├── KeyboardHotkeys    (register/unregister keyboard bindings)
      ├── MouseHotkeys       (hooks for click + wheel events)
      └── ActionHandlers     (_action_handler, _action_start_handler, ...)

Каждый модуль ≤ 250 LOC. HotkeyService делегирует вызовы.
"""
from __future__ import annotations

from app.backend.services.hotkeys.dispatcher import HotkeyDispatcher, default_hotkeys
from app.backend.services.hotkeys.bindings import BindingStore
from app.backend.services.hotkeys.validators import KeyValidator
from app.backend.services.hotkeys.keyboard_hotkeys import KeyboardHotkeyManager
from app.backend.services.hotkeys.mouse_hotkeys import MouseHotkeyManager
from app.backend.services.hotkeys.handlers import ActionHandlers
from app.backend.services.hotkeys.service import HotkeyService

__all__ = [
    "HotkeyService",
    "HotkeyDispatcher",
    "default_hotkeys",
    "BindingStore",
    "KeyValidator",
    "KeyboardHotkeyManager",
    "MouseHotkeyManager",
    "ActionHandlers",
]
