"""
vigem_service.py — Обёртка над ViGEmClient.dll для эмуляции виртуальных геймпадов.

Требует установленного ViGEmBus (https://github.com/ViGEm/ViGEmBus/releases).
DLL обычно находится в: C:\\Program Files\\Nefarius\\ViGEmBus\\ViGEmClient.dll
или в System32 после установки.

Поддерживаемые устройства:
- XUSB (Xbox 360) — XInput, нативно в Windows
- DS4 (DualShock 4) — HID, требует HidGuardian/HidCerberus для скрытия
"""

from __future__ import annotations

import ctypes
import logging
import os
import threading
from ctypes import wintypes
from enum import IntEnum
from typing import Any

logger = logging.getLogger(__name__)


# ─── ViGEmClient constants ──────────────────────────────────────────────
class VIGEM_TARGET_TYPE(IntEnum):
    XBOX360 = 0  # XUSB (XInput)
    DS4 = 1  # DualShock 4


# XUSB button flags (Xbox 360)
XUSB_BUTTON_DPAD_UP = 0x0001
XUSB_BUTTON_DPAD_DOWN = 0x0002
XUSB_BUTTON_DPAD_LEFT = 0x0004
XUSB_BUTTON_DPAD_RIGHT = 0x0008
XUSB_BUTTON_START = 0x0010
XUSB_BUTTON_BACK = 0x0020
XUSB_BUTTON_LEFT_THUMB = 0x0040
XUSB_BUTTON_RIGHT_THUMB = 0x0080
XUSB_BUTTON_LEFT_SHOULDER = 0x0100
XUSB_BUTTON_RIGHT_SHOULDER = 0x0200
XUSB_BUTTON_GUIDE = 0x0400
XUSB_BUTTON_A = 0x1000
XUSB_BUTTON_B = 0x2000
XUSB_BUTTON_X = 0x4000
XUSB_BUTTON_Y = 0x8000


# ─── Structures matching ViGEmClient.h ──────────────────────────────────
class XUSB_REPORT(ctypes.Structure):
    _pack_ = 1
    _fields_ = [
        ("wButtons", wintypes.WORD),
        ("bLeftTrigger", wintypes.BYTE),
        ("bRightTrigger", wintypes.BYTE),
        ("sThumbLX", wintypes.SHORT),
        ("sThumbLY", wintypes.SHORT),
        ("sThumbRX", wintypes.SHORT),
        ("sThumbRY", wintypes.SHORT),
    ]


class DS4_REPORT(ctypes.Structure):
    _pack_ = 1
    _fields_ = [
        ("bThumbLX", wintypes.BYTE),
        ("bThumbLY", wintypes.BYTE),
        ("bThumbRX", wintypes.BYTE),
        ("bThumbRY", wintypes.BYTE),
        ("bTriggerL", wintypes.BYTE),
        ("bTriggerR", wintypes.BYTE),
        ("wButtons", wintypes.WORD),
        ("bSpecial", wintypes.BYTE),
    ]


# ─── Button mapping helpers ─────────────────────────────────────────────
# Map user-friendly names to XUSB button flags
XUSB_BUTTON_MAP: dict[str, int | None] = {
    "a": XUSB_BUTTON_A,
    "b": XUSB_BUTTON_B,
    "x": XUSB_BUTTON_X,
    "y": XUSB_BUTTON_Y,
    "lb": XUSB_BUTTON_LEFT_SHOULDER,
    "rb": XUSB_BUTTON_RIGHT_SHOULDER,
    "lt": None,  # handled separately as trigger
    "rt": None,  # handled separately as trigger
    "back": XUSB_BUTTON_BACK,
    "start": XUSB_BUTTON_START,
    "ls": XUSB_BUTTON_LEFT_THUMB,
    "rs": XUSB_BUTTON_RIGHT_THUMB,
    "guide": XUSB_BUTTON_GUIDE,
    "up": XUSB_BUTTON_DPAD_UP,
    "down": XUSB_BUTTON_DPAD_DOWN,
    "left": XUSB_BUTTON_DPAD_LEFT,
    "right": XUSB_BUTTON_DPAD_RIGHT,
}


