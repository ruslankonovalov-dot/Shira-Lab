"""app/backend/bridges/bridge_base.py — Базовый класс для всех bridge-миксинов.

Содержит:
- Общие сигналы (чтобы все миксины могли их emit)
- Механизм отложенного сохранения (_schedule_save, _flush_save)
- Инициализация сервисов (clicker, macro, aim, ...)
- Логирование
- Управление app hwnd (для window/topmost операций)
"""
from __future__ import annotations

import logging
import threading

from PySide6.QtCore import QObject, Signal, Slot

logger = logging.getLogger(__name__)


class BridgeBase(QObject):
    """Базовый класс с общей инфраструктурой для всех bridge-миксинов.

    Наследники получают доступ к:
        self.clicker, self.macro, self.recorder, self.aim,
        self.hotkeys, self.stealth, self.state, self._hwnd

    И методам:
        _schedule_save(), _flush_save(), log()
    """

    # ─── Общие сигналы (один источник правды для всех миксинов) ───
    statusChanged = Signal(str)
    clickerStatusChanged = Signal()
    aimStatusChanged = Signal()
    macroStatusChanged = Signal()
    recorderStatusChanged = Signal()
    hotkeysChanged = Signal()
    settingsChanged = Signal()
    overlayChanged = Signal()

    # ─── Инициализация ────────────────────────────────────────────
    def __init__(self, parent=None):
        super().__init__(parent)

        # Сервисы (создаются здесь, доступны всем миксинам)
        from app.backend.models.runtime_state import RuntimeState
        from app.backend.services.aim_service import AimService
        from app.backend.services.clicker_service import ClickerService
        from app.backend.services.macro_service import MacroService
        from app.backend.services.recorder_service import RecorderService
        from app.backend.services.stealth_input import StealthInput

        self.clicker = ClickerService()
        self.macro = MacroService()
        self.recorder = RecorderService()
        self.aim = AimService()
        self.stealth = StealthInput()
        self.state = RuntimeState()

        # HotkeyService требует ссылку на bridge (наследник BridgeBase)
        from app.backend.services.hotkey_service import HotkeyService
        self.hotkeys = HotkeyService(self)

        # Сохранение профиля (debounced)
        self._save_timer: threading.Timer | None = None
        self._save_lock = threading.Lock()
        self._suppress_save = False

        # HWND главного окна (устанавливается из main.py после load QML)
        self._hwnd: int = 0
        self._overlay_hwnd: int = 0

        # Загрузка профиля
        from app.backend.persistence import load_profile
        try:
            load_profile(self)
        except Exception:
            logger.exception("Failed to load profile")

        # Применение горячих клавиш из профиля
        try:
            self.hotkeys.set_bindings(self.state.hotkeys)
        except Exception:
            logger.exception("Failed to set hotkey bindings")

    # ─── Debounced save ───────────────────────────────────────────
    def _schedule_save(self):
        """Отложенное сохранение профиля (debounce 400ms)."""
        if self._suppress_save:
            return
        with self._save_lock:
            if self._save_timer is not None:
                self._save_timer.cancel()
            self._save_timer = threading.Timer(0.4, self._flush_save)
            self._save_timer.daemon = True
            self._save_timer.start()

    def _flush_save(self):
        """Реальное сохранение профиля на диск."""
        try:
            from app.backend.persistence import save_profile
            save_profile(self)
        except Exception:
            logger.exception("Failed to save profile")

    @Slot(str)
    def saveProfileNow(self, _=""):
        """Принудительное немедленное сохранение (для QML)."""
        self._flush_save()

    # ─── Логирование ──────────────────────────────────────────────
    def log(self, level: str, source: str, message: str):
        """Логирование события с указанием источника."""
        getattr(logger, level.lower(), logger.info)(
            "[%s] %s", source, message
        )

    @Slot(str, str, str)
    def logMessageSlot(self, level, source, message):
        """@Slot-обёртка над log() для вызова из QML."""
        self.log(level, source, message)

    # ─── HWND управление ──────────────────────────────────────────
    def set_app_hwnd(self, hwnd: int):
        """Устанавливается из main.py после создания окна."""
        self._hwnd = hwnd

    def set_overlay_hwnd(self, hwnd: int):
        """Устанавливается из OverlayHUD.qml после создания overlay окна."""
        self._overlay_hwnd = hwnd
