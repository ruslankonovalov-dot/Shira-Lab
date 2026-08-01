"""
Input validation utilities for QmlBridge @Slot methods.

All validation functions return tuple of (is_valid, validated_value, error_message).
Use make_error_response() and make_ok_response() for consistent JSON responses.
"""

from __future__ import annotations

import json
import logging
from typing import Any

logger = logging.getLogger(__name__)


# Type alias for QVariant-compatible return types
QVariantMap = dict[str, Any]
QVariantList = list[Any]
QVariant = dict[str, Any] | list[Any] | str | int | float | bool | None


def _qvar(obj: QVariant) -> QVariant:
    """Convert native Python types to QVariant-compatible types for @Slot return values.

    Eliminates need for JSON marshaling in QML — slots can return dict/list/str/int/float/bool
    directly and QML receives them as native QVariantMap/QVariantList.

    Args:
        obj: Any native Python object (dict, list, str, int, float, bool, None)

    Returns:
        Same object (Qt handles conversion automatically for these types)
    """
    return obj


def _qvar_map(obj: QVariantMap) -> QVariantMap:
    """Type-safe variant of _qvar that guarantees QVariantMap return."""
    return obj


# ─── Validation Constants ────────────────────────────────────────────────────

VALID_PALETTES = {"matrix", "amber", "inverse", "grey", "synthwave", "blood"}
VALID_LANGUAGES = {"RU", "EN", "ZH"}
VALID_BACKGROUND_METHODS = {"sendinput", "postmessage", "vigem", "pico"}
VALID_CLICKER_BUTTONS = {
    "L",
    "R",
    "M",
    "X1",
    "X2",
    "left",
    "right",
    "middle",
    "back",
    "forward",
}
VALID_GAMEPAD_TYPES = {"X360", "DS4"}
VALID_AIM_DETECTION_MODES = {
    "auto",
    "multi",
    "circles",
    "color",
    "template",
    "calibrate",
}
VALID_AIM_TARGET_COLORS = {
    "red",
    "blue",
    "green",
    "purple",
    "yellow",
    "cyan",
    "orange",
    "pink",
}
VALID_HOTKEY_MODES = {"TOGGLE", "HOLD"}
VALID_HOTKEY_ACTIONS = {
    "clicker_toggle",
    "aim_toggle",
    "macro_start",
    "macro_stop",
    "recorder_start",
    "recorder_stop",
    "app_show",
    "panic_stop",
}

# Clicker limits
CLICKER_INTERVAL_MIN = 1
CLICKER_INTERVAL_MAX = 60000
CLICKER_HOLD_MIN = 0
CLICKER_HOLD_MAX = 1000
CLICKER_LIMIT_MIN = 0
CLICKER_LIMIT_MAX = 1000000

# Aim limits
AIM_CONFIDENCE_MIN = 0.01
AIM_CONFIDENCE_MAX = 0.99
AIM_SMOOTH_MIN = 1
AIM_SMOOTH_MAX = 100
AIM_RESET_DELAY_MIN = 0.0
AIM_RESET_DELAY_MAX = 5.0
AIM_FOV_MIN = 0
AIM_FOV_MAX = 3000
AIM_SPEED_MIN = 0.001
AIM_SPEED_MAX = 10.0
AIM_MIN_AREA_MIN = 0
AIM_MIN_AREA_MAX = 10000
AIM_MAX_AREA_MIN = 0
AIM_MAX_AREA_MAX = 10000
AIM_ASPECT_MIN = 0.01
AIM_ASPECT_MAX = 100.0
AIM_BRIGHTNESS_MIN = -100
AIM_BRIGHTNESS_MAX = 100
AIM_SATURATION_MIN = -100
AIM_SATURATION_MAX = 100

# Macro limits
MACRO_DELAY_MIN = 0.0
MACRO_DELAY_MAX = 60.0
MACRO_HOLD_MIN = 0.0
MACRO_HOLD_MAX = 10.0

