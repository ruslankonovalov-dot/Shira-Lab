"""app/backend/services/theme_detector.py -- Auto-detect Windows theme.

Reads registry key AppsUseLightTheme to auto-detect dark/light mode.
"""
from __future__ import annotations

import logging
import platform
from typing import Dict, Literal, Callable, Optional

logger = logging.getLogger(__name__)

Theme = str


def detect_windows_theme() -> Theme:
    """Return 'dark' or 'light' based on Windows system theme.

    On non-Windows returns 'dark' as safe default.
    """
    if platform.system() != "Windows":
        return "dark"

    try:
        import winreg
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize"
        )
        try:
            value, _ = winreg.QueryValueEx(key, "AppsUseLightTheme")
            return "light" if value == 1 else "dark"
        finally:
            winreg.CloseKey(key)
    except FileNotFoundError:
        # Key doesn't exist -- older Windows version
        return "dark"
    except OSError as e:
        logger.warning("Failed to detect Windows theme: %s", e)
        return "dark"


def on_theme_change(callback: Callable[[], None]) -> None:
    """Register callback to be called when theme changes.

    TODO: Implement via WMI subscription or polling timer.
    """
    # Placeholder for future implementation
    # Possible approaches:
    # 1. WMI event subscription on RegistryKeyChangeEvent
    # 2. Polling every 5 seconds via QTimer
    # 3. WM_SETTINGCHANGE hook (but not all apps send it)
    logger.debug("Theme change subscription not yet implemented")


# ─── Recommended palettes for each theme ────────────────────

DARK_PALETTE: Dict[str, Dict[str, str]] = {
    "matrix": {"bg": "#000000", "fg": "#00FF00"},
    "cyberpunk": {"bg": "#0A0014", "fg": "#FF00FF"},
    "amber": {"bg": "#1A0F00", "fg": "#FFB000"},
}

LIGHT_PALETTE: Dict[str, Dict[str, str]] = {
    "matrix": {"bg": "#F0F0F0", "fg": "#006600"},
    "cyberpunk": {"bg": "#F8F0F8", "fg": "#990099"},
    "amber": {"bg": "#FFFAF0", "fg": "#996600"},
}


def get_palette_for_theme(theme: Theme, palette_id: str = "matrix") -> Dict[str, str]:
    """Return palette taking system theme into account."""
    source = LIGHT_PALETTE if theme == "light" else DARK_PALETTE
    return source.get(palette_id, source["matrix"])
