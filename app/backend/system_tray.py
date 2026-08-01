from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Protocol, cast

from PySide6.QtCore import QObject, QTimer, Signal
from PySide6.QtGui import QAction, QIcon
from PySide6.QtWidgets import QApplication, QMenu, QSystemTrayIcon

logger = logging.getLogger(__name__)


class _TrayBridge(Protocol):
    def getSettings(self) -> dict[str, Any]: ...
    def resetAllHotkeys(self) -> dict[str, Any]: ...
    def setTerminalPalette(self, palette_id: str) -> None: ...
    def saveProfile(self, name: str) -> dict[str, Any]: ...
    def setHotkey(self, action: str, key: str, mode: str) -> dict[str, Any]: ...
    def toggleOverlayHUD(self) -> None: ...
    def panicStop(self) -> dict[str, Any]: ...
    def getClickerStatus(self) -> dict[str, Any]: ...
    def aimStatus(self) -> dict[str, Any]: ...
    def getMacroStatus(self) -> dict[str, Any]: ...
    def recorderStatus(self) -> dict[str, Any]: ...
    @property
    def overlayVisible(self) -> bool: ...
    @property
    def profile_controller(self) -> Any: ...


class SystemTrayManager(QObject):
    """Manages system tray icon with context menu for gaming multi-tool."""

    # Signals to QML/main window
    showWindowRequested = Signal()
    hideWindowRequested = Signal()
    quitRequested = Signal()

    # Module control signals
    clickerToggled = Signal()
    aimToggled = Signal()
    macroToggled = Signal()
    recorderToggled = Signal()

    # Status signals for menu updates
    statusUpdateRequested = Signal()

    def __init__(self, bridge: _TrayBridge, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._bridge: _TrayBridge = bridge
        self._tray: QSystemTrayIcon | None = None
        self._menu: QMenu | None = None
        self._actions: dict[str, QAction] = {}

        # Icon paths
        self._project_root = Path(__file__).resolve().parents[2]
        self._base_icon_path: Path | None = None
        self._overlay_dir = Path(__file__).resolve().parent / "assets" / "overlays"
        self._current_overlay: str | None = (
            None  # track current overlay to avoid redundant icon changes
        )

        self._setup_tray()
        # Don't call _update_menu_states() here - wait for timer to fire after bridge init
        # self._update_menu_states()

        # Timer to periodically update menu states based on bridge status
        # Start with a delay to allow bridge initialization to complete
        self._update_timer: QTimer | None = QTimer(self)
        self._update_timer.timeout.connect(self._update_menu_states)
        self._update_timer.setSingleShot(True)
        QTimer.singleShot(
            2000, lambda: self._update_timer.start(1000) if self._update_timer else None
        )

    def _setup_tray(self) -> None:
        # Create tray icon
        self._tray = QSystemTrayIcon(self)

        # Set icon — search for shira.ico, then Ico_Shine.png, then app icon
        icon_path: Path | None = None
        for candidate in [
            self._project_root / "shira.ico",
            self._project_root / "Ico_Shine.png",
        ]:
            if candidate.exists():
                icon_path = candidate
                break
        if icon_path:
            self._base_icon_path = icon_path
            self._tray.setIcon(QIcon(str(icon_path)))
        else:
            # Fallback to app icon
            app = QApplication.instance()
            if app is not None:
                # QApplication.instance() returns QCoreApplication | None;
                # cast to QApplication which has windowIcon()
                self._tray.setIcon(cast(QApplication, app).windowIcon())

        self._tray.setToolTip("Shira Lab - Gaming Multi-tool")

        # Create context menu
        self._menu = QMenu()

        # --- Status Header (non-clickable) ---
        self._actions["status_header"] = self._menu.addAction("═══ SHIRA LAB ═══")
        self._actions["status_header"].setEnabled(False)
        font = self._actions["status_header"].font()
        font.setBold(True)
        self._actions["status_header"].setFont(font)

        self._menu.addSeparator()

        # --- Module Controls ---
        # Clicker
        self._actions["clicker"] = self._menu.addAction("● CLICKER: Idle")
        self._actions["clicker"].triggered.connect(self._on_clicker_toggle)

        # Aim
        self._actions["aim"] = self._menu.addAction("○ AIM: Idle")
        self._actions["aim"].triggered.connect(self._on_aim_toggle)

        # Macro
        self._actions["macro"] = self._menu.addAction("○ MACRO: Idle")
        self._actions["macro"].triggered.connect(self._on_macro_toggle)

        # Recorder
        self._actions["recorder"] = self._menu.addAction("○ RECORDER: Idle")
        self._actions["recorder"].triggered.connect(self._on_recorder_toggle)

        self._menu.addSeparator()

        # --- Window Controls ---
        self._actions["show_hide"] = self._menu.addAction("Show Window")
        self._actions["show_hide"].triggered.connect(self._toggle_window_visibility)

        self._actions["overlay"] = self._menu.addAction("Overlay HUD: On")
        self._actions["overlay"].setCheckable(True)
        self._actions["overlay"].setChecked(True)
        self._actions["overlay"].triggered.connect(self._on_overlay_toggle)

        self._menu.addSeparator()

        # --- Profiles Submenu ---
        self._profiles_menu = self._menu.addMenu("Profiles")
        self._update_profiles_menu()

        self._menu.addSeparator()

        # --- Panic Key ---
        self._actions["panic"] = self._menu.addAction("⛔ PANIC STOP (F12)")
        self._actions["panic"].triggered.connect(self._on_panic_stop)
        font = self._actions["panic"].font()
        font.setBold(True)
        self._actions["panic"].setFont(font)

        self._menu.addSeparator()

        # --- Settings / Quit ---
        self._actions["settings"] = self._menu.addAction("Settings...")
        self._actions["settings"].triggered.connect(self.showWindowRequested.emit)

        self._actions["quit"] = self._menu.addAction("Exit")
        self._actions["quit"].triggered.connect(self.quitRequested.emit)

        # Set menu
        self._tray.setContextMenu(self._menu)

        # Tray activation (click)
        self._tray.activated.connect(self._on_tray_activated)

        # Show tray
        self._tray.show()

    def _update_profiles_menu(self) -> None:
        """Update profiles submenu with available profiles."""
        self._profiles_menu.clear()

        # Guard against bridge not fully initialized
        if not hasattr(self._bridge, "getSettings"):
            return

        try:
            settings = self._bridge.getSettings()
            profiles = settings.get("profiles", {})
            current = settings.get("active_profile", "default")
        except (AttributeError, KeyError, ValueError, TypeError):
            logger.exception("Failed to parse settings for profiles")
            profiles = {}
            current = "default"

        # Default profile action
        act = self._profiles_menu.addAction(
            f"{'●' if current == 'default' else '○'} Default"
        )
        act.setData("default")
        act.triggered.connect(lambda _checked, p="default": self._switch_profile(p))

        if profiles:
            self._profiles_menu.addSeparator()
            for name in sorted(profiles.keys()):
                act = self._profiles_menu.addAction(
                    f"{'●' if current == name else '○'} {name}"
                )
                act.setData(name)
                act.triggered.connect(lambda _checked, p=name: self._switch_profile(p))

        self._profiles_menu.addSeparator()
        save_act = self._profiles_menu.addAction("+ Save Current as Profile...")
        save_act.triggered.connect(self._save_current_profile)

    def _switch_profile(self, profile_name: str) -> None:
        """Switch to a profile by name."""
        # Guard against bridge not fully initialized
        if not hasattr(self._bridge, "getSettings"):
            return

        try:
            settings = self._bridge.getSettings()
            profiles = settings.get("profiles", {})

            if profile_name == "default":
                # Reset to defaults (reload default hotkeys etc)
                self._bridge.resetAllHotkeys()
                self._bridge.setTerminalPalette(
                    settings.get("terminal_palette", "matrix")
                )
                self._bridge.saveProfile("")
            elif profile_name in profiles:
                profile = profiles[profile_name]
                # Apply profile settings
                if "hotkeys" in profile:
                    for action, binding in profile["hotkeys"].items():
                        self._bridge.setHotkey(
                            action,
                            binding.get("key", ""),
                            binding.get("mode", "TOGGLE"),
                        )
                if "terminal_palette" in profile:
                    self._bridge.setTerminalPalette(profile["terminal_palette"])
                if "target_hwnd" in profile:
                    self._bridge.profile_controller.setModuleTargetWindow(
                        "clicker", profile["target_hwnd"]
                    )
                self._bridge.saveProfile("")

            # Update active profile
            self._bridge.saveProfile(profile_name)
            self._update_profiles_menu()
            self._update_menu_states()
        except (AttributeError, KeyError, ValueError, TypeError) as e:
            logger.debug(f"Failed to switch profile: {e}")

    def _save_current_profile(self) -> None:
        """Save current configuration as a new profile."""
        # This would open a dialog - for now just print
        logger.debug("Save profile dialog needed")

    def _on_tray_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            # Left click - toggle window visibility
            self._toggle_window_visibility()
        elif reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self.showWindowRequested.emit()

    def _toggle_window_visibility(self) -> None:
        """Toggle main window visibility."""
        # Emit signal to main to toggle - main knows actual window state
        # We don't track state here; main will handle show/hide based on current visibility
        self.showWindowRequested.emit()

    def _on_clicker_toggle(self) -> None:
        """Handle clicker toggle from tray menu."""
        self.clickerToggled.emit()

    def _on_aim_toggle(self) -> None:
        """Handle aim toggle from tray menu."""
        self.aimToggled.emit()

    def _on_macro_toggle(self) -> None:
        """Handle macro toggle from tray menu."""
        self.macroToggled.emit()

    def _on_recorder_toggle(self) -> None:
        """Handle recorder toggle from tray menu."""
        self.recorderToggled.emit()

    def _on_overlay_toggle(self) -> None:
        """Handle overlay toggle from tray menu."""
        self._bridge.toggleOverlayHUD()

    def _on_panic_stop(self) -> None:
        """Handle panic stop from tray menu."""
        self._bridge.panicStop()

    def _update_menu_states(self) -> None:
        """Periodically update menu action states based on bridge status."""
        try:
            # Guard against bridge not fully initialized
            if not hasattr(self._bridge, "getClickerStatus"):
                return

            clicker_status = self._bridge.getClickerStatus() or {}
            aim_status = self._bridge.aimStatus() or {}
            macro_status = self._bridge.getMacroStatus() or {}
            recorder_status = self._bridge.recorderStatus() or {}

            clk_running = clicker_status.get("is_running", False)
            aim_running = aim_status.get("is_running", False)
            macro_running = macro_status.get("is_running", False)
            rec_recording = recorder_status.get("is_recording", False)
            rec_playing = recorder_status.get("is_playing", False)

            self._actions["clicker"].setText(
                f"{'●' if clk_running else '○'} CLICKER: {'Running' if clk_running else 'Idle'}"
            )
            self._actions["aim"].setText(
                f"{'●' if aim_running else '○'} AIM: {'Running' if aim_running else 'Idle'}"
            )
            self._actions["macro"].setText(
                f"{'●' if macro_running else '○'} MACRO: {'Running' if macro_running else 'Idle'}"
            )

            if rec_recording:
                rec_state = "Recording"
            elif rec_playing:
                rec_state = "Playing"
            else:
                rec_state = "Idle"
            self._actions["recorder"].setText(
                f"{'●' if (rec_recording or rec_playing) else '○'} RECORDER: {rec_state}"
            )

            # Guard against overlayVisible property not being initialized yet
            # overlayVisible is a @Property(bool) on QmlBridge, not a method
            try:
                overlay_visible = self._bridge.overlayVisible
                self._actions["overlay"].setChecked(overlay_visible)
            except (AttributeError, RuntimeError):
                logger.debug("overlayVisible property not ready yet")

        except (AttributeError, KeyError, ValueError, TypeError):
            logger.exception("Failed to update tray menu states")

    def update_base_icon(self, png_path: Path) -> None:
        """Update tray icon from a generated palette PNG."""
        if not self._tray:
            return
        try:
            if png_path.exists():
                self._tray.setIcon(QIcon(str(png_path)))
        except (OSError, ValueError, RuntimeError):
            logger.exception("Failed to update tray icon")

    def is_visible(self) -> bool:
        """Check if tray icon is currently visible."""
        return self._tray is not None and self._tray.isVisible()

    def cleanup(self) -> None:
        """Clean up tray resources on shutdown."""
        if self._tray:
            self._tray.hide()
            self._tray.deleteLater()
            self._tray = None
        if self._menu:
            self._menu.deleteLater()
            self._menu = None
        if self._update_timer:
            self._update_timer.stop()
            self._update_timer = None
        self._actions.clear()
        logger.debug("SystemTrayManager cleaned up")
