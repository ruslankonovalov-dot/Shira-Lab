"""app/main.py — PySide6 entry point с терминальным UI."""

from __future__ import annotations

import ctypes
import logging
import logging.handlers
import sys
from ctypes import wintypes
from pathlib import Path

from PySide6.QtCore import QObject, QTimer, QUrl
from PySide6.QtGui import QFont, QIcon, QWindow
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuick import QQuickWindow
from PySide6.QtWidgets import QApplication

# ─── Win32 constants for overlay click-through ─────────────────────────
GWL_EXSTYLE = -20
WS_EX_LAYERED = 0x00080000
WS_EX_TRANSPARENT = 0x00000020
WS_EX_NOACTIVATE = 0x08000000

_user32 = ctypes.windll.user32
_user32.GetWindowLongW.argtypes = [wintypes.HWND, ctypes.c_int]
_user32.GetWindowLongW.restype = ctypes.c_long
_user32.SetWindowLongW.argtypes = [wintypes.HWND, ctypes.c_int, ctypes.c_long]
_user32.SetWindowLongW.restype = ctypes.c_long
_user32.SetLayeredWindowAttributes.argtypes = [
    wintypes.HWND,
    wintypes.COLORREF,
    wintypes.BYTE,
    wintypes.DWORD,
]
_user32.SetLayeredWindowAttributes.restype = wintypes.BOOL


# ─── Logging Configuration ────────────────────────────────────────────
# Must be configured BEFORE any module that creates a logger.
def setup_logging() -> logging.Logger:
    """Configure logging: stdout + rotating file."""
    log_dir = Path(__file__).resolve().parents[1] / "logs"
    log_dir.mkdir(exist_ok=True)
    log_file = log_dir / "shira_lab.log"

    # Root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)

    # Format
    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
    )

    # Console handler (stdout)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # File handler (rotating, max 5MB per file, 3 files)
    file_handler = logging.handlers.RotatingFileHandler(
        str(log_file),
        maxBytes=5 * 1024 * 1024,
        backupCount=3,
        encoding="utf-8",  # 5 MB
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)

    # Reduce noise from libraries
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("PySide6").setLevel(logging.WARNING)

    # Get logger for this module
    logger = logging.getLogger(__name__)

    logger.info("=" * 60)
    logger.info("Shira Lab starting...")
    logger.info("=" * 60)

    return logger


# Module-level logger
logger = setup_logging()

LWA_COLORKEY = 0x00000001


def make_window_click_through(hwnd: int) -> None:
    """Makes a window click-through (mouse events pass through to windows below)."""
    if not hwnd:
        return
    try:
        ex_style = _user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
        _user32.SetWindowLongW(
            hwnd,
            GWL_EXSTYLE,
            ctypes.c_long(ex_style | WS_EX_LAYERED | WS_EX_TRANSPARENT | WS_EX_NOACTIVATE),
        )
        # Set color key to transparent (pure black corner pixel becomes click-through)
        _user32.SetLayeredWindowAttributes(hwnd, 0, 0, LWA_COLORKEY)
    except (OSError, RuntimeError, AttributeError) as e:
        logger.warning("Click-through setup failed: %s", e)


