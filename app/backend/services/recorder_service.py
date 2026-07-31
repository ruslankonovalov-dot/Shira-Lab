from __future__ import annotations

import json
import logging
import os
import threading
import time
from pathlib import Path
from typing import (
    Any,
    Protocol,
)

# keyboard lib — тоже нет стабов
from pynput import keyboard as pynput_key
from pynput import mouse
from pynput.keyboard import Controller as KeyboardController
from pynput.keyboard import Key as PynputKey
from pynput.keyboard import Listener as KeyboardListener
from pynput.mouse import Controller as MouseController
from pynput.mouse import Listener as MouseListener

from app.backend.services.singleton import singleton
from app.backend.services.stealth_input import VK_MAP, StealthInput
from app.backend.services.vigem_service import (
    VIGEM_TARGET_TYPE,
    XUSB_REPORT,
)

logger = logging.getLogger(__name__)

# Type aliases
BackgroundMethod = str
RecordedEvents = list[list[Any]]

# Bridge protocol для типизации _bridge
class BridgeLike(Protocol):
    def log(self, level: str, module: str, message: str) -> None: ...


@singleton
class RecorderService:
    def __init__(self) -> None:
        # Use absolute path next to script — independent of CWD.
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
        self.records_dir: str = os.path.join(base_dir, "records")
        os.makedirs(self.records_dir, exist_ok=True)
        self.is_recording: bool = False
        self.is_playing: bool = False
        self.recorded_events: RecordedEvents = []
        self.start_time: float = 0.0
        self._m_listener: MouseListener | None = None
        self._k_listener: KeyboardListener | None = None
        self._m_listener_thread: threading.Thread | None = None
        self._k_listener_thread: threading.Thread | None = None
        self._lock: threading.RLock = threading.RLock()  # Protect all state
        # Per-module target window (set by bridge)
        self.target_hwnd: int | None = None
        # Background input method: "sendinput", "postmessage", "vigem", "pico"
        self._background_method: BackgroundMethod = "sendinput"
        # Bridge reference for logging
        self._bridge: BridgeLike | None = None

    @property
    def background_method(self) -> BackgroundMethod:
        with self._lock:
            return self._background_method

    @background_method.setter
    def background_method(self, value: str) -> None:
        with self._lock:
            if value in ("sendinput", "postmessage", "vigem", "pico"):
                self._background_method = value

    def set_bridge(self, bridge: BridgeLike | None) -> None:
        """Set bridge reference for logging."""
        self._bridge = bridge

    def _log(self, level: str, message: str) -> None:
        if self._bridge:
            self._bridge.log(level, "RECORDER", message)

    def _safe_record_path(self, name: str) -> str | None:
        """Resolve a record filename to a safe absolute path inside records_dir.

        SECURITY: Prevents path traversal attacks (e.g. name='../../../etc/passwd').
        Returns None if the name is invalid or escapes the records directory.

        Windows-safe: uses Path.resolve() and is_relative_to() (Python 3.9+)
        instead of os.path.commonpath which fails across different drives.
        """
        if not name or not name.endswith(".json"):
            return None
        # Strip any directory components — only filename is allowed
        safe_name = os.path.basename(name)
        if safe_name != name:
            # User tried to pass a path with separators — reject
            return None
        try:
            records_dir = Path(self.records_dir).resolve()
            target_path = (records_dir / safe_name).resolve()
            # Python 3.9+: is_relative_to handles cross-drive correctly on Windows
            if not target_path.is_relative_to(records_dir):
                return None
            return str(target_path)
        except Exception:
            return None

    def list_records(self) -> dict[str, Any]:
        try:
            items = [f for f in os.listdir(self.records_dir) if f.endswith(".json")]
            items.sort(reverse=True)
        except Exception:
            logger.exception("Failed to list records")
            items = []
        return {"ok": True, "records": items}

    def delete_record(self, name: str) -> dict[str, Any]:
        path = self._safe_record_path(name)
        if path and os.path.exists(path):
            try:
                os.remove(path)
            except Exception:
                logger.exception(f"Failed to delete record {name}")
        return self.list_records()

    def start_recording(self) -> dict[str, Any]:
        with self._lock:
            if self.is_recording:
                return self.status()
            # Ensure previous listeners are fully stopped
            self._stop_listeners_locked()
            self.is_recording = True
            self.recorded_events = []
            self.start_time = time.time()
            self._m_listener = mouse.Listener(on_click=self._on_click, on_move=self._on_move)
            self._k_listener = pynput_key.Listener(on_press=self._on_key_down, on_release=self._on_key_up)
            self._m_listener_thread = threading.Thread(target=self._m_listener.run, daemon=True)
            self._k_listener_thread = threading.Thread(target=self._k_listener.run, daemon=True)
            self._m_listener_thread.start()
            self._k_listener_thread.start()
            self._log("OK", "Recording started")
            return self.status()

    def stop_recording(self) -> dict[str, Any]:
        with self._lock:
            if not self.is_recording:
                return self.status()
            self.is_recording = False
            self._stop_listeners_locked()
            event_count = len(self.recorded_events)
            self._save_record()
            self._log("OK", f"Recording stopped — {event_count} events saved")
            return self.status()

    def _stop_listeners_locked(self) -> None:
        """Stop listeners and join threads. Must be called with _lock held."""
        for listener, thread in [(self._m_listener, self._m_listener_thread),
                                 (self._k_listener, self._k_listener_thread)]:
            if listener:
                try:
                    listener.stop()
                except Exception:
                    logger.exception("Failed to stop input listener")
            if thread and thread.is_alive():
                thread.join(timeout=1.0)
        self._m_listener = None
        self._k_listener = None
        self._m_listener_thread = None
        self._k_listener_thread = None

    def play_record(self, name: str, repeats: int = 1) -> dict[str, Any]:
        with self._lock:
            path = self._safe_record_path(name)
            if not path or not os.path.exists(path):
                self._log("WARN", f"Record not found: {name}")
                return {"ok": False, "error": "Record not found"}
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except Exception as e:
                self._log("ERROR", f"Failed to load {name}: {e}")
                return {"ok": False, "error": f"Failed to load record: {e}"}
            if self.is_playing:
                return self.status()
            self.is_playing = True
            self._log("OK", f"Playing '{name}' x{repeats}")
            threading.Thread(target=self._play_thread, args=(data, max(1, int(repeats))), daemon=True).start()
            return self.status()

    def stop_playing(self) -> dict[str, Any]:
        with self._lock:
            was_playing = self.is_playing
            self.is_playing = False
            if was_playing:
                self._log("INFO", "Playback stopped")
            return self.status()

    def set_background_method(self, method: str) -> dict[str, Any]:
        with self._lock:
            if method in ("sendinput", "postmessage", "vigem", "pico"):
                self.background_method = method
            return self.status()

    def _vigem_press_button(self, btn_name: str) -> bool:
        """Press a gamepad button via ViGEm. Returns success."""
        try:
            import ctypes

            from app.backend.services.vigem_service import (
                XUSB_BUTTON_MAP,
                get_vigem_service,
            )
            vigem = get_vigem_service()
            if not vigem.connect():
                return False
            mask = XUSB_BUTTON_MAP.get(btn_name.lower(), 0)
            if not mask:
                return False
            # Get or create first X360 target
            target_id = 1
            with vigem._lock:
                if target_id not in vigem._targets:
                    new_id = vigem.add_x360()
                    if not new_id:
                        return False
                    target_id = new_id
                target, ttype = vigem._targets[target_id]
                if ttype != VIGEM_TARGET_TYPE.XBOX360:
                    return False
                if vigem._dll is None or vigem._client is None:
                    return False
            # Press
            report = XUSB_REPORT()
            report.wButtons = mask
            err = vigem._dll.vigem_target_x360_update(vigem._client, target, ctypes.byref(report))
            return bool(err == 0)
        except Exception:
            logger.exception("ViGEm press button failed")
            return False

    def _vigem_release_all(self) -> bool:
        """Release all gamepad buttons via ViGEm. Returns success."""
        try:
            import ctypes

            from app.backend.services.vigem_service import get_vigem_service
            vigem = get_vigem_service()
            if not vigem.connect():
                return False
            target_id = 1
            with vigem._lock:
                if target_id not in vigem._targets:
                    return True  # nothing to release
                target, ttype = vigem._targets[target_id]
                if ttype != VIGEM_TARGET_TYPE.XBOX360:
                    return False
                if vigem._dll is None or vigem._client is None:
                    return False
            # Release
            report = XUSB_REPORT()
            report.wButtons = 0
            err = vigem._dll.vigem_target_x360_update(vigem._client, target, ctypes.byref(report))
            return bool(err == 0)
        except Exception:
            logger.exception("ViGEm release failed")
            return False

    def _press_key(self, key_name: str, hold_ms: int) -> None:
        """Send key press using configured background method."""
        vk = VK_MAP.get(key_name.lower()) if key_name else None
        if not vk:
            return

        if self.target_hwnd:
            if self.background_method == "postmessage":
                from utils import send_background_key
                send_background_key(self.target_hwnd, key_name.upper())
            elif self.background_method == "vigem":
                # Map keyboard key to gamepad button and send via ViGEm
                key_to_gamepad = {
                    "space": "a", "enter": "a",
                    "shift": "lb", "ctrl": "rb",
                    "q": "x", "e": "y", "r": "b",
                    "tab": "back", "escape": "start",
                    "w": "up", "s": "down", "a": "left", "d": "right",
                    "mouse1": "lt", "mouse2": "rt",
                }
                gamepad_btn = key_to_gamepad.get(key_name.lower())
                if gamepad_btn:
                    self._vigem_press_button(gamepad_btn)
                return
            elif self.background_method == "pico":
                # Send key via Pico HID
                self._pico_press_key(key_name, hold_ms)
                return
            else:  # sendinput (global)
                StealthInput.send_key_vk(vk, hold_ms)
        else:
            # No target window - use global keyboard library (foreground)
            import keyboard
            keyboard.press(key_name)
            if hold_ms > 0:
                time.sleep(hold_ms / 1000.0)
            keyboard.release(key_name)

    def press_key(self, key_name: str) -> None:
        """Press key only (for background methods)."""
        vk = VK_MAP.get(key_name.lower()) if key_name else None
        if not vk:
            return
        if self.target_hwnd and self.background_method == "postmessage":
            from utils import send_background_key
            send_background_key(self.target_hwnd, key_name.upper())
        elif self.target_hwnd and self.background_method == "vigem":
            key_to_gamepad = {
                "space": "a", "enter": "a",
                "shift": "lb", "ctrl": "rb",
                "q": "x", "e": "y", "r": "b",
                "tab": "back", "escape": "start",
                "w": "up", "s": "down", "a": "left", "d": "right",
                "mouse1": "lt", "mouse2": "rt",
            }
            gamepad_btn = key_to_gamepad.get(key_name.lower())
            if gamepad_btn:
                self._vigem_press_button(gamepad_btn)
        elif self.target_hwnd and self.background_method == "pico":
            self._pico_press_key(key_name, 0)
        else:
            StealthInput.send_key_vk(vk, 0)

    def release_key(self, key_name: str) -> None:
        """Release key only (for background methods)."""
        if self.target_hwnd and self.background_method == "postmessage":
            from utils import send_background_key_up
            send_background_key_up(self.target_hwnd, key_name.upper())
        elif self.target_hwnd and self.background_method == "vigem":
            self._vigem_release_all()
        elif self.target_hwnd and self.background_method == "pico":
            from app.backend.services.pico_service import get_pico_service
            pico = get_pico_service()
            if pico.is_connected:
                pico.gp_set_buttons(0)

    def _send_click(self, button: str, hold_ms: int) -> None:
        """Send mouse click using configured background method."""
        if self.target_hwnd:
            if self.background_method == "postmessage":
                from utils import send_background_click
                send_background_click(self.target_hwnd, button=button)
            elif self.background_method == "vigem":
                # Map mouse button to gamepad trigger/button and send via ViGEm
                button_to_gamepad = {
                    "L": "a",      # Left click -> A button
                    "R": "b",      # Right click -> B button
                    "M": "x",      # Middle click -> X button
                    "X1": "lb",    # X1 -> Left bumper
                    "X2": "rb",    # X2 -> Right bumper
                }
                gamepad_btn = button_to_gamepad.get(button)
                if gamepad_btn:
                    self._vigem_press_button(gamepad_btn)
                return
            elif self.background_method == "pico":
                # Send mouse click via Pico HID
                self._pico_send_click(button, hold_ms)
                return
            else:  # sendinput (global)
                StealthInput.send_mouse_click(button, hold_ms)
        else:
            # No target window - use global mouse_event
            import ctypes
            buttons = {
                "L": {"down": 0x0002, "up": 0x0004, "data": 0},
                "R": {"down": 0x0008, "up": 0x0010, "data": 0},
                "M": {"down": 0x0020, "up": 0x0040, "data": 0},
                "X1": {"down": 0x0080, "up": 0x0100, "data": 1},
                "X2": {"down": 0x0080, "up": 0x0100, "data": 2},
            }
            info = buttons.get(button, buttons["L"])
            ctypes.windll.user32.mouse_event(info["down"], 0, 0, info["data"], 0)
            if hold_ms > 0:
                time.sleep(hold_ms / 1000.0)
            ctypes.windll.user32.mouse_event(info["up"], 0, 0, info["data"], 0)

    def press_click(self, button: str) -> None:
        """Press mouse button only (for background methods)."""
        if self.target_hwnd and self.background_method == "postmessage":
            from utils import send_background_click
            send_background_click(self.target_hwnd, button=button)
        elif self.target_hwnd and self.background_method == "vigem":
            button_to_gamepad = {
                "L": "a", "R": "b", "M": "x", "X1": "lb", "X2": "rb",
            }
            gamepad_btn = button_to_gamepad.get(button)
            if gamepad_btn:
                self._vigem_press_button(gamepad_btn)
        elif self.target_hwnd and self.background_method == "pico":
            self._pico_send_click(button, 0)

    def release_click(self, button: str) -> None:
        """Release mouse button only (for background methods)."""
        if self.target_hwnd and self.background_method == "postmessage":
            from utils import send_background_click_up
            send_background_click_up(self.target_hwnd, button)
        elif self.target_hwnd and self.background_method == "vigem":
            self._vigem_release_all()
        elif self.target_hwnd and self.background_method == "pico":
            from app.backend.services.pico_service import get_pico_service
            pico = get_pico_service()
            if pico.is_connected:
                pico.ms_click(0, 0)

    def _play_thread(self, data: list[list[Any]], repeats: int) -> None:
        m_ctrl: MouseController = mouse.Controller()
        k_ctrl: KeyboardController = pynput_key.Controller()
        try:
            events: list[list[Any]] = data.get("events", []) if isinstance(data, dict) else data
            for _ in range(repeats):
                if not self.is_playing:
                    break
                start_p = time.time()
                for ev in events:
                    if not self.is_playing:
                        break
                    target_time = ev[-1]
                    while (time.time() - start_p) < target_time:
                        if not self.is_playing:
                            break
                        time.sleep(0.001)
                    try:
                        if ev[0] == "m":
                            # Mouse move
                            if self.target_hwnd and self.background_method != "sendinput":
                                # For background, we'd need PostMessage for moves
                                # For now, use global move
                                m_ctrl.position = (int(ev[1]), int(ev[2]))
                            else:
                                m_ctrl.position = (int(ev[1]), int(ev[2]))
                        elif ev[0] == "c":
                            # Mouse click
                            btn = ev[3].split(".")[-1].upper()
                            if ev[4]:  # press
                                if self.target_hwnd and self.background_method != "sendinput":
                                    self._send_click(btn, 0)  # hold=0 for press
                                else:
                                    m_ctrl.position = (int(ev[1]), int(ev[2]))
                                    m_ctrl.press(getattr(mouse.Button, btn))
                            else:  # release
                                if self.target_hwnd and self.background_method != "sendinput":
                                    # Use PostMessage for background release
                                    from utils import send_background_click_up
                                    send_background_click_up(self.target_hwnd, btn, int(ev[1]), int(ev[2]))
                                else:
                                    m_ctrl.release(getattr(mouse.Button, btn))
                        elif ev[0] in ("kd", "ku"):
                            # Key down/up
                            key_str = str(ev[1]).replace("Key.", "").replace("'", "").lower()
                            k_obj = self._resolve_key_obj(ev[1])
                            if k_obj is None:
                                continue
                            if ev[0] == "kd":
                                if self.target_hwnd and self.background_method != "sendinput":
                                    self._press_key(key_str, 50)  # small hold for background
                                else:
                                    k_ctrl.press(k_obj)
                            else:
                                if self.target_hwnd and self.background_method != "sendinput":
                                    # Key up - use PostMessage for background release
                                    from utils import send_background_key_up
                                    send_background_key_up(self.target_hwnd, key_str)
                                else:
                                    k_ctrl.release(k_obj)
                    except Exception as e:
                        # Report error via bridge (user-visible) AND log
                        self._log("ERROR", f"Playback error: {e}")
                        logger.exception("Failed to execute action during playback")
                        time.sleep(0.05)
        finally:
            self.is_playing = False

    def _on_move(self, x: int, y: int) -> None:
        if self.is_recording:
            self.recorded_events.append(["m", x, y, time.time() - self.start_time])

    def _on_click(self, x: int, y: int, button: MouseController, pressed: bool) -> None:
        if self.is_recording:
            self.recorded_events.append(["c", x, y, str(button), pressed, time.time() - self.start_time])

    def _on_key_down(self, key: PynputKey) -> None:
        if self.is_recording:
            self.recorded_events.append(["kd", str(key), time.time() - self.start_time])

    def _on_key_up(self, key: PynputKey) -> None:
        if self.is_recording:
            self.recorded_events.append(["ku", str(key), time.time() - self.start_time])

    def _resolve_key_obj(self, key: PynputKey) -> PynputKey | None:
        """Convert a pynput key string back to a pynput key object."""
        try:
            key_str = str(key).replace("Key.", "").replace("'", "").lower()
            return getattr(pynput_key.Key, key_str, key_str)
        except Exception:
            return None

    def _save_record(self) -> None:
        """Save recorded events to a JSON file in records_dir.

        Filename format: REC_YYYYMMDD_HHMMSS.json
        If recording is empty, no file is created.
        """
        if not self.recorded_events:
            return
        try:
            import datetime
            filename = "REC_" + datetime.datetime.now().strftime("%Y%m%d_%H%M%S") + ".json"
            path = os.path.join(self.records_dir, filename)
            data = {
                "events": self.recorded_events,
                "created_at": datetime.datetime.now().isoformat(),
                "events_count": len(self.recorded_events),
            }
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except Exception:
            logger.exception("Failed to save record")

    def status(self) -> dict[str, Any]:
        with self._lock:
            return {
                "ok": True,
                "is_recording": self.is_recording,
                "is_playing": self.is_playing,
                "events_count": len(self.recorded_events),
                "background_method": self.background_method,
            }

    def _pico_press_key(self, key_name: str, hold_ms: int) -> bool:
        """Send key press via Pico HID (gamepad button or keyboard tap).

        Properly handles tap vs hold with correct timing.
        """
        try:
            from app.backend.services.pico_service import get_pico_service
            pico = get_pico_service()
            if not pico.is_connected:
                # Try to connect using saved config from profile
                port, baudrate = self._get_pico_config()
                if port:
                    pico = get_pico_service(port=port, baudrate=baudrate)
                if not pico.connect():
                    self._log("ERROR", "Pico not connected for key press")
                    return False

            # Map common keys to gamepad buttons (XInput layout)
            btn_map = {
                "space": 0x1000, "enter": 0x1000,  # A
                "shift": 0x0100, "ctrl": 0x0200,  # LB, RB
                "q": 0x4000, "e": 0x8000, "r": 0x2000,  # X, Y, B
                "tab": 0x0020, "escape": 0x0010,  # BACK, START
                "w": 0x0001, "s": 0x0002, "a": 0x0004, "d": 0x0008,  # DPAD
                "mouse1": 0x0100, "mouse2": 0x0200,  # LT, RT (as LB, RB)
            }
            btn = btn_map.get(key_name.lower())
            if btn is None:
                self._log("WARN", f"Pico: no mapping for key '{key_name}'")
                return False

            if hold_ms > 0:
                # Press -> wait -> release
                ok = pico.gp_set_buttons(btn)
                if not ok:
                    return False
                time.sleep(hold_ms / 1000.0)
                return pico.gp_set_buttons(0)  # Release all
            else:
                # Tap: press and immediately release
                return pico.gp_set_buttons(btn) and pico.gp_set_buttons(0)

        except Exception as e:
            self._log("ERROR", f"Pico key press failed: {e}")
            logger.exception("Pico key press failed")
            return False

    def _get_pico_config(self) -> tuple[str | None, int]:
        """Read Pico port/baudrate from profile. Returns (port, baudrate)."""
        try:
            import json

            from app.backend.persistence import PROFILE_PATH
            data = json.loads(PROFILE_PATH.read_text(encoding="utf-8"))
            state = data.get("state") or {}
            port = state.get("pico_port")
            baudrate = int(state.get("pico_baudrate", 115200))
            return port, baudrate
        except Exception:
            return None, 115200

    def _pico_send_click(self, button: str, hold_ms: int) -> bool:
        """Send mouse click via Pico HID."""
        try:
            from app.backend.services.pico_service import get_pico_service
            pico = get_pico_service()
            if not pico.is_connected:
                port, baudrate = self._get_pico_config()
                if port:
                    pico = get_pico_service(port=port, baudrate=baudrate)
                if not pico.connect():
                    self._log("ERROR", "Pico not connected for mouse click")
                    return False

            btn_map = {"L": 1, "R": 2, "M": 4, "X1": 8, "X2": 16}
            btn_mask = btn_map.get(button, 1)
            return pico.ms_click(btn_mask, hold_ms)

        except Exception as e:
            self._log("ERROR", f"Pico click failed: {e}")
            logger.exception("Pico click failed")
            return False
