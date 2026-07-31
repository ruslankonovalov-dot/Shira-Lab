"""app/backend/services/hotkeys/handlers.py — Action handlers.

Перенесено из hotkey_service.py:
- _action_handler (строки 177–228)
- _action_start_handler (строки 259–295)
- _action_stop_handler (строки 297–335)
"""
from __future__ import annotations

import logging
from typing import Any, Callable

logger = logging.getLogger(__name__)


class ActionHandlers:
    """Содержит handlers для каждого действия.

    Каждый handler получает api (bridge) и вызывает соответствующий метод сервиса.
    """

    def __init__(self, api: Any):
        self._api = api

    def get_handler(self, action: str) -> Callable[[], None]:
        """Возвращает toggle-обработчик для действия."""
        handlers = {
            "clicker_toggle":   self._clicker_toggle,
            "aim_toggle":       self._aim_toggle,
            "macro_start":      self._macro_start_toggle,
            "macro_stop":       self._macro_stop,
            "recorder_start":   self._recorder_start_toggle,
            "recorder_stop":    self._recorder_stop,
            "app_show":         self._app_show,
            "panic_stop":       self._panic_stop,
        }
        return handlers.get(action, lambda: logger.warning("Unknown action: %s", action))

    def get_start_handler(self, action: str) -> Callable[[], None]:
        """Возвращает start-обработчик (для HOLD режима)."""
        handlers = {
            "clicker_toggle":   self._clicker_start,
            "aim_toggle":       self._aim_start,
            "macro_start":      self._macro_start,
            "recorder_start":   self._recorder_start,
        }
        return handlers.get(action, lambda: None)

    def get_stop_handler(self, action: str) -> Callable[[], None]:
        """Возвращает stop-обработчик (для HOLD режима)."""
        handlers = {
            "clicker_toggle":   self._clicker_stop,
            "aim_toggle":       self._aim_stop,
            "macro_start":      self._macro_stop,
            "recorder_start":   self._recorder_stop,
        }
        return handlers.get(action, lambda: None)

    # ─── Toggle handlers ─────────────────────────────────────────
    def _clicker_toggle(self):
        try:
            status = self._api.clicker.get_status()
            if status.get("running"):
                self._api.clicker.stop()
            else:
                self._api.clicker.start(target_hwnd=self._api.state.target_hwnd)
        except Exception:
            logger.exception("clicker_toggle failed")

    def _aim_toggle(self):
        try:
            status = self._api.aim.get_status()
            if status.get("running"):
                self._api.aim.stop()
            else:
                self._api.aim.start()
        except Exception:
            logger.exception("aim_toggle failed")

    def _macro_start_toggle(self):
        try:
            status = self._api.macro.get_status()
            if status.get("running"):
                self._api.macro.stop()
            else:
                self._api.macro.start(target_hwnd=self._api.state.target_hwnd)
        except Exception:
            logger.exception("macro_start_toggle failed")

    def _macro_stop(self):
        try:
            self._api.macro.stop()
        except Exception:
            logger.exception("macro_stop failed")

    def _recorder_start_toggle(self):
        try:
            status = self._api.recorder.status()
            if status.get("recording"):
                self._api.recorder.stop_recording()
            else:
                self._api.recorder.start_recording()
        except Exception:
            logger.exception("recorder_start_toggle failed")

    def _recorder_stop(self):
        try:
            self._api.recorder.stop_playing()
            self._api.recorder.stop_recording()
        except Exception:
            logger.exception("recorder_stop failed")

    def _app_show(self):
        try:
            self._api.showAppWindow()
        except Exception:
            logger.exception("app_show failed")

    def _panic_stop(self):
        try:
            self._api.panicStop()
        except Exception:
            logger.exception("panic_stop failed")

    # ─── Start/Stop handlers (HOLD mode) ─────────────────────────
    def _clicker_start(self):
        try:
            self._api.clicker.start(target_hwnd=self._api.state.target_hwnd)
        except Exception:
            logger.exception("clicker_start failed")

    def _clicker_stop(self):
        try:
            self._api.clicker.stop()
        except Exception:
            logger.exception("clicker_stop failed")

    def _aim_start(self):
        try:
            self._api.aim.start()
        except Exception:
            logger.exception("aim_start failed")

    def _aim_stop(self):
        try:
            self._api.aim.stop()
        except Exception:
            logger.exception("aim_stop failed")

    def _macro_start(self):
        try:
            self._api.macro.start(target_hwnd=self._api.state.target_hwnd)
        except Exception:
            logger.exception("macro_start failed")

    def _recorder_start(self):
        try:
            self._api.recorder.start_recording()
        except Exception:
            logger.exception("recorder_start failed")
