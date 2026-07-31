# window_utils.py — Win32 helpers
import ctypes
from ctypes import wintypes

GWL_EXSTYLE = -20
WS_EX_APPWINDOW = 0x00040000
WS_EX_TOPMOST = 0x00000008
WS_EX_TOOLWINDOW = 0x00000080

HWND_TOPMOST = wintypes.HWND(-1)
HWND_NOTOPMOST = wintypes.HWND(-2)

SWP_NOMOVE = 0x0002
SWP_NOSIZE = 0x0001
SWP_SHOWWINDOW = 0x0040
SWP_NOACTIVATE = 0x0010

SPI_GETWORKAREA = 0x0030

user32 = ctypes.windll.user32

# WNDENUMPROC нужно определять вручную — нет в wintypes
WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

user32.SetWindowPos.argtypes = [wintypes.HWND, wintypes.HWND, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, wintypes.UINT]
user32.SetWindowPos.restype = wintypes.BOOL
user32.GetWindowLongW.argtypes = [wintypes.HWND, ctypes.c_int]
user32.GetWindowLongW.restype = ctypes.c_long
user32.SetWindowLongW.argtypes = [wintypes.HWND, ctypes.c_int, ctypes.c_long]
user32.SetWindowLongW.restype = ctypes.c_long
user32.FindWindowW.argtypes = [wintypes.LPCWSTR, wintypes.LPCWSTR]
user32.FindWindowW.restype = wintypes.HWND
user32.GetForegroundWindow.argtypes = []
user32.GetForegroundWindow.restype = wintypes.HWND
user32.IsWindowVisible.argtypes = [wintypes.HWND]
user32.IsWindowVisible.restype = wintypes.BOOL
user32.GetWindowTextLengthW.argtypes = [wintypes.HWND]
user32.GetWindowTextLengthW.restype = ctypes.c_int
user32.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
user32.GetWindowTextW.restype = ctypes.c_int
user32.EnumWindows.argtypes = [WNDENUMPROC, wintypes.LPARAM]
user32.EnumWindows.restype = wintypes.BOOL
user32.SystemParametersInfoW.argtypes = [wintypes.UINT, wintypes.UINT, ctypes.c_void_p, wintypes.UINT]
user32.SystemParametersInfoW.restype = wintypes.BOOL


def set_window_topmost(hwnd: int, pinned: bool) -> None:
    if not hwnd:
        return
    hwnd_c = wintypes.HWND(hwnd)
    try:
        ex_style = user32.GetWindowLongW(hwnd_c, GWL_EXSTYLE)
    except Exception:
        ex_style = 0
    if pinned:
        new_style = ex_style | WS_EX_TOPMOST
        insert_after = HWND_TOPMOST
    else:
        new_style = ex_style & ~WS_EX_TOPMOST
        insert_after = HWND_NOTOPMOST
    if new_style != ex_style:
        try:
            user32.SetWindowLongW(hwnd_c, GWL_EXSTYLE, ctypes.c_long(new_style))
        except Exception:
            pass
    flags = SWP_NOMOVE | SWP_NOSIZE | SWP_SHOWWINDOW
    try:
        user32.SetWindowPos(hwnd_c, insert_after, 0, 0, 0, 0, flags)
    except Exception:
        pass


def set_overlay_always_topmost(hwnd: int) -> None:
    """Make the overlay ALWAYS topmost with highest priority.

    Sets WS_EX_TOPMOST | WS_EX_TOOLWINDOW:
    - WS_EX_TOPMOST: always above non-topmost windows (including the app window)
    - WS_EX_TOOLWINDOW: hides from taskbar and Alt+Tab (replaces Qt.Tool flag)

    Then calls SetWindowPos with HWND_TOPMOST to assert Z-order.
    This is called AFTER any app pin operation to ensure overlay stays above app.
    """
    if not hwnd:
        return
    hwnd_c = wintypes.HWND(hwnd)
    try:
        ex_style = user32.GetWindowLongW(hwnd_c, GWL_EXSTYLE)
    except Exception:
        ex_style = 0
    # Add TOPMOST + TOOLWINDOW, keep any existing flags
    new_style = ex_style | WS_EX_TOPMOST | WS_EX_TOOLWINDOW
    if new_style != ex_style:
        try:
            user32.SetWindowLongW(hwnd_c, GWL_EXSTYLE, ctypes.c_long(new_style))
        except Exception:
            pass
    # Assert Z-order: TOPMOST with NOACTIVATE (don't steal focus)
    flags = SWP_NOMOVE | SWP_NOSIZE | SWP_SHOWWINDOW | SWP_NOACTIVATE
    try:
        user32.SetWindowPos(hwnd_c, HWND_TOPMOST, 0, 0, 0, 0, flags)
    except Exception:
        pass


def get_work_area() -> tuple[int, int, int, int]:
    """Returns (x, y, width, height) of the work area (excluding taskbar).

    Uses SystemParametersInfoW with SPI_GETWORKAREA — this is the most
    reliable way to get the available desktop area on Windows.
    """
    try:
        rect = wintypes.RECT()
        if user32.SystemParametersInfoW(SPI_GETWORKAREA, 0, ctypes.byref(rect), 0):
            return (rect.left, rect.top, rect.right - rect.left, rect.bottom - rect.top)
    except Exception:
        pass
    # Fallback: assume 1920x1080 with 40px taskbar
    return (0, 0, 1920, 1040)


