"""app/backend/bridges/__init__.py — Пакет Bridge-миксинов.

Экспортирует главный класс QmlBridge, который собирает все миксины в один QObject
для QML. Это — результат рефакторинга God Object `qml_bridge.py` (2077 LOC).

Архитектура:
    QmlBridge (главный фасад)
      ↑ наследует
      ├── BridgeBase           (_schedule_save, log, signals)
      ├── SettingsBridge       (getSettings, setTerminalPalette, ...)
      ├── WindowBridge         (getHwnd, windowDragMove, toggleWindowPin, ...)
      ├── ClickerBridge        (getClickerStatus, startClicker, stopClicker, ...)
      ├── MacroBridge          (getMacroStatus, addMacroAction, ...)
      ├── RecorderBridge       (recorderStatus, recorderStart, recorderPlay, ...)
      ├── AimBridge            (aimStatus, aimStart, aimSetConfig, ...)
      ├── HotkeysBridge        (getHotkeys, setHotkey, resetHotkey, ...)
      ├── GamepadBridge        (getVigemStatus, vigemSetGamepadState, ...)
      ├── PicoBridge           (getPicoStatus, picoSendKey, ...)
      ├── OverlayBridge        (toggleOverlayHUD, clampOverlayPosition, ...)
      └── DiagnosticsBridge    (getDiagnostics, panicStop, ...)

Каждый миксин ≤ 250 LOC. QmlBridge.__init__ создаёт все сервисы.
"""
from __future__ import annotations

from app.backend.bridges.aim_bridge import AimBridge
from app.backend.bridges.bridge_base import BridgeBase
from app.backend.bridges.clicker_bridge import ClickerBridge
from app.backend.bridges.diagnostics_bridge import DiagnosticsBridge
from app.backend.bridges.gamepad_bridge import GamepadBridge
from app.backend.bridges.hotkeys_bridge import HotkeysBridge
from app.backend.bridges.macro_bridge import MacroBridge
from app.backend.bridges.overlay_bridge import OverlayBridge
from app.backend.bridges.pico_bridge import PicoBridge
from app.backend.bridges.recorder_bridge import RecorderBridge
from app.backend.bridges.settings_bridge import SettingsBridge
from app.backend.bridges.window_bridge import WindowBridge


class QmlBridge(
    SettingsBridge,
    WindowBridge,
    ClickerBridge,
    MacroBridge,
    RecorderBridge,
    AimBridge,
    HotkeysBridge,
    GamepadBridge,
    PicoBridge,
    OverlayBridge,
    DiagnosticsBridge,
    BridgeBase,
):
    """Фасад: собирает все bridge-миксины в один QObject для QML.

    Все @Slot-методы доступны из QML как Bridge.methodName() —
    QML не видит разницы между монолитом и миксинами.

    Чтобы добавить новый домен:
    1. Создать app/backend/bridges/<domain>_bridge.py с классом <Domain>Bridge(BridgeBase)
    2. Добавить импорт сюда
    3. Добавить класс в список наследования QmlBridge
    4. Инициализировать сервисы в __init__ (если нужно)
    """
    pass


__all__ = [
    "QmlBridge",
    "BridgeBase",
    "SettingsBridge",
    "WindowBridge",
    "ClickerBridge",
    "MacroBridge",
    "RecorderBridge",
    "AimBridge",
    "HotkeysBridge",
    "GamepadBridge",
    "PicoBridge",
    "OverlayBridge",
    "DiagnosticsBridge",
]
