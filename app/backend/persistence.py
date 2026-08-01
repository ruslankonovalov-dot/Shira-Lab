from __future__ import annotations

import json
import logging
import threading
from pathlib import Path
from typing import Any

from app.backend.models.runtime_state import RuntimeState
from app.backend.services.hotkey_service import HOTKEY_ACTIONS, default_hotkeys

logger = logging.getLogger(__name__)

PROFILE_DIR = Path(__file__).resolve().parent.parent.parent / "data"
PROFILE_PATH = PROFILE_DIR / "profile.json"

# Global lock for profile save/load to prevent race conditions
_profile_lock = threading.RLock()


def _ensure_dir() -> None:
    PROFILE_DIR.mkdir(parents=True, exist_ok=True)


def _normalize_hotkeys(raw: Any) -> dict[str, dict[str, str]]:
    defaults = default_hotkeys()
    if not isinstance(raw, dict):
        return defaults
    out: dict[str, dict[str, str]] = {}
    for action in HOTKEY_ACTIONS:
        item = raw.get(action)
        if not isinstance(item, dict):
            out[action] = dict(defaults[action])
            continue
        key = str(item.get("key", "")).strip().lower()
        mode = str(item.get("mode", "TOGGLE")).upper()
        if mode not in ("TOGGLE", "HOLD"):
            mode = "TOGGLE"
        out[action] = {"key": key, "mode": mode}
    return out


def _state_to_dict(state: RuntimeState) -> dict[str, Any]:
    return {
        "target_hwnd": state.target_hwnd,
        "target_name": state.target_name,
        "clicker_target_hwnd": state.clicker_target_hwnd,
        "clicker_target_name": state.clicker_target_name,
        "macro_target_hwnd": state.macro_target_hwnd,
        "macro_target_name": state.macro_target_name,
        "aim_target_hwnd": state.aim_target_hwnd,
        "aim_target_name": state.aim_target_name,
        "recorder_target_hwnd": state.recorder_target_hwnd,
        "recorder_target_name": state.recorder_target_name,
        "theme": dict(state.theme),
        "ui_lang": state.ui_lang,
        "is_pinned": state.is_pinned,
        "hotkeys": dict(state.hotkeys),
        "terminal_palette": state.terminal_palette,
        "background_method": state.background_method,
        # Gamepad / ViGEm
        "gamepad_enabled": state.gamepad_enabled,
        "gamepad_controller_type": state.gamepad_controller_type,
        "gamepad_target_index": state.gamepad_target_index,
        "gamepad_button_map": dict(state.gamepad_button_map),
        # Pico Physical HID
        "pico_enabled": getattr(state, "pico_enabled", False),
        "pico_port": getattr(state, "pico_port", None),
        "pico_baudrate": getattr(state, "pico_baudrate", 115200),
        "pico_mode": getattr(state, "pico_mode", "COMPOSITE"),
        "pico_button_map": dict(getattr(state, "pico_button_map", {})),
    }


