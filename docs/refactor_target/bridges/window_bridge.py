"""app/backend/bridges/window_bridge.py — Window-методы моста QML.

Перенесено из qml_bridge.py, секция "Window management" (строки 664–815).

Содержит:
- getHwnd, getWorkArea, clampOverlayPosition, reassertOverlayTopmost
- windowDragMove, toggleWindowPin, windowMinimize, windowToggleMaximize
- windowClose, showAppWindow, isAppVisible
- apply_acrylic_on_start, _apply_transparency (DWM acrylic)
"""
from __future__ import annotations

import ctypes
import json

from app.backend.bridges.bridge_base import BridgeBase
from PySide6.QtCore import Slot

from app.backend.models.runtime_state import TERMINAL_PALETTES


class WindowBridge(BridgeBase):
    """Методы управления окном приложения и overlay."""

    # ─── DWM Acrylic ──────────────────────────────────────────────
    def apply_acrylic_on_start(self, hwnd):
        """Применяет DWM acrylic к HWND окна (вызывается из main.py)."""
        self._hwnd = hwnd
        self._apply_transparency()

    def _apply_transparency(self):
        """Перерисовывает acrylic tint на основе текущей палитры/прозрачности."""
        if not self._hwnd:
            return
        palette = TERMINAL_PALETTES.get(self.state.terminal_palette, TERMINAL_PALETTES["matrix"])
        tint_color = palette["bg"]
        tint_alpha = int(200 - self.state.global_transparency * 180)
        tint_alpha = max(20, min(255, tint_alpha))
        try:
            # Lazy import: dwm_acrylic может быть не на всех платформах
            from app.backend.services.dwm_acrylic import (
                disable_acrylic_blur,
                enable_acrylic_blur,
            )
            if self.state.global_blur_enabled or self.state.global_transparency > 0:
                enable_acrylic_blur(self._hwnd, tint_color, tint_alpha)
            else:
                disable_acrylic_blur(self._hwnd)
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning("DWM acrylic: %s", e)

    # ─── HWND ─────────────────────────────────────────────────────
    @Slot(result=int)
    def getHwnd(self):
        return self._hwnd

    @Slot(result=str)
    def getWorkArea(self):
        """Возвращает размер рабочей области экрана."""
        try:
            class RECT(ctypes.Structure):
                _fields_ = [("left", ctypes.c_long), ("top", ctypes.c_long),
                            ("right", ctypes.c_long), ("bottom", ctypes.c_long)]
            r = RECT()
            ctypes.windll.user32.SystemParametersInfoW(0x0030, 0, ctypes.byref(r), 0)
            return json.dumps({"x": r.left, "y": r.top, "w": r.right - r.left, "h": r.bottom - r.top})
        except Exception:
            return json.dumps({"x": 0, "y": 0, "w": 1920, "h": 1080})

    # ─── Overlay positioning ──────────────────────────────────────
    @Slot(int, int, int, int, result=str)
    def clampOverlayPosition(self, x, y, w, h):
        """Ограничивает позицию overlay в пределах рабочей области."""
        try:
            work = json.loads(self.getWorkArea())
            x = max(work["x"], min(x, work["x"] + work["w"] - w))
            y = max(work["y"], min(y, work["y"] + work["h"] - h))
            return json.dumps({"x": x, "y": y})
        except Exception:
            return json.dumps({"x": x, "y": y})

    @Slot()
    def reassertOverlayTopmost(self):
        """Повторно применяет topmost к overlay окну (после потери фокуса)."""
        if self._overlay_hwnd:
            from window_utils import set_window_topmost
            set_window_topmost(self._overlay_hwnd, True)

    # ─── Window controls ──────────────────────────────────────────
    @Slot(int, int)
    def windowDragMove(self, dx, dy):
        if self._hwnd:
            user32 = ctypes.windll.user32
            # SWP_NOSIZE | SWP_NOZORDER | SWP_NOACTIVATE
            user32.SetWindowPos(self._hwnd, 0, dx, dy, 0, 0, 0x0001 | 0x0004 | 0x0010)

    @Slot(result=bool)
    def toggleWindowPin(self):
        self.state.is_pinned = not self.state.is_pinned
        if self._hwnd:
            from window_utils import set_window_topmost
            set_window_topmost(self._hwnd, self.state.is_pinned)
        self._schedule_save()
        return self.state.is_pinned

    @Slot()
    def windowMinimize(self):
        if self._hwnd:
            ctypes.windll.user32.ShowWindow(self._hwnd, 6)  # SW_MINIMIZE

    @Slot()
    def windowToggleMaximize(self):
        if self._hwnd:
            user32 = ctypes.windll.user32
            if user32.IsZoomed(self._hwnd):
                user32.ShowWindow(self._hwnd, 9)  # SW_RESTORE
            else:
                user32.ShowWindow(self._hwnd, 3)  # SW_MAXIMIZE

    @Slot()
    def windowClose(self):
        from PySide6.QtWidgets import QApplication
        QApplication.quit()

    @Slot()
    def showAppWindow(self):
        if self._hwnd:
            user32 = ctypes.windll.user32
            user32.ShowWindow(self._hwnd, 9)  # SW_RESTORE
            user32.SetForegroundWindow(self._hwnd)

    # ─── Visibility check ─────────────────────────────────────────
    @Slot(result=bool)
    def isAppVisible(self):
        return self.is_app_visible()

    def is_app_visible(self) -> bool:
        """Проверяет, видимо ли окно (не свёрнуто и не скрыто)."""
        if not self._hwnd:
            return False
        try:
            user32 = ctypes.windll.user32
            return bool(user32.IsWindowVisible(self._hwnd))
        except Exception:
            return False

    # ─── Target window ────────────────────────────────────────────
    @Slot(result=str)
    def getWindows(self):
        """Возвращает список видимых окон для выбора target."""
        from window_utils import get_visible_windows
        windows = [{"hwnd": 0, "title": "GLOBAL_SCREEN"}]
        for hwnd, title in sorted(get_visible_windows(), key=lambda x: x[1].lower()):
            windows.append({"hwnd": int(hwnd), "title": title})
        return json.dumps({"ok": True, "windows": windows})

    @Slot(str, int, result=str)
    def setModuleTargetWindow(self, module, hwnd):
        """Устанавливает target окно для конкретного модуля."""
        # TODO: реализовать per-module target (clicker, macro, recorder, aim)
        if hwnd == 0:
            self.state.target_hwnd = None
            self.state.target_name = "GLOBAL_SCREEN"
        else:
            from window_utils import get_visible_windows
            for item_hwnd, title in get_visible_windows():
                if int(item_hwnd) == hwnd:
                    self.state.target_hwnd = hwnd
                    self.state.target_name = title
                    break
        self._schedule_save()
        return self.state.target_name