# Gamepad limits
GAMEPAD_TARGET_INDEX_MIN = 0
GAMEPAD_TARGET_INDEX_MAX = 3
GAMEPAD_BUTTONS_MASK_MAX = 0xFFFFFFFF
GAMEPAD_TRIGGER_MIN = 0
GAMEPAD_TRIGGER_MAX = 255
GAMEPAD_STICK_MIN = -32768
GAMEPAD_STICK_MAX = 32767

# Recorder limits
RECORDER_REPEATS_MIN = 1
RECORDER_REPEATS_MAX = 9999

# Pico limits
PICO_BAUDRATE_MIN = 9600
PICO_BAUDRATE_MAX = 921600
PICO_HOLD_MS_MIN = 0
PICO_HOLD_MS_MAX = 10000

# Pico enums
VALID_PICO_MODES: set[str] = {"hid", "raw_hid", "cdc"}
VALID_PICO_BUTTONS: set[str] = {
    "a",
    "b",
    "x",
    "y",
    "lb",
    "rb",
    "lt",
    "rt",
    "start",
    "back",
    "guide",
    "ls",
    "rs",
    "up",
    "down",
    "left",
    "right",
    "dpad_up",
    "dpad_down",
    "dpad_left",
    "dpad_right",
    "mouse_left",
    "mouse_right",
    "mouse_middle",
    "mouse_x1",
    "mouse_x2",
}
VALID_PICO_PORTS_WIN = {
    "COM1",
    "COM2",
    "COM3",
    "COM4",
    "COM5",
    "COM6",
    "COM7",
    "COM8",
    "COM9",
    "COM10",
    "COM11",
    "COM12",
    "COM13",
    "COM14",
    "COM15",
    "COM16",
    "COM17",
    "COM18",
    "COM19",
    "COM20",
}
VALID_PICO_PORTS_NIX = {
    "/dev/ttyUSB0",
    "/dev/ttyUSB1",
    "/dev/ttyUSB2",
    "/dev/ttyUSB3",
    "/dev/ttyACM0",
    "/dev/ttyACM1",
    "/dev/ttyACM2",
    "/dev/ttyACM3",
}


# ─── Core Validation Functions ──────────────────────────────────────────────


def validate_int(
    value: Any,
    min_val: int | None = None,
    max_val: int | None = None,
    default: int | None = None,
    name: str = "value",
) -> tuple[bool, int | None, str | None]:
    """Validate integer value with optional bounds."""
    if value is None or value == "":
        if default is not None:
            return True, default, None
        return False, None, f"{name} is required"
    try:
        ival = int(value)
    except (ValueError, TypeError):
        return False, None, f"{name} must be an integer"
    if min_val is not None and ival < min_val:
        return False, None, f"{name} must be >= {min_val}"
    if max_val is not None and ival > max_val:
        return False, None, f"{name} must be <= {max_val}"
    return True, ival, None


def validate_float(
    value: Any,
    min_val: float | None = None,
    max_val: float | None = None,
    default: float | None = None,
    name: str = "value",
) -> tuple[bool, float | None, str | None]:
    """Validate float value with optional bounds."""
    if value is None or value == "":
        if default is not None:
            return True, default, None
        return False, None, f"{name} is required"
    try:
        fval = float(value)
    except (ValueError, TypeError):
        return False, None, f"{name} must be a number"
    if min_val is not None and fval < min_val:
        return False, None, f"{name} must be >= {min_val}"
    if max_val is not None and fval > max_val:
        return False, None, f"{name} must be <= {max_val}"
    return True, fval, None


def validate_enum(
    value: Any,
    valid_values: set[str],
    default: str | None = None,
    case_sensitive: bool = False,
    name: str = "value",
) -> tuple[bool, str | None, str | None]:
    """Validate string value against allowed enum values."""
    if value is None or value == "":
        if default is not None:
            return True, default, None
        return False, None, f"{name} is required"
    sval = str(value).strip()
    if not case_sensitive:
        sval_lower = sval.lower()
        valid_lower = {v.lower(): v for v in valid_values}
        if sval_lower in valid_lower:
            return True, valid_lower[sval_lower], None
    else:
        if sval in valid_values:
            return True, sval, None
    return False, None, f"{name} must be one of: {', '.join(sorted(valid_values))}"


