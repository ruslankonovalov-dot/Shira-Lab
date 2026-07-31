"""app/backend/bridges/recorder_bridge.py — Recorder-методы моста QML.

Перенесено из qml_bridge.py, секция "Recorder" (строки 1002–1057).
"""
from __future__ import annotations

import json

from app.backend.bridges.bridge_base import BridgeBase
from PySide6.QtCore import Slot


class RecorderBridge(BridgeBase):
    """Методы recorder: recorderStatus, recorderStart, recorderPlay, ..."""

    @Slot(result=str)
    def recorderStatus(self):
        return json.dumps(self.recorder.status())

    @Slot(result=str)
    def recorderList(self):
        return json.dumps(self.recorder.list_records())

    @Slot(result=str)
    def recorderStart(self):
        out = self.recorder.start_recording()
        self.recorderStatusChanged.emit()
        return json.dumps(out)

    @Slot(result=str)
    def recorderStop(self):
        out = self.recorder.stop_recording()
        self.recorderStatusChanged.emit()
        return json.dumps(out)

    @Slot(str, int, result=str)
    def recorderPlay(self, name, repeats=1):
        out = self.recorder.play_record(name, repeats)
        self.recorderStatusChanged.emit()
        return json.dumps(out)

    @Slot(result=str)
    def recorderStopPlay(self):
        out = self.recorder.stop_playing()
        self.recorderStatusChanged.emit()
        return json.dumps(out)

    @Slot(str, result=str)
    def setRecorderBackgroundMethod(self, method):
        out = self.recorder.set_background_method(method)
        self._schedule_save()
        return json.dumps(out)

    @Slot(str)
    def recorderDelete(self, name):
        self.recorder.delete_record(name)
        self.recorderStatusChanged.emit()

    # ─── NEW: Drag & Drop reorder (SSS) ───────────────────────────
    @Slot(str, str, result=str)
    def recorderRename(self, old_name, new_name):
        out = getattr(
            self.recorder, "rename_record",
            lambda *a: {"ok": False, "error": "rename not implemented"}
        )(old_name, new_name)
        return json.dumps(out)

    @Slot(result=str)
    def recorderExportAll(self):
        """Экспортирует все записи в один zip-архив."""
        out = getattr(
            self.recorder, "export_all",
            lambda: {"ok": False, "error": "export_all not implemented"}
        )()
        return json.dumps(out)
