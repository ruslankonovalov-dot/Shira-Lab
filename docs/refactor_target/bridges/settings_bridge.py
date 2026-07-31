"""app/backend/bridges/settings_bridge.py — Settings-методы моста QML.

Перенесено из qml_bridge.py, секция "Settings" (примерно строки 306–593).

Содержит:
- getSettings, setTerminalPalette, setUiLang
- setGlobalTransparency, setInterfaceTransparency
- setGlobalBlurEnabled, setInterfaceBlurEnabled
- setBgFitMode, chooseBackgroundImage, clearBackgroundImage
- _regenerate_palette_icon (асинхронная регенерация иконки)
- Profile manager: saveGameProfile, loadGameProfile, listGameProfiles, deleteGameProfile
"""
from __future__ import annotations

import json
from pathlib import Path

from app.backend.bridges.bridge_base import BridgeBase
from PySide6.QtCore import Slot

from app.backend.models.runtime_state import TERMINAL_PALETTES
from config import LANGUAGES, LOGO_SHIRA


class SettingsBridge(BridgeBase):
    """Методы настроек: палитры, прозрачность, blur, язык, профили."""

    # ─── Get settings ─────────────────────────────────────────────
    @Slot(result=str)
    def getSettings(self):
        """Возвращает JSON со всеми настройками для QML."""
        lang = dict(LANGUAGES.get(self.state.ui_lang, LANGUAGES["RU"]))
        bg_uri = ""
        if self.state.bg_image_path:
            try:
                p = Path(self.state.bg_image_path)
                if p.exists():
                    bg_uri = p.resolve().as_uri()
            except OSError:
                pass
        return json.dumps({
            "terminal_palette": self.state.terminal_palette,
            "global_transparency": self.state.global_transparency,
            "interface_transparency": self.state.interface_transparency,
            "global_blur_enabled": self.state.global_blur_enabled,
            "interface_blur_enabled": self.state.interface_blur_enabled,
            "is_pinned": self.state.is_pinned,
            "ui_lang": self.state.ui_lang,
            "bg_image_path": self.state.bg_image_path or "",
            "bg_image_uri": bg_uri,
            "bg_fit_mode": self.state.bg_fit_mode,
            "target_hwnd": self.state.target_hwnd or 0,
            "target_name": self.state.target_name,
            "lang": lang,
            "logo_shira": LOGO_SHIRA,
            "palettes": TERMINAL_PALETTES,
        })

    # ─── Palette ──────────────────────────────────────────────────
    @Slot(str)
    def setTerminalPalette(self, palette_id):
        if palette_id in TERMINAL_PALETTES:
            self.state.terminal_palette = palette_id
            self._schedule_save()
            self._apply_transparency()  # из WindowBridge
            self.settingsChanged.emit()
            self._regenerate_palette_icon(palette_id)

    def _regenerate_palette_icon(self, palette_id: str):
        """Асинхронная регенерация иконки приложения в новой палитре."""
        # TODO: перенести логику из qml_bridge.py строки 330–435
        pass

    # ─── Transparency ─────────────────────────────────────────────
    @Slot(float)
    def setGlobalTransparency(self, value):
        self.state.global_transparency = max(0.0, min(1.0, float(value)))
        self._schedule_save()
        self._apply_transparency()

    @Slot(float)
    def setInterfaceTransparency(self, value):
        self.state.interface_transparency = max(0.0, min(1.0, float(value)))
        self._schedule_save()
        self.settingsChanged.emit()

    @Slot(bool)
    def setGlobalBlurEnabled(self, enabled):
        self.state.global_blur_enabled = bool(enabled)
        self._schedule_save()
        self._apply_transparency()

    @Slot(bool)
    def setInterfaceBlurEnabled(self, enabled):
        self.state.interface_blur_enabled = bool(enabled)
        self._schedule_save()
        self.settingsChanged.emit()

    # ─── Language ─────────────────────────────────────────────────
    @Slot(str)
    def setUiLang(self, code):
        code = code.upper()
        if code in LANGUAGES:
            self.state.ui_lang = code
            self._schedule_save()
            self.settingsChanged.emit()

    # ─── Background image ─────────────────────────────────────────
    @Slot(str)
    def setBgFitMode(self, mode):
        mode = mode.upper()
        if mode in ("COVER", "CONTAIN", "STRETCH", "CENTER"):
            self.state.bg_fit_mode = mode
            self._schedule_save()

    @Slot(result=str)
    def chooseBackgroundImage(self):
        from PySide6.QtWidgets import QFileDialog
        path, _ = QFileDialog.getOpenFileName(
            None, "Choose background image", "",
            "Images (*.png *.jpg *.jpeg *.bmp *.gif *.webp)"
        )
        if path:
            self.state.bg_image_path = path
            self._schedule_save()
            return path
        return ""

    @Slot()
    def clearBackgroundImage(self):
        self.state.bg_image_path = None
        self._schedule_save()
        self.settingsChanged.emit()

    # ─── Game profiles ────────────────────────────────────────────
    @Slot(str, result=str)
    def saveGameProfile(self, name):
        """Сохраняет текущую конфигурацию как game profile."""
        from app.backend.profile_manager import ProfileManager
        pm = ProfileManager()
        return json.dumps(pm.save(self, name))

    @Slot(str, result=str)
    def loadGameProfile(self, name):
        from app.backend.profile_manager import ProfileManager
        pm = ProfileManager()
        return json.dumps(pm.load(self, name))

    @Slot(result=str)
    def listGameProfiles(self):
        from app.backend.profile_manager import ProfileManager
        pm = ProfileManager()
        return json.dumps(pm.list_profiles())

    @Slot(str, result=str)
    def deleteGameProfile(self, name):
        from app.backend.profile_manager import ProfileManager
        pm = ProfileManager()
        return json.dumps(pm.delete(name))
