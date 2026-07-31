"""app/backend/bridges/macro_bridge.py — Macro-методы моста QML.

Перенесено из qml_bridge.py, секция "Macro" (строки 944–1001).

Включает undo/redo (новое, для SSS-уровня).
"""
from __future__ import annotations

import json

from PySide6.QtCore import Slot

from app.backend.bridges.bridge_base import BridgeBase


class MacroBridge(BridgeBase):
    """Методы макро-движка: getMacroStatus, addMacroAction, start/stop, undo/redo."""

    @Slot(result=str)
    def getMacroStatus(self):
        return json.dumps(self.macro.get_status())

    @Slot(str, result=str)
    def setMacroMode(self, mode):
        out = self.macro.set_run_mode(mode)
        self._schedule_save()
        return json.dumps(out)

    @Slot(str, result=str)
    def setMacroBackgroundMethod(self, method):
        out = self.macro.set_background_method(method)
        self._schedule_save()
        return json.dumps(out)

    @Slot(str, float, float, result=str)
    def addMacroAction(self, key, delay, hold):
        out = self.macro.add_action(key, delay, hold)
        self._schedule_save()
        return json.dumps(out)

    @Slot(result=str)
    def clearMacroActions(self):
        out = self.macro.clear_actions()
        self._schedule_save()
        return json.dumps(out)

    @Slot(result=str)
    def startMacro(self):
        out = self.macro.start(target_hwnd=self.state.target_hwnd)
        self._schedule_save()
        self.macroStatusChanged.emit()
        return json.dumps(out)

    @Slot(result=str)
    def stopMacro(self):
        out = self.macro.stop()
        self._schedule_save()
        self.macroStatusChanged.emit()
        return json.dumps(out)

    # ─── Undo/Redo (NEW for SSS) ──────────────────────────────────
    @Slot(result=str)
    def macroUndo(self):
        out = getattr(self.macro, "undo", lambda: {"ok": False, "error": "undo not implemented"})()
        return json.dumps(out)

    @Slot(result=str)
    def macroRedo(self):
        out = getattr(self.macro, "redo", lambda: {"ok": False, "error": "redo not implemented"})()
        return json.dumps(out)

    @Slot(int, int, result=str)
    def macroMoveAction(self, from_index, to_index):
        """Drag & Drop: переместить action в списке."""
        out = getattr(
            self.macro, "move_action",
            lambda *a: {"ok": False, "error": "move_action not implemented"}
        )(from_index, to_index)
        self._schedule_save()
        return json.dumps(out)

    @Slot(int, result=str)
    def macroDeleteAction(self, index):
        """Удалить конкретный action по индексу."""
        out = getattr(
            self.macro, "delete_action",
            lambda *a: {"ok": False, "error": "delete_action not implemented"}
        )(index)
        self._schedule_save()
        return json.dumps(out)