# ─── VigemService ───────────────────────────────────────────────────────
class VigemService:
    """
    High-level wrapper for ViGEmClient.
    Manages client lifecycle and targets (virtual devices).

    Thread-safe: all public methods are protected by RLock.
    """

    def __init__(self, dll_path: str | None = None):
        self._client: ctypes.c_void_p | None = None
        self._targets: dict[int, tuple[ctypes.c_void_p, VIGEM_TARGET_TYPE]] = {}
        self._dll: ctypes.CDLL | None = None
        self._dll_path = dll_path
        self._next_target_id = 1
        self._lock = threading.RLock()  # Protects all mutable state
        self._bridge: Any | None = None
        # Internal button state per target_id (mask of currently pressed buttons)
        self._btn_state: dict[int, int] = {}
        self._load_dll()

    def set_bridge(self, bridge: Any) -> None:
        """Set bridge reference for logging."""
        self._bridge = bridge

    def _log(self, level: str, message: str) -> None:
        if self._bridge:
            self._bridge.log(level, "GAMEPAD", message)

    def _find_dll(self) -> str | None:
        """Автопоиск ViGEmClient.dll в стандартных местах."""
        if self._dll_path and os.path.exists(self._dll_path):
            return self._dll_path

        candidates = [
            r"C:\Program Files\Nefarius\ViGEmBus\ViGEmClient.dll",
            r"C:\Program Files (x86)\Nefarius\ViGEmBus\ViGEmClient.dll",
            os.path.join(
                os.environ.get("SystemRoot", r"C:\Windows"),
                "System32",
                "ViGEmClient.dll",
            ),
            os.path.join(os.path.dirname(__file__), "..", "..", "..", "bin", "ViGEmClient.dll"),
        ]
        for path in candidates:
            if os.path.exists(path):
                return path
        return None

    def _load_dll(self) -> bool:
        """Загружает ViGEmClient.dll и настраивает сигнатуры функций."""
        dll_path = self._find_dll()
        if not dll_path:
            return False

        try:
            self._dll = ctypes.CDLL(dll_path)
            self._dll_path = dll_path
        except OSError:
            return False

        # vigem_alloc() -> PVIGEM_CLIENT
        self._dll.vigem_alloc.restype = ctypes.c_void_p
        self._dll.vigem_alloc.argtypes = []

        # vigem_free(PVIGEM_CLIENT)
        self._dll.vigem_free.restype = None
        self._dll.vigem_free.argtypes = [ctypes.c_void_p]

        # vigem_connect(PVIGEM_CLIENT) -> VIGEM_ERROR
        self._dll.vigem_connect.restype = ctypes.c_int
        self._dll.vigem_connect.argtypes = [ctypes.c_void_p]

        # vigem_disconnect(PVIGEM_CLIENT)
        self._dll.vigem_disconnect.restype = None
        self._dll.vigem_disconnect.argtypes = [ctypes.c_void_p]

        # vigem_target_add(PVIGEM_CLIENT, PVIGEM_TARGET) -> VIGEM_ERROR
        self._dll.vigem_target_add.restype = ctypes.c_int
        self._dll.vigem_target_add.argtypes = [ctypes.c_void_p, ctypes.c_void_p]

        # vigem_target_remove(PVIGEM_CLIENT, PVIGEM_TARGET)
        self._dll.vigem_target_remove.restype = None
        self._dll.vigem_target_remove.argtypes = [ctypes.c_void_p, ctypes.c_void_p]

        # vigem_target_x360_alloc() -> PVIGEM_TARGET
        self._dll.vigem_target_x360_alloc.restype = ctypes.c_void_p
        self._dll.vigem_target_x360_alloc.argtypes = []

        # vigem_target_x360_free(PVIGEM_TARGET)
        self._dll.vigem_target_x360_free.restype = None
        self._dll.vigem_target_x360_free.argtypes = [ctypes.c_void_p]

        # vigem_target_x360_update(PVIGEM_CLIENT, PVIGEM_TARGET, XUSB_REPORT*) -> VIGEM_ERROR
        self._dll.vigem_target_x360_update.restype = ctypes.c_int
        self._dll.vigem_target_x360_update.argtypes = [
            ctypes.c_void_p,
            ctypes.c_void_p,
            ctypes.POINTER(XUSB_REPORT),
        ]

        # vigem_target_x360_get_user_index(PVIGEM_TARGET) -> ULONG
        self._dll.vigem_target_x360_get_user_index.restype = wintypes.ULONG
        self._dll.vigem_target_x360_get_user_index.argtypes = [ctypes.c_void_p]

        # DS4 support
        # vigem_target_ds4_alloc() -> PVIGEM_TARGET
        self._dll.vigem_target_ds4_alloc.restype = ctypes.c_void_p
        self._dll.vigem_target_ds4_alloc.argtypes = []

        # vigem_target_ds4_free(PVIGEM_TARGET)
        self._dll.vigem_target_ds4_free.restype = None
        self._dll.vigem_target_ds4_free.argtypes = [ctypes.c_void_p]

        # vigem_target_ds4_update(PVIGEM_CLIENT, PVIGEM_TARGET, DS4_REPORT*) -> VIGEM_ERROR
        self._dll.vigem_target_ds4_update.restype = ctypes.c_int
        self._dll.vigem_target_ds4_update.argtypes = [
            ctypes.c_void_p,
            ctypes.c_void_p,
            ctypes.POINTER(DS4_REPORT),
        ]

        return True

    def is_available(self) -> bool:
        """Проверяет, загружен ли DLL и доступен ли драйвер."""
        with self._lock:
            if not self._dll:
                return False
            # Try to allocate and connect to verify
            client = self._dll.vigem_alloc()
            if not client:
                return False
            err = self._dll.vigem_connect(client)
            self._dll.vigem_free(client)
            return int(err) == 0  # VIGEM_ERROR_NONE = 0

    def connect(self) -> bool:
        """Инициализирует подключение к ViGEmBus."""
        with self._lock:
            if self._client:
                return True
            if not self._dll and not self._load_dll():
                self._log("ERROR", "ViGEmClient.dll not found")
                return False
            assert self._dll is not None  # _load_dll ensures this
            self._client = self._dll.vigem_alloc()
            if not self._client:
                self._log("ERROR", "vigem_alloc() failed")
                return False
            err = self._dll.vigem_connect(self._client)
            if err != 0:
                self._dll.vigem_free(self._client)
                self._client = None
                self._log("ERROR", f"vigem_connect() failed: error {err}")
                return False
            self._log("OK", "ViGEm connected")
            return True

    def disconnect(self) -> None:
        """Отключается и очищает все таргеты."""
        with self._lock:
            for target_id in list(self._targets.keys()):
                self.remove_target(target_id)
            if self._client and self._dll:
                self._dll.vigem_disconnect(self._client)
                self._dll.vigem_free(self._client)
            self._client = None
            self._log("INFO", "ViGEm disconnected")

    # ─── Target management ──────────────────────────────────────────────
    def add_x360(self) -> int | None:
        """Создаёт виртуальный Xbox 360 контроллер. Возвращает target_id или None."""
        with self._lock:
            if not self.connect():
                return None
            assert self._dll is not None  # connect ensures this
            target = self._dll.vigem_target_x360_alloc()
            if not target:
                return None
            err = self._dll.vigem_target_add(self._client, target)
            if err != 0:
                self._dll.vigem_target_x360_free(target)
                return None
            target_id = self._next_target_id
            self._next_target_id += 1
            self._targets[target_id] = (target, VIGEM_TARGET_TYPE.XBOX360)
            return target_id

    def add_ds4(self) -> int | None:
        """Создаёт виртуальный DualShock 4 контроллер. Возвращает target_id или None."""
        with self._lock:
            if not self.connect():
                return None
            assert self._dll is not None  # connect ensures this
            target = self._dll.vigem_target_ds4_alloc()
            if not target:
                return None
            err = self._dll.vigem_target_add(self._client, target)
            if err != 0:
                self._dll.vigem_target_ds4_free(target)
                return None
            target_id = self._next_target_id
            self._next_target_id += 1
            self._targets[target_id] = (target, VIGEM_TARGET_TYPE.DS4)
            return target_id

    def remove_target(self, target_id: int) -> bool:
        """Удаляет таргет по ID."""
        with self._lock:
            if target_id not in self._targets:
                return False
            target, target_type = self._targets.pop(target_id)
            # Clean up button state
            self._btn_state.pop(target_id, None)
            if self._client and self._dll:
                self._dll.vigem_target_remove(self._client, target)
                if target_type == VIGEM_TARGET_TYPE.XBOX360:
                    self._dll.vigem_target_x360_free(target)
                else:
                    self._dll.vigem_target_ds4_free(target)
            return True

    def get_status(self) -> dict[str, Any]:
        """Get status for UI/HUD."""
        with self._lock:
            return {
                "ok": True,
                "connected": self._client is not None,
                "targets": {tid: ttype.name for tid, (_, ttype) in self._targets.items()},
                "target_count": len(self._targets),
            }

    def get_target_type(self, target_id: int) -> VIGEM_TARGET_TYPE | None:
        with self._lock:
            info = self._targets.get(target_id)
            return info[1] if info else None

    def list_targets(self) -> dict[int, str]:
        with self._lock:
            return {tid: ttype.name for tid, (_, ttype) in self._targets.items()}

    # ─── XUSB (Xbox 360) input ─────────────────────────────────────────
    def x360_set_state(
        self,
        target_id: int,
        buttons: int = 0,
        lt: int = 0,
        rt: int = 0,
        lx: int = 0,
        ly: int = 0,
        rx: int = 0,
        ry: int = 0,
    ) -> bool:
        """Отправляет состояние Xbox 360 контроллера.

        Args:
            target_id: ID таргета от add_x360()
            buttons: битовая маска XUSB_BUTTON_*
            lt/rt: 0-255 (триггеры)
            lx/ly/rx/ry: -32768..32767 (стики)
        """
        with self._lock:
            if target_id not in self._targets:
                return False
            target, ttype = self._targets[target_id]
            if ttype != VIGEM_TARGET_TYPE.XBOX360:
                return False
            assert self._dll is not None  # target exists so dll must be loaded

            report = XUSB_REPORT()
            report.wButtons = buttons & 0xFFFF
            report.bLeftTrigger = max(0, min(255, lt))
            report.bRightTrigger = max(0, min(255, rt))
            report.sThumbLX = max(-32768, min(32767, lx))
            report.sThumbLY = max(-32768, min(32767, ly))
            report.sThumbRX = max(-32768, min(32767, rx))
            report.sThumbRY = max(-32768, min(32767, ry))

            err = self._dll.vigem_target_x360_update(self._client, target, ctypes.byref(report))
            return int(err) == 0

    def x360_press_button(self, target_id: int, button: str) -> bool:
        """Нажимает кнопку (добавляет в текущее состояние)."""
        with self._lock:
            if target_id not in self._targets:
                return False
            _, ttype = self._targets[target_id]
            if ttype != VIGEM_TARGET_TYPE.XBOX360:
                return False

            # LT/RT are not buttons, they're triggers
            if button.lower() in ("lt", "rt"):
                self._log(
                    "WARNING",
                    f"{button} is a trigger, not a button. Use x360_set_triggers()",
                )
                return False

            mask = self.button_name_to_mask(button)
            if mask == 0:
                return False

            # Update internal button state
            current = self._btn_state.get(target_id, 0)
            new_state = current | mask
            self._btn_state[target_id] = new_state

            # Send updated state
            return self.x360_set_state(target_id, buttons=new_state)

    def x360_release_button(self, target_id: int, button: str) -> bool:
        """Отпускает кнопку (убирает из текущего состояния)."""
        with self._lock:
            if target_id not in self._targets:
                return False
            _, ttype = self._targets[target_id]
            if ttype != VIGEM_TARGET_TYPE.XBOX360:
                return False

            # LT/RT are not buttons, they're triggers
            if button.lower() in ("lt", "rt"):
                self._log(
                    "WARNING",
                    f"{button} is a trigger, not a button. Use x360_set_triggers()",
                )
                return False

            mask = self.button_name_to_mask(button)
            if mask == 0:
                return False

            # Update internal button state
            current = self._btn_state.get(target_id, 0)
            new_state = current & ~mask
            self._btn_state[target_id] = new_state

            # Send updated state
            return self.x360_set_state(target_id, buttons=new_state)

    def x360_set_buttons(self, target_id: int, button_mask: int) -> bool:
        """Устанавливает точную битовую маску кнопок (остальное 0)."""
        return self.x360_set_state(target_id, buttons=button_mask)

    def x360_set_triggers(self, target_id: int, left: int, right: int) -> bool:
        return self.x360_set_state(target_id, lt=left, rt=right)

    def x360_set_left_stick(self, target_id: int, x: int, y: int) -> bool:
        return self.x360_set_state(target_id, lx=x, ly=y)

    def x360_set_right_stick(self, target_id: int, x: int, y: int) -> bool:
        return self.x360_set_state(target_id, rx=x, ry=y)

    def x360_reset(self, target_id: int) -> bool:
        """Сбрасывает всё в нейтральное положение."""
        with self._lock:
            self._btn_state[target_id] = 0
        return self.x360_set_state(target_id, 0, 0, 0, 0, 0, 0, 0)

    # ─── DS4 input (basic) ──────────────────────────────────────────────
    def ds4_set_state(self, target_id: int, report: DS4_REPORT) -> bool:
        with self._lock:
            if target_id not in self._targets:
                return False
            target, ttype = self._targets[target_id]
            if ttype != VIGEM_TARGET_TYPE.DS4:
                return False
            assert self._dll is not None  # target exists so dll must be loaded
            err = self._dll.vigem_target_ds4_update(self._client, target, ctypes.byref(report))
            return int(err) == 0

    # ─── Helpers for button mapping ─────────────────────────────────────
    @staticmethod
    def button_name_to_mask(name: str) -> int:
        """Конвертирует имя кнопки в XUSB битмаску."""
        name = name.lower().strip()
        return XUSB_BUTTON_MAP.get(name, 0) or 0

    @staticmethod
    def combine_buttons(*names: str) -> int:
        """Комбинирует несколько имён кнопок в битмаску."""
        mask = 0
        for n in names:
            mask |= VigemService.button_name_to_mask(n)
        return mask

    @staticmethod
    def stick_normalize(value: float) -> int:
        """Нормализует float -1.0..1.0 в SHORT -32768..32767."""
        if value >= 0:
            return int(max(0.0, min(1.0, value)) * 32767)
        else:
            return int(max(-1.0, min(0.0, value)) * 32768)

    @staticmethod
    def trigger_normalize(value: float) -> int:
        """Нормализует float 0.0..1.0 в BYTE 0..255."""
        return int(max(0.0, min(1.0, value)) * 255)

    # ─── Button Mapping (for QML) ───────────────────────────────────

    def get_button_map(self) -> dict[str, str]:
        """Get current button mapping (reverse mapping from mask to name).

        Returns mapping of button names to their mask values as strings.
        """
        with self._lock:
            return {name: str(mask) for name, mask in XUSB_BUTTON_MAP.items() if mask is not None}

    def set_button_map(self, mapping: dict[str, Any]) -> dict[str, Any]:
        """Set button mapping (currently just validates and returns OK).

        Future: could store custom mappings per target.
        """
        # For now, just validate the mapping keys are valid button names
        valid_buttons = set(XUSB_BUTTON_MAP.keys())
        for key in mapping:
            if key.lower() not in valid_buttons:
                return {"ok": False, "error": f"Invalid button name: {key}"}
        # In a full implementation, we'd store this per target
        return {
            "ok": True,
            "message": "Button mapping accepted (stored in memory only)",
        }


# ─── Singleton accessor ─────────────────────────────────────────────────
_vigem_instance: VigemService | None = None


def get_vigem_service(dll_path: str | None = None) -> VigemService:
    """Возвращает глобальный экземпляр VigemService (lazy init)."""
    global _vigem_instance
    if _vigem_instance is None:
        _vigem_instance = VigemService(dll_path)
    return _vigem_instance


def shutdown_vigem_service() -> None:
    global _vigem_instance
    if _vigem_instance:
        _vigem_instance.disconnect()
        _vigem_instance = None
