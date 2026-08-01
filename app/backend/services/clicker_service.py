from __future__ import annotations

import ctypes
import logging
import threading
import time
from typing import TYPE_CHECKING, Any

from app.backend.services.input_validation import VALID_BACKGROUND_METHODS
from app.backend.services.singleton import singleton
from app.backend.services.stealth_input import StealthInput
from utils import send_background_click

# Type alias for background method
BackgroundMethod = str

if TYPE_CHECKING:
    from app.backend.qml_bridge import QmlBridge
    from app.backend.services.pico_service import PicoService
    from app.backend.services.vigem_service import VigemService

logger = logging.getLogger(__name__)


@singleton
class ClickerService:
    def __init__(self) -> None:
        self._lock = threading.RLock()  # Protects all mutable state
        self._is_running: bool = False
        self._interval_ms: int = 100
        self._limit: int = 0
        self._hold_ms: int = 0
        self._button: str = "L"
        self._click_count: int = 0
        self._worker: threading.Thread | None = None
        self._mouse_event = ctypes.windll.user32.mouse_event
        self._buttons: dict[str, dict[str, int]] = {
            "L": {"down": 0x0002, "up": 0x0004, "data": 0},
            "R": {"down": 0x0008, "up": 0x0010, "data": 0},
            "M": {"down": 0x0020, "up": 0x0040, "data": 0},
            "X1": {"down": 0x0080, "up": 0x0100, "data": 1},
            "X2": {"down": 0x0080, "up": 0x0100, "data": 2},
        }
        # Background input method: "sendinput" (global), "postmessage" (PostMessage to hwnd),
        # "vigem" (ViGEm virtual gamepad), "pico" (Pico HID)
        # NOTE: "sendinput_attached" removed — didn't work in browser/Notepad
        self._background_method: str = "sendinput"
        # Per-module target window (set by bridge)
        self._target_hwnd: int | None = None
        # ViGEm service (lazy init)
        self._vigem_service: VigemService | None = None
        # Pico service (lazy init)
        self._pico_service: PicoService | None = None
        # CPS tracking
        self._cps: float = 0.0
        self._cps_timestamps: list[float] = []
        # Bridge reference for logging (set by QmlBridge)
        self._bridge: QmlBridge | None = None

    def set_bridge(self, bridge: QmlBridge | None) -> None:
        """Set bridge reference for logging."""
        self._bridge = bridge

    def _log(self, level: str, message: str) -> None:
        if self._bridge:
            self._bridge.log(level, "CLICKER", message)

    # ─── Thread-safe property accessors ──────────────────────────────────────

    @property
    def is_running(self) -> bool:
        with self._lock:
            return self._is_running

    @is_running.setter
    def is_running(self, value: bool) -> None:
        with self._lock:
            self._is_running = value

    @property
    def interval_ms(self) -> int:
        with self._lock:
            return self._interval_ms

    @interval_ms.setter
    def interval_ms(self, value: int) -> None:
        with self._lock:
            self._interval_ms = max(1, int(value))

    @property
    def hold_ms(self) -> int:
        with self._lock:
            return self._hold_ms

    @hold_ms.setter
    def hold_ms(self, value: int) -> None:
        with self._lock:
            self._hold_ms = max(0, int(value))

    @property
    def button(self) -> str:
        with self._lock:
            return self._button

    @button.setter
    def button(self, value: str) -> None:
        with self._lock:
            self._button = value if value in self._buttons else "L"

    @property
    def limit(self) -> int:
        with self._lock:
            return self._limit

    @limit.setter
    def limit(self, value: int) -> None:
        with self._lock:
            self._limit = max(0, int(value))

    @property
    def background_method(self) -> BackgroundMethod:
        with self._lock:
            return self._background_method

    @background_method.setter
    def background_method(self, value: BackgroundMethod) -> None:
        with self._lock:
            if value in VALID_BACKGROUND_METHODS:
                self._background_method = value
            else:
                self._log(
                    "WARN",
                    f"Invalid background method '{value}', keeping current: {self._background_method}",
                )

    @property
    def target_hwnd(self) -> int | None:
        with self._lock:
            return self._target_hwnd

    @target_hwnd.setter
    def target_hwnd(self, value: int | None) -> None:
        with self._lock:
            self._target_hwnd = value

    @property
    def click_count(self) -> int:
        with self._lock:
            return self._click_count

    @click_count.setter
    def click_count(self, value: int) -> None:
        with self._lock:
            self._click_count = int(value)

    @property
    def cps(self) -> float:
        with self._lock:
            return self._cps

    @cps.setter
    def cps(self, value: float) -> None:
        with self._lock:
            self._cps = value

    def update_config(
        self,
        interval_ms: int,
        hold_ms: int,
        button: str,
        limit: int,
        background_method: BackgroundMethod | None = None,
    ) -> dict[str, Any]:
        self.interval_ms = max(1, int(interval_ms))
        self.hold_ms = max(0, int(hold_ms))
        self.button = button if button in self._buttons else "L"
        self.limit = max(0, int(limit))
        if background_method:
            self.background_method = background_method
            self._log(
                "INFO",
                f"Config: interval={self.interval_ms}ms button={self.button} method={self.background_method}",
            )
        return self.get_status()

    def start(self, target_hwnd: int | None = None) -> dict[str, Any]:
        with self._lock:
            if self._is_running:
                return self.get_status()
            if target_hwnd is None:
                target_hwnd = self._target_hwnd
            self._is_running = True
            self._click_count = 0
            self._cps_timestamps.clear()
            # Snapshot config values to avoid holding lock in loop
            interval_ms = self._interval_ms
            hold_ms = self._hold_ms
            button = self._button
            limit = self._limit
            background_method = self._background_method
        self._log(
            "OK",
            f"Started — method={background_method} target_hwnd={target_hwnd or 'None (global)'}",
        )
        self._worker = threading.Thread(
            target=self._loop,
            args=(target_hwnd, interval_ms, hold_ms, button, limit, background_method),
            daemon=True,
        )
        self._worker.start()
        return self.get_status()

    def stop(self) -> dict[str, Any]:
        with self._lock:
            was_running = self._is_running
            click_count = self._click_count
        if was_running:
            self._log("INFO", f"Stopped — total clicks={click_count}")
        with self._lock:
            self._is_running = False
        return self.get_status()

    def _loop(
        self,
        target_hwnd: int | None,
        interval_ms: int,
        hold_ms: int,
        button: str,
        limit: int,
        background_method: str,
    ) -> None:
        buttons = self._buttons  # constant
        mouse_event = self._mouse_event  # constant

        while True:
            with self._lock:
                if not self._is_running:
                    break
                # Check limit
                if limit > 0 and self._click_count >= limit:
                    self._is_running = False
                    break

            if target_hwnd:
                self._send_background_click(target_hwnd, button, hold_ms, background_method)
            else:
                info = buttons.get(button, buttons["L"])
                mouse_event(info["down"], 0, 0, info["data"], 0)
                if hold_ms > 0:
                    time.sleep(hold_ms / 1000.0)
                mouse_event(info["up"], 0, 0, info["data"], 0)

            with self._lock:
                self._click_count += 1
                click_count = self._click_count

            # Log every 10th click (avoid log spam)
            if click_count % 10 == 0:
                self._log("OK", f"Click #{click_count} sent via {background_method}")

            # Track CPS
            now = time.time()
            with self._lock:
                self._cps_timestamps.append(now)
                # Keep only last 2 seconds
                self._cps_timestamps = [t for t in self._cps_timestamps if now - t < 2.0]
                if len(self._cps_timestamps) >= 2:
                    time_span = self._cps_timestamps[-1] - self._cps_timestamps[0]
                    if time_span > 0:
                        self._cps = len(self._cps_timestamps) / time_span
                    else:
                        self._cps = 0.0
                else:
                    self._cps = 0.0

            time.sleep(interval_ms / 1000.0)

        # Reset CPS when stopped
        with self._lock:
            self._cps = 0.0
            self._cps_timestamps.clear()

    def _send_background_click(self, hwnd: int, button: str, hold_ms: int, method: str) -> None:
        """Send click using configured background_method."""
        if method == "postmessage":
            send_background_click(hwnd, button=button)
            self._log("OK", f"PostMessage click → hwnd={hwnd}")
        elif method == "vigem":
            # Map mouse button to gamepad button
            btn_map = {"L": "a", "R": "b", "M": "x", "X1": "lb", "X2": "rb"}
            self._vigem_press_button(btn_map.get(button, "a"), hold_ms)
        elif method == "pico":
            self._pico_send_click(button, hold_ms)
        else:  # "sendinput" - global SendInput (requires foreground)
            StealthInput.send_mouse_click(button, hold_ms)

    def _pico_send_click(self, button: str, hold_ms: int) -> bool:
        """Send mouse click via Pico HID device."""
        try:
            from app.backend.services.pico_service import get_pico_service

            pico = get_pico_service()
            if not pico.is_connected:
                # Try to connect using runtime state config
                import json

                from app.backend.persistence import PROFILE_PATH

                port: str | None = None
                baudrate = 115200
                try:
                    data = json.loads(PROFILE_PATH.read_text(encoding="utf-8"))
                    state = data.get("state") or {}
                    port = state.get("pico_port")
                    baudrate = int(state.get("pico_baudrate", 115200))
                except (OSError, json.JSONDecodeError, ValueError):
                    pass
                if port:
                    pico = get_pico_service(port=port, baudrate=baudrate)
                else:
                    pico = get_pico_service()
                if not pico.connect():
                    return False
            # Map clicker button to Pico mouse button
            btn_map = {"L": 1, "R": 2, "M": 4, "X1": 8, "X2": 16}
            btn_mask = btn_map.get(button, 1)
            return pico.ms_click(btn_mask, hold_ms)
        except (OSError, ValueError, RuntimeError, AttributeError, ImportError) as e:
            import logging

            logging.getLogger(__name__).debug(f"Pico click failed: {e}")
            return False

    def _vigem_press_button(self, button_name: str, hold_ms: int) -> bool:
        """Press a button on the ViGEm virtual controller."""
        try:
            if self._vigem_service is None:
                from app.backend.services.vigem_service import get_vigem_service

                self._vigem_service = get_vigem_service()
                if not self._vigem_service.connect():
                    return False
            # Map button name to XUSB button flag
            from app.backend.services.vigem_service import (
                VIGEM_TARGET_TYPE,
                XUSB_REPORT,
                VigemService,
            )

            button_flag = VigemService.button_name_to_mask(button_name.lower())
            if not button_flag:
                return False
            # Get or create the first X360 target
            target_id: int = 1
            if target_id not in self._vigem_service._targets:
                new_target_id = self._vigem_service.add_x360()
                if not new_target_id:
                    return False
                target_id = new_target_id
            target, ttype = self._vigem_service._targets[target_id]
            if ttype != VIGEM_TARGET_TYPE.XBOX360:
                return False

            import ctypes

            # Press
            report = XUSB_REPORT()
            report.wButtons = button_flag
            report.bLeftTrigger = 0
            report.bRightTrigger = 0
            report.sThumbLX = 0
            report.sThumbLY = 0
            report.sThumbRX = 0
            report.sThumbRY = 0
            if self._vigem_service._dll is None or self._vigem_service._client is None:
                return False
            err: int = self._vigem_service._dll.vigem_target_x360_update(
                self._vigem_service._client, target, ctypes.byref(report)
            )
            if err != 0:
                return False

            # Hold
            if hold_ms > 0:
                time.sleep(hold_ms / 1000.0)

            # Release
            report.wButtons = 0
            err = self._vigem_service._dll.vigem_target_x360_update(
                self._vigem_service._client, target, ctypes.byref(report)
            )
            return err == 0
        except (OSError, ValueError, RuntimeError, AttributeError) as e:
            import logging

            logging.getLogger(__name__).debug(f"ViGEm button press failed: {e}")
            return False

    def get_click_count(self) -> int:
        """Get current click count (compatible with test expectations)."""
        with self._lock:
            return self._click_count

    def get_status(self) -> dict[str, Any]:
        return {
            "is_running": self.is_running,
            "interval_ms": self.interval_ms,
            "hold_ms": self.hold_ms,
            "button": self.button,
            "limit": self.limit,
            "click_count": self.click_count,
            "cps": round(self.cps, 1),
            "background_method": self.background_method,
        }
