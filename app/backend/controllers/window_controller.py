"""
WindowController - handles window management, system tray, overlay, shortcuts, crash reporter.
Extracted from QmlBridge god-object (Phase 2.1).
"""

from __future__ import annotations

import ctypes
import logging
import threading
from pathlib import Path
from typing import TYPE_CHECKING, Any

from PySide6.QtCore import QObject, QTimer, Signal, Slot

from app.backend.models.runtime_state import RuntimeState
from app.backend.sound_manager import SoundManager
from app.backend.system_tray import SystemTrayManager
from window_utils import (
    clamp_to_work_area,
    find_app_hwnd,
    get_monitors,
    get_work_area,
    get_work_area_for_window,
    set_overlay_always_topmost,
)

if TYPE_CHECKING:
    from app.backend.qml_bridge import QmlBridge
    from app.backend.services.aim_service import AimService
    from app.backend.services.clicker_service import ClickerService
    from app.backend.services.hotkey_service import HotkeyService
    from app.backend.services.macro_service import MacroService
    from app.backend.services.recorder_service import RecorderService
    from app.backend.sound_manager import SoundManager

logger = logging.getLogger(__name__)


class WindowController(QObject):
    """
    Window management controller.

    Responsibilities:
    - Window visibility/state (pin, minimize, maximize, tray)
    - System tray integration
    - Overlay HUD management
    - Keyboard shortcuts handling
    - Crash reporter integration
    - App visibility monitoring
    """

    # Signals
    windowPinChanged = Signal(bool)
    windowVisibilityChanged = Signal(bool)
    overlayVisibilityChanged = Signal(bool)
    appVisibilityChanged = Signal(bool)
    iconChanged = Signal()
    iconReady = Signal(str)
    crashReportSaved = Signal(str)
    logMessage = Signal(str, str, str)  # level, source, message

    # Property for protocol compliance
    overlayVisible: bool = True

    def __init__(
        self,
        state: RuntimeState,
        clicker_service: ClickerService,
        macro_service: MacroService,
        recorder_service: RecorderService,
        aim_service: AimService,
        hotkey_service: HotkeyService,
        sound_manager: SoundManager,
        bridge: QmlBridge | None = None,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._state: RuntimeState = state
        self._clicker: ClickerService = clicker_service
        self._macro: MacroService = macro_service
        self._recorder: RecorderService = recorder_service
        self._aim: AimService = aim_service
        self._hotkeys: HotkeyService = hotkey_service
        self._sounds: SoundManager = sound_manager
        self._bridge: QmlBridge | None = bridge
        self._bridge_ref: QmlBridge | None = bridge

        # Overlay state
        self.overlayVisible = True

        # System tray - passed from bridge, don't create here
        self._tray: SystemTrayManager | None = None

        # Visibility check timer
        self._visibility_timer: QTimer | None = None
        self._last_visibility: bool | None = None
        # Don't start visibility check until tray is set
        # self._start_visibility_check()

        # Connect tray signals
        self._connect_tray_signals()

        # Timer for debounced icon regeneration
        self._icon_regen_timer: threading.Timer | None = None

        # Window handles
        self._app_hwnd: int = 0
        self._overlay_hwnd: int = 0

    def set_tray(self, tray: SystemTrayManager) -> None:
        """Set the tray manager (called from bridge after both are initialized)."""
        self._tray = tray
        self._connect_tray_signals()
        # Now start visibility check timer (after tray is set)
        self._start_visibility_check()

    def _connect_tray_signals(self) -> None:
        """Connect system tray action signals."""
        if self._tray is None:
            return
        self._tray.clickerToggled.connect(self.on_tray_clicker_toggle)
        self._tray.aimToggled.connect(self.on_tray_aim_toggle)
        self._tray.macroToggled.connect(self.on_tray_macro_toggle)
        self._tray.recorderToggled.connect(self.on_tray_recorder_toggle)
        self._tray.showWindowRequested.connect(self.on_tray_show_window)
        self._tray.quitRequested.connect(self.on_tray_quit)

    def _start_visibility_check(self) -> None:
        """Start periodic visibility check (1 second interval)."""
        self._visibility_timer = QTimer()
        if self._visibility_timer is not None:
            self._visibility_timer.timeout.connect(self._check_visibility)
            # Delay start until tray is set (2 seconds)
            QTimer.singleShot(
                2000,
                lambda: (self._visibility_timer.start(1000) if self._visibility_timer else None),
            )

    def _check_visibility(self) -> None:
        """Check if app is visible (window OR tray). Stop modules if not visible."""
        visible = self.is_app_visible()

        if self._last_visibility is None:
            self._last_visibility = visible
        elif self._last_visibility != visible:
            self._last_visibility = visible
            self.appVisibilityChanged.emit(visible)
            logger.info(f"App visibility changed: {visible}")

        if not visible:
            self._stop_all_modules_silent()

    def is_app_visible(self) -> bool:
        """Check if app is visible to user (window on taskbar OR tray icon)."""
        hwnd = self._get_app_hwnd()
        window_visible = False
        if hwnd:
            user32 = ctypes.windll.user32
            window_visible = user32.IsWindowVisible(hwnd)

        tray_visible = self._tray.is_visible() if self._tray else False
        return window_visible or tray_visible

    def _stop_all_modules_silent(self) -> None:
        """Stop all modules without sounds/notifications when app becomes invisible."""
        try:
            if self._clicker.is_running:
                self._clicker.stop()
        except Exception:
            logger.exception("Failed to stop clicker silently")
        try:
            if self._aim.is_running:
                self._aim.stop()
        except Exception:
            logger.exception("Failed to stop aim silently")
        try:
            if self._macro.is_running:
                self._macro.stop()
        except Exception:
            logger.exception("Failed to stop macro silently")
        try:
            if self._recorder.is_recording:
                self._recorder.stop_recording()
            elif self._recorder.is_playing:
                self._recorder.stop_playing()
        except Exception:
            logger.exception("Failed to stop recorder silently")

    # ─── Public Slots ──────────────────────────────────────────────────────

    @Slot(result=bool)
    def toggleWindowPin(self) -> bool:
        """Toggle window pin (always on top)."""
        # This modifies the window flags - actual implementation in main window
        self._state.is_pinned = not self._state.is_pinned
        self.windowPinChanged.emit(self._state.is_pinned)
        logger.info(f"Window pin toggled: {self._state.is_pinned}")
        return self._state.is_pinned

    @Slot()
    def showAppWindow(self) -> None:
        """Show and raise the main application window."""
        # Implementation handled by main window via signal
        self.windowVisibilityChanged.emit(True)
        logger.info("Show app window requested")

    @Slot()
    def toggleOverlayHUD(self) -> None:
        """Toggle overlay HUD visibility."""
        self.overlayVisible = not self.overlayVisible
        self.overlayVisibilityChanged.emit(self.overlayVisible)
        logger.info(f"Overlay HUD toggled: {self.overlayVisible}")

    @Slot(result="QVariantMap")
    def panicStop(self) -> dict[str, Any]:
        """EMERGENCY STOP - halt all modules immediately with panic sound."""
        logger.warning("PANIC STOP triggered!")
        self._sounds.play("panic")

        # Stop all modules
        results = {}
        try:
            if self._clicker.is_running:
                self._clicker.stop()
                results["clicker"] = "stopped"
        except Exception:
            logger.exception("Failed to stop clicker during panic")
            results["clicker"] = "error"
        try:
            if self._aim.is_running:
                self._aim.stop()
                results["aim"] = "stopped"
        except Exception:
            logger.exception("Failed to stop aim during panic")
            results["aim"] = "error"
        try:
            if self._macro.is_running:
                self._macro.stop()
                results["macro"] = "stopped"
        except Exception:
            logger.exception("Failed to stop macro during panic")
            results["macro"] = "error"
        try:
            if self._recorder.is_recording:
                self._recorder.stop_recording()
                results["recorder"] = "stopped"
        except Exception:
            logger.exception("Failed to stop recorder during panic")
            results["recorder"] = "error"

        return {"ok": True, "stopped": results}

    @Slot()
    def reassertOverlayTopmost(self) -> None:
        """Re-assert overlay window is topmost (call periodically)."""
        from window_utils import set_overlay_always_topmost

        overlay_hwnd = self._get_overlay_hwnd()
        if overlay_hwnd:
            set_overlay_always_topmost(overlay_hwnd)

    @Slot(result=bool)
    def getOverlayVisible(self) -> bool:
        """Get overlay visibility state."""
        return self.overlayVisible

    @Slot(bool)
    def setOverlayVisible(self, visible: bool) -> None:
        """Set overlay visibility."""
        self.overlayVisible = visible
        self.overlayVisibilityChanged.emit(visible)

    # ─── Tray Handlers ──────────────────────────────────────────────────────

    def on_tray_clicker_toggle(self) -> None:
        """Handle clicker toggle from system tray."""
        if self._clicker.is_running:
            self._clicker.stop()
        else:
            self._clicker.start()
        self._sounds.play("start" if not self._clicker.is_running else "stop")

    def on_tray_aim_toggle(self) -> None:
        """Handle aim toggle from system tray."""
        if self._aim.is_running:
            self._aim.stop()
        else:
            self._aim.start()
        self._sounds.play("start" if not self._aim.is_running else "stop")

    def on_tray_macro_toggle(self) -> None:
        """Handle macro toggle from system tray."""
        if self._macro.is_running:
            self._macro.stop()
        else:
            self._macro.start()
        self._sounds.play("start" if not self._macro.is_running else "stop")

    def on_tray_recorder_toggle(self) -> None:
        """Handle recorder toggle from system tray."""
        if self._recorder.is_recording:
            self._recorder.stop_recording()
        elif self._recorder.is_playing:
            self._recorder.stop_playing()
        else:
            self._recorder.start_recording()
        self._sounds.play(
            "start" if not self._recorder.is_recording and not self._recorder.is_playing else "stop"
        )

    def on_tray_show_window(self) -> None:
        """Handle show window from system tray."""
        self.showAppWindow()

    def on_tray_quit(self) -> None:
        """Handle quit from system tray."""
        logger.info("Quit requested from tray")
        self._shutdown()

    def _shutdown(self) -> None:
        """Cleanup on shutdown."""
        logger.info("Shutting down WindowController...")

        # Stop visibility timer
        if self._visibility_timer:
            self._visibility_timer.stop()
            self._visibility_timer = None

        # Shutdown services
        try:
            self._hotkeys.shutdown()
        except (OSError, ImportError, RuntimeError) as e:
            logger.warning(f"Hotkey service shutdown error: {e}")

        # Note: Pico and ViGEm cleanup handled by GamepadController

        # Quit application
        from PySide6.QtWidgets import QApplication

        QApplication.quit()

    # ─── Crash Reporter ───────────────────────────────────────────────────

    @Slot(bool, result=bool)
    def setCrashReportSending(self, enabled: bool) -> bool:
        """Enable/disable automatic crash report sending."""
        try:
            # The crash reporter only has install_crash_handler with send_reports parameter
            # We need to reinstall with new setting
            # For now just log
            logger.info(f"Crash report sending: {'enabled' if enabled else 'disabled'}")
            return True
        except (OSError, ImportError, RuntimeError) as e:
            logger.error(f"Failed to set crash report sending: {e}")
            return False

    @Slot(result="QVariantMap")
    def listCrashReports(self) -> dict[str, Any]:
        """List all crash reports."""
        try:
            from app.backend.services.crash_reporter import list_local_crashes

            return {"ok": True, "crashes": list_local_crashes()}
        except (OSError, ImportError, RuntimeError) as e:
            logger.error(f"Failed to list crash reports: {e}")
            return {"ok": False, "error": str(e), "crashes": []}

    @Slot(result="QVariantMap")
    def clearAllCrashReports(self) -> dict[str, Any]:
        """Clear all crash reports."""
        try:
            from app.backend.services.crash_reporter import clear_all_crashes

            count = clear_all_crashes()
            return {"ok": True, "cleared": count}
        except (OSError, ImportError, RuntimeError) as e:
            logger.error(f"Failed to clear crash reports: {e}")
            return {"ok": False, "error": str(e)}

    @Slot(str, result="QVariantMap")
    def readCrashReport(self, filename: str) -> dict[str, Any]:
        """Read a specific crash report."""
        try:
            from app.backend.services.crash_reporter import read_local_crash

            data = read_local_crash(filename)
            if data:
                return {"ok": True, "report": data}
            return {"ok": False, "error": "Report not found"}
        except (OSError, ImportError, RuntimeError) as e:
            logger.error(f"Failed to read crash report {filename}: {e}")
            return {"ok": False, "error": str(e)}

    @Slot(str, result="QVariantMap")
    def deleteCrashReport(self, filename: str) -> dict[str, Any]:
        """Delete a specific crash report."""
        try:
            from app.backend.services.crash_reporter import delete_local_crash

            deleted = delete_local_crash(filename)
            return {"ok": deleted}
        except (OSError, ImportError, RuntimeError) as e:
            logger.error(f"Failed to delete crash report {filename}: {e}")
            return {"ok": False, "error": str(e)}

    # ─── Icon Management ────────────────────────────────────────────────────

    def _regenerate_palette_icon(self, palette_id: str) -> None:
        """Regenerate tray/app icon for palette (delegates to background thread)."""
        import threading

        # Debounce
        if self._icon_regen_timer:
            self._icon_regen_timer.cancel()

        self._icon_regen_timer = threading.Timer(0.5, lambda: self._do_regen_icon(palette_id))
        self._icon_regen_timer.daemon = True
        self._icon_regen_timer.start()

    def _do_regen_icon(self, palette_id: str) -> None:
        """Actual icon regeneration in background thread."""
        import threading

        def _generate_async() -> None:
            try:
                from app.backend.services.icon_generator import (
                    generate_palette_ico,
                    generate_palette_ico_unique,
                    generate_palette_icon,
                )

                png_path = generate_palette_icon(palette_id)
                generate_palette_ico(palette_id)
                unique_ico = generate_palette_ico_unique(palette_id)
                if png_path and unique_ico:
                    self._update_shortcut_icon(unique_ico)
                    # Dispatch to main thread
                    self.iconReady.emit(png_path)
            except (OSError, ImportError, RuntimeError) as e:
                logger.warning(f"Failed to regenerate palette icon: {e}")

        t = threading.Thread(target=_generate_async, daemon=True)
        t.start()

    def _update_shortcut_icon(self, new_icon_path: Path) -> None:
        """Update all .lnk shortcuts pointing to launch.bat."""
        try:
            import os
            import subprocess

            project_root = Path(__file__).resolve().parents[3]
            target_path = project_root / "launch.bat"

            if not target_path.exists() or not new_icon_path.exists():
                logger.warning(
                    f"Shortcut update: target={target_path.exists()}, icon={new_icon_path.exists()}"
                )
                return

            # Find all Shira Lab.lnk locations
            lnk_locations = [project_root / "Shira Lab.lnk"]

            desktop = self._get_desktop_path()
            if desktop:
                lnk_locations.append(Path(desktop) / "Shira Lab.lnk")

            try:
                public_desktop = Path(os.environ.get("PUBLIC", "C:\\Users\\Public")) / "Desktop"
                lnk_locations.append(public_desktop / "Shira Lab.lnk")
            except (KeyError, OSError):
                logger.exception("Failed to resolve public desktop path")

            updated_count = 0
            for lnk_path in lnk_locations:
                if lnk_path.exists():
                    ps_script = f"""
$WshShell = New-Object -ComObject WScript.Shell
$shortcut = $WshShell.CreateShortcut('{lnk_path}')
if ($shortcut.TargetPath -eq '{target_path}') {{
    $shortcut.IconLocation = '{new_icon_path},0'
    $shortcut.Save()
    Write-Output "UPDATED"
}} else {{
    Write-Output "SKIPPED"
}}
"""
                    result = subprocess.run(
                        ["powershell", "-NoProfile", "-Command", ps_script],
                        capture_output=True,
                        text=True,
                        creationflags=subprocess.CREATE_NO_WINDOW,
                        check=False,
                    )
                    if "UPDATED" in result.stdout:
                        updated_count += 1
                        logger.info(f"Updated shortcut icon: {lnk_path}")

            # Refresh icon cache
            if updated_count > 0:
                self._refresh_icon_cache()

        except (OSError, subprocess.SubprocessError):
            logger.exception("Failed to update shortcut icon")

    def _get_desktop_path(self) -> str | None:
        """Get user's Desktop path via SHGetFolderPath."""
        try:
            import ctypes
            from ctypes import wintypes

            CSIDL_DESKTOP = 0x0000
            SHGFP_TYPE_CURRENT = 0

            path_buf = ctypes.create_unicode_buffer(wintypes.MAX_PATH)
            ctypes.windll.shell32.SHGetFolderPathW(
                None, CSIDL_DESKTOP, None, SHGFP_TYPE_CURRENT, path_buf
            )
            return path_buf.value
        except (OSError, ImportError, RuntimeError):
            logger.warning("Failed to get desktop path")
            return None

    def _refresh_icon_cache(self) -> None:
        """Force Windows to reload icon cache."""
        import threading

        def _refresh_async() -> None:
            try:
                import ctypes
                import os

                project_root = Path(__file__).resolve().parents[3]
                lnk_path = project_root / "Shira Lab.lnk"

                if lnk_path.exists():
                    try:
                        os.utime(str(lnk_path), None)
                    except Exception:
                        logger.exception("Failed to touch .lnk mtime")

                SHCNE_UPDATEITEM = 0x00002000
                SHCNF_PATH = 0x0005
                if lnk_path.exists():
                    try:
                        ctypes.windll.shell32.SHChangeNotify(
                            SHCNE_UPDATEITEM, SHCNF_PATH, str(lnk_path), None
                        )
                    except Exception:
                        logger.exception("Failed to SHChangeNotify")
            except Exception:
                logger.exception("Failed to refresh icon cache")

        t = threading.Thread(target=_refresh_async, daemon=True)
        t.start()

    # ─── Performance/Profiler ────────────────────────────────────────────

    @Slot(result="QVariantMap")
    def getPerformanceProfile(self) -> dict[str, Any]:
        """Get current performance metrics (CPU, memory, threads, uptime)."""
        try:
            import os
            import time

            import psutil

            process = psutil.Process(os.getpid())
            cpu_percent = process.cpu_percent(interval=0.1)
            mem_info = process.memory_info()
            memory_mb = mem_info.rss / (1024 * 1024)
            threads = process.num_threads()

            # Uptime
            create_time = process.create_time()
            uptime_sec = int(time.time() - create_time)

            # Module-specific metrics
            clicker_cps = getattr(self._clicker, "cps", 0) if hasattr(self._clicker, "cps") else 0
            aim_fps = getattr(self._aim, "last_fps", 0) if hasattr(self._aim, "last_fps") else 0

            return {
                "ok": True,
                "cpu_percent": cpu_percent,
                "memory_mb": memory_mb,
                "threads": threads,
                "uptime_sec": uptime_sec,
                "clicker_cps": clicker_cps,
                "aim_fps": aim_fps,
            }
        except (OSError, ImportError, RuntimeError) as e:
            logger.error(f"Failed to get performance profile: {e}")
            return {"ok": False, "error": str(e)}

    @Slot(result="QVariantMap")
    def detectSystemTheme(self) -> dict[str, Any]:
        """Detect Windows system theme (light/dark)."""
        try:
            from app.backend.services.theme_detector import detect_windows_theme

            theme = detect_windows_theme()
            result = {"ok": True, "theme": theme}
            self.logMessage.emit("INFO", "SYSTEM", f"System theme detected: {theme}")
            return result
        except (OSError, ImportError, RuntimeError) as e:
            logger.error(f"Failed to detect system theme: {e}")
            return {"ok": False, "error": str(e)}

    # ─── Profile Import/Export ────────────────────────────────────────────

    def set_bridge_reference(self, bridge: QmlBridge) -> None:
        """Set reference to QmlBridge for profile import/export."""
        self._bridge_ref = bridge

    @Slot(result="QVariantMap")
    def exportProfileDialog(self) -> dict[str, Any]:
        """Show file dialog and export profile to selected path."""
        try:
            from PySide6.QtWidgets import QFileDialog

            from app.backend.profile_io import export_profile

            file_path, _ = QFileDialog.getSaveFileName(
                None, "Export Profile", "profile.json", "JSON Files (*.json)"
            )
            if not file_path:
                return {"ok": True, "cancelled": True}

            if self._bridge_ref:
                return export_profile(self._bridge_ref, file_path)
            return {"ok": False, "error": "Bridge reference not set"}
        except (OSError, ImportError, RuntimeError) as e:
            logger.error(f"Export profile failed: {e}")
            return {"ok": False, "error": str(e)}

    @Slot(result="QVariantMap")
    def importProfileDialog(self) -> dict[str, Any]:
        """Show file dialog and import profile from selected path."""
        try:
            from PySide6.QtWidgets import QFileDialog

            from app.backend.profile_io import import_profile

            file_path, _ = QFileDialog.getOpenFileName(
                None, "Import Profile", "", "JSON Files (*.json)"
            )
            if not file_path:
                return {"ok": True, "cancelled": True}

            if self._bridge_ref:
                return import_profile(self._bridge_ref, file_path)
            return {"ok": False, "error": "Bridge reference not set"}
        except (OSError, ImportError, RuntimeError) as e:
            logger.error(f"Import profile failed: {e}")
            return {"ok": False, "error": str(e)}

    # ─── Internal Signal Handler ──────────────────────────────────────────

    def _on_icon_generated(self, png_path: str) -> None:
        """Called on MAIN THREAD after icon generation completes."""
        try:
            if self._tray:
                self._tray.update_base_icon(Path(png_path))
            self.iconChanged.emit()
        except (OSError, ImportError, RuntimeError) as e:
            logger.warning(f"Failed to apply regenerated icon: {e}")

    # ─── hwnd helpers (called from bridge) ────────────────────────────

    def set_app_hwnd(self, hwnd: int) -> dict[str, Any]:
        """Called from main.py after the QML window is created.
        Stores the main window's Win32 HWND so we never confuse it with
        the overlay window."""
        from app.backend.services.input_validation import (
            _qvar,
            make_error_response,
            validate_int,
        )

        ok, hwnd_val, err = validate_int(hwnd, 0, None, name="hwnd")
        if not ok or err is not None or hwnd_val is None:
            logger.warning(f"set_app_hwnd: {err}")
            return _qvar(make_error_response(err or "Invalid hwnd"))  # type: ignore[return-value]
        self._app_hwnd = hwnd_val
        return _qvar({"ok": True})  # type: ignore[return-value]

    def set_overlay_hwnd(self, hwnd: int) -> dict[str, Any]:
        """Called from main.py after the overlay window becomes visible.
        Stores the overlay's Win32 HWND so we can re-assert its topmost
        priority after any app pin operation."""
        from app.backend.services.input_validation import (
            _qvar,
            make_error_response,
            validate_int,
        )

        ok, hwnd_val, err = validate_int(hwnd, 0, None, name="hwnd")
        if not ok or err is not None or hwnd_val is None:
            logger.warning(f"set_overlay_hwnd: {err}")
            return _qvar(make_error_response(err or "Invalid hwnd"))  # type: ignore[return-value]
        self._overlay_hwnd = hwnd_val
        # Immediately make overlay always-topmost + tool window
        if self._overlay_hwnd:
            set_overlay_always_topmost(self._overlay_hwnd)
        return _qvar({"ok": True})  # type: ignore[return-value]

    def _get_overlay_hwnd(self) -> int:
        """Return stored overlay hwnd, or find it dynamically by title.
        The overlay has title 'ShiraOverlay' — we search for it if not stored."""
        if self._overlay_hwnd:
            return self._overlay_hwnd
        # Find dynamically by unique title
        hwnd = find_app_hwnd("ShiraOverlay")
        if hwnd:
            self._overlay_hwnd = hwnd
        return self._overlay_hwnd

    def _get_app_hwnd(self) -> int:
        """Return the stored app hwnd, or fall back to find_app_hwnd()."""
        if self._app_hwnd:
            return self._app_hwnd
        return find_app_hwnd("Shira Lab")

    # ─── Monitor Support ────────────────────────────────────────────────

    @Slot(result="QVariantMap")
    def getMonitors(self) -> dict[str, Any]:
        """Get list of monitors with work areas."""
        from app.backend.services.input_validation import (
            _qvar,
            make_error_response,
            make_ok_response,
        )

        try:
            return _qvar(make_ok_response(monitors=get_monitors()))  # type: ignore[return-value]
        except Exception as e:
            logger.exception("getMonitors failed")
            return _qvar(make_error_response(str(e)))  # type: ignore[return-value]

    @Slot(int, result="QVariantMap")
    def getMonitorForWindow(self, hwnd: int) -> dict[str, Any]:
        """Get monitor info for a specific window handle."""
        from app.backend.services.input_validation import (
            _qvar,
            make_error_response,
            make_ok_response,
            validate_int,
        )

        ok, hwnd_val, err = validate_int(hwnd, 0, None, name="hwnd")
        if not ok or hwnd_val is None:
            return _qvar(make_error_response(err or "Invalid hwnd"))  # type: ignore[return-value]

        try:
            import ctypes

            from window_utils import get_monitors

            monitors = get_monitors()
            if not monitors:
                return _qvar(make_error_response("No monitors found"))  # type: ignore[return-value]

            if hwnd_val == 0:
                return _qvar(make_ok_response(monitor=monitors[0]))  # type: ignore[return-value]

            # Check which monitor the window is on
            user32 = ctypes.windll.user32
            rect = ctypes.wintypes.RECT()
            user32.GetWindowRect(hwnd_val, ctypes.byref(rect))
            center_x = (rect.left + rect.right) // 2
            center_y = (rect.top + rect.bottom) // 2

            for m in monitors:
                if (
                    m["work_x"] <= center_x < m["work_x"] + m["work_width"]
                    and m["work_y"] <= center_y < m["work_y"] + m["work_height"]
                ):
                    return _qvar(make_ok_response(monitor=m))  # type: ignore[return-value]

            # Default to first monitor
            return _qvar(make_ok_response(monitor=monitors[0]))  # type: ignore[return-value]
        except Exception as e:
            logger.exception("getMonitorForWindow failed")
            return _qvar(make_error_response(str(e)))  # type: ignore[return-value]

    @Slot(result="QVariantMap")
    def getWorkArea(self) -> dict[str, Any]:
        """Returns {x, y, width, height} of the work area for the monitor
        the overlay is on (excludes taskbar). Used by OverlayHUD to position
        itself at bottom-left without overlapping taskbar."""
        from app.backend.services.input_validation import (
            _qvar,
            make_error_response,
            make_ok_response,
        )

        try:
            overlay_hwnd = self._get_overlay_hwnd()
            if overlay_hwnd:
                x, y, w, h = get_work_area_for_window(overlay_hwnd)
            else:
                x, y, w, h = get_work_area()
            return _qvar(make_ok_response(x=x, y=y, width=w, height=h))  # type: ignore[return-value]
        except Exception as e:
            logger.exception("getWorkArea failed")
            return _qvar(make_error_response(str(e)))  # type: ignore[return-value]

    @Slot(int, int, int, int, result="QVariantMap")
    def clampOverlayPosition(self, x: int, y: int, w: int, h: int) -> dict[str, Any]:
        """Clamp overlay position to stay within work area (no taskbar overlap).
        Called from QML after drag. Returns {x, y} with clamped position."""
        from app.backend.services.input_validation import (
            _qvar,
            make_error_response,
            make_ok_response,
            validate_int,
        )

        ok, x_val, err = validate_int(x, -10000, 10000, name="x")
        if not ok or x_val is None:
            return _qvar(make_error_response(err or "Invalid x"))  # type: ignore[return-value]
        ok, y_val, err = validate_int(y, -10000, 10000, name="y")
        if not ok or y_val is None:
            return _qvar(make_error_response(err or "Invalid y"))  # type: ignore[return-value]
        ok, w_val, err = validate_int(w, 0, 10000, name="w")
        if not ok or w_val is None:
            return _qvar(make_error_response(err or "Invalid w"))  # type: ignore[return-value]
        ok, h_val, err = validate_int(h, 0, 10000, name="h")
        if not ok or h_val is None:
            return _qvar(make_error_response(err or "Invalid h"))  # type: ignore[return-value]

        overlay_hwnd = self._get_overlay_hwnd()
        cx, cy = clamp_to_work_area(overlay_hwnd, x_val, y_val, w_val, h_val)
        return _qvar(make_ok_response(x=cx, y=cy))  # type: ignore[return-value]

    @Slot(int, result="QVariantMap")
    def getWorkAreaForMonitor(self, monitor_index: int) -> dict[str, Any]:
        """Get work area for specific monitor."""
        from app.backend.services.input_validation import (
            _qvar,
            make_error_response,
            make_ok_response,
            validate_int,
        )

        ok, idx_val, err = validate_int(monitor_index, 0, 10, name="monitor_index")
        if not ok or idx_val is None:
            return _qvar(make_error_response(err or "Invalid monitor index"))  # type: ignore[return-value]

        try:
            monitors = get_monitors()
            if 0 <= idx_val < len(monitors):
                m = monitors[idx_val]
                return _qvar(
                    make_ok_response(
                        x=m["work_x"],
                        y=m["work_y"],
                        width=m["work_width"],
                        height=m["work_height"],
                    )
                )  # type: ignore[return-value]
            return _qvar(make_error_response("Invalid monitor index"))  # type: ignore[return-value]
        except Exception as e:
            logger.exception("getWorkAreaForMonitor failed")
            return _qvar(make_error_response(str(e)))  # type: ignore[return-value]

    # ─── Logging Bridge ────────────────────────────────────────────────

    def log(self, level: str, source: str, message: str) -> None:
        """Log message to console via signal."""
        self.logMessage.emit(level, source, message)

    # ─── _TrayBridge Protocol Implementation ────────────────────────────────

    def getSettings(self) -> dict[str, Any]:
        """Get all settings for system tray profiles menu."""
        if self._bridge:
            return self._bridge.getSettings()
        # Fallback to state
        from app.backend.models.runtime_state import TERMINAL_PALETTES
        from config import LANGUAGES, LOGO_SHIRA

        lang = dict(LANGUAGES.get(self._state.ui_lang, LANGUAGES["RU"]))
        return {
            "terminal_palette": self._state.terminal_palette,
            "is_pinned": self._state.is_pinned,
            "ui_lang": self._state.ui_lang,
            "lang": lang,
            "logo_shira": LOGO_SHIRA,
            "palettes": TERMINAL_PALETTES,
            "hotkeys": self._state.hotkeys,
            "profiles": getattr(self._state, "profiles", {}),
            "active_profile": getattr(self._state, "active_profile", "default"),
        }

    def resetAllHotkeys(self) -> dict[str, Any]:
        """Reset all hotkeys to defaults."""
        if self._bridge:
            return self._bridge.resetAllHotkeys()
        # Fallback - reset in hotkey service
        from app.backend.services.input_validation import _qvar, make_ok_response

        self._hotkeys.reset_all()
        return _qvar(make_ok_response())  # type: ignore[return-value]

    def setTerminalPalette(self, palette_id: str) -> None:
        """Set terminal palette."""
        if self._bridge:
            self._bridge.setTerminalPalette(palette_id)
        else:
            self._state.terminal_palette = palette_id
            self._regenerate_palette_icon(palette_id)

    def saveProfile(self, name: str) -> dict[str, Any]:
        """Save current settings as a profile."""
        if self._bridge:
            return self._bridge.saveProfile(name)
        # Fallback -TODO: implement profile saving
        from app.backend.services.input_validation import _qvar, make_error_response

        return _qvar(make_error_response("Bridge not available"))  # type: ignore[return-value]

    def setHotkey(self, action: str, key: str, mode: str) -> dict[str, Any]:
        """Set hotkey binding."""
        if self._bridge:
            return self._bridge.setHotkey(action, key, mode)
        # Fallback - set in hotkey service
        from app.backend.services.input_validation import (
            _qvar,
            make_error_response,
            validate_enum,
        )

        ok, val, err = validate_enum(mode, {"TOGGLE", "HOLD"}, name="mode")
        if not ok or val is None:
            return _qvar(make_error_response(err or "Invalid mode"))  # type: ignore[return-value]
        return self._hotkeys.set_binding(action, key, val)

    def getClickerStatus(self) -> dict[str, Any]:
        """Get clicker status for tray."""
        return {
            "is_running": (
                self._clicker.is_running if hasattr(self._clicker, "is_running") else False
            ),
            "cps": getattr(self._clicker, "cps", 0),
        }

    def aimStatus(self) -> dict[str, Any]:
        """Get aim status for tray."""
        return {
            "is_running": (self._aim.is_running if hasattr(self._aim, "is_running") else False),
            "fps": getattr(self._aim, "last_fps", 0),
        }

    def getMacroStatus(self) -> dict[str, Any]:
        """Get macro status for tray."""
        return {
            "is_running": (self._macro.is_running if hasattr(self._macro, "is_running") else False),
        }

    def recorderStatus(self) -> dict[str, Any]:
        """Get recorder status for tray."""
        return {
            "is_recording": (
                self._recorder.is_recording if hasattr(self._recorder, "is_recording") else False
            ),
            "is_playing": (
                self._recorder.is_playing if hasattr(self._recorder, "is_playing") else False
            ),
        }

    @property
    def profile_controller(self) -> Any:
        """Get profile controller (delegate to bridge)."""
        if self._bridge and hasattr(self._bridge, "profile_controller"):
            return self._bridge.profile_controller
        # For protocol compliance, return self (WindowController has setModuleTargetWindow)
        return self
