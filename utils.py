# utils.py — Win32 PostMessageW helpers
import ctypes

user32 = ctypes.windll.user32

WM_KEYDOWN = 0x0100
WM_KEYUP = 0x0101
WM_LBUTTONDOWN = 0x0201
WM_LBUTTONUP = 0x0202
WM_RBUTTONDOWN = 0x0204
WM_RBUTTONUP = 0x0205
WM_MBUTTONDOWN = 0x0207
WM_MBUTTONUP = 0x0208
WM_XBUTTONDOWN = 0x020B
WM_XBUTTONUP = 0x020C
MK_LBUTTON = 0x0001
MK_RBUTTON = 0x0002
MK_MBUTTON = 0x0010
MK_XBUTTON1 = 0x0020
MK_XBUTTON2 = 0x0040

_VK_MAP: dict[str, int] = {
    "space": 0x20,
    "enter": 0x0D,
    "return": 0x0D,
    "tab": 0x09,
    "esc": 0x1B,
    "escape": 0x1B,
    "backspace": 0x08,
    "delete": 0x2E,
    "insert": 0x2D,
    "home": 0x24,
    "end": 0x23,
    "pageup": 0x21,
    "pagedown": 0x22,
    "shift": 0x10,
    "ctrl": 0x11,
    "control": 0x11,
    "alt": 0x12,
    "left": 0x25,
    "up": 0x26,
    "right": 0x27,
    "down": 0x28,
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
}

_BUTTON_MSG: dict[str, tuple[int, int, int, int]] = {
    "L": (WM_LBUTTONDOWN, WM_LBUTTONUP, MK_LBUTTON, 0),
    "R": (WM_RBUTTONDOWN, WM_RBUTTONUP, MK_RBUTTON, 0),
    "M": (WM_MBUTTONDOWN, WM_MBUTTONUP, MK_MBUTTON, 0),
    "X1": (WM_XBUTTONDOWN, WM_XBUTTONUP, MK_XBUTTON1, 1),
    "X2": (WM_XBUTTONDOWN, WM_XBUTTONUP, MK_XBUTTON2, 2),
}


def _make_lparam(x: int, y: int) -> int:
    return (y << 16) | (x & 0xFFFF)


def _vk_from_name(key: str) -> int | None:
    k = (key or "").strip().lower()
    if not k:
        return None
    if k in _VK_MAP:
        return _VK_MAP[k]
    if len(k) == 1 and k.isalnum():
        return ord(k.upper())
    return None


def send_background_click(hwnd: int, x: int = 0, y: int = 0, button: str = "L") -> None:
    if not hwnd:
        return
    info = _BUTTON_MSG.get(str(button).upper(), _BUTTON_MSG["L"])
    down, up, wparam_base, x_btn = info
    lparam = _make_lparam(int(x), int(y))
    if str(button).upper() in ("X1", "X2"):
        wparam_full = (x_btn << 16) | wparam_base
        user32.PostMessageW(hwnd, down, wparam_full, lparam)
        user32.PostMessageW(hwnd, up, wparam_full, lparam)
    else:
        user32.PostMessageW(hwnd, down, wparam_base, lparam)
        user32.PostMessageW(hwnd, up, wparam_base, lparam)


def send_background_key(hwnd: int, key: str) -> None:
    if not hwnd:
        return
    vk = _vk_from_name(key)
    if vk is None:
        return
    user32.PostMessageW(hwnd, WM_KEYDOWN, vk, 0x00000001)
    user32.PostMessageW(hwnd, WM_KEYUP, vk, 0xC0000001)


def send_background_click_up(hwnd: int, button: str, x: int = 0, y: int = 0) -> bool:
    """PostMessage WM_*UP only (for background release)."""
    if not hwnd:
        return False
    button = str(button).upper()
    info = _BUTTON_MSG.get(button)
    if not info:
        return False
    _down, up, wparam_base, x_btn = info
    lparam = _make_lparam(int(x), int(y))
    if button in ("X1", "X2"):
        wparam_full = (x_btn << 16) | wparam_base
        user32.PostMessageW(hwnd, up, wparam_full, lparam)
    else:
        user32.PostMessageW(hwnd, up, wparam_base, lparam)
    return True


def send_background_key_up(hwnd: int, key: str) -> bool:
    """PostMessage WM_KEYUP only (for background release)."""
    if not hwnd:
        return False
    vk = _vk_from_name(key)
    if vk is None:
        return False
    user32.PostMessageW(hwnd, WM_KEYUP, vk, 0xC0000001)
    return True


__all__ = [
    "send_background_click",
    "send_background_click_up",
    "send_background_key",
    "send_background_key_up",
]
