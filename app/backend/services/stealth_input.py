"""
stealth_input.py — Stealth-отправка ввода через Win32 SendInput с scancodes.

Зачем:
    Обычные методы (keyboard.press, mouse_event, PostMessage) детектятся
    античитами и играми с raw input:
    - keyboard lib использует WH_KEYBOARD_LL hook — виден в Hook Chain
    - mouse_event помечает события флагом LLKHF_INJECTED
    - PostMessage не доходит до DirectX окон

    SendInput с флагом KEYEVENTF_SCANCODE отправляет события на уровне
    hardware simulation — Win32 помечает их как "real" hardware events.
    Большинство игр и приложений их принимают.

Ограничения:
    - НЕ обходит kernel-level античиты (EasyAntiCheat, BattlEye, Vanguard)
    - НЕ работает для окон с UIPI (более высокий integrity level)
    - Требует что окно-цель было в фокусе (для клавиатуры)

Использование:
    from app.backend.services.stealth_input import StealthInput
    s = StealthInput()
    s.send_key_scancode(0x1E)  # scancode 'A'
    s.send_mouse_click('L')
"""

from __future__ import annotations

import ctypes
import logging
from ctypes import wintypes
from typing import ClassVar

logger = logging.getLogger(__name__)


# ─── Win32 constants ────────────────────────────────────────────────────
INPUT_MOUSE = 0
INPUT_KEYBOARD = 1

KEYEVENTF_EXTENDEDKEY = 0x0001
KEYEVENTF_KEYUP = 0x0002
KEYEVENTF_SCANCODE = 0x0008
KEYEVENTF_UNICODE = 0x0004

MOUSEEVENTF_MOVE = 0x0001
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004
MOUSEEVENTF_RIGHTDOWN = 0x0008
MOUSEEVENTF_RIGHTUP = 0x0010
MOUSEEVENTF_MIDDLEDOWN = 0x0020
MOUSEEVENTF_MIDDLEUP = 0x0040
MOUSEEVENTF_XDOWN = 0x0080
MOUSEEVENTF_XUP = 0x0100
MOUSEEVENTF_WHEEL = 0x0800
MOUSEEVENTF_HWHEEL = 0x1000
MOUSEEVENTF_ABSOLUTE = 0x8000

XBUTTON1 = 0x0001
XBUTTON2 = 0x0002

WHEEL_DELTA = 120

# AttachThreadInput constants
ATTACH_THREAD_INPUT = True
DETACH_THREAD_INPUT = False


# ─── Win32 structures ───────────────────────────────────────────────────
class MOUSEINPUT(ctypes.Structure):
    _fields_ = [
        ("dx", wintypes.LONG),
        ("dy", wintypes.LONG),
        ("mouseData", wintypes.DWORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.POINTER(wintypes.ULONG)),
    ]


class KEYBDINPUT(ctypes.Structure):
    _fields_ = [
        ("wVk", wintypes.WORD),
        ("wScan", wintypes.WORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.POINTER(wintypes.ULONG)),
    ]


class HARDWAREINPUT(ctypes.Structure):
    _fields_ = [
        ("uMsg", wintypes.DWORD),
        ("wParamL", wintypes.WORD),
        ("wParamH", wintypes.WORD),
    ]


class _INPUT_UNION(ctypes.Union):
    _fields_: ClassVar = [
        ("mi", MOUSEINPUT),
        ("ki", KEYBDINPUT),
        ("hi", HARDWAREINPUT),
    ]


class INPUT(ctypes.Structure):
    _anonymous_ = ("_input",)
    _fields_ = [
        ("type", wintypes.DWORD),
        ("_input", _INPUT_UNION),
    ]


_user32 = ctypes.windll.user32
_user32.SendInput.argtypes = [wintypes.UINT, ctypes.POINTER(INPUT), ctypes.c_int]
_user32.SendInput.restype = wintypes.UINT

_user32.MapVirtualKeyW.argtypes = [wintypes.UINT, wintypes.UINT]
_user32.MapVirtualKeyW.restype = wintypes.UINT

