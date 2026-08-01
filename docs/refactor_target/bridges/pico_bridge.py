"""app/backend/bridges/pico_bridge.py — Pico HID-методы моста QML.

Перенесено из qml_bridge.py, секция "Pico" (строки 1636–1915).
"""

from __future__ import annotations

import json

from PySide6.QtCore import Slot

from app.backend.bridges.bridge_base import BridgeBase


class PicoBridge(BridgeBase):
    """Методы Pico HID устройства: getPicoStatus, picoSendKey, picoSendMouse, ..."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._pico = None

    @property
    def pico(self):
        if self._pico is None:
            try:
                from app.backend.services.pico_service import PicoService

                self._pico = PicoService()
            except Exception:
                return None
        return self._pico

    @Slot(result=str)
    def getPicoStatus(self):
        if not self.pico:
            return json.dumps({"ok": False, "error": "Pico service not available"})
        return json.dumps(self.pico.get_status())

    @Slot(result=str)
    def listPicoDevices(self):
        if not self.pico:
            return json.dumps({"ok": False, "error": "Pico service not available"})
        return json.dumps(self.pico.list_devices())

    @Slot(str, int, result=str)
    def setPicoPort(self, port, baudrate=115200):
        if not self.pico:
            return json.dumps({"ok": False, "error": "Pico service not available"})
        return json.dumps(self.pico.set_port(port, baudrate))

    @Slot(str, result=str)
    def setPicoMode(self, mode):
        if not self.pico:
            return json.dumps({"ok": False, "error": "Pico service not available"})
        return json.dumps(self.pico.set_mode(mode))

    @Slot(str, result=str)
    def startPico(self, port=""):
        if not self.pico:
            return json.dumps({"ok": False, "error": "Pico service not available"})
        return json.dumps(self.pico.start(port))

    @Slot(result=str)
    def stopPico(self):
        if not self.pico:
            return json.dumps({"ok": False, "error": "Pico service not available"})
        return json.dumps(self.pico.stop())

    @Slot(str, str, int, result=str)
    def picoSendKey(self, key, action, hold_ms=50):
        if not self.pico:
            return json.dumps({"ok": False, "error": "Pico service not available"})
        return json.dumps(self.pico.send_key(key, action, hold_ms))

    @Slot(int, int, int, int, result=str)
    def picoSendMouse(self, dx, dy, button=0, hold_ms=0):
        if not self.pico:
            return json.dumps({"ok": False, "error": "Pico service not available"})
        return json.dumps(self.pico.send_mouse(dx, dy, button, hold_ms))

    @Slot(int, int, int, int, int, int, int, int, result=str)
    def picoSendGamepad(self, buttons, lt, rt, lx, ly, rx, ry, mask=65535):
        if not self.pico:
            return json.dumps({"ok": False, "error": "Pico service not available"})
        return json.dumps(self.pico.send_gamepad(buttons, lt, rt, lx, ly, rx, ry, mask))

    @Slot(str, int, int, int, result=str)
    def picoSetStick(self, which, x, y, hold_ms=0):
        if not self.pico:
            return json.dumps({"ok": False, "error": "Pico service not available"})
        return json.dumps(self.pico.set_stick(which, x, y, hold_ms))

    @Slot(int, int, result=str)
    def picoSetTriggers(self, lt, rt):
        if not self.pico:
            return json.dumps({"ok": False, "error": "Pico service not available"})
        return json.dumps(self.pico.set_triggers(lt, rt))

    @Slot(result=str)
    def picoReset(self):
        if not self.pico:
            return json.dumps({"ok": False, "error": "Pico service not available"})
        return json.dumps(self.pico.reset())
