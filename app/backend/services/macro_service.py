from __future__ import annotations

import json
import logging
import threading
import time
from typing import TYPE_CHECKING, Any, Dict, List, Literal, Optional, TypedDict, Union, cast, TypeGuard

from app.backend.services.stealth_input import StealthInput

from app.backend.services.pico_service import PicoService, get_pico_service

if TYPE_CHECKING:
    from app.backend.services.vigem_service import VigemService, VIGEM_TARGET_TYPE, get_vigem_service
    from app.backend.qml_bridge import QmlBridge

from app.backend.services.singleton import singleton

logger = logging.getLogger(__name__)


# ─── TypedDict for Undo/Redo Stack Entries ───────────────────────────────────
class AddActionEntry(TypedDict):
    op: str
    action: Dict[str, object]
    index: int


class ClearActionsEntry(TypedDict):
    op: str
    actions: List[Dict[str, object]]


class MoveActionEntry(TypedDict):
    op: str
    action: Dict[str, object]
    from_index: int
    to_index: int


class DeleteActionEntry(TypedDict):
    op: str
    action: Dict[str, object]
    index: int


UndoEntry = Union[AddActionEntry, ClearActionsEntry, MoveActionEntry, DeleteActionEntry]
RedoEntry = UndoEntry  # Same structure for redo stack


# ─── Type Guard Functions for Undo/Redo Entries ──────────────────────────────
def _is_add_entry(entry: UndoEntry) -> TypeGuard[AddActionEntry]:
    return entry.get("op") == "add"


def _is_clear_entry(entry: UndoEntry) -> TypeGuard[ClearActionsEntry]:
    return entry.get("op") == "clear"


def _is_move_entry(entry: UndoEntry) -> TypeGuard[MoveActionEntry]:
    return entry.get("op") == "move"


def _is_delete_entry(entry: UndoEntry) -> TypeGuard[DeleteActionEntry]:
    return entry.get("op") == "delete"


# Type aliases
KeyAction = Dict[str, object]
RunMode = str
BackgroundMethod = str
VigemServiceRef = Optional["VigemService"]
PicoServiceRef = Optional[PicoService]


