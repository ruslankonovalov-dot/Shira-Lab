"""app/backend/services/hotkeys/validators.py — Валидаторы клавиш.

Перенесено из hotkey_service.py:
- _parse_key_string (строки 337–368)
- _is_modifier (строки 369–371)
- _parse_mouse_button (строки 373–384)
- _is_valid_wheel (строки 386–388)
- _normalize_button_n (строки 390–401)
- validate_key (строки 884–955)
"""
from __future__ import annotations

import re
from typing import Any


class KeyValidator:
    """Валидация и парсинг строк клавиш: 'ctrl+shift+a', 'mouse4', 'wheel_up'."""

    MODIFIERS = {"ctrl", "alt", "shift", "win", "cmd"}
    MOUSE_BUTTONS = {"left", "right", "middle", "mouse4", "mouse5", "x1", "x2"}
    WHEEL_EVENTS = {"wheel_up", "wheel_down", "wheel_left", "wheel_right"}

    @staticmethod
    def parse_key_string(key: str) -> dict:
        """Парсит строку вида 'ctrl+shift+a' → {modifiers, main, type}.

        Returns:
            {
                "modifiers": ["ctrl", "shift"],
                "main": "a",
                "type": "keyboard" | "mouse" | "wheel" | "sequence",
                "raw": "ctrl+shift+a"
            }
        """
        if not key or not isinstance(key, str):
            return {"modifiers": [], "main": "", "type": "invalid", "raw": ""}

        key = key.strip().lower()
        parts = [p.strip() for p in re.split(r"\+", key) if p.strip()]
        if not parts:
            return {"modifiers": [], "main": "", "type": "invalid", "raw": key}

        # Последний — main, остальные — modifiers
        main = parts[-1]
        modifiers = [p for p in parts[:-1] if p]

        # Определяем тип
        if main in KeyValidator.MOUSE_BUTTONS:
            key_type = "mouse"
        elif main in KeyValidator.WHEEL_EVENTS:
            key_type = "wheel"
        elif len(parts) > 1 and main not in KeyValidator.MODIFIERS:
            key_type = "keyboard"
        elif len(parts) == 1 and main in KeyValidator.MODIFIERS:
            # Только модификатор — невалидно как single key
            key_type = "invalid"
        else:
            key_type = "keyboard"

        return {
            "modifiers": modifiers,
            "main": main,
            "type": key_type,
            "raw": key,
        }

    @staticmethod
    def is_modifier(key: str) -> bool:
        return key.strip().lower() in KeyValidator.MODIFIERS

    @staticmethod
    def parse_mouse_button(main: str) -> int | None:
        """Конвертирует имя кнопки в button_n для pynput (1=left, 2=right, 3=middle)."""
        mapping = {
            "left": 1, "right": 2, "middle": 3,
            "mouse4": 4, "mouse5": 5, "x1": 4, "x2": 5,
        }
        return mapping.get(main.strip().lower())

    @staticmethod
    def is_valid_wheel(main: str) -> bool:
        return main.strip().lower() in KeyValidator.WHEEL_EVENTS

    @staticmethod
    def normalize_button_n(button_n) -> int | None:
        """Нормализует button_n в человекочитаемое имя."""
        try:
            n = int(button_n)
            mapping = {1: "left", 2: "right", 3: "middle", 4: "mouse4", 5: "mouse5"}
            return mapping.get(n)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def validate_key(key: str, mode: str = "TOGGLE") -> dict:
        """Полная валидация клавиши для заданного режима.

        Returns:
            {"ok": True} или {"ok": False, "error": "..."}
        """
        if not key or not key.strip():
            return {"ok": False, "error": "Empty key"}

        key = key.strip().lower()
        mode = (mode or "TOGGLE").upper()
        if mode not in ("TOGGLE", "HOLD"):
            return {"ok": False, "error": f"Invalid mode: {mode}"}

        parsed = KeyValidator.parse_key_string(key)
        if parsed["type"] == "invalid":
            return {"ok": False, "error": f"Invalid key format: {key}"}

        # Дополнительная проверка: нельзя назначить только модификатор
        if parsed["main"] in KeyValidator.MODIFIERS and not parsed["modifiers"]:
            return {"ok": False, "error": "Modifier alone is not a valid key"}

        return {"ok": True, "parsed": parsed}
