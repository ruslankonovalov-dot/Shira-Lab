"""
GamepadController - handles ViGEm virtual gamepad, Pico HID, physical gamepad detection.
Extracted from QmlBridge god-object (Phase 2.1).
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from PySide6.QtCore import QObject, Signal, Slot

from app.backend.services.input_validation import (GAMEPAD_BUTTONS_MASK_MAX,
                                                   GAMEPAD_STICK_MAX,
                                                   GAMEPAD_STICK_MIN,
                                                   GAMEPAD_TARGET_INDEX_MAX,
                                                   GAMEPAD_TARGET_INDEX_MIN,
                                                   GAMEPAD_TRIGGER_MAX,
                                                   GAMEPAD_TRIGGER_MIN,
                                                   PICO_HOLD_MS_MAX,
                                                   PICO_HOLD_MS_MIN,
                                                   VALID_BACKGROUND_METHODS,
                                                   VALID_GAMEPAD_TYPES,
                                                   VALID_PICO_BUTTONS,
                                                   VALID_PICO_MODES,
                                                   QVariantMap)
from app.backend.services.pico_service import (PicoDevice, PicoService,
                                               get_pico_service)
from app.backend.services.vigem_service import VigemService, get_vigem_service
from window_utils import get_visible_windows

if TYPE_CHECKING:
    from app.backend.services.pico_service import PicoService
    from app.backend.services.vigem_service import VigemService

# PicoService is used at runtime for list_picos() static method
from app.backend.services.pico_service import PicoService as PicoServiceRuntime

# Type aliases
BackgroundMethod = str  # "sendinput", "postmessage", "vigem", "pico"
GamepadType = str  # "X360", "DS4"
PicoModeStr = str  # "COMPOSITE", "KEYBOARD", "MOUSE", "GAMEPAD", "hid", "raw_hid", "cdc"
GamepadStatus = dict[str, Any]
WindowInfo = dict[str, Any]

# QVariant-compatible return type - QmlBridge expects dict for @Slot(result="QVariantMap")
QVariant = QVariantMap

logger = logging.getLogger(__name__)


class GamepadController(QObject):
    """
    Gamepad management controller.

    Responsibilities:
    - ViGEm service (virtual X360/DS4 controllers)
    - Pico service (physical Raspberry Pi Pico HID device)
    - Physical gamepad detection (XInput)
    - Button mapping configuration
    - Background input methods (SendInput, PostMessage, ViGEm, Pico)
    """

    # Signals
    vigemStatusChanged = Signal()
    picoStatusChanged = Signal()
    physicalGamepadsChanged = Signal()
    logMessage = Signal(str, str, str)  # level, source, message

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._vigem: VigemService = get_vigem_service()
        self._pico: PicoService = get_pico_service()

        # Set bridge reference for logging
        self._vigem.set_bridge(self)
        self._pico.set_bridge(self)

        # Background input methods
        self._clicker_bg_method: BackgroundMethod = "sendinput"
        self._macro_bg_method: BackgroundMethod = "sendinput"
        self._recorder_bg_method: BackgroundMethod = "sendinput"
        self._gamepad_bg_method: BackgroundMethod = "sendinput"

        # Valid button names for ViGEm (from XUSB_BUTTON_MAP)
        self.VALID_VIGEM_BUTTONS: set[str] = {
            "a",
            "b",
            "x",
            "y",
            "lb",
            "rb",
            "back",
            "start",
            "ls",
            "rs",
            "guide",
            "up",
            "down",
            "left",
            "right",
        }

    # ─── ViGEm Service ──────────────────────────────────────────────────────

    @Slot(str, result="QVariantMap")
    def setGamepadControllerType(self, controller_type: str) -> QVariantMap:
        """Set controller type (X360 or DS4)."""
        from app.backend.services.input_validation import (make_error_response,
                                                           validate_enum)

        ok, val, err = validate_enum(controller_type, VALID_GAMEPAD_TYPES, name="controller_type")
        if not ok:
            logger.warning(f"setGamepadControllerType: {err}")
            return make_error_response(err or "Invalid controller type")

        try:
            # VigemService doesn't have set_controller_type directly.
            # Controller type is set when adding targets (add_x360 / add_ds4).
            # This method is kept for QML API compatibility.
            result = {"ok": True, "controller_type": val}
            self.vigemStatusChanged.emit()
            return result
        except Exception as e:
            logger.exception("setGamepadControllerType failed")
            return make_error_response(str(e))

    @Slot(str, result="QVariantMap")
    def setGamepadTargetIndex(self, index_str: str) -> QVariantMap:
        """Set target virtual gamepad index (0-3)."""
        from app.backend.services.input_validation import (make_error_response,
                                                           validate_int)

        try:
            index = int(index_str)
        except (TypeError, ValueError):
            return make_error_response("target_index must be integer")

        ok, val, err = validate_int(
            index,
            GAMEPAD_TARGET_INDEX_MIN,
            GAMEPAD_TARGET_INDEX_MAX,
            name="target_index",
        )
        if not ok:
            return make_error_response(err or "Invalid target index")

        try:
            # VigemService doesn't have set_target_index - targets managed via add_x360/add_ds4
            result = {"ok": True, "target_index": val}
            self.vigemStatusChanged.emit()
            return result
        except Exception as e:
            logger.exception("setGamepadTargetIndex failed")
            return make_error_response(str(e))

    @Slot(str, int, result="QVariantMap")
    def setGamepadBackgroundMethod(self, method: str, _target_index: int = 0) -> QVariantMap:
        """Set background input method for virtual gamepad."""
        from app.backend.services.input_validation import (make_error_response,
                                                           validate_enum)

        ok, val, err = validate_enum(method, VALID_BACKGROUND_METHODS, name="background_method")
        if not ok or val is None:
            logger.warning(f"setGamepadBackgroundMethod: {err}")
            return make_error_response(err or "Invalid background method")

        try:
            self._gamepad_bg_method = val
            # VigemService doesn't have set_background_method; stored for reference
            result = {"ok": True, "method": val}
            self.vigemStatusChanged.emit()
            return result
        except Exception as e:
            logger.exception("setGamepadBackgroundMethod failed")
            return make_error_response(str(e))

    @Slot(result="QVariantMap")
    def getVigemStatus(self) -> QVariantMap:
        """Get ViGEm service status."""
        try:
            return self._vigem.get_status()
        except Exception as e:
            logger.exception("getVigemStatus failed")
            return {"ok": False, "error": str(e)}

    @Slot(result="QVariantMap")
    def detectPhysicalGamepads(self) -> QVariantMap:
        """Detect physical XInput gamepads."""
        try:
            return self._detect_physical_gamepads()
        except Exception as e:
            logger.exception("detectPhysicalGamepads failed")
            return {"ok": False, "error": str(e), "gamepads": []}

    def _detect_physical_gamepads(self) -> QVariantMap:
        """Internal physical gamepad detection (XInput)."""
        import ctypes
        from ctypes import wintypes

        class XINPUT_GAMEPAD(ctypes.Structure):
            _fields_ = [
                ("wButtons", wintypes.WORD),
                ("bLeftTrigger", wintypes.BYTE),
                ("bRightTrigger", wintypes.BYTE),
                ("sThumbLX", wintypes.SHORT),
                ("sThumbLY", wintypes.SHORT),
                ("sThumbRX", wintypes.SHORT),
                ("sThumbRY", wintypes.SHORT),
            ]

        class XINPUT_STATE(ctypes.Structure):
            _fields_ = [
                ("dwPacketNumber", wintypes.DWORD),
                ("Gamepad", XINPUT_GAMEPAD),
            ]

        class XINPUT_BATTERY_INFORMATION(ctypes.Structure):
            _fields_ = [
                ("BatteryType", wintypes.BYTE),
                ("BatteryLevel", wintypes.BYTE),
            ]

        class XINPUT_CAPABILITIES(ctypes.Structure):
            _fields_ = [
                ("Type", wintypes.BYTE),
                ("SubType", wintypes.BYTE),
                ("Flags", wintypes.WORD),
                ("Gamepad", XINPUT_GAMEPAD),
                ("Vibration", XINPUT_GAMEPAD),
            ]

        xinput = None
        for dll_name in ("xinput1_4.dll", "xinput1_3.dll", "xinput9_1_0.dll"):
            try:
                xinput = ctypes.windll.LoadLibrary(dll_name)
                break
            except OSError:
                continue

        if not xinput:
            return {"ok": False, "error": "XInput DLL not found", "gamepads": []}

        xinput.XInputGetState.argtypes = [wintypes.DWORD, ctypes.POINTER(XINPUT_STATE)]
        xinput.XInputGetState.restype = wintypes.DWORD

        xinput.XInputGetCapabilities.argtypes = [
            wintypes.DWORD,
            wintypes.DWORD,
            ctypes.POINTER(XINPUT_CAPABILITIES),
        ]
        xinput.XInputGetCapabilities.restype = wintypes.DWORD

        xinput.XInputGetBatteryInformation.argtypes = [
            wintypes.DWORD,
            wintypes.BYTE,
            ctypes.POINTER(XINPUT_BATTERY_INFORMATION),
        ]
        xinput.XInputGetBatteryInformation.restype = wintypes.DWORD

        ERROR_SUCCESS = 0
        ERROR_DEVICE_NOT_CONNECTED = 1167

        BATTERY_DEVTYPE_GAMEPAD = 0x00
        BATTERY_TYPE_DISCONNECTED = 0x00
        BATTERY_TYPE_WIRED = 0x01
        BATTERY_TYPE_ALKALINE = 0x02
        BATTERY_TYPE_NIMH = 0x03
        BATTERY_TYPE_UNKNOWN = 0xFF

        battery_type_names = {
            BATTERY_TYPE_DISCONNECTED: "Disconnected",
            BATTERY_TYPE_WIRED: "Wired",
            BATTERY_TYPE_ALKALINE: "Alkaline",
            BATTERY_TYPE_NIMH: "NiMH",
            BATTERY_TYPE_UNKNOWN: "Unknown",
        }

        gamepads: list[dict[str, Any]] = []

        for user_index in range(4):  # XInput supports up to 4 controllers
            state = XINPUT_STATE()
            result = xinput.XInputGetState(user_index, ctypes.byref(state))

            if result != ERROR_SUCCESS:
                if result == ERROR_DEVICE_NOT_CONNECTED:
                    continue
                continue

            # Controller is connected, get capabilities
            caps = XINPUT_CAPABILITIES()
            xinput.XInputGetCapabilities(user_index, 0, ctypes.byref(caps))

            # Get battery info
            battery = XINPUT_BATTERY_INFORMATION()
            xinput.XInputGetBatteryInformation(
                user_index, BATTERY_DEVTYPE_GAMEPAD, ctypes.byref(battery)
            )

            sub_type = caps.SubType
            if sub_type == 1:
                ctrl_type = "XInput Gamepad"
            elif sub_type == 2:
                ctrl_type = "Arcade Stick"
            elif sub_type == 3:
                ctrl_type = "Flight Stick"
            elif sub_type == 4:
                ctrl_type = "Dance Pad"
            elif sub_type == 5:
                ctrl_type = "Guitar"
            elif sub_type == 6:
                ctrl_type = "Drum Kit"
            elif sub_type == 7:
                ctrl_type = "Arcade Pad"
            else:
                ctrl_type = "Unknown"

            battery_level = battery.BatteryLevel
            battery_type = battery_type_names.get(battery.BatteryType, "Unknown")

            gp = state.Gamepad
            gamepads.append(
                {
                    "user_index": user_index,
                    "connected": True,
                    "controller_type": ctrl_type,
                    "sub_type": sub_type,
                    "packet_number": state.dwPacketNumber,
                    "buttons": gp.wButtons,
                    "left_trigger": gp.bLeftTrigger,
                    "right_trigger": gp.bRightTrigger,
                    "thumb_lx": gp.sThumbLX,
                    "thumb_ly": gp.sThumbLY,
                    "thumb_rx": gp.sThumbRX,
                    "thumb_ry": gp.sThumbRY,
                    "battery_type": battery_type,
                    "battery_level": battery_level if battery_type != "Wired" else 100,
                    "is_wired": battery.BatteryType == BATTERY_TYPE_WIRED,
                    "vibration_supported": (caps.Flags & 0x01) != 0,
                }
            )

        self.physicalGamepadsChanged.emit()
        return {"ok": True, "gamepads": gamepads}

    # ─── ViGEm Button Mapping ───────────────────────────────────────────────

    @Slot(result="QVariantMap")
    def getVigemButtonMap(self) -> QVariantMap:
        """Get current ViGEm button mapping."""
        try:
            return {"ok": True, "map": self._vigem.get_button_map()}
        except Exception as e:
            logger.exception("getVigemButtonMap failed")
            return {"ok": False, "error": str(e), "map": {}}

    @Slot("QVariantMap", result="QVariantMap")
    def setVigemButtonMap(self, mapping: dict[str, Any]) -> QVariantMap:
        """Set ViGEm button mapping."""
        from app.backend.services.input_validation import make_error_response

        try:
            result = self._vigem.set_button_map(mapping)
            self.vigemStatusChanged.emit()
            return result
        except Exception as e:
            logger.exception("setVigemButtonMap failed")
            return make_error_response(str(e))

    @Slot("QVariantMap", result="QVariantMap")
    def sendVigemTestState(self, state_map: dict[str, Any]) -> QVariantMap:
        """Send test state to virtual gamepad (for GamepadPage test controls).

        Expected state_map keys: buttons, lt, rt, lx, ly, rx, ry, target_id
        All values validated against gamepad limits.
        """
        from app.backend.services.input_validation import (make_error_response,
                                                           make_ok_response,
                                                           validate_int)

        # Validate target_id (0-3)
        ok, target_id_val, err = validate_int(
            state_map.get("target_id", 0) if state_map else 0,
            GAMEPAD_TARGET_INDEX_MIN,
            GAMEPAD_TARGET_INDEX_MAX,
            default=0,
            name="target_id",
        )
        if not ok or target_id_val is None:
            logger.warning(f"sendVigemTestState: {err}")
            return make_error_response(err or "Invalid target_id")

        # Validate buttons (0..0xFFFFFFFF)
        ok, buttons_val, err = validate_int(
            state_map.get("buttons", 0) if state_map else 0,
            0,
            GAMEPAD_BUTTONS_MASK_MAX,
            default=0,
            name="buttons",
        )
        if not ok or buttons_val is None:
            logger.warning(f"sendVigemTestState: {err}")
            return make_error_response(err or "Invalid buttons")

        # Validate triggers (0..255)
        ok, lt_val, err = validate_int(
            state_map.get("lt", 0) if state_map else 0,
            GAMEPAD_TRIGGER_MIN,
            GAMEPAD_TRIGGER_MAX,
            default=0,
            name="lt",
        )
        if not ok or lt_val is None:
            logger.warning(f"sendVigemTestState: {err}")
            return make_error_response(err or "Invalid lt")
        ok, rt_val, err = validate_int(
            state_map.get("rt", 0) if state_map else 0,
            GAMEPAD_TRIGGER_MIN,
            GAMEPAD_TRIGGER_MAX,
            default=0,
            name="rt",
        )
        if not ok or rt_val is None:
            logger.warning(f"sendVigemTestState: {err}")
            return make_error_response(err or "Invalid rt")

        # Validate sticks (-32768..32767)
        ok, lx_val, err = validate_int(
            state_map.get("lx", 0) if state_map else 0,
            GAMEPAD_STICK_MIN,
            GAMEPAD_STICK_MAX,
            default=0,
            name="lx",
        )
        if not ok or lx_val is None:
            logger.warning(f"sendVigemTestState: {err}")
            return make_error_response(err or "Invalid lx")
        ok, ly_val, err = validate_int(
            state_map.get("ly", 0) if state_map else 0,
            GAMEPAD_STICK_MIN,
            GAMEPAD_STICK_MAX,
            default=0,
            name="ly",
        )
        if not ok or ly_val is None:
            logger.warning(f"sendVigemTestState: {err}")
            return make_error_response(err or "Invalid ly")
        ok, rx_val, err = validate_int(
            state_map.get("rx", 0) if state_map else 0,
            GAMEPAD_STICK_MIN,
            GAMEPAD_STICK_MAX,
            default=0,
            name="rx",
        )
        if not ok or rx_val is None:
            logger.warning(f"sendVigemTestState: {err}")
            return make_error_response(err or "Invalid rx")
        ok, ry_val, err = validate_int(
            state_map.get("ry", 0) if state_map else 0,
            GAMEPAD_STICK_MIN,
            GAMEPAD_STICK_MAX,
            default=0,
            name="ry",
        )
        if not ok or ry_val is None:
            logger.warning(f"sendVigemTestState: {err}")
            return make_error_response(err or "Invalid ry")

        try:
            result = self._vigem.x360_set_state(
                target_id=target_id_val,
                buttons=buttons_val,
                lt=lt_val,
                rt=rt_val,
                lx=lx_val,
                ly=ly_val,
                rx=rx_val,
                ry=ry_val,
            )
            return make_ok_response(result=result)
        except Exception as e:
            logger.exception("sendVigemTestState failed")
            return make_error_response(str(e))

    # ─── ViGEm Button Press/Release ─────────────────────────────────────────

    @Slot(int, str, result="QVariantMap")
    def vIGEmPressButton(self, target_id: int, button_name: str) -> QVariantMap:
        """Press a button on virtual gamepad."""
        from app.backend.services.input_validation import (make_error_response,
                                                           make_ok_response,
                                                           validate_enum,
                                                           validate_int)

        ok, target_id_val, err = validate_int(
            target_id,
            GAMEPAD_TARGET_INDEX_MIN,
            GAMEPAD_TARGET_INDEX_MAX,
            name="target_id",
        )
        if not ok or target_id_val is None:
            logger.warning(f"vIGEmPressButton: {err}")
            return make_error_response(err or "Invalid target_id")

        ok, button_val, err = validate_enum(
            button_name,
            self.VALID_VIGEM_BUTTONS,
            case_sensitive=False,
            name="button_name",
        )
        if not ok or button_val is None:
            logger.warning(f"vIGEmPressButton: {err}")
            return make_error_response(err or "Invalid button_name")

        try:
            result = self._vigem.x360_press_button(target_id_val, button_val)
            return make_ok_response(result=result)
        except Exception as e:
            logger.exception("vIGEmPressButton failed")
            return make_error_response(str(e))

    @Slot(int, str, result="QVariantMap")
    def vIGEmReleaseButton(self, target_id: int, button_name: str) -> QVariantMap:
        """Release a button on virtual gamepad."""
        from app.backend.services.input_validation import (make_error_response,
                                                           make_ok_response,
                                                           validate_enum,
                                                           validate_int)

        ok, target_id_val, err = validate_int(
            target_id,
            GAMEPAD_TARGET_INDEX_MIN,
            GAMEPAD_TARGET_INDEX_MAX,
            name="target_id",
        )
        if not ok or target_id_val is None:
            logger.warning(f"vIGEmReleaseButton: {err}")
            return make_error_response(err or "Invalid target_id")

        ok, button_val, err = validate_enum(
            button_name,
            self.VALID_VIGEM_BUTTONS,
            case_sensitive=False,
            name="button_name",
        )
        if not ok or button_val is None:
            logger.warning(f"vIGEmReleaseButton: {err}")
            return make_error_response(err or "Invalid button_name")

        try:
            result = self._vigem.x360_release_button(target_id_val, button_val)
            return make_ok_response(result=result)
        except Exception as e:
            logger.exception("vIGEmReleaseButton failed")
            return make_error_response(str(e))

    # ─── Pico Service ────────────────────────────────────────────────────

    @Slot(result="QVariantMap")
    def listPicoDevices(self) -> QVariantMap:
        """List available Pico devices."""
        try:
            devices: list[PicoDevice] = PicoServiceRuntime.list_picos()
            return {
                "ok": True,
                "devices": [
                    {
                        "port": d.port,
                        "vid": d.vid,
                        "pid": d.pid,
                        "serial": d.serial_number,
                        "desc": d.description,
                    }
                    for d in devices
                ],
            }
        except Exception as e:
            logger.exception("listPicoDevices failed")
            return {"ok": False, "error": str(e), "devices": []}

    @Slot(str, result="QVariantMap")
    def startPico(self, port: str = "") -> QVariantMap:
        """Connect to Pico device."""
        from app.backend.services.input_validation import (make_error_response,
                                                           make_ok_response)

        try:
            result = self._pico.connect(port if port else None)
            self.picoStatusChanged.emit()
            return make_ok_response(ok=bool(result))
        except Exception as e:
            logger.exception("startPico failed")
            return make_error_response(str(e))

    @Slot(result="QVariantMap")
    def stopPico(self) -> QVariantMap:
        """Disconnect from Pico device."""
        from app.backend.services.input_validation import (make_error_response,
                                                           make_ok_response)

        try:
            self._pico.disconnect()
            self.picoStatusChanged.emit()
            return make_ok_response()
        except Exception as e:
            logger.exception("stopPico failed")
            return make_error_response(str(e))

    @Slot(result="QVariantMap")
    def getPicoStatus(self) -> QVariantMap:
        """Get Pico connection status."""
        try:
            info = self._pico.device_info
            current_mode = self._pico.current_mode
            return {
                "ok": True,
                "connected": self._pico.is_connected,
                "mode": current_mode.name if current_mode else "UNKNOWN",
                "fw_version": info.fw_version if info else "unknown",
                "capabilities": info.capabilities if info else 0,
                "port": self._pico._port,
            }
        except Exception as e:
            logger.exception("getPicoStatus failed")
            return {"ok": False, "error": str(e)}

    @Slot(str, result="QVariantMap")
    def setPicoMode(self, mode: str) -> QVariantMap:
        """Set Pico USB mode (COMPOSITE, KEYBOARD, MOUSE, GAMEPAD)."""
        from app.backend.services.input_validation import (make_error_response,
                                                           make_ok_response,
                                                           validate_enum)
        from app.backend.services.pico_service import \
            PicoMode as PicoServiceMode

        ok, val, err = validate_enum(mode, VALID_PICO_MODES, name="mode")
        if not ok or val is None:
            return make_error_response(err or "Invalid mode")

        try:
            # Map string to PicoMode enum (VALID_PICO_MODES uses lowercase)
            mode_enum = PicoServiceMode[val.upper()]
            result = self._pico.set_mode(mode_enum)
            self.picoStatusChanged.emit()
            return make_ok_response(ok=bool(result))
        except Exception as e:
            logger.exception("setPicoMode failed")
            return make_error_response(str(e))

    @Slot(str, str, result="QVariantMap")
    def setPicoButtonMap(self, key: str, button: str) -> QVariantMap:
        """Set Pico button mapping for a key (not implemented in firmware yet)."""
        from app.backend.services.input_validation import (make_error_response,
                                                           make_ok_response,
                                                           validate_enum,
                                                           validate_str)

        ok, key_val, err = validate_str(key, min_len=1, max_len=50, name="key")
        if not ok or key_val is None:
            return make_error_response(err or "Invalid key")

        ok, val, err = validate_enum(button, VALID_PICO_BUTTONS, name="button")
        if not ok or val is None:
            return make_error_response(err or "Invalid button")

        # Button mapping not yet implemented in firmware/service
        self.picoStatusChanged.emit()
        return make_ok_response(ok=False, error="Button mapping not yet implemented in firmware")

    @Slot(result="QVariantMap")
    def picoReset(self) -> QVariantMap:
        """Reset Pico to neutral state."""
        from app.backend.services.input_validation import (make_error_response,
                                                           make_ok_response)

        try:
            result = self._pico.reset()
            return make_ok_response(ok=bool(result))
        except Exception as e:
            logger.exception("picoReset failed")
            return make_error_response(str(e))

    @Slot(str, str, int, result="QVariantMap")
    def picoSendKey(self, key: str, action: str, hold_ms: int = 50) -> QVariantMap:
        """Send keyboard action via Pico (press, release, tap)."""
        from app.backend.services.input_validation import (make_error_response,
                                                           make_ok_response,
                                                           validate_enum,
                                                           validate_int,
                                                           validate_str)

        ok, key_val, err = validate_str(key, min_len=1, max_len=50, name="key")
        if not ok or key_val is None:
            return make_error_response(err or "Invalid key")

        ok, action_val, err = validate_enum(action, {"press", "release", "tap"}, name="action")
        if not ok or action_val is None:
            return make_error_response(err or "Invalid action")

        ok, hold_val, err = validate_int(
            hold_ms, PICO_HOLD_MS_MIN, PICO_HOLD_MS_MAX, default=50, name="hold_ms"
        )
        if not ok or hold_val is None:
            return make_error_response(err or "Invalid hold_ms")

        try:
            if action_val == "press":
                result = self._pico.kb_press(key_val)
            elif action_val == "release":
                result = self._pico.kb_release(key_val)
            else:  # tap
                result = self._pico.kb_tap(key_val, hold_val)
            return make_ok_response(ok=bool(result))
        except Exception as e:
            logger.exception("picoSendKey failed")
            return make_error_response(str(e))

    @Slot(int, int, int, int, result="QVariantMap")
    def picoSendMouse(self, x: int, y: int, button: int = 0, hold_ms: int = 0) -> QVariantMap:
        """Send mouse action via Pico (click or move+click)."""
        from app.backend.services.input_validation import (make_error_response,
                                                           make_ok_response,
                                                           validate_int)

        ok, x_val, err = validate_int(x, -32768, 32767, name="x")
        if not ok or x_val is None:
            return make_error_response(err or "Invalid x")
        ok, y_val, err = validate_int(y, -32768, 32767, name="y")
        if not ok or y_val is None:
            return make_error_response(err or "Invalid y")
        ok, btn_val, err = validate_int(button, 0, 31, name="button")
        if not ok or btn_val is None:
            return make_error_response(err or "Invalid button")
        ok, hold_val, err = validate_int(
            hold_ms, PICO_HOLD_MS_MIN, PICO_HOLD_MS_MAX, default=0, name="hold_ms"
        )
        if not ok or hold_val is None:
            return make_error_response(err or "Invalid hold_ms")

        try:
            if x_val != 0 or y_val != 0:
                self._pico.ms_move(x_val, y_val, absolute=False)
            if btn_val != 0:
                self._pico.ms_click(btn_val, hold_val)
            return make_ok_response()
        except Exception as e:
            logger.exception("picoSendMouse failed")
            return make_error_response(str(e))

    @Slot(int, int, int, int, int, int, int, result="QVariantMap")
    def picoSendGamepad(
        self, buttons: int, lt: int, rt: int, lx: int, ly: int, rx: int, ry: int
    ) -> QVariantMap:
        """Send gamepad state via Pico."""
        from app.backend.services.input_validation import (make_error_response,
                                                           make_ok_response,
                                                           validate_int)

        ok, buttons_val, err = validate_int(buttons, 0, GAMEPAD_BUTTONS_MASK_MAX, name="buttons")
        if not ok or buttons_val is None:
            return make_error_response(err or "Invalid buttons")
        ok, lt_val, err = validate_int(lt, GAMEPAD_TRIGGER_MIN, GAMEPAD_TRIGGER_MAX, name="lt")
        if not ok or lt_val is None:
            return make_error_response(err or "Invalid lt")
        ok, rt_val, err = validate_int(rt, GAMEPAD_TRIGGER_MIN, GAMEPAD_TRIGGER_MAX, name="rt")
        if not ok or rt_val is None:
            return make_error_response(err or "Invalid rt")
        ok, lx_val, err = validate_int(lx, GAMEPAD_STICK_MIN, GAMEPAD_STICK_MAX, name="lx")
        if not ok or lx_val is None:
            return make_error_response(err or "Invalid lx")
        ok, ly_val, err = validate_int(ly, GAMEPAD_STICK_MIN, GAMEPAD_STICK_MAX, name="ly")
        if not ok or ly_val is None:
            return make_error_response(err or "Invalid ly")
        ok, rx_val, err = validate_int(rx, GAMEPAD_STICK_MIN, GAMEPAD_STICK_MAX, name="rx")
        if not ok or rx_val is None:
            return make_error_response(err or "Invalid rx")
        ok, ry_val, err = validate_int(ry, GAMEPAD_STICK_MIN, GAMEPAD_STICK_MAX, name="ry")
        if not ok or ry_val is None:
            return make_error_response(err or "Invalid ry")

        try:
            result = self._pico.gp_set_state(
                buttons=buttons_val,
                lt=lt_val,
                rt=rt_val,
                lx=lx_val,
                ly=ly_val,
                rx=rx_val,
                ry=ry_val,
            )
            return make_ok_response(ok=bool(result))
        except Exception as e:
            logger.exception("picoSendGamepad failed")
            return make_error_response(str(e))

    @Slot(int, int, int, result="QVariantMap")
    def picoSetStick(self, stick: int, x: int, y: int) -> QVariantMap:
        """Set stick position via Pico (0=left, 1=right)."""
        from app.backend.services.input_validation import (make_error_response,
                                                           make_ok_response,
                                                           validate_int)

        ok, stick_val, err = validate_int(stick, 0, 1, name="stick")
        if not ok or stick_val is None:
            return make_error_response(err or "Invalid stick")
        ok, x_val, err = validate_int(x, GAMEPAD_STICK_MIN, GAMEPAD_STICK_MAX, name="x")
        if not ok or x_val is None:
            return make_error_response(err or "Invalid x")
        ok, y_val, err = validate_int(y, GAMEPAD_STICK_MIN, GAMEPAD_STICK_MAX, name="y")
        if not ok or y_val is None:
            return make_error_response(err or "Invalid y")

        try:
            if stick_val == 0:
                result = self._pico.gp_set_left_stick(x_val, y_val)
            else:
                result = self._pico.gp_set_right_stick(x_val, y_val)
            return make_ok_response(ok=bool(result))
        except Exception as e:
            logger.exception("picoSetStick failed")
            return make_error_response(str(e))

    # ─── Background Methods for Other Modules ──────────────────────────────

    @Slot(str, result="QVariantMap")
    def setClickerBackgroundMethod(self, method: str) -> QVariantMap:
        """Set background input method for clicker service."""
        from app.backend.services.input_validation import (make_error_response,
                                                           make_ok_response,
                                                           validate_enum)

        ok, val, err = validate_enum(method, VALID_BACKGROUND_METHODS, name="method")
        if not ok or val is None:
            return make_error_response(err or "Invalid method")
        self._clicker_bg_method = val
        return make_ok_response()

    @Slot(str, result="QVariantMap")
    def setMacroBackgroundMethod(self, method: str) -> QVariantMap:
        """Set background input method for macro service."""
        from app.backend.services.input_validation import (make_error_response,
                                                           make_ok_response,
                                                           validate_enum)

        ok, val, err = validate_enum(method, VALID_BACKGROUND_METHODS, name="method")
        if not ok or val is None:
            return make_error_response(err or "Invalid method")
        self._macro_bg_method = val
        return make_ok_response()

    @Slot(str, result="QVariantMap")
    def setRecorderBackgroundMethod(self, method: str) -> QVariantMap:
        """Set background input method for recorder service."""
        from app.backend.services.input_validation import (make_error_response,
                                                           make_ok_response,
                                                           validate_enum)

        ok, val, err = validate_enum(method, VALID_BACKGROUND_METHODS, name="method")
        if not ok or val is None:
            return make_error_response(err or "Invalid method")
        self._recorder_bg_method = val
        return make_ok_response()

    @Slot(result="QVariantMap")
    def getClickerBackgroundMethod(self) -> QVariantMap:
        """Get clicker background method."""
        from app.backend.services.input_validation import make_ok_response

        return make_ok_response(method=self._clicker_bg_method)

    @Slot(result="QVariantMap")
    def getMacroBackgroundMethod(self) -> QVariantMap:
        """Get macro background method."""
        from app.backend.services.input_validation import make_ok_response

        return make_ok_response(method=self._macro_bg_method)

    @Slot(result="QVariantMap")
    def getRecorderBackgroundMethod(self) -> QVariantMap:
        """Get recorder background method."""
        from app.backend.services.input_validation import make_ok_response

        return make_ok_response(method=self._recorder_bg_method)

    @Slot(result="QVariantMap")
    def getGamepadBackgroundMethod(self) -> QVariantMap:
        """Get gamepad background method."""
        from app.backend.services.input_validation import make_ok_response

        return make_ok_response(method=self._gamepad_bg_method)

    # ─── Windows List ────────────────────────────────────────────────────

    @Slot(result="QVariantMap")
    def getWindows(self) -> QVariantMap:
        """Get list of visible windows."""
        try:
            windows = get_visible_windows()
            return {"ok": True, "windows": windows}
        except Exception as e:
            logger.exception("getWindows failed")
            return {"ok": False, "error": str(e), "windows": []}

    # ─── Logging Bridge ────────────────────────────────────────────────

    def log(self, level: str, source: str, message: str) -> None:
        """Log message to console via signal."""
        self.logMessage.emit(level, source, message)