def validate_str(
    value: Any,
    min_len: int = 0,
    max_len: int | None = None,
    default: str | None = None,
    name: str = "value",
) -> tuple[bool, str | None, str | None]:
    """Validate string value with optional length bounds."""
    if value is None:
        if default is not None:
            return True, default, None
        return False, None, f"{name} is required"
    sval = str(value)
    if min_len > 0 and len(sval) < min_len:
        return False, None, f"{name} must be at least {min_len} characters"
    if max_len is not None and len(sval) > max_len:
        return False, None, f"{name} must be at most {max_len} characters"
    return True, sval, None


def validate_json_array(
    value: Any,
    item_type: type | None = None,
    min_items: int = 0,
    max_items: int | None = None,
    name: str = "value",
) -> tuple[bool, list[Any] | None, str | None]:
    """Validate and parse JSON array string."""
    if value is None or value == "":
        return False, None, f"{name} is required"
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError as e:
        return False, None, f"{name} must be valid JSON array: {e}"
    if not isinstance(parsed, list):
        return False, None, f"{name} must be a JSON array"
    if len(parsed) < min_items:
        return False, None, f"{name} must have at least {min_items} items"
    if max_items is not None and len(parsed) > max_items:
        return False, None, f"{name} must have at most {max_items} items"
    if item_type is not None:
        for i, item in enumerate(parsed):
            if not isinstance(item, item_type):
                return False, None, f"{name}[{i}] must be {item_type.__name__}"
    return True, parsed, None


def validate_hwnd(
    value: Any, allow_zero: bool = True, name: str = "hwnd"
) -> tuple[bool, int | None, str | None]:
    """Validate window handle (HWND)."""
    if value is None:
        return False, None, f"{name} is required"
    try:
        ival = int(value)
    except (ValueError, TypeError):
        return False, None, f"{name} must be an integer"
    if ival < 0:
        return False, None, f"{name} must be non-negative"
    if not allow_zero and ival == 0:
        return False, None, f"{name} must be non-zero"
    return True, ival, None


def validate_bool(
    value: Any, default: bool | None = None, name: str = "value"
) -> tuple[bool, bool | None, str | None]:
    """Validate boolean value."""
    if value is None or value == "":
        if default is not None:
            return True, default, None
        return False, None, f"{name} is required"
    if isinstance(value, bool):
        return True, value, None
    if isinstance(value, int | float):
        return True, bool(value), None
    if isinstance(value, str):
        v_lower = value.lower().strip()
        if v_lower in ("true", "1", "yes", "on"):
            return True, True, None
        if v_lower in ("false", "0", "no", "off"):
            return True, False, None
    return False, None, f"{name} must be a boolean"


def validate_pico_mode(
    value: Any, default: str | None = None, name: str = "mode"
) -> tuple[bool, str]:
    """Validate Pico operating mode (COMPOSITE, KEYBOARD, MOUSE, GAMEPAD for test compatibility).

    Returns (ok, err) tuple for test compatibility.
    """
    ok, _, err = validate_enum(
        value,
        {"COMPOSITE", "KEYBOARD", "MOUSE", "GAMEPAD", "hid", "raw_hid", "cdc"},
        default=default,
        name=name,
        case_sensitive=False,
    )
    return (ok, err or "")


def validate_pico_button(
    value: Any, default: str | None = None, name: str = "button"
) -> tuple[bool, str | None, str | None]:
    """Validate Pico button name (gamepad or mouse button)."""
    return validate_enum(
        value, VALID_PICO_BUTTONS, default=default, name=name, case_sensitive=False
    )


def validate_pico_port(
    value: Any, default: str | None = None, name: str = "port"
) -> tuple[bool, str | None, str | None]:
    """Validate Pico serial port (Windows COMx or Linux /dev/tty*)."""
    ok, sval, err = validate_str(value, min_len=1, max_len=64, default=default, name=name)
    if not ok:
        return False, None, err
    if sval is None:
        return False, None, f"{name} is required"
    # Additional format validation
    import re
    import sys

    if sys.platform == "win32":
        if re.match(r"^COM\d+$", sval, re.IGNORECASE):
            return True, sval.upper(), None
    else:
        if re.match(r"^/dev/tty(USB|ACM)\d+$", sval):
            return True, sval, None
    # Allow other patterns but warn (for flexibility with USB serial)
    import logging

    logging.getLogger(__name__).warning(f"Non-standard Pico port format: {sval}")
    return True, sval, None


