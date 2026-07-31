"""
pico_protocol.py — Протокол общения с Raspberry Pi Pico (Serial CDC / HID).
Пакеты: [START=0xAA] [CMD=1B] [LEN=1B] [PAYLOAD...] [CRC8] [END=0x55]
"""
from __future__ import annotations

import struct
from dataclasses import dataclass
from enum import IntEnum


# ─── Команды ───────────────────────────────────────────────────────────────
class PicoCmd(IntEnum):
    # Info / Control
    GET_INFO      = 0x10  # Запрос версии прошивки/возможностей
    RESET         = 0xFF  # Сброс устройства
    SET_MODE      = 0x11  # Смена режима (KB/MS/GP/Composite)

    # Keyboard
    KEY_PRESS     = 0x01  # Нажать клавишу (keycode, hold_ms)
    KEY_RELEASE   = 0x02  # Отпустить клавишу (keycode)
    KEY_TAP       = 0x03  # Тап (keycode, hold_ms)
    KEY_MODIFIERS = 0x04  # Установить модификаторы (bitmask)

    # Mouse
    MOUSE_MOVE    = 0x20  # Движение (dx, dy, absolute_flag)
    MOUSE_CLICK   = 0x21  # Клик (btn_mask, hold_ms)
    MOUSE_PRESS   = 0x22  # Нажать кнопку (btn_mask)
    MOUSE_RELEASE = 0x23  # Отпустить кнопку (btn_mask)
    MOUSE_SCROLL  = 0x24  # Скролл (dy)

    # Gamepad (XInput layout)
    GAMEPAD_STATE = 0x40  # Полное состояние (buttons, lt, rt, lx, ly, rx, ry)
    GAMEPAD_BTNS  = 0x41  # Только кнопки (bitmask)
    GAMEPAD_TRIG  = 0x42  # Только триггеры (lt, rt)
    GAMEPAD_STICK = 0x43  # Стик (which, x, y)

    # System
    PING          = 0xF0  # Пинг
    GET_CAPS      = 0xF1  # Получить capabilities bitmask


class PicoResp(IntEnum):
    ACK           = 0x00
    NACK          = 0x01
    INFO          = 0x10
    CAPS          = 0x11
    PONG          = 0xF0
    ERROR         = 0xFE


# ─── Capabilities bitmask ──────────────────────────────────────────────────
class PicoCap(IntEnum):
    KEYBOARD  = 0x01
    MOUSE     = 0x02
    GAMEPAD   = 0x04
    CONSUMER  = 0x08  # Media keys
    ABSOLUTE  = 0x10  # Absolute mouse mode


# ─── Backward-compatible command/response constants ──────────────────────────
CMD_GET_INFO      = PicoCmd.GET_INFO
CMD_RESET         = PicoCmd.RESET
CMD_SET_MODE      = PicoCmd.SET_MODE
CMD_KB_PRESS      = PicoCmd.KEY_PRESS
CMD_KB_RELEASE    = PicoCmd.KEY_RELEASE
CMD_KB_TAP        = PicoCmd.KEY_TAP
CMD_KB_MODIFIERS  = PicoCmd.KEY_MODIFIERS
CMD_MS_MOVE       = PicoCmd.MOUSE_MOVE
CMD_MS_CLICK      = PicoCmd.MOUSE_CLICK
CMD_MS_PRESS      = PicoCmd.MOUSE_PRESS
CMD_MS_RELEASE    = PicoCmd.MOUSE_RELEASE
CMD_MS_SCROLL     = PicoCmd.MOUSE_SCROLL
CMD_GP_STATE      = PicoCmd.GAMEPAD_STATE
CMD_GP_BUTTONS    = PicoCmd.GAMEPAD_BTNS
CMD_GP_TRIGGERS   = PicoCmd.GAMEPAD_TRIG
CMD_GP_STICK      = PicoCmd.GAMEPAD_STICK
CMD_PING          = PicoCmd.PING
CMD_GET_CAPS      = PicoCmd.GET_CAPS

RESP_ACK          = PicoResp.ACK
RESP_NACK         = PicoResp.NACK
RESP_INFO         = PicoResp.INFO
RESP_CAPS         = PicoResp.CAPS
RESP_PONG         = PicoResp.PONG
RESP_ERROR        = PicoResp.ERROR
RESP_OK           = PicoResp.ACK


# ─── Mouse buttons ─────────────────────────────────────────────────────────
class MouseBtn(IntEnum):
    LEFT   = 0x01
    RIGHT  = 0x02
    MIDDLE = 0x04
    BACK   = 0x08
    FORWARD= 0x10


