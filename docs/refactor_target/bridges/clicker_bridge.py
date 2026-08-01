"""app/backend/bridges/clicker_bridge.py — Clicker-методы моста QML.

Перенесено из qml_bridge.py, секция "Clicker" (строки 896–943).
"""

from __future__ import annotations

import json

from PySide6.QtCore import Slot

from app.backend.bridges.bridge_base import BridgeBase


class ClickerBridge(BridgeBase):
    """Методы авто-кликера: getClickerStatus, startClicker, stopClicker, ..."""

    @Slot(result=str)
    def getClickerStatus(self):
        return json.dumps(self.clicker.get_status())

    @Slot(result=float)
    def getClickerCPS(self):
        """Текущий фактический CPS (clicks per second)."""
        try:
            return float(self.clicker.get_cps())
        except Exception:
            return 0.0

    @Slot(int, int, str, int, str, result=str)
    def setClickerConfig(self, interval_ms, hold_ms, button, limit, background_method):
        status = self.clicker.update_config(interval_ms, hold_ms, button, limit, background_method)
        self._schedule_save()
        return json.dumps(status)

    @Slot(result=str)
    def startClicker(self):
        status = self.clicker.start(target_hwnd=self.state.target_hwnd)
        self._schedule_save()
        self.clickerStatusChanged.emit()
        return json.dumps(status)

    @Slot(result=str)
    def stopClicker(self):
        status = self.clicker.stop()
        self._schedule_save()
        self.clickerStatusChanged.emit()
        return json.dumps(status)