@singleton
class MacroService:
    def __init__(self) -> None:
        self._lock = threading.RLock()  # Protects all mutable state
        self._is_running: bool = False
        self._run_mode: str = "SEQUENTIAL"
        self._actions: List[KeyAction] = []
        self._threads: List[threading.Thread] = []
        # Background input method: "sendinput", "postmessage", "vigem", "pico"
        self._background_method: BackgroundMethod = "sendinput"
        # Per-module target window (set by bridge)
        self._target_hwnd: Optional[int] = None
        # Bridge reference for logging
        self._bridge: Optional["QmlBridge"] = None
        # Cached service instances (lazy init, like clicker_service)
        self._vigem_service: VigemServiceRef = None
        self._pico_service: PicoServiceRef = None
        # ─── NEW: Undo/Redo stacks ───────────────────────────────
        self._undo_stack: List[UndoEntry] = []
        self._redo_stack: List[RedoEntry] = []
        self._MAX_UNDO: int = 100  # Limit memory usage

    def set_bridge(self, bridge: Optional["QmlBridge"]) -> None:
        """Set bridge reference for logging."""
        self._bridge = bridge

    def _log(self, level: str, message: str) -> None:
        if self._bridge:
            self._bridge.log(level, "MACRO", message)

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
    def run_mode(self) -> RunMode:
        with self._lock:
            return self._run_mode

    @run_mode.setter
    def run_mode(self, value: str) -> None:
        with self._lock:
            if value in ("SEQUENTIAL", "PARALLEL"):
                self._run_mode = value

    @property
    def background_method(self) -> BackgroundMethod:
        with self._lock:
            return self._background_method

    @background_method.setter
    def background_method(self, value: str) -> None:
        with self._lock:
            if value in ("sendinput", "postmessage", "vigem", "pico"):
                self._background_method = value

    @property
    def target_hwnd(self) -> Optional[int]:
        with self._lock:
            return self._target_hwnd

    @target_hwnd.setter
    def target_hwnd(self, value: Optional[int]) -> None:
        with self._lock:
            self._target_hwnd = value

    @property
    def actions(self) -> List[KeyAction]:
        with self._lock:
            return list(self._actions)  # Return copy for thread safety

    def set_run_mode(self, mode: str) -> Dict[str, object]:
        mode = str(mode or "SEQUENTIAL").upper()
        with self._lock:
            if mode not in ("SEQUENTIAL", "PARALLEL"):
                mode = "SEQUENTIAL"
            self._run_mode = mode
        return self.get_status()

    def set_background_method(self, method: str) -> Dict[str, object]:
        with self._lock:
            if method in ("sendinput", "postmessage", "vigem", "pico"):
                self._background_method = method
        return self.get_status()

    def add_action(self, key: str, delay: float, hold: float) -> Dict[str, object]:
        key = str(key).lower().strip()
        delay = max(0.0, float(delay))
        hold = max(0.0, float(hold))
        with self._lock:
            action: KeyAction = {
                "key": key,
                "delay": delay,
                "hold": hold,
            }
            self._actions.append(action)
            action_num = len(self._actions)

            # ─── NEW: Push to undo stack ──────────────────────────
            self._undo_stack.append(
                AddActionEntry(op="add", action=dict(action), index=action_num - 1)
            )
            self._redo_stack.clear()  # New action invalidates redo history
            # Trim stack if too large
            if len(self._undo_stack) > self._MAX_UNDO:
                self._undo_stack.pop(0)

        # Detailed logging — like clicker
        hold_type = "HOLD" if hold > 0 else "TAP"
        hold_str = f"{hold * 1000:.0f}ms" if hold > 0 else "0ms"
        self._log(
            "OK",
            f"Action #{action_num} bound: key='{key}' | type={hold_type} | hold={hold_str} | delay={delay:.2f}s | total={action_num}",
        )
        return self.get_status()

    def clear_actions(self) -> Dict[str, object]:
        with self._lock:
            count = len(self._actions)
            if count > 0:
                # ─── NEW: Save snapshot for undo ──────────────────
                self._undo_stack.append(
                    ClearActionsEntry(op="clear", actions=list(self._actions))
                )
                self._redo_stack.clear()
            self._actions = []
        if count > 0:
            self._log("INFO", f"Cleared {count} action(s)")
        else:
            self._log("INFO", "No actions to clear")
        return self.get_status()

    # ─── NEW: Undo/Redo methods ──────────────────────────────────────────
    def undo(self) -> Dict[str, object]:
        """Undo the last action (add, clear, move, or delete)."""
        with self._lock:
            if not self._undo_stack:
                self._log("INFO", "Undo: nothing to undo")
                return {"ok": False, "error": "Nothing to undo", **self.get_status()}

            entry = self._undo_stack.pop()

            if _is_add_entry(entry):
                # Remove the action that was added
                idx = entry["index"]
                if 0 <= idx < len(self._actions):
                    removed = self._actions.pop(idx)
                    self._redo_stack.append(
                        cast(AddActionEntry, {"op": "add", "action": dict(removed), "index": idx})
                    )
                self._log("INFO", f"Undo: removed action #{idx + 1}")
            elif _is_clear_entry(entry):
                # Restore cleared actions
                self._actions = list(entry["actions"])
                self._redo_stack.append(
                    cast(ClearActionsEntry, {"op": "clear", "actions": list(entry["actions"])})
                )
                self._log("INFO", f"Undo: restored {len(self._actions)} action(s)")
            elif _is_move_entry(entry):
                # Reverse the move
                self._actions.pop(entry["to_index"])
                self._actions.insert(entry["from_index"], entry["action"])
                self._redo_stack.append(
                    cast(MoveActionEntry, {
                        "op": "move",
                        "action": dict(entry["action"]),
                        "from_index": entry["to_index"],  # swapped
                        "to_index": entry["from_index"],
                    })
                )
                self._log("INFO", f"Undo: moved action back to #{entry['from_index'] + 1}")
            elif _is_delete_entry(entry):
                # Restore deleted action
                self._actions.insert(entry["index"], entry["action"])
                self._redo_stack.append(
                    cast(DeleteActionEntry, {
                        "op": "delete", "action": dict(entry["action"]), "index": entry["index"]
                    })
                )
                self._log("INFO", f"Undo: restored action #{entry['index'] + 1}")

            return {"ok": True, **self.get_status()}

    def redo(self) -> Dict[str, object]:
        """Redo the previously undone action."""
        with self._lock:
            if not self._redo_stack:
                self._log("INFO", "Redo: nothing to redo")
                return {"ok": False, "error": "Nothing to redo", **self.get_status()}

            entry = self._redo_stack.pop()

            if _is_add_entry(entry):
                # Re-add the action
                self._actions.insert(entry["index"], dict(entry["action"]))
                self._undo_stack.append(
                    cast(AddActionEntry, {"op": "add", "action": dict(entry["action"]), "index": entry["index"]})
                )
                self._log("INFO", f"Redo: re-added action #{entry['index'] + 1}")
            elif _is_clear_entry(entry):
                # Clear again
                self._undo_stack.append(
                    cast(ClearActionsEntry, {"op": "clear", "actions": list(self._actions)})
                )
                self._actions = []
                self._log("INFO", "Redo: cleared actions")
            elif _is_move_entry(entry):
                # Re-apply the move
                self._actions.pop(entry["from_index"])
                self._actions.insert(entry["to_index"], entry["action"])
                self._undo_stack.append(
                    cast(MoveActionEntry, {
                        "op": "move",
                        "action": dict(entry["action"]),
                        "from_index": entry["from_index"],
                        "to_index": entry["to_index"],
                    })
                )
                self._log("INFO", f"Redo: moved action to #{entry['to_index'] + 1}")
            elif _is_delete_entry(entry):
                # Delete again
                self._actions.pop(entry["index"])
                self._undo_stack.append(
                    cast(DeleteActionEntry, {
                        "op": "delete", "action": dict(entry["action"]), "index": entry["index"]
                    })
                )
                self._log("INFO", f"Redo: deleted action #{entry['index'] + 1}")

            return {"ok": True, **self.get_status()}

    def delete_action(self, index: int) -> Dict[str, object]:
        """Delete a specific action by index (1-click delete)."""
        with self._lock:
            if index < 0 or index >= len(self._actions):
                return {"ok": False, "error": f"Invalid index {index}", **self.get_status()}

            removed = self._actions.pop(index)
            self._undo_stack.append(
                DeleteActionEntry(op="delete", action=dict(removed), index=index)
            )
            self._redo_stack.clear()

            self._log("INFO", f"Deleted action #{index + 1}: key='{removed['key']}'")
            return {"ok": True, **self.get_status()}

    def move_action(self, from_index: int, to_index: int) -> Dict[str, object]:
        """Move action from one position to another (drag & drop reorder)."""
        with self._lock:
            if (
                from_index < 0
                or from_index >= len(self._actions)
                or to_index < 0
                or to_index >= len(self._actions)
                or from_index == to_index
            ):
                return {"ok": False, "error": "Invalid indices", **self.get_status()}

            action = self._actions.pop(from_index)
            self._actions.insert(to_index, action)
            self._undo_stack.append(
                MoveActionEntry(
                    op="move",
                    action=dict(action),
                    from_index=from_index,
                    to_index=to_index,
                )
            )
            self._redo_stack.clear()

            self._log("INFO", f"Moved action #{from_index + 1} → #{to_index + 1}")
            return {"ok": True, **self.get_status()}

    def get_undo_redo_status(self) -> Dict[str, object]:
        """Returns undo/redo availability for UI button state."""
        with self._lock:
            return {
                "can_undo": len(self._undo_stack) > 0,
                "can_redo": len(self._redo_stack) > 0,
                "undo_count": len(self._undo_stack),
                "redo_count": len(self._redo_stack),
            }

    def start(self, target_hwnd: int | None = None) -> Dict[str, object]:
        with self._lock:
            if self._is_running or not self._actions:
                if not self._actions:
                    self._log("WARN", "Cannot start — no actions configured")
                return self.get_status()
            # Snapshot config values to avoid holding lock in workers
            if target_hwnd is None:
                target_hwnd = self._target_hwnd
            self._is_running = True
            run_mode = self._run_mode
            actions = list(self._actions)  # Copy for thread safety

        self._log("OK", f"Started — mode={run_mode} actions={len(actions)}")

        if run_mode == "SEQUENTIAL":
            t = threading.Thread(target=self._sequential_worker, args=(target_hwnd, actions), daemon=True)
            t.start()
            with self._lock:
                self._threads = [t]
        else:
            threads = []
            for action in actions:
                t = threading.Thread(target=self._parallel_worker, args=(target_hwnd, action), daemon=True)
                t.start()
                threads.append(t)
            with self._lock:
                self._threads = threads
        return self.get_status()

    def stop(self) -> Dict[str, object]:
        with self._lock:
            was_running = self._is_running
            self._is_running = False
        if was_running:
            self._log("INFO", "Stopped")
        return self.get_status()

    def _press(self, target_hwnd: Optional[int], key: str, hold: float) -> None:
        # Convert hold from seconds to milliseconds
        hold_ms = int(hold * 1000) if hold > 0 else 0

        # Read background_method under lock each call to support live changes
        with self._lock:
            background_method = self._background_method

        if target_hwnd:
            if background_method == "sendinput":
                # Use global SendInput (stealth) - requires focus
                vk = self._vk_from_name(key)
                if vk:
                    StealthInput.send_key_vk(vk, hold_ms)
                return
            elif background_method == "vigem":
                # Map keyboard key to gamepad button and use ViGEm
                self._vigem_press_key_mapped(key, hold_ms)
                return
            elif background_method == "pico":
                # Send key via Pico HID
                self._pico_press_key_mapped(key, hold_ms)
                return
            else:
                # Default: PostMessage (background)
                from utils import send_background_key

                send_background_key(target_hwnd, key)
                return

        # No target window - use global keyboard library (foreground)
        import keyboard

        keyboard.press(key)
        if hold > 0:
            time.sleep(hold)
        keyboard.release(key)

    def _sequential_worker(self, target_hwnd: Optional[int], actions: List[Dict[str, Any]]) -> None:
        time.sleep(0.2)
        cycle = 0
        while True:
            with self._lock:
                if not self._is_running:
                    break
            cycle += 1
            self._log("INFO", f"Cycle {cycle} started — {len(actions)} actions")
            for i, action in enumerate(actions):
                with self._lock:
                    if not self._is_running:
                        break
                hold_type = "HOLD" if action["hold"] > 0 else "TAP"
                self._log(
                    "OK",
                    f"  [{cycle}.{i+1}/{len(actions)}] key='{action['key']}' {hold_type} hold={action['hold']*1000:.0f}ms delay={action['delay']:.2f}s",
                )
                self._press(target_hwnd, action["key"], action["hold"])
                end_sleep = time.time() + action["delay"]
                while True:
                    with self._lock:
                        if not self._is_running:
                            break
                    if time.time() >= end_sleep:
                        break
                    time.sleep(0.01)

    def _parallel_worker(self, target_hwnd: Optional[int], action: Dict[str, Any]) -> None:
        time.sleep(0.2)
        cycle = 0
        while True:
            with self._lock:
                if not self._is_running:
                    break
            cycle += 1
            hold_type = "HOLD" if action["hold"] > 0 else "TAP"
            self._log(
                "OK",
                f"  [P.{cycle}] key='{action['key']}' {hold_type} hold={action['hold']*1000:.0f}ms delay={action['delay']:.2f}s",
            )
            self._press(target_hwnd, action["key"], action["hold"])
            end_sleep = time.time() + action["delay"]
            while True:
                with self._lock:
                    if not self._is_running:
                        break
                if time.time() >= end_sleep:
                    break
                time.sleep(0.02)

    def _vigem_press_key_mapped(self, key: str, hold_ms: int) -> bool:
        """Map keyboard key to gamepad button and press via ViGEm."""
        # Cache ViGEm service (lazy init) like clicker_service
        try:
            if self._vigem_service is None:
                from app.backend.services.vigem_service import get_vigem_service

                self._vigem_service = get_vigem_service()
                if not self._vigem_service.connect():
                    self._vigem_service = None
                    return False

            from app.backend.services.vigem_service import VigemService, XUSB_REPORT, VIGEM_TARGET_TYPE
            import ctypes

            # Map key name to XUSB button flag
            button_flag = VigemService.button_name_to_mask(key.lower())
            if not button_flag:
                # Try to map from default gamepad button map
                default_map = {
                    "space": "a",
                    "enter": "a",
                    "shift": "lb",
                    "ctrl": "rb",
                    "q": "x",
                    "e": "y",
                    "r": "b",
                    "tab": "back",
                    "escape": "start",
                    "w": "up",
                    "s": "down",
                    "a": "left",
                    "d": "right",
                }
                mapped = default_map.get(key.lower())
                if mapped:
                    button_flag = VigemService.button_name_to_mask(mapped.lower())

            if not button_flag:
                return False

            # Get or create the X360 target
            target_id: int = 1
            if target_id not in self._vigem_service._targets:
                new_target_id = self._vigem_service.add_x360()
                if not new_target_id:
                    return False
                target_id = new_target_id

            target, ttype = self._vigem_service._targets[target_id]
            if ttype != VIGEM_TARGET_TYPE.XBOX360:
                return False

            # Send press
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
            err = self._vigem_service._dll.vigem_target_x360_update(
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
            return bool(err == 0)
        except Exception as e:
            logging.getLogger(__name__).debug(f"ViGEm key press failed: {e}")
            return False

    def _vk_from_name(self, key: str) -> int | None:
        """Convert key name to VK code."""
        k = (key or "").strip().lower()
        if not k:
            return None

        # Check VK_MAP from stealth_input
        from app.backend.services.stealth_input import VK_MAP

        return VK_MAP.get(k)

    def _pico_press_key_mapped(self, key: str, hold_ms: int) -> bool:
        """Map keyboard key to gamepad button and press via Pico HID."""
        # Cache Pico service (lazy init) like clicker_service
        try:
            if self._pico_service is None:
                from app.backend.services.pico_service import get_pico_service

                self._pico_service = get_pico_service()

            pico = self._pico_service

            if not pico.is_connected:
                # Try to connect using runtime state config
                from app.backend.persistence import PROFILE_PATH
                import json

                port: Optional[str] = None
                baudrate = 115200
                try:
                    data = json.loads(PROFILE_PATH.read_text(encoding="utf-8"))
                    state = data.get("state") or {}
                    port = state.get("pico_port")
                    baudrate = int(state.get("pico_baudrate", 115200))
                except Exception:
                    pass
                if port:
                    # Reconfigure existing instance with new port
                    pico._port = port
                    pico._baudrate = baudrate
                if not pico.connect():
                    return False

            # Map key to gamepad button (XInput layout)
            btn_map = {
                "space": 0x1000,
                "enter": 0x1000,  # A
                "shift": 0x0100,
                "ctrl": 0x0200,  # LB, RB
                "q": 0x4000,
                "e": 0x8000,
                "r": 0x2000,  # X, Y, B
                "tab": 0x0020,
                "escape": 0x0010,  # BACK, START
                "w": 0x0001,
                "s": 0x0002,
                "a": 0x0004,
                "d": 0x0008,  # DPAD
            }
            btn = btn_map.get(key.lower())
            if btn is None:
                return False

            if hold_ms > 0:
                # Press -> wait -> release
                if not pico.gp_set_buttons(btn):
                    return False
                time.sleep(hold_ms / 1000.0)
                return pico.gp_set_buttons(0)
            else:
                # Tap: press and immediately release
                return pico.gp_set_buttons(btn) and pico.gp_set_buttons(0)

        except Exception as e:
            logging.getLogger(__name__).debug(f"Pico key press failed: {e}")
            return False

    def get_status(self) -> Dict[str, object]:
        with self._lock:
            return {
                "is_running": self._is_running,
                "run_mode": self._run_mode,
                "actions": list(self._actions),
                "actions_count": len(self._actions),
                "background_method": self._background_method,
                # ─── NEW: Undo/Redo status ─────────────────────────
                "can_undo": len(self._undo_stack) > 0,
                "can_redo": len(self._redo_stack) > 0,
                "undo_count": len(self._undo_stack),
                "redo_count": len(self._redo_stack),
            }
