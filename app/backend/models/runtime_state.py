from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, TypedDict


class Palette(TypedDict, total=False):
    """Terminal color palette definition. Single source of truth for all palettes."""
    name: str
    bg: str
    fg: str
    acc: str
    muted: str
    success: str
    danger: str
    warning: str
    icon_color: str


TERMINAL_PALETTES: dict[str, Palette] = {
    "matrix": {
        "name": "Terminal Green",
        "bg": "#0d1b0d", "fg": "#8fbf8f", "acc": "#6aa86a",
        "muted": "#3d5a3d", "success": "#8fbf8f", "danger": "#cf6a6a",
        "warning": "#d4b87a", "icon_color": "#8fbf8f",
    },
    "amber": {
        "name": "Amber CRT",
        "bg": "#1a1202", "fg": "#d4a843", "acc": "#c8963a",
        "muted": "#6b5426", "success": "#8fc97a", "danger": "#c97a7a",
        "warning": "#d4b843", "icon_color": "#d4a843",
    },
    "inverse": {
        "name": "Инверсия",
        "bg": "#e8e8e8", "fg": "#2a2a2a", "acc": "#555555",
        "muted": "#a0a0a0", "success": "#4a7a4a", "danger": "#a04040",
        "warning": "#907030", "icon_color": "#e8e8e8",
    },
    "grey": {
        "name": "Paper White",
        "bg": "#181818", "fg": "#c8c8c8", "acc": "#a0a0a0",
        "muted": "#555555", "success": "#88aa88", "danger": "#aa7777",
        "warning": "#aaa888", "icon_color": "#a0a0a0",
    },
    "synthwave": {
        "name": "Dusk",
        "bg": "#141020", "fg": "#b8a8d0", "acc": "#9888b8",
        "muted": "#5a4a7a", "success": "#7ab88a", "danger": "#b87a7a",
        "warning": "#d0b87a", "icon_color": "#b8a8d0",
    },
    "blood": {
        "name": "Crimson",
        "bg": "#1a0808", "fg": "#d08888", "acc": "#c07070",
        "muted": "#6a3a3a", "success": "#7ab88a", "danger": "#c07070",
        "warning": "#d0b87a", "icon_color": "#d08888",
    },
}


class PicoButtonMap(TypedDict):
    """Pico HID button mapping configuration."""
    space: str
    enter: str
    shift: str
    ctrl: str
    q: str
    e: str
    r: str
    tab: str
    escape: str
    w: str
    s: str
    a: str
    d: str
    mouse1: str
    mouse2: str


def default_hotkeys() -> dict[str, dict[str, str]]:
    from app.backend.services.hotkey_service import default_hotkeys as _dh
    return _dh()


@dataclass
class RuntimeState:
    # Global target (legacy, kept for compatibility)
    target_hwnd: int | None = None
    target_name: str = "GLOBAL_SCREEN"
    # Per-module target windows
    clicker_target_hwnd: int | None = None
    clicker_target_name: str = "GLOBAL_SCREEN"
    macro_target_hwnd: int | None = None
    macro_target_name: str = "GLOBAL_SCREEN"
    aim_target_hwnd: int | None = None
    aim_target_name: str = "GLOBAL_SCREEN"
    recorder_target_hwnd: int | None = None
    recorder_target_name: str = "GLOBAL_SCREEN"
    gamepad_target_hwnd: int | None = None
    gamepad_target_name: str = "GLOBAL_SCREEN"
    clicker_background_method: str = "sendinput"
    macro_background_method: str = "sendinput"
    recorder_background_method: str = "sendinput"
    theme: dict[str, str] = field(default_factory=lambda: {
        "bg": "#437835", "btn": "#2E5F24", "fg": "#DFFFE0",
        "acc": "#A5FF7A", "border": "#6FD36A", "trough": "#6FD36A",
        "danger_text": "#FF6B6B", "danger": "#220000",
        "success": "#66FF99", "warning": "#FFD166", "icon_color": "#A5FF7A",
    })
    ui_lang: str = "RU"
    is_pinned: bool = True
    hotkeys: dict[str, dict[str, str]] = field(default_factory=default_hotkeys)
    terminal_palette: str = "matrix"
    # Background input method: "sendinput" (global SendInput), "postmessage" (PostMessage to hwnd), "vigem" (ViGEm virtual gamepad), "pico" (Raspberry Pi Pico HID)
    background_method: str = "sendinput"
    # Gamepad / ViGEmBus
    gamepad_enabled: bool = False
    gamepad_controller_type: str = "X360"
    gamepad_target_index: int = 0              # 0-3 (max 4 virtual controllers)
    gamepad_background_method: str = "sendinput"  # "sendinput", "postmessage", "vigem", "pico"
    gamepad_button_map: dict[str, str] = field(default_factory=lambda: {
        "space": "A", "enter": "A",
        "shift": "LB", "ctrl": "RB",
        "q": "X", "e": "Y", "r": "B",
        "tab": "BACK", "escape": "START",
        "w": "DPAD_UP", "s": "DPAD_DOWN", "a": "DPAD_LEFT", "d": "DPAD_RIGHT",
        "mouse1": "LT", "mouse2": "RT",
    })
    # Pico Hardware Input
    pico_enabled: bool = False
    pico_port: str = ""                        # COM port (e.g. "COM3")
    pico_baudrate: int = 115200                # Baudrate (default 115200)
    pico_mode: str = "COMPOSITE"               # "KEYBOARD", "MOUSE", "GAMEPAD", "COMPOSITE"
    pico_button_map: dict[str, str] = field(default_factory=lambda: {
        "space": "A", "enter": "A",
        "shift": "LB", "ctrl": "RB",
        "q": "X", "e": "Y", "r": "B",
        "tab": "BACK", "escape": "START",
        "w": "DPAD_UP", "s": "DPAD_DOWN", "a": "DPAD_LEFT", "d": "DPAD_RIGHT",
        "mouse1": "LT", "mouse2": "RT",
    })

    # Service state flags (for test compatibility and QML binding)
    clicker_running: bool = False
    aim_running: bool = False
    macro_running: bool = False
    recorder_recording: bool = False
    recorder_playing: bool = False

    # Service configs (synced with services)
    clicker_config: dict[str, Any] = field(default_factory=lambda: {
        "interval_ms": 100, "hold_ms": 0, "button": "L", "limit": 0, "background_method": "sendinput"
    })
    aim_config: dict[str, Any] = field(default_factory=lambda: {
        "speed": 0.5, "fov": 300, "background_method": "sendinput",
        "detection_mode": "auto", "target_color": "red"
    })
    macro_config: dict[str, Any] = field(default_factory=lambda: {
        "mode": "SEQUENTIAL", "background_method": "sendinput"
    })
    recorder_config: dict[str, Any] = field(default_factory=lambda: {
        "background_method": "sendinput"
    })

    # Palettes and profiles (for test compatibility)
    palettes: dict[str, Any] = field(default_factory=lambda: TERMINAL_PALETTES)
    game_profiles: dict[str, Any] = field(default_factory=dict)

    def set_module_target(self, module: str, hwnd: int | None) -> None:
        """Set target window for a module."""
        attr = f"{module}_target_hwnd"
        if hasattr(self, attr):
            setattr(self, attr, hwnd)

    def get_module_target(self, module: str) -> dict[str, Any]:
        """Get target window for a module."""
        hwnd_attr = f"{module}_target_hwnd"
        name_attr = f"{module}_target_name"
        hwnd = getattr(self, hwnd_attr, None)
        name = getattr(self, name_attr, "GLOBAL_SCREEN")
        return {"hwnd": hwnd, "name": name}