# ─── Gamepad buttons (XInput mapping) ──────────────────────────────────────
class GPBtn(IntEnum):
    A           = 0x1000
    B           = 0x2000
    X           = 0x4000
    Y           = 0x8000
    LB          = 0x0100
    RB          = 0x0200
    BACK        = 0x0020
    START       = 0x0010
    LS          = 0x0040
    RS          = 0x0080
    GUIDE       = 0x0400
    DPAD_UP     = 0x0001
    DPAD_DOWN   = 0x0002
    DPAD_LEFT   = 0x0004
    DPAD_RIGHT  = 0x0008


# ─── CRC8 (Dallas/Maxim / 1-Wire) ────────────────────────────────────────────
# Polynomial: 0x31 (x^8 + x^5 + x^4 + 1), Init: 0xFF, No reflection, Final XOR: 0x00
# This matches the Pico firmware's CRC8-Dallas/Maxim implementation per Maxim spec.
_CRC8_POLY: int = 0x31
_CRC8_INIT: int = 0xFF  # Maxim 1-Wire standard initial value

# Pre-compute lookup table using standard algorithm
_CRC8_TABLE_LIST: list[int] = [0] * 256
for i in range(256):
    crc = i
    for _ in range(8):
        if crc & 0x80:
            crc = (crc << 1) ^ _CRC8_POLY
        else:
            crc = crc << 1
        crc &= 0xFF
    _CRC8_TABLE_LIST[i] = crc
_CRC8_TABLE: tuple[int, ...] = tuple(_CRC8_TABLE_LIST)


def crc8(data: bytes, init: int = _CRC8_INIT) -> int:
    """CRC8-Dallas/Maxim (poly 0x31, init 0xFF by default, no reflect).

    Args:
        data: Input bytes
        init: Initial CRC value (0xFF for Maxim 1-Wire, 0x00 for legacy)

    Returns:
        8-bit CRC value
    """
    crc = init & 0xFF
    for b in data:
        crc = _CRC8_TABLE[(crc ^ b) & 0xFF]
    return crc


# ─── Пакет ─────────────────────────────────────────────────────────────────
START_BYTE = 0xAA
END_BYTE   = 0x55
MAX_PAYLOAD = 60

@dataclass
class PicoPacket:
    cmd: int
    payload: bytes

    def encode(self) -> bytes:
        """Вернуть полный пакет с START/LEN/CRC/END."""
        length = len(self.payload)
        if length > MAX_PAYLOAD:
            raise ValueError(f"Payload too large: {length} > {MAX_PAYLOAD}")
        head = bytes([START_BYTE, self.cmd & 0xFF, length])
        crc = crc8(head[1:] + self.payload)  # CRC от CMD+LEN+PAYLOAD (init=0xFF)
        return head + self.payload + bytes([crc, END_BYTE])

    @staticmethod
    def decode(buffer: bytes) -> list[tuple[PicoPacket, int]]:
        """
        Извлечь пакеты из буфера. Возвращает список (packet, consumed_bytes).
        Неполные пакеты игнорируются (consumed=0).
        """
        packets = []
        i = 0
        while i < len(buffer):
            # Ищем START
            if buffer[i] != START_BYTE:
                i += 1
                continue
            if i + 4 > len(buffer):  # минимум START+CMD+LEN+CRC+END
                break
            cmd = buffer[i + 1]
            length = buffer[i + 2]
            if length > MAX_PAYLOAD:
                i += 1
                continue
            packet_end = i + 3 + length + 2  # +CRC+END
            if packet_end > len(buffer):
                break
            payload = buffer[i + 3 : i + 3 + length]
            crc_recv = buffer[packet_end - 2]
            end_byte = buffer[packet_end - 1]
            if end_byte != END_BYTE:
                i += 1
                continue
            # Проверяем CRC
            crc_calc = crc8(bytes([cmd, length]) + payload)
            if crc_calc != crc_recv:
                i += 1
                continue
            packets.append((PicoPacket(cmd, payload), packet_end - i))
            i = packet_end
        return packets


# ─── Payload builders ──────────────────────────────────────────────────────

def build_key_press(keycode: int, hold_ms: int = 0) -> bytes:
    return struct.pack('<HH', keycode & 0xFFFF, hold_ms & 0xFFFF)

def build_key_release(keycode: int) -> bytes:
    return struct.pack('<H', keycode & 0xFFFF)

def build_key_tap(keycode: int, hold_ms: int = 50) -> bytes:
    return struct.pack('<HH', keycode & 0xFFFF, hold_ms & 0xFFFF)

def build_key_modifiers(mask: int) -> bytes:
    return struct.pack('<H', mask & 0xFFFF)

