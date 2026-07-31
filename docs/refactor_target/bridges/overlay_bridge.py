"""app/backend/bridges/overlay_bridge.py — Overlay HUD-методы моста QML.

Перенесено из qml_bridge.py, секции overlay (строки 1303–1313).
"""
from __future__ import annotations

import json

from PySide6.QtCore import Slot

from app.backend.bridges.bridge_base import BridgeBase


class OverlayBridge(BridgeBase):
    """Методы Overlay HUD: toggleOverlayHUD, getOverlayVisibility, ..."""

    @Slot(bool, result=str)
    def toggleOverlayHUD(self, visible: bool):
        """Включает/выключает overlay HUD."""
        self.state.overlay_visible = bool(visible)
        self._schedule_save()
        self.overlayChanged.emit()
        return json.dumps({"ok": True, "visible": self.state.overlay_visible})

    @Slot(result=str)
    def getOverlayVisibility(self):
        return json.dumps({
            "visible": getattr(self.state, "overlay_visible", False),
            "overlay_hwnd": self._overlay_hwnd,
        })

    @Slot(int, int, int, int, result=str)
    def setOverlayGeometry(self, x, y, w, h):
        """Устанавливает позицию/размер overlay (drag & resize)."""
        try:
            import ctypes
            if self._overlay_hwnd:
                # SWP_NOZORDER | SWP_NOACTIVATE
                ctypes.windll.user32.SetWindowPos(
                    self._overlay_hwnd, 0, x, y, w, h, 0x0004 | 0x0010
                )
            return json.dumps({"ok": True})
        except Exception as e:
            return json.dumps({"ok": False, "error": str(e)})