def _state_from_dict(data: dict[str, Any]) -> RuntimeState:
    d0 = RuntimeState()
    t = dict(d0.theme)
    if isinstance(data.get("theme"), dict):
        t.update(data["theme"])
    th = data.get("target_hwnd")
    if th is not None:
        try:
            th = int(th)
        except (ValueError, TypeError):
            th = None

    # Per-module targets
    def load_target_hwnd(key: str, default_val: int | None) -> int | None:
        val = data.get(key)
        if val is not None:
            try:
                return int(val)
            except (ValueError, TypeError):
                return default_val
        return default_val

    def load_target_name(key: str, default_val: str) -> str:
        val = data.get(key)
        return str(val) if val is not None else default_val

    palette = str(data.get("terminal_palette", d0.terminal_palette)).lower()
    if palette not in ("matrix", "amber", "inverse", "grey", "synthwave", "blood"):
        palette = d0.terminal_palette
    bg_method = str(data.get("background_method", d0.background_method)).lower()
    if bg_method not in ("sendinput", "postmessage", "vigem", "pico"):
        bg_method = d0.background_method
    # Gamepad settings
    gp_enabled = bool(data.get("gamepad_enabled", d0.gamepad_enabled))
    gp_type = str(data.get("gamepad_controller_type", d0.gamepad_controller_type)).upper()
    if gp_type not in ("X360", "DS4"):
        gp_type = d0.gamepad_controller_type
    gp_index = int(data.get("gamepad_target_index", d0.gamepad_target_index))
    gp_map_raw = data.get("gamepad_button_map", {})
    gp_map = {}
    if isinstance(gp_map_raw, dict):
        for k, v in gp_map_raw.items():
            gp_map[str(k).lower()] = str(v).lower()
    # Pico Physical HID settings
    pico_enabled = bool(data.get("pico_enabled", getattr(d0, "pico_enabled", False)))
    pico_port = data.get("pico_port", getattr(d0, "pico_port", None))
    pico_baudrate = int(data.get("pico_baudrate", getattr(d0, "pico_baudrate", 115200)))
    pico_mode = str(data.get("pico_mode", getattr(d0, "pico_mode", "COMPOSITE"))).upper()
    if pico_mode not in ("KEYBOARD", "MOUSE", "GAMEPAD", "COMPOSITE"):
        pico_mode = "COMPOSITE"
    # Gamepad background method
    gp_bg_method = str(data.get("gamepad_background_method", d0.gamepad_background_method)).lower()
    if gp_bg_method not in ("sendinput", "postmessage", "vigem", "pico"):
        gp_bg_method = d0.gamepad_background_method
    pico_map_raw = data.get("pico_button_map", {})
    pico_map = {}
    if isinstance(pico_map_raw, dict):
        for k, v in pico_map_raw.items():
            pico_map[str(k).lower()] = str(v).lower()

    return RuntimeState(
        target_hwnd=th,
        target_name=str(data.get("target_name", d0.target_name)),
        clicker_target_hwnd=load_target_hwnd("clicker_target_hwnd", d0.clicker_target_hwnd),
        clicker_target_name=load_target_name("clicker_target_name", d0.clicker_target_name),
        macro_target_hwnd=load_target_hwnd("macro_target_hwnd", d0.macro_target_hwnd),
        macro_target_name=load_target_name("macro_target_name", d0.macro_target_name),
        aim_target_hwnd=load_target_hwnd("aim_target_hwnd", d0.aim_target_hwnd),
        aim_target_name=load_target_name("aim_target_name", d0.aim_target_name),
        recorder_target_hwnd=load_target_hwnd("recorder_target_hwnd", d0.recorder_target_hwnd),
        recorder_target_name=load_target_name("recorder_target_name", d0.recorder_target_name),
        theme=t,
        ui_lang=(
            str(data.get("ui_lang", d0.ui_lang)).upper()
            if str(data.get("ui_lang", d0.ui_lang)).upper() in ("RU", "EN")
            else d0.ui_lang
        ),
        is_pinned=bool(data.get("is_pinned", d0.is_pinned)),
        hotkeys=_normalize_hotkeys(data.get("hotkeys")),
        terminal_palette=palette,
        background_method=bg_method,
        gamepad_enabled=gp_enabled,
        gamepad_controller_type=gp_type,
        gamepad_target_index=gp_index,
        gamepad_background_method=gp_bg_method,
        gamepad_button_map=gp_map,
        pico_enabled=pico_enabled,
        pico_port=pico_port or "",
        pico_baudrate=pico_baudrate,
        pico_mode=pico_mode,
        pico_button_map=pico_map,
    )


