#!/usr/bin/env python3
"""Shira Lab — точка входа."""
# CRITICAL: Set AppUserModelID BEFORE any imports or QApplication creation.
# This prevents Windows from showing the default Python icon in the taskbar
# during the 2-3 seconds it takes to import PySide6 and create the window.
import os
import sys

if sys.platform == "win32":
    try:
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("ShiraLab.ShiraLab")
    except Exception:  # noqa: BLE001 - best effort for AppUserModelID
        pass

# Set style env var BEFORE importing PySide6
os.environ["QT_QUICK_CONTROLS_STYLE"] = "Basic"

from app.main import main

if __name__ == "__main__":
    main()
