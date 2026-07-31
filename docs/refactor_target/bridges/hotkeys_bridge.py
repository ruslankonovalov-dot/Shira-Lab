"""app/backend/bridges/hotkeys_bridge.py — Hotkey-методы моста QML.

Перенесено из qml_bridge.py, секция "Hotkeys" (строки 1229–1288).
"""
from __future__ import annotations

import json

from app.backend.bridges.bridge_base import BridgeBase
from PySide6.QtCore import Slot

from app.backend.services.hotkey_service import default_hotkeys


class HotkeysBridge(BridgeBase):
    """Методы горячих клавиш: getHotkeys, setHotkey, resetHotkey, ..."""

    @Slot(result=str)
    def getHotkeys(self):
        return json.dumps({
            "available": self.hotkeys.is_available(),
            "mouse_available": self.hotkeys.is_mouse_available(),
            "wheel_available": self.hotkeys.is_wheel_available(),
            "bindings": self.hotkeys.get_bindings(),
        })

    @Slot(str, str, str, result=str)
    def setHotkey(self, action, key, mode):
        if key:
            v = self.hotkeys.validate_key(key, mode)
            if not v.get("ok"):
                return json.dumps({"ok": False, "error": v.get("error", "Invalid key")})
        result = self.hotkeys.set_binding(action, key, mode)
        if result.get("ok"):
            self.state.hotkeys[action] = {
                "key": str(key or "").strip().lower(),
                "mode": str(mode or "TOGGLE").upper()
            }
            self._schedule_save()
            self.hotkeysChanged.emit()
        return json.dumps(result)

    @Slot(str, result=str)
    def resetHotkey(self, action):
        result = self.hotkeys.reset_binding(action)
        if result.get("ok"):
            defaults = default_hotkeys()
            if action in defaults:
                self.state.hotkeys[action] = dict(defaults[action])
                self._schedule_save()
                self.hotkeysChanged.emit()
        return json.dumps(result)

    @Slot(result=str)
    def resetAllHotkeys(self):
        result = self.hotkeys.reset_all()
        if result.get("ok"):
            self.state.hotkeys = default_hotkeys()
            self._schedule_save()
            self.hotkeysChanged.emit()
        return json.dumps(result)

    @Slot(result=str)
    def hotkeysDebugStatus(self):
        return json.dumps(self.hotkeys.debug_status())

    @Slot(result=str)
    def hotkeysDebugTestMouse(self):
        return json.dumps(self.hotkeys.debug_test_mouse_listener())