def build_mouse_move(dx: int, dy: int, absolute: bool = False) -> bytes:
    dx = max(-32768, min(32767, dx))
    dy = max(-32768, min(32767, dy))
    flags = 0x01 if absolute else 0x00
    return struct.pack('<hhB', dx, dy, flags)

def build_mouse_click(btn_mask: int, hold_ms: int = 0) -> bytes:
    btn_mask &= 0xFF
    hold_ms = max(0, min(65535, hold_ms))
    return struct.pack('<HH', btn_mask, hold_ms)

def build_mouse_press(btn_mask: int) -> bytes:
    return struct.pack('<B', btn_mask & 0xFF)

def build_mouse_release(btn_mask: int) -> bytes:
    return struct.pack('<B', btn_mask & 0xFF)

def build_mouse_scroll(dy: int) -> bytes:
    dy = max(-127, min(127, dy))
    return struct.pack('<b', dy)

def build_gamepad_state(
    buttons: int = 0,
    lt: int = 0,
    rt: int = 0,
    lx: int = 0,
    ly: int = 0,
    rx: int = 0,
    ry: int = 0
) -> bytes:
    buttons &= 0xFFFF
    lt = max(0, min(255, lt))
    rt = max(0, min(255, rt))
    lx = max(-32768, min(32767, lx))
    ly = max(-32768, min(32767, ly))
    rx = max(-32768, min(32767, rx))
    ry = max(-32768, min(32767, ry))
    return struct.pack('<HBBhhhh', buttons, lt, rt, lx, ly, rx, ry)

def build_gamepad_buttons(buttons: int) -> bytes:
    return struct.pack('<H', buttons & 0xFFFF)

def build_gamepad_triggers(lt: int, rt: int) -> bytes:
    lt = max(0, min(255, lt))
    rt = max(0, min(255, rt))
    return struct.pack('<BB', lt, rt)

def build_gamepad_stick(which: int, x: int, y: int) -> bytes:
    # which: 0=L, 1=R
    x = max(-32768, min(32767, x))
    y = max(-32768, min(32767, y))
    return struct.pack('<Bhh', which & 0xFF, x, y)

def build_set_mode(mode: int) -> bytes:
    # 0=KB, 1=MS, 2=GP, 3=Composite
    return struct.pack('<B', mode & 0xFF)


# ─── Response parsers ──────────────────────────────────────────────────────

@dataclass
class PicoInfo:
    fw_version: str
    capabilities: int
    vid: int
    pid: int

def parse_info(payload: bytes) -> PicoInfo | None:
    if len(payload) < 6:
        return None
    # fmt: major, minor, patch, caps, vid, pid
    major, minor, patch, caps, vid, pid = struct.unpack('<BBBHBB', payload[:7])
    return PicoInfo(
        fw_version=f"{major}.{minor}.{patch}",
        capabilities=caps,
        vid=vid,
        pid=pid,
    )

def parse_caps(payload: bytes) -> int:
    if len(payload) >= 1:
        return payload[0]
    return 0


# Alias for backward compatibility with tests
calculate_crc8 = crc8


__all__ = [
    # Builders
    "build_gamepad_buttons",
    "build_gamepad_state",
    "build_gamepad_stick",
    "build_gamepad_triggers",
    "build_key_modifiers",
    "build_key_press",
    "build_key_release",
    "build_key_tap",
    "build_mouse_click",
    "build_mouse_move",
    "build_mouse_press",
    "build_mouse_release",
    "build_mouse_scroll",
    "build_set_mode",
    # Commands
    "CMD_GET_CAPS",
    "CMD_GET_INFO",
    "CMD_GP_BUTTONS",
    "CMD_GP_STATE",
    "CMD_GP_STICK",
    "CMD_GP_TRIGGERS",
    "CMD_KB_MODIFIERS",
    "CMD_KB_PRESS",
    "CMD_KB_RELEASE",
    "CMD_KB_TAP",
    "CMD_MS_CLICK",
    "CMD_MS_MOVE",
    "CMD_MS_PRESS",
    "CMD_MS_RELEASE",
    "CMD_MS_SCROLL",
    "CMD_PING",
    "CMD_RESET",
    "CMD_SET_MODE",
    # Constants
    "END_BYTE",
    "MAX_PAYLOAD",
    "START_BYTE",
    # CRC
    "crc8",
    # Gamepad buttons
    "GPBtn",
    # Mouse buttons
    "MouseBtn",
    # Packet
    "PicoPacket",
    # Parsers
    "PicoInfo",
    "PicoResp",
    "PicoCap",
    "parse_caps",
    "parse_info",
    # Types
    "PicoCmd",
]
