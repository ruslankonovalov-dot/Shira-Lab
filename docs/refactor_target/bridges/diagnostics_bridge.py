"""app/backend/bridges/diagnostics_bridge.py — Diagnostics-методы моста QML.

Перенесено из qml_bridge.py, секции Diagnostics + panic_stop (строки 1289–1345).
"""
from __future__ import annotations

import json
import platform

from app.backend.bridges.bridge_base import BridgeBase
from PySide6.QtCore import Slot


class DiagnosticsBridge(BridgeBase):
    """Диагностика + panic stop: getDiagnostics, panicStop, ..."""

    @Slot(result=str)
    def getDiagnostics(self):
        """Возвращает полную диагностическую информацию для DiagnosticsPage."""
        return json.dumps({
            "platform": platform.platform(),
            "python": platform.python_version(),
            "is_pinned": self.state.is_pinned,
            "hotkeys_available": self.hotkeys.is_available(),
            "mouse_hotkeys_available": self.hotkeys.is_mouse_available(),
            "wheel_hotkeys_available": self.hotkeys.is_wheel_available(),
            "terminal_palette": self.state.terminal_palette,
            "global_transparency": self.state.global_transparency,
            "clicker": self.clicker.get_status(),
            "macro": self.macro.get_status(),
            "recorder": self.recorder.status(),
            "aim": self.aim.get_status(),
            "ui": "pyside6",
            "app_hwnd": self._hwnd,
            "overlay_hwnd": self._overlay_hwnd,
        })

    @Slot(result=str)
    def panicStop(self):
        """Аварийная остановка ВСЕХ модулей (F12 / panic button)."""
        results = {}
        try:
            results["clicker"] = self.clicker.stop()
        except Exception as e:
            results["clicker"] = {"ok": False, "error": str(e)}
        try:
            results["macro"] = self.macro.stop()
        except Exception as e:
            results["macro"] = {"ok": False, "error": str(e)}
        try:
            results["recorder_playing"] = self.recorder.stop_playing()
        except Exception as e:
            results["recorder_playing"] = {"ok": False, "error": str(e)}
        try:
            results["recorder_recording"] = self.recorder.stop_recording()
        except Exception as e:
            results["recorder_recording"] = {"ok": False, "error": str(e)}
        try:
            results["aim"] = self.aim.stop()
        except Exception as e:
            results["aim"] = {"ok": False, "error": str(e)}

        self.statusChanged.emit("PANIC_STOP executed")
        return json.dumps({"ok": True, "results": results})

    # ─── NEW: Performance Profiler (SSS) ──────────────────────────
    @Slot(result=str)
    def getPerformanceProfile(self):
        """Возвращает метрики производительности для Diagnostics → Profiler."""
        import time

        import psutil  # type: ignore
        try:
            process = psutil.Process()
            return json.dumps({
                "ok": True,
                "cpu_percent": process.cpu_percent(interval=0.1),
                "memory_mb": process.memory_info().rss / 1024 / 1024,
                "threads": process.num_threads(),
                "uptime_sec": time.time() - process.create_time(),
                "clicker_cps": getattr(self.clicker, "get_cps", lambda: 0)(),
                "aim_fps": getattr(self.aim, "get_fps", lambda: 0)(),
                "hotkey_latency_ms": getattr(self.hotkeys, "get_latency_ms", lambda: 0)(),
            })
        except Exception as e:
            return json.dumps({"ok": False, "error": str(e)})