# ─── Monitor-specific work area (for multi-monitor) ──────────────────
MONITOR_DEFAULTTONEAREST = 0x00000002

class MONITORINFO(ctypes.Structure):
    _fields_ = [
        ("cbSize", wintypes.DWORD),
        ("rcMonitor", wintypes.RECT),
        ("rcWork", wintypes.RECT),
        ("dwFlags", wintypes.DWORD),
    ]

try:
    user32.MonitorFromWindow.argtypes = [wintypes.HWND, wintypes.DWORD]
    user32.MonitorFromWindow.restype = wintypes.HANDLE
    user32.GetMonitorInfoW.argtypes = [wintypes.HANDLE, ctypes.POINTER(MONITORINFO)]
    user32.GetMonitorInfoW.restype = wintypes.BOOL
except Exception:
    pass


def get_work_area_for_window(hwnd: int) -> tuple[int, int, int, int]:
    """Get work area for the monitor that the given window is on.

    This is more accurate than SPI_GETWORKAREA for multi-monitor setups.
    Returns (x, y, width, height) excluding the taskbar.
    """
    if not hwnd:
        return get_work_area()
    try:
        hmon = user32.MonitorFromWindow(wintypes.HWND(hwnd), MONITOR_DEFAULTTONEAREST)
        mi = MONITORINFO()
        mi.cbSize = ctypes.sizeof(mi)
        if user32.GetMonitorInfoW(hmon, ctypes.byref(mi)):
            return (mi.rcWork.left, mi.rcWork.top,
                    mi.rcWork.right - mi.rcWork.left,
                    mi.rcWork.bottom - mi.rcWork.top)
    except Exception:
        pass
    return get_work_area()


def clamp_to_work_area(hwnd: int, x: int, y: int, w: int, h: int) -> tuple[int, int]:
    """Clamp window position so it stays within the work area (no taskbar overlap).

    Returns (clamped_x, clamped_y).
    """
    wa_x, wa_y, wa_w, wa_h = get_work_area_for_window(hwnd)
    # Clamp X: keep window fully visible horizontally
    cx = max(wa_x, min(x, wa_x + wa_w - w))
    # Clamp Y: keep window fully visible vertically, NEVER below work area
    cy = max(wa_y, min(y, wa_y + wa_h - h))
    return (cx, cy)


def find_app_hwnd(title: str = "Shira Lab") -> int:
    """Find application window by title."""
    try:
        hwnd = user32.FindWindowW(None, title)
        if hwnd:
            return int(hwnd)
    except Exception:
        pass
    return 0


def get_foreground_hwnd() -> int:
    """Get currently foreground window handle."""
    try:
        hwnd = user32.GetForegroundWindow()
        if hwnd:
            return int(hwnd)
    except Exception:
        pass
    return 0


def get_visible_windows() -> list[tuple[int, str]]:
    """Get list of visible windows as (hwnd, title) tuples."""
    windows: list[tuple[int, str]] = []

    def enum_handler(hwnd: wintypes.HWND, _: wintypes.LPARAM) -> int:
        if user32.IsWindowVisible(hwnd):
            length = user32.GetWindowTextLengthW(hwnd)
            if length > 0:
                buff = ctypes.create_unicode_buffer(length + 1)
                user32.GetWindowTextW(hwnd, buff, length + 1)
                windows.append((int(hwnd), buff.value))
        return True

    user32.EnumWindows(WNDENUMPROC(enum_handler), 0)
    return windows


def get_monitors() -> list[dict[str, int]]:
    """Get list of monitors with work areas.

    Returns list of dicts: [{x, y, width, height, work_x, work_y, work_width, work_height}, ...]
    """
    monitors: list[dict[str, int]] = []

    def enum_monitor_proc(hmon: wintypes.HANDLE, _: wintypes.HANDLE, __: wintypes.LPRECT, ___: wintypes.LPARAM) -> int:
        mi = MONITORINFO()
        mi.cbSize = ctypes.sizeof(mi)
        if user32.GetMonitorInfoW(hmon, ctypes.byref(mi)):
            monitors.append({
                "x": mi.rcMonitor.left,
                "y": mi.rcMonitor.top,
                "width": mi.rcMonitor.right - mi.rcMonitor.left,
                "height": mi.rcMonitor.bottom - mi.rcMonitor.top,
                "work_x": mi.rcWork.left,
                "work_y": mi.rcWork.top,
                "work_width": mi.rcWork.right - mi.rcWork.left,
                "work_height": mi.rcWork.bottom - mi.rcWork.top,
            })
        return True

    MONITORENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HANDLE, wintypes.HANDLE, ctypes.POINTER(wintypes.RECT), wintypes.LPARAM)
    try:
        user32.EnumDisplayMonitors(None, None, MONITORENUMPROC(enum_monitor_proc), 0)
    except Exception:
        # Fallback
        wa = get_work_area()
        monitors.append({
            "x": wa[0], "y": wa[1], "width": wa[2], "height": wa[3],
            "work_x": wa[0], "work_y": wa[1], "work_width": wa[2], "work_height": wa[3],
        })

    return monitors