"""app/backend/bridges/gamepad_bridge.py — ViGEm Gamepad-методы моста QML.

Перенесено из qml_bridge.py, секция "Vigem" (строки 1388–1635).
"""

from __future__ import annotations

import json

from PySide6.QtCore import Slot

from app.backend.bridges.bridge_base import BridgeBase


class GamepadBridge(BridgeBase):
    """Методы виртуального геймпада (ViGEm): getVigemStatus, vigemSetGamepadState, ..."""

    def __init__(self, parent=None):
        super().__init__(parent)
        # ViGEm инициализируется лениво (требует драйвер)
        self._vigem = None

    @property
    def vigem(self):
        if self._vigem is None:
            try:
                from app.backend.services.vigem_service import VigemService

                self._vigem = VigemService()
            except Exception:
                return None
        return self._vigem

    @Slot(result=str)
    def getVigemStatus(self):
        if not self.vigem:
            return json.dumps({"ok": False, "error": "ViGEm not available"})
        return json.dumps(self.vigem.get_status())

    @Slot(str, result=str)
    def setVigemControllerType(self, controller_type: str):
        if not self.vigem:
            return json.dumps({"ok": False, "error": "ViGEm not available"})
        return json.dumps(self.vigem.set_controller_type(controller_type))

    @Slot(int, result=str)
    def setVigemTargetIndex(self, index: int):
        if not self.vigem:
            return json.dumps({"ok": False, "error": "ViGEm not available"})
        return json.dumps(self.vigem.set_target_index(index))

    @Slot(str, str, result=str)
    def setVigemButtonMap(self, key: str, gamepad_btn: str):
        if not self.vigem:
            return json.dumps({"ok": False, "error": "ViGEm not available"})
        return json.dumps(self.vigem.set_button_map(key, gamepad_btn))

    @Slot(result=str)
    def startVigem(self):
        if not self.vigem:
            return json.dumps({"ok": False, "error": "ViGEm not available"})
        return json.dumps(self.vigem.start())

    @Slot(result=str)
    def stopVigem(self):
        if not self.vigem:
            return json.dumps({"ok": False, "error": "ViGEm not available"})
        return json.dumps(self.vigem.stop())

    @Slot(result=str)
    def refreshVigemTargets(self):
        if not self.vigem:
            return json.dumps({"ok": False, "error": "ViGEm not available"})
        return json.dumps(self.vigem.refresh_targets())

    @Slot(int, int, int, int, int, int, int, int, result=str)
    def vigemSetGamepadState(self, target_id, buttons, lt, rt, lx, ly, rx, ry):
        if not self.vigem:
            return json.dumps({"ok": False, "error": "ViGEm not available"})
        return json.dumps(self.vigem.set_gamepad_state(target_id, buttons, lt, rt, lx, ly, rx, ry))

    @Slot(int, int, result=str)
    def vigemSetButtons(self, target_id, button_mask):
        if not self.vigem:
            return json.dumps({"ok": False, "error": "ViGEm not available"})
        return json.dumps(self.vigem.set_buttons(target_id, button_mask))

    @Slot(int, int, result=str)
    def vigemSetTriggers(self, target_id, left, right):
        if not self.vigem:
            return json.dumps({"ok": False, "error": "ViGEm not available"})
        return json.dumps(self.vigem.set_triggers(target_id, left, right))

    @Slot(int, int, int, result=str)
    def vigemSetLeftStick(self, target_id, x, y):
        if not self.vigem:
            return json.dumps({"ok": False, "error": "ViGEm not available"})
        return json.dumps(self.vigem.set_left_stick(target_id, x, y))

    @Slot(int, int, int, result=str)
    def vigemSetRightStick(self, target_id, x, y):
        if not self.vigem:
            return json.dumps({"ok": False, "error": "ViGEm not available"})
        return json.dumps(self.vigem.set_right_stick(target_id, x, y))

    @Slot(int, result=str)
    def vigemReset(self, target_id):
        if not self.vigem:
            return json.dumps({"ok": False, "error": "ViGEm not available"})
        return json.dumps(self.vigem.reset(target_id))

    @Slot(str, result=str)
    def setGamepadBackgroundMethod(self, method):
        if not self.vigem:
            return json.dumps({"ok": False, "error": "ViGEm not available"})
        return json.dumps(self.vigem.set_background_method(method))

    @Slot(result=str)
    def detectPhysicalGamepads(self):
        """Список физических геймпадов через XInput (для info panel)."""
        import ctypes

        try:
            # XINPUT_STATE structure
            class XINPUT_GAMEPAD(ctypes.Structure):
                _fields_ = [
                    ("wButtons", ctypes.c_ushort),
                    ("bLeftTrigger", ctypes.c_ubyte),
                    ("bRightTrigger", ctypes.c_ubyte),
                    ("sThumbLX", ctypes.c_short),
                    ("sThumbLY", ctypes.c_short),
                    ("sThumbRX", ctypes.c_short),
                    ("sThumbRY", ctypes.c_short),
                ]

            class XINPUT_STATE(ctypes.Structure):
                _fields_ = [
                    ("dwPacketNumber", ctypes.c_uint),
                    ("Gamepad", XINPUT_GAMEPAD),
                ]

            xinput = ctypes.windll.xinput1_4
            devices = []
            for i in range(4):
                state = XINPUT_STATE()
                if xinput.XInputGetState(i, ctypes.byref(state)) == 0:
                    devices.append(
                        {
                            "index": i,
                            "buttons": state.Gamepad.wButtons,
                            "left_trigger": state.Gamepad.bLeftTrigger,
                            "right_trigger": state.Gamepad.bRightTrigger,
                        }
                    )
            return json.dumps({"ok": True, "devices": devices})
        except Exception as e:
            return json.dumps({"ok": False, "error": str(e)})
