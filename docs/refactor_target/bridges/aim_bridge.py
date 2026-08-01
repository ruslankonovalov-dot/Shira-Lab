"""app/backend/bridges/aim_bridge.py — Aim-методы моста QML.

Перенесено из qml_bridge.py, секция "Aim" (строки 1058–1228).
"""

from __future__ import annotations

import json

from PySide6.QtCore import Slot

from app.backend.bridges.bridge_base import BridgeBase


class AimBridge(BridgeBase):
    """Методы aim assist: aimStatus, aimStart, aimStop, aimSetConfig, ..."""

    @Slot(result=str)
    def aimStatus(self):
        return json.dumps(self.aim.get_status())

    @Slot(float, int, float, result=str)
    def aimSetConfig(self, confidence, smooth_steps, reset_delay):
        out = self.aim.update_config(confidence, smooth_steps, reset_delay)
        self._schedule_save()
        return json.dumps(out)

    @Slot(int, int, int, int, result=str)
    def aimSetRegion(self, top, left, width, height):
        out = self.aim.set_scan_region(top, left, width, height)
        self._schedule_save()
        return json.dumps(out)

    @Slot(result=str)
    def aimStart(self):
        out = self.aim.start()
        self._schedule_save()
        self.aimStatusChanged.emit()
        return json.dumps(out)

    @Slot(result=str)
    def aimStop(self):
        out = self.aim.stop()
        self._schedule_save()
        self.aimStatusChanged.emit()
        return json.dumps(out)

    @Slot(str, result=str)
    def setAimBackgroundMethod(self, method):
        out = self.aim.set_background_method(method)
        self._schedule_save()
        return json.dumps(out)

    @Slot(str, result=str)
    def setAimTargetColor(self, color):
        out = self.aim.set_target_color(color)
        self._schedule_save()
        return json.dumps(out)

    @Slot(int, result=str)
    def setAimFov(self, radius):
        out = self.aim.set_fov(radius)
        self._schedule_save()
        return json.dumps(out)

    @Slot(float, result=str)
    def setAimSpeed(self, speed):
        out = self.aim.set_aim_speed(speed)
        self._schedule_save()
        return json.dumps(out)

    @Slot(str, result=str)
    def setAimDetectionMode(self, mode):
        out = self.aim.set_detection_mode(mode)
        self._schedule_save()
        return json.dumps(out)

    @Slot(str, result=str)
    def setAimMultiColors(self, colors_json):
        import json

        colors = json.loads(colors_json)
        out = self.aim.set_multi_colors(colors)
        self._schedule_save()
        return json.dumps(out)

    @Slot(int, int, int, int, int, int, result=str)
    def setAimFilters(
        self,
        min_area,
        max_area,
        aspect_min_x100,
        aspect_max_x100,
        brightness,
        saturation,
    ):
        out = self.aim.set_filters(
            min_area, max_area, aspect_min_x100, aspect_max_x100, brightness, saturation
        )
        self._schedule_save()
        return json.dumps(out)

    @Slot(int, int, result=str)
    def aimSampleColor(self, x, y):
        """Берёт цвет пикселя в точке (x, y) для калибровки."""
        out = self.aim.sample_color_at(x, y)
        return json.dumps(out)

    @Slot(result=str)
    def getMousePosition(self):
        """Возвращает текущие координаты курсора (для UI калибровки)."""
        import ctypes

        try:

            class POINT(ctypes.Structure):
                _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]

            pt = POINT()
            ctypes.windll.user32.GetCursorPos(ctypes.byref(pt))
            return json.dumps({"x": pt.x, "y": pt.y})
        except Exception:
            return json.dumps({"x": 0, "y": 0})