def main() -> None:
    app = QApplication(sys.argv)
    app.setApplicationName("Shira Lab")
    app.setOrganizationName("ShiraLab")
    app.setApplicationVersion("0.17.0")
    app.setQuitOnLastWindowClosed(False)  # Keep running in tray

    # Application icon — Shira logo
    # Generate palette-colored icon on startup (uses saved palette or default matrix)
    project_root = Path(__file__).resolve().parents[1]

    # Read saved palette from profile.json (or default to matrix)
    saved_palette = "matrix"
    try:
        import json

        profile_path = project_root / "data" / "profile.json"
        if profile_path.exists():
            data = json.loads(profile_path.read_text(encoding="utf-8"))
            state = data.get("state") or {}
            if state.get("terminal_palette"):
                saved_palette = state["terminal_palette"]
                logger.info(f"Loaded saved palette: {saved_palette}")
    except (OSError, json.JSONDecodeError, ValueError, KeyError):
        logger.exception("Failed to read saved palette from profile")

    # ─── Bulletproof icon setup ───────────────────────────────────────
    # Try multiple sources in order of preference. CANNOT fail — last resort
    # creates a solid-color icon from QPixmap (no file dependency).
    icon_set = False

    # Step 1: Try generating palette-colored icon via icon_generator
    try:
        from app.backend.services.icon_generator import \
            PROJECT_ROOT as ICON_ROOT
        from app.backend.services.icon_generator import (
            generate_palette_ico, generate_palette_ico_unique,
            generate_palette_icon)

        png_path = generate_palette_icon(saved_palette)
        generate_palette_ico(saved_palette)
        unique_ico = generate_palette_ico_unique(saved_palette)

        if unique_ico and unique_ico.exists():
            app.setWindowIcon(QIcon(str(unique_ico)))
            icon_set = True
            logger.info(f"Icon: generated unique ICO: {unique_ico}")
        elif png_path and png_path.exists():
            app.setWindowIcon(QIcon(str(png_path)))
            icon_set = True
            logger.info(f"Icon: generated PNG: {png_path}")
    except (OSError, RuntimeError, ImportError, ValueError, AttributeError) as e:
        logger.warning(f"Icon: generation failed: {e}")

    # Step 2: Try existing icon files
    if not icon_set:
        for candidate in [
            project_root / f"shira_{saved_palette}.ico",
            project_root / "shira.ico",
            project_root / "shira_current.png",
            project_root / "Ico_Shine.png",
        ]:
            if candidate.exists():
                icon = QIcon(str(candidate))
                if not icon.isNull():
                    app.setWindowIcon(icon)
                    icon_set = True
                    logger.info(f"Icon: using existing file: {candidate}")
                    break

    # Step 3: Last resort — create solid-color icon from QPixmap (no file needed)
    if not icon_set:
        try:
            from PySide6.QtGui import QColor, QPainter, QPixmap

            from app.backend.models.runtime_state import TERMINAL_PALETTES

            palette = TERMINAL_PALETTES.get(saved_palette, {})
            color = QColor(palette.get("acc", "#6aa86a"))
            pix = QPixmap(256, 256)
            pix.fill(QColor(0, 0, 0, 0))
            painter = QPainter(pix)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            painter.fillRect(16, 16, 224, 224, color)
            painter.setPen(QColor(255, 255, 255))
            painter.setFont(QFont("Consolas", 48, QFont.Weight.Bold))
            painter.drawText(pix.rect(), 0x0084, "S")  # AlignCenter
            painter.end()
            app.setWindowIcon(QIcon(pix))
            icon_set = True
            logger.info("Icon: created emergency QPixmap icon")
        except (OSError, RuntimeError, ImportError, ValueError, AttributeError) as e:
            logger.warning(f"Icon: emergency creation failed: {e}")

    # Step 4: Flush Windows icon cache
    if sys.platform == "win32":
        try:
            import ctypes

            # SHChangeNotify: tells Windows to refresh icon cache
            ctypes.windll.shell32.SHChangeNotify(0x080000, 0x0000, None, None)
        except (OSError, AttributeError, ValueError):
            pass

    # Шрифт по умолчанию — моноширинный терминальный
    font = QFont("Consolas", 10)
    font.setStyleHint(QFont.StyleHint.Monospace)
    app.setFont(font)

    # Импортируем bridge (создаёт все сервисы)
    from app.backend.qml_bridge import QmlBridge

    bridge = QmlBridge()

    # Загружаем QML
    engine = QQmlApplicationEngine()
    engine.rootContext().setContextProperty("Bridge", bridge)

    qml_dir = Path(__file__).resolve().parent / "ui"
    engine.addImportPath(str(qml_dir))
    main_qml = qml_dir / "main.qml"

    if not main_qml.exists():
        logger.error("%s not found", main_qml)
        sys.exit(1)

    # Enable QML output to stderr BEFORE loading
    engine.setOutputWarningsToStandardError(True)

    engine.load(QUrl.fromLocalFile(str(main_qml)))

    if not engine.rootObjects():
        logger.error("Failed to load QML")
        sys.exit(1)

    # main_window is a QQuickWindow (QML ApplicationWindow)
    main_window = engine.rootObjects()[0]
    if not isinstance(main_window, QQuickWindow):
        # Cast for type checking
        from typing import cast

        main_window = cast(QQuickWindow, main_window)

    # ─── RE-SET icon after window creation ──────────────────────────────
    # QML engine.load() may override the app icon when creating the window.
    # Re-apply the icon AFTER the window exists.
    try:
        from app.backend.services.icon_generator import OUTPUT_ICO, OUTPUT_PNG
        from app.backend.services.icon_generator import \
            PROJECT_ROOT as ICON_ROOT

        current_palette = getattr(bridge.state, "terminal_palette", saved_palette)
        unique_ico = ICON_ROOT / f"shira_{current_palette}.ico"
        icon_path = (
            unique_ico
            if unique_ico.exists()
            else (OUTPUT_ICO if OUTPUT_ICO.exists() else OUTPUT_PNG)
        )
        if icon_path and icon_path.exists():
            icon = QIcon(str(icon_path))
            app.setWindowIcon(icon)
            main_window.setIcon(icon)
            try:
                import ctypes

                hwnd = int(main_window.winId())
                if hwnd:
                    hicon = ctypes.windll.user32.LoadImageW(0, str(icon_path), 1, 0, 0, 0x00000010)
                    if hicon:
                        ctypes.windll.user32.SendMessageW(hwnd, 0x0080, 1, hicon)
                        ctypes.windll.user32.SendMessageW(hwnd, 0x0080, 0, hicon)
                    SWP_FRAMECHANGED = 0x0020
                    SWP_NOMOVE = 0x0002
                    SWP_NOSIZE = 0x0001
                    SWP_NOZORDER = 0x0004
                    ctypes.windll.user32.SetWindowPos(
                        hwnd,
                        0,
                        0,
                        0,
                        0,
                        0,
                        SWP_NOMOVE | SWP_NOSIZE | SWP_NOZORDER | SWP_FRAMECHANGED,
                    )
            except (OSError, RuntimeError, AttributeError, ValueError):
                pass
    except (OSError, RuntimeError, AttributeError, ValueError) as e:
        logger.warning(f"Failed to re-set icon after window creation: {e}")

    # ─── Store the main window's Win32 HWND in the bridge ───────────────
    # CRITICAL: This must happen BEFORE any bridge method that needs the app hwnd.
    # Without this, find_app_hwnd("Shira Lab") might return the OVERLAY's hwnd
    # (Qt sets the app name "Shira Lab" as the overlay's Win32 title when the
    # overlay has no explicit title), causing minimize/pin to act on the overlay
    # instead of the app.
    try:
        app_hwnd = int(main_window.winId())
        bridge.set_app_hwnd(app_hwnd)
        # Force Windows to refresh the taskbar icon after window creation
        try:
            import ctypes

            SWP_FRAMECHANGED = 0x0020
            SWP_NOMOVE = 0x0002
            SWP_NOSIZE = 0x0001
            SWP_NOZORDER = 0x0004
            ctypes.windll.user32.SetWindowPos(
                app_hwnd,
                0,
                0,
                0,
                0,
                0,
                SWP_NOMOVE | SWP_NOSIZE | SWP_NOZORDER | SWP_FRAMECHANGED,
            )
        except (OSError, RuntimeError, AttributeError, ValueError):
            pass
        # Apply topmost on startup if is_pinned was saved as True
        if bridge.state.is_pinned:
            from window_utils import set_window_topmost

            set_window_topmost(app_hwnd, True)
    except (OSError, RuntimeError, AttributeError, ValueError) as e:
        logger.warning("Failed to store app hwnd: %s", e)

    # Connect bridge tray signals to main window
    # These are for window show/hide/quit ONLY.
    # Module toggles are handled inside QmlBridge itself (no duplicates here).
    def on_show_hide_window() -> None:
        """Toggle main window visibility based on current state."""
        if main_window.isVisible():
            main_window.hide()
        else:
            main_window.show()
            main_window.raise_()
            main_window.requestActivate()

    def on_quit() -> None:
        # Flush any pending save BEFORE cleanup
        try:
            bridge._flush_save()
        except (OSError, RuntimeError, AttributeError, ValueError):
            pass
        if bridge.tray is not None:
            bridge.tray.cleanup()
        # Clean up hotkey service listeners
        try:
            bridge.hotkeys.shutdown()
        except (OSError, RuntimeError, AttributeError, ValueError) as e:
            logger.warning("Hotkey shutdown error: %s", e)
        # Clean up Pico service
        try:
            if getattr(bridge, "_pico", None):
                bridge._pico.disconnect()
        except (OSError, RuntimeError, AttributeError, ValueError) as e:
            logger.warning("Pico shutdown error: %s", e)
        # Clean up ViGEm service
        try:
            if getattr(bridge, "_vigem", None):
                bridge._vigem.disconnect()
        except (OSError, RuntimeError, AttributeError, ValueError) as e:
            logger.warning("ViGEm shutdown error: %s", e)
        app.quit()

    if bridge.tray is not None:
        bridge.tray.showWindowRequested.connect(on_show_hide_window)
        bridge.tray.quitRequested.connect(on_quit)

    # ─── Make overlay window INDEPENDENT from main window ──────────────
    # CRITICAL: QML Window declared inside ApplicationWindow gets a transient
    # parent set to the main window. When the main window is minimized, Qt
    # automatically hides all transient children. We must break this link
    # by calling setTransientParent(None) from Python.
    overlay_obj = main_window.findChild(QWindow, "overlayHUD")
    if overlay_obj:
        overlay_obj.setTransientParent(None)  # type: ignore[arg-type]
        # Store overlay hwnd immediately (don't wait for sync_timer)
        try:
            overlay_hwnd = int(overlay_obj.winId())
            bridge.set_overlay_hwnd(overlay_hwnd)
        except Exception:
            logger.exception("Failed to store overlay hwnd")

    # Setup overlay HUD visibility sync.
    # NOTE: We do NOT apply click-through (WS_EX_TRANSPARENT) to the overlay
    # because it has interactive buttons (PIN, minimize). Click-through would make
    # those buttons unclickable.
    def sync_overlay() -> None:
        overlay = main_window.findChild(QObject, "overlayHUD")
        if overlay:
            visible = bridge.overlayVisible
            if overlay.property("visible") != visible:
                overlay.setProperty("visible", visible)
            # When overlay becomes visible, store its hwnd + apply always-topmost
            if visible:
                try:
                    overlay_hwnd = int(overlay.property("winId") or 0)
                    if overlay_hwnd:
                        bridge.set_overlay_hwnd(overlay_hwnd)
                except Exception:
                    logger.exception("Failed to store overlay hwnd on visibility change")

    sync_timer = QTimer()
    sync_timer.timeout.connect(sync_overlay)
    sync_timer.start(500)

    # Handle overlay visibility change from bridge
    def on_overlay_visibility_changed() -> None:
        sync_overlay()

    bridge.overlayVisibilityChanged.connect(on_overlay_visibility_changed)

    # ─── Periodic overlay topmost re-assert (every 2 seconds) ───────────
    # This ensures the overlay ALWAYS stays above the app window, even after
    # app pin changes, window focus changes, or any other Z-order events.
    topmost_timer = QTimer()
    topmost_timer.timeout.connect(lambda: bridge.reassertOverlayTopmost())
    topmost_timer.start(2000)

    # ─── Update app window icon (taskbar) when palette changes ──────────
    # When user switches palette in Settings, bridge regenerates the icon
    # and emits iconChanged. We reload the icon here.
    def on_icon_changed() -> None:
        try:
            from app.backend.services.icon_generator import (OUTPUT_ICO,
                                                             OUTPUT_PNG)
            from app.backend.services.icon_generator import \
                PROJECT_ROOT as ICON_ROOT

            # Get current palette for unique ICO + unique AppUserModelID
            current_palette = getattr(bridge.state, "terminal_palette", "matrix")
            unique_ico = ICON_ROOT / f"shira_{current_palette}.ico"

            # Flush Windows icon cache
            try:
                import ctypes

                ctypes.windll.shell32.SHChangeNotify(0x080000, 0x0000, None, None)
            except (OSError, AttributeError, ValueError):
                pass

            # Prefer unique ICO (forces Windows to reload due to different path)
            icon_path = (
                unique_ico
                if unique_ico.exists()
                else (OUTPUT_ICO if OUTPUT_ICO.exists() else OUTPUT_PNG)
            )

            if icon_path and icon_path.exists():
                new_icon = QIcon(str(icon_path))
                app.setWindowIcon(new_icon)
                main_window.setIcon(new_icon)

            # Update tray icon
            if hasattr(bridge, "tray") and bridge.tray and icon_path and icon_path.exists():
                bridge.tray.update_base_icon(Path(str(icon_path)))

            # Force Windows taskbar to refresh icon via Win32 API
            try:
                import ctypes

                hwnd = int(main_window.winId())
                if hwnd and icon_path and icon_path.exists():
                    hicon = ctypes.windll.user32.LoadImageW(
                        0,
                        str(icon_path),
                        1,
                        0,
                        0,
                        0x00000010,  # LR_LOADFROMFILE
                    )
                    if hicon:
                        ctypes.windll.user32.SendMessageW(
                            hwnd, 0x0080, 1, hicon
                        )  # WM_SETICON ICON_BIG
                        ctypes.windll.user32.SendMessageW(
                            hwnd, 0x0080, 0, hicon
                        )  # WM_SETICON ICON_SMALL
                        # Force Windows to redraw window frame + taskbar icon
                        SWP_FRAMECHANGED = 0x0020
                        SWP_NOMOVE = 0x0002
                        SWP_NOSIZE = 0x0001
                        SWP_NOZORDER = 0x0004
                        ctypes.windll.user32.SetWindowPos(
                            hwnd,
                            0,
                            0,
                            0,
                            0,
                            0,
                            SWP_NOMOVE | SWP_NOSIZE | SWP_NOZORDER | SWP_FRAMECHANGED,
                        )
            except (OSError, AttributeError, ValueError):
                pass
        except (OSError, RuntimeError, ValueError, AttributeError) as e:
            logger.warning("Failed to update icon on palette change: %s", e)

    bridge.iconChanged.connect(on_icon_changed)

    # ─── v1.0.0 SSS upgrade: Async update checker at startup ────────────
    # Checks GitHub Releases in background. If newer version exists,
    # bridge.updateCheckResult signal fires → QML shows update banner.
    try:
        bridge.checkForUpdatesAsync("0.17.0")
        logger.info("Update check started in background")
    except (OSError, RuntimeError, ValueError, AttributeError, ImportError) as e:
        logger.debug("Update check failed: %s", e)

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