_user32.GetCursorPos.argtypes = [ctypes.POINTER(wintypes.POINT)]
_user32.GetCursorPos.restype = wintypes.BOOL

# AttachThreadInput functions
_user32.AttachThreadInput.argtypes = [wintypes.DWORD, wintypes.DWORD, wintypes.BOOL]
_user32.AttachThreadInput.restype = wintypes.BOOL
_user32.GetWindowThreadProcessId.argtypes = [
    wintypes.HWND,
    ctypes.POINTER(wintypes.DWORD),
]
_user32.GetWindowThreadProcessId.restype = wintypes.DWORD
_kernel32 = ctypes.windll.kernel32
_kernel32.GetCurrentThreadId.argtypes = []
_kernel32.GetCurrentThreadId.restype = wintypes.DWORD


# VK → scancode через MAPVK_VK_TO_VSC
MAPVK_VK_TO_VSC = 0


class StealthInput:
    """
    Stealth-отправка ввода через SendInput с scancodes.

    Преимущества:
    - События помечаются как hardware-sourced (через scancode)
    - Не использует low-level hooks (не виден в Hook Chain)
    - Работает в большинстве игр и приложений

    Недостатки:
    - Не обходит kernel anti-cheat
    - Глобальный ввод (не фоновый) — нужно окно-цель в фокусе
    """

    # VK-коды для мыши (используются для макросов, не для SendInput)
    # SendInput для мыши использует MOUSEINPUT, не KEYBDINPUT

    @staticmethod
    def _make_keyboard_input(scancode: int, key_up: bool = False, extended: bool = False) -> INPUT:
        """Создаёт INPUT структуру для клавиши по scancode."""
        flags = KEYEVENTF_SCANCODE
        if extended:
            flags |= KEYEVENTF_EXTENDEDKEY
        if key_up:
            flags |= KEYEVENTF_KEYUP
        inp = INPUT()
        inp.type = INPUT_KEYBOARD
        inp.ki.wVk = 0
        inp.ki.wScan = scancode
        inp.ki.dwFlags = flags
        inp.ki.time = 0
        inp.ki.dwExtraInfo = ctypes.pointer(wintypes.ULONG(0))
        return inp

    @staticmethod
    def _make_mouse_input(flags: int, data: int = 0) -> INPUT:
        """Создаёт INPUT структуру для мыши."""
        inp = INPUT()
        inp.type = INPUT_MOUSE
        inp.mi.dx = 0
        inp.mi.dy = 0
        inp.mi.mouseData = data
        inp.mi.dwFlags = flags
        inp.mi.time = 0
        inp.mi.dwExtraInfo = ctypes.pointer(wintypes.ULONG(0))
        return inp

    @staticmethod
    def send_key_scancode(scancode: int, hold_ms: int = 0, extended: bool = False) -> bool:
        """
        Отправляет keydown + keyup для клавиши по scancode.

        Параметры:
            scancode: hardware scancode клавиши (например 0x1E для 'A')
            hold_ms: сколько держать нажатой (0 = моментально)
            extended: True для расширенных клавиш (Right Alt, Right Ctrl, Numpad)

        Возвращает True при успехе.
        """
        import time

        try:
            down = StealthInput._make_keyboard_input(scancode, key_up=False, extended=extended)
            up = StealthInput._make_keyboard_input(scancode, key_up=True, extended=extended)

            inputs = (INPUT * 1)(down)
            sent: int = _user32.SendInput(1, inputs, ctypes.sizeof(INPUT))
            if sent != 1:
                return False

            if hold_ms > 0:
                time.sleep(hold_ms / 1000.0)

            inputs = (INPUT * 1)(up)
            sent = _user32.SendInput(1, inputs, ctypes.sizeof(INPUT))
            return bool(sent == 1)
        except (OSError, RuntimeError, ValueError, AttributeError):
            logger.debug("Failed to send key via SendInput")
            return False

    @staticmethod
    def send_key_vk(vk: int, hold_ms: int = 0) -> bool:
        """
        Отправляет клавишу по VK-коду, конвертируя в scancode через
        MapVirtualKeyW(MAPVK_VK_TO_VSC).
        """
        try:
            scancode = _user32.MapVirtualKeyW(vk, MAPVK_VK_TO_VSC)
            if not scancode:
                return False
            # Comprehensive extended key set
            EXTENDED_VK = {
                0xA3,  # RCONTROL
                0xA5,  # RMENU (Right Alt)
                0x21,  # PageUp
                0x22,  # PageDown
                0x23,  # End
                0x24,  # Home
                0x25,  # Left Arrow
                0x26,  # Up Arrow
                0x27,  # Right Arrow
                0x28,  # Down Arrow
                0x2D,  # Insert
                0x2E,  # Delete
                0x6A,  # Multiply (Numpad *)
                0x6B,  # Add (Numpad +)
                0x6D,  # Subtract (Numpad -)
                0x6E,  # Decimal (Numpad .)
                0x6F,  # Divide (Numpad /)
            }
            extended = vk in EXTENDED_VK
            return StealthInput.send_key_scancode(scancode, hold_ms, extended)
        except (OSError, RuntimeError, ValueError, AttributeError):
            logger.debug("Failed to send key VK via SendInput")
            return False

    @staticmethod
    def send_mouse_click(button: str = "L", hold_ms: int = 0) -> bool:
        """
        Отправляет клик мыши в текущей позиции курсора.

        button: "L", "R", "M", "X1", "X2"
        """
        import time

        try:
            button = button.upper()
            if button == "L":
                down_flags = MOUSEEVENTF_LEFTDOWN
                up_flags = MOUSEEVENTF_LEFTUP
                data = 0
            elif button == "R":
                down_flags = MOUSEEVENTF_RIGHTDOWN
                up_flags = MOUSEEVENTF_RIGHTUP
                data = 0
            elif button == "M":
                down_flags = MOUSEEVENTF_MIDDLEDOWN
                up_flags = MOUSEEVENTF_MIDDLEUP
                data = 0
            elif button == "X1":
                down_flags = MOUSEEVENTF_XDOWN
                up_flags = MOUSEEVENTF_XUP
                data = XBUTTON1
            elif button == "X2":
                down_flags = MOUSEEVENTF_XDOWN
                up_flags = MOUSEEVENTF_XUP
                data = XBUTTON2
            else:
                return False

            down = StealthInput._make_mouse_input(down_flags, data)
            inputs = (INPUT * 1)(down)
            sent: int = _user32.SendInput(1, inputs, ctypes.sizeof(INPUT))
            if sent != 1:
                return False

            if hold_ms > 0:
                time.sleep(hold_ms / 1000.0)

            up = StealthInput._make_mouse_input(up_flags, data)
            inputs = (INPUT * 1)(up)
            sent = _user32.SendInput(1, inputs, ctypes.sizeof(INPUT))
            return bool(sent == 1)
        except (OSError, RuntimeError, ValueError, AttributeError):
            logger.debug("Failed to send mouse click via SendInput")
            return False

    @staticmethod
    def send_mouse_wheel(direction: str = "up", delta: int = WHEEL_DELTA) -> bool:
        """
        Отправляет колесо мыши.

        direction: "up", "down", "left", "right"
        delta: величина прокрутки (по умолчанию 120 = 1 notch)
        """
        try:
            direction = direction.lower()
            if direction == "up":
                flags = MOUSEEVENTF_WHEEL
                data = delta
            elif direction == "down":
                flags = MOUSEEVENTF_WHEEL
                data = -delta
            elif direction == "right":
                flags = MOUSEEVENTF_HWHEEL
                data = delta
            elif direction == "left":
                flags = MOUSEEVENTF_HWHEEL
                data = -delta
            else:
                return False

            inp = StealthInput._make_mouse_input(flags, data)
            inputs = (INPUT * 1)(inp)
            sent: int = _user32.SendInput(1, inputs, ctypes.sizeof(INPUT))
            return bool(sent == 1)
        except (OSError, RuntimeError, ValueError, AttributeError):
            logger.debug("Failed to send mouse wheel via SendInput")
            return False

    @staticmethod
    def send_mouse_move(dx: int, dy: int, absolute: bool = False) -> bool:
        """
        Перемещает курсор на dx/dy пикселей (relative) или в абсолютные
        координаты 0..65535 (absolute).
        """
        try:
            flags = MOUSEEVENTF_MOVE
            if absolute:
                flags |= MOUSEEVENTF_ABSOLUTE
            inp = StealthInput._make_mouse_input(flags, 0)
            inp.mi.dx = dx
            inp.mi.dy = dy
            inputs = (INPUT * 1)(inp)
            sent: int = _user32.SendInput(1, inputs, ctypes.sizeof(INPUT))
            return bool(sent == 1)
        except (OSError, RuntimeError, ValueError, AttributeError):
            logger.debug("Failed to send mouse move via SendInput")
            return False

    # ─── AttachThreadInput + SendInput (background input to specific window) ────
    @staticmethod
    def _attach_thread_input(hwnd: int, attach: bool = True) -> bool:
        """
        Attaches/detaches current thread input to target window's thread.
        Required for SendInput to work with background/inactive windows.
        """
        try:
            if hwnd == 0:
                return False
            target_tid: int = _user32.GetWindowThreadProcessId(hwnd, None)
            current_tid: int = _kernel32.GetCurrentThreadId()
            if target_tid == 0 or target_tid == current_tid:
                return False
            result: int = _user32.AttachThreadInput(current_tid, target_tid, attach)
            return bool(result)
        except (OSError, RuntimeError, ValueError, AttributeError):
            logger.debug("Failed to attach/detach thread input")
            return False

    @staticmethod
    def send_key_scancode_attached(
        hwnd: int, scancode: int, hold_ms: int = 0, extended: bool = False
    ) -> bool:
        """
        Send keystroke to specific window using AttachThreadInput + SendInput.
        This works for background/inactive windows in many games without anticheat.

        Parameters:
            hwnd: Target window handle
            scancode: Hardware scancode
            hold_ms: Hold duration in milliseconds
            extended: True for extended keys (Right Alt, Right Ctrl, arrows, etc.)
        """
        import time

        if not hwnd:
            return False
        # Attach
        if not StealthInput._attach_thread_input(hwnd, True):
            return False
        try:
            down = StealthInput._make_keyboard_input(scancode, key_up=False, extended=extended)
            up = StealthInput._make_keyboard_input(scancode, key_up=True, extended=extended)

            inputs = (INPUT * 1)(down)
            sent: int = _user32.SendInput(1, inputs, ctypes.sizeof(INPUT))
            if sent != 1:
                return False

            if hold_ms > 0:
                time.sleep(hold_ms / 1000.0)

            inputs = (INPUT * 1)(up)
            sent = _user32.SendInput(1, inputs, ctypes.sizeof(INPUT))
            return bool(sent == 1)
        finally:
            # Always detach
            StealthInput._attach_thread_input(hwnd, False)

    @staticmethod
    def send_key_vk_attached(hwnd: int, vk: int, hold_ms: int = 0) -> bool:
        """
        Send keystroke by VK code to specific window using AttachThreadInput + SendInput.
        """
        try:
            scancode = _user32.MapVirtualKeyW(vk, MAPVK_VK_TO_VSC)
            if not scancode:
                return False
            extended = vk in (0xA3, 0xA5)  # RCONTROL, RMENU
            return StealthInput.send_key_scancode_attached(hwnd, scancode, hold_ms, extended)
        except (OSError, RuntimeError, ValueError, AttributeError):
            logger.debug("Failed to send key VK attached")
            return False

    @staticmethod
    def send_mouse_click_attached(hwnd: int, button: str = "L", hold_ms: int = 0) -> bool:
        """
        Send mouse click to specific window using AttachThreadInput + SendInput.
        Works for background/inactive windows in many games without anticheat.

        button: "L", "R", "M", "X1", "X2"
        """
        import time

        try:
            button = button.upper()
            if button == "L":
                down_flags = MOUSEEVENTF_LEFTDOWN
                up_flags = MOUSEEVENTF_LEFTUP
                data = 0
            elif button == "R":
                down_flags = MOUSEEVENTF_RIGHTDOWN
                up_flags = MOUSEEVENTF_RIGHTUP
                data = 0
            elif button == "M":
                down_flags = MOUSEEVENTF_MIDDLEDOWN
                up_flags = MOUSEEVENTF_MIDDLEUP
                data = 0
            elif button == "X1":
                down_flags = MOUSEEVENTF_XDOWN
                up_flags = MOUSEEVENTF_XUP
                data = XBUTTON1
            elif button == "X2":
                down_flags = MOUSEEVENTF_XDOWN
                up_flags = MOUSEEVENTF_XUP
                data = XBUTTON2
            else:
                return False

            # Attach
            if not StealthInput._attach_thread_input(hwnd, True):
                return False

            try:
                down = StealthInput._make_mouse_input(down_flags, data)
                inputs = (INPUT * 1)(down)
                sent: int = _user32.SendInput(1, inputs, ctypes.sizeof(INPUT))
                if sent != 1:
                    return False

                if hold_ms > 0:
                    time.sleep(hold_ms / 1000.0)

                up = StealthInput._make_mouse_input(up_flags, data)
                inputs = (INPUT * 1)(up)
                sent = _user32.SendInput(1, inputs, ctypes.sizeof(INPUT))
                return bool(sent == 1)
            finally:
                StealthInput._attach_thread_input(hwnd, False)
        except (OSError, RuntimeError, ValueError, AttributeError):
            logger.debug("Failed to send mouse click attached")
            return False