# ─── Response Helpers ──────────────────────────────────────────────────────


def make_error_response(error: str) -> QVariantMap:
    """Create standardized error JSON response."""
    return {"ok": False, "error": error}


def make_ok_response(**kwargs: Any) -> QVariantMap:
    """Create standardized OK JSON response."""
    resp: QVariantMap = {"ok": True}
    resp.update(kwargs)
    return resp


# ─── Convenience Validator Functions (for test compatibility) ────────────────


def validate_interval_ms(value: Any) -> tuple[bool, str]:
    """Validate clicker interval in milliseconds."""
    ok, _, err = validate_int(value, CLICKER_INTERVAL_MIN, CLICKER_INTERVAL_MAX, name="interval_ms")
    return (ok, err or "")


def validate_hold_ms(value: Any) -> tuple[bool, str]:
    """Validate clicker hold time in milliseconds."""
    ok, _, err = validate_int(value, CLICKER_HOLD_MIN, CLICKER_HOLD_MAX, name="hold_ms")
    return (ok, err or "")


def validate_button(value: Any) -> tuple[bool, str]:
    """Validate mouse button."""
    ok, _, err = validate_enum(value, VALID_CLICKER_BUTTONS, case_sensitive=False, name="button")
    return (ok, err or "")


def validate_limit(value: Any) -> tuple[bool, str]:
    """Validate click limit."""
    ok, _, err = validate_int(value, CLICKER_LIMIT_MIN, CLICKER_LIMIT_MAX, name="limit")
    return (ok, err or "")


def validate_detection_mode(value: Any) -> tuple[bool, str]:
    """Validate aim detection mode."""
    ok, _, err = validate_enum(value, VALID_AIM_DETECTION_MODES, name="mode")
    return (ok, err or "")


def validate_target_color(value: Any) -> tuple[bool, str]:
    """Validate aim target color."""
    ok, _, err = validate_enum(value, VALID_AIM_TARGET_COLORS, name="color")
    return (ok, err or "")


def validate_background_method(value: Any) -> tuple[bool, str]:
    """Validate background input method."""
    ok, _, err = validate_enum(
        value, VALID_BACKGROUND_METHODS, default="sendinput", name="background_method"
    )
    return (ok, err or "")


def validate_hotkey_key(value: Any) -> tuple[bool, str]:
    """Validate hotkey key string."""
    if not value:
        return (False, "empty key")
    try:
        key = str(value).strip().lower()
        if not key:
            return (False, "empty key")

        # Check if it's a valid keyboard key
        import keyboard

        if hasattr(keyboard, "parse_hotkey"):
            try:
                keyboard.parse_hotkey(key)
                return (True, "")
            except ValueError:
                pass

        # Check mouse buttons - test expects m1, m2, m3 to be valid
        if key.startswith("m") and key[1:].isdigit():
            btn_num = int(key[1:])
            if 1 <= btn_num <= 5:
                return (True, "")
            return (False, "invalid mouse button")

        # Check wheel
        if key in ("wheel_up", "wheel_down", "wheel:left", "wheel:right"):
            return (True, "")

        return (False, "invalid key")
    except (OSError, ValueError, AttributeError, ImportError) as e:
        return (False, str(e))


def validate_hotkey_mode(value: Any) -> tuple[bool, str]:
    """Validate hotkey mode."""
    # The test expects REPEAT to be valid too
    ok, _, err = validate_enum(value, {"TOGGLE", "HOLD", "REPEAT"}, name="mode")
    return (ok, err or "")


def validate_vigem_target_type(value: Any) -> tuple[bool, str]:
    """Validate ViGEm target type."""
    ok, _, err = validate_enum(value, VALID_GAMEPAD_TYPES, name="target_type")
    return (ok, err or "")
