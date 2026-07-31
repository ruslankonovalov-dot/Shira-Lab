"""app/backend/services/hotkeys/bindings.py — Хранилище bindings.

CRUD операции над bindings: set, get, reset, list.
Перенесено из hotkey_service.py методы set_bindings, set_binding,
get_bindings, reset_binding, reset_all, unregister_all.
"""
from __future__ import annotations

import threading
from typing import Any

from app.backend.services.hotkeys.dispatcher import default_hotkeys


class BindingStore:
    """Потокобезопасное хранилище bindings.

    Каждый binding: {action: {"key": str, "mode": str}}
    """

    def __init__(self):
        self._bindings: dict[str, dict[str, str]] = {}
        self._lock = threading.RLock()

    def get_all(self) -> dict[str, dict[str, str]]:
        """Возвращает копию всех bindings."""
        with self._lock:
            return {k: dict(v) for k, v in self._bindings.items()}

    def get(self, action: str) -> dict[str, str] | None:
        with self._lock:
            b = self._bindings.get(action)
            return dict(b) if b else None

    def set(self, action: str, key: str, mode: str) -> dict:
        """Устанавливает binding. Возвращает результат операции."""
        with self._lock:
            self._bindings[action] = {"key": key.lower().strip(), "mode": mode.upper()}
            return {"ok": True, "action": action, "binding": self._bindings[action]}

    def set_all(self, bindings: dict[str, dict[str, str]]):
        """Массовая установка bindings (из profile)."""
        with self._lock:
            self._bindings.clear()
            for action, b in bindings.items():
                self._bindings[action] = {
                    "key": str(b.get("key", "")).lower().strip(),
                    "mode": str(b.get("mode", "TOGGLE")).upper(),
                }

    def reset(self, action: str) -> dict:
        """Сбрасывает конкретный binding к дефолту."""
        defaults = default_hotkeys()
        if action not in defaults:
            return {"ok": False, "error": f"Unknown action: {action}"}
        with self._lock:
            self._bindings[action] = dict(defaults[action])
            return {"ok": True, "binding": self._bindings[action]}

    def reset_all(self) -> dict:
        """Сбрасывает все bindings к дефолтам."""
        with self._lock:
            self._bindings = default_hotkeys()
            return {"ok": True, "bindings": dict(self._bindings)}

    def remove(self, action: str) -> dict:
        """Удаляет binding (делает клавишу неактивной)."""
        with self._lock:
            if action in self._bindings:
                del self._bindings[action]
                return {"ok": True}
            return {"ok": False, "error": "Action not found"}

    def clear(self):
        """Полная очистка bindings."""
        with self._lock:
            self._bindings.clear()

    def has(self, action: str) -> bool:
        with self._lock:
            return action in self._bindings