# ─── VK-таблица для удобства (используется макросами) ───────────────────
VK_MAP = {
    # Letters (VK codes = ASCII uppercase)
    **{chr(c): c for c in range(ord("A"), ord("Z") + 1)},
    **{str(c): c + ord("0") for c in range(10)},  # 0-9
    # Function keys
    "f1": 0x70,
    "f2": 0x71,
    "f3": 0x72,
    "f4": 0x73,
    "f5": 0x74,
    "f6": 0x75,
    "f7": 0x76,
    "f8": 0x77,
    "f9": 0x78,
    "f10": 0x79,
    "f11": 0x7A,
    "f12": 0x7B,
    # Modifiers
    "shift": 0x10,
    "ctrl": 0x11,
    "alt": 0x12,
    "menu": 0x12,
    "left shift": 0xA0,
    "right shift": 0xA1,
    "left ctrl": 0xA2,
    "right ctrl": 0xA3,
    "left alt": 0xA4,
    "left menu": 0xA4,
    "right alt": 0xA5,
    "right menu": 0xA5,
    "left windows": 0x5B,
    "right windows": 0x5C,
    "windows": 0x5B,
    # Navigation
    "space": 0x20,
    "enter": 0x0D,
    "return": 0x0D,
    "tab": 0x09,
    "esc": 0x1B,
    "escape": 0x1B,
    "backspace": 0x08,
    "delete": 0x2E,
    "del": 0x2E,
    "insert": 0x2D,
    "home": 0x24,
    "end": 0x23,
    "pageup": 0x21,
    "page up": 0x21,
    "pagedown": 0x22,
    "page down": 0x22,
    # Arrows
    "up": 0x26,
    "down": 0x28,
    "left": 0x25,
    "right": 0x27,
    # Special
    "caps lock": 0x14,
    "num lock": 0x90,
    "scroll lock": 0x91,
    "print screen": 0x2C,
    "pause": 0x13,
}


def vk_from_name(name: str) -> int | None:
    """Возвращает VK-код по имени клавиши. None если неизвестно."""
    k = (name or "").strip().lower()
    if not k:
        return None
    return VK_MAP.get(k)