def save_profile(api: Any) -> None:
    """Save current profile to disk."""
    with _profile_lock:
        _ensure_dir()
        clicker = api.clicker.get_status() if hasattr(api, "clicker") else {}
        aim = api.aim.get_status() if hasattr(api, "aim") else {}
        macro = api.macro.get_status() if hasattr(api, "macro") else {}
        recorder = api.recorder.status() if hasattr(api, "recorder") else {}
        payload = {
            "version": 5,
            "state": _state_to_dict(api.state),
            "clicker": {
                "interval_ms": clicker.get("interval_ms", 100),
                "hold_ms": clicker.get("hold_ms", 0),
                "button": clicker.get("button", "L"),
                "limit": clicker.get("limit", 0),
                "background_method": clicker.get("background_method", "sendinput"),
            },
            "aim": {
                "confidence": aim.get("confidence", 0.6),
                "smooth_steps": aim.get("smooth_steps", 10),
                "reset_delay": aim.get("reset_delay", 0.2),
                "scan_region": aim.get(
                    "scan_region",
                    {"top": 100, "left": 100, "width": 300, "height": 300},
                ),
                "background_method": aim.get("background_method", "sendinput"),
            },
            "macro": {
                "run_mode": macro.get("run_mode", "SEQUENTIAL"),
                "actions": list(macro.get("actions", [])),
                "background_method": macro.get("background_method", "sendinput"),
            },
            "recorder": {
                "background_method": recorder.get("background_method", "sendinput"),
            },
            "gamepad": {
                "background_method": (
                    api.state.gamepad_background_method
                    if hasattr(api.state, "gamepad_background_method")
                    else "sendinput"
                ),
            },
        }
        PROFILE_PATH.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def load_profile(api: Any) -> bool:
    """Load profile from disk."""
    with _profile_lock:
        if not PROFILE_PATH.is_file():
            return False
        prev = getattr(api, "_suppress_save", False)
        api._suppress_save = True
        try:
            try:
                raw = json.loads(PROFILE_PATH.read_text(encoding="utf-8"))
            except Exception:
                logger.exception("Failed to parse profile.json")
                return False
            if not isinstance(raw, dict):
                return False
            if "state" in raw:
                # Update state IN PLACE — don't replace the object!
                # Controllers (ProfileController, WindowController, etc.) hold
                # references to the original RuntimeState object. If we replace
                # api.state with a new object, those controllers still point to
                # the OLD one, and changes are never saved.
                new_state = _state_from_dict(raw["state"])
                old_state = api.state
                # Copy all fields from new_state into old_state (in-place update)
                for field_name in vars(new_state):
                    setattr(old_state, field_name, getattr(new_state, field_name))
                # api.state already points to old_state, no reassignment needed
            c = raw.get("clicker") or {}
            if c and hasattr(api, "clicker"):
                api.clicker.update_config(
                    int(c.get("interval_ms", 100)),
                    int(c.get("hold_ms", 0)),
                    str(c.get("button", "L")),
                    int(c.get("limit", 0)),
                    str(c.get("background_method", "sendinput")),
                )
            a = raw.get("aim") or {}
            if a and hasattr(api, "aim"):
                api.aim.update_config(
                    float(a.get("confidence", 0.6)),
                    int(a.get("smooth_steps", 10)),
                    float(a.get("reset_delay", 0.2)),
                )
                sr = a.get("scan_region") or {}
                if sr:
                    api.aim.set_scan_region(
                        int(sr.get("top", 100)),
                        int(sr.get("left", 100)),
                        int(sr.get("width", 300)),
                        int(sr.get("height", 300)),
                    )
                api.aim.set_background_method(str(a.get("background_method", "sendinput")))
            m = raw.get("macro") or {}
            if m and hasattr(api, "macro"):
                api.macro.set_run_mode(str(m.get("run_mode", "SEQUENTIAL")))
                api.macro.set_background_method(str(m.get("background_method", "sendinput")))
                api.macro.clear_actions()
                for act in m.get("actions") or []:
                    api.macro.add_action(
                        act.get("key", "space"),
                        float(act.get("delay", 0.5)),
                        float(act.get("hold", 0.05)),
                    )
            r = raw.get("recorder") or {}
            if r and hasattr(api, "recorder"):
                api.recorder.set_background_method(str(r.get("background_method", "sendinput")))
            g = raw.get("gamepad") or {}
            if g and hasattr(api.state, "gamepad_background_method"):
                # state is already loaded from _state_from_dict, but we need to set it on the service
                pass  # handled via state
            return True
        finally:
            api._suppress_save = prev
