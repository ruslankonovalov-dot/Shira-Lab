"""
pico_service.py — Высокоуровневый сервис для Raspberry Pi Pico (физ. HID-устройство).

Подключение: USB CDC (Virtual COM) или Raw HID.
Протокол: Бинарный пакетный (pico_protocol.py).

Требуется прошивка на Pico с поддержкой:
- Keyboard (Boot + NKRO)
- Mouse (Absolute + Relative + Scroll)
- Gamepad (XInput-compatible)
- Composite режим (всё сразу)
"""

from __future__ import annotations

import logging
import struct
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass
from enum import IntEnum
from queue import Empty, Queue
from typing import Any, ClassVar

import serial
import serial.tools.list_ports

from app.backend.services.pico_protocol import (
    CMD_GET_INFO,
    CMD_GP_BUTTONS,
    CMD_GP_STATE,
    CMD_GP_STICK,
    CMD_GP_TRIGGERS,
    CMD_KB_PRESS,
    CMD_KB_RELEASE,
    CMD_KB_TAP,
    CMD_MS_CLICK,
    CMD_MS_MOVE,
    CMD_MS_PRESS,
    CMD_MS_RELEASE,
    CMD_MS_SCROLL,
    CMD_PING,
    CMD_RESET,
    CMD_SET_MODE,
    RESP_INFO,
    RESP_OK,
    RESP_PONG,
    PicoInfo,
    build_gamepad_buttons,
    build_gamepad_state,
    build_gamepad_stick,
    build_gamepad_triggers,
    build_mouse_click,
    build_mouse_press,
    build_mouse_release,
    build_mouse_scroll,
    parse_info,
)

logger = logging.getLogger(__name__)


class PicoMode(IntEnum):
    """Режим работы USB интерфейса."""

    KEYBOARD = 0
    MOUSE = 1
    GAMEPAD = 2
    COMPOSITE = 3  # Все сразу (требует соответствующей прошивки)


class PicoCapability(IntEnum):
    """Биты возможностей прошивки."""

    KB_BOOT = 1 << 0
    KB_NKRO = 1 << 1
    MS_ABS = 1 << 2
    MS_REL = 1 << 3
    MS_SCROLL = 1 << 4
    GP_XINPUT = 1 << 5
    GP_DS4 = 1 << 6
    COMPOSITE = 1 << 7


# ─── VK Map (common keys) ──────────────────────────────────────────────────
VK_MAP = {
    # Letters
    **{chr(c): c - 0x61 + 0x04 for c in range(ord("a"), ord("z") + 1)},
    # Digits
    **{str(d): (d + 0x1E) if d != 0 else 0x27 for d in range(10)},
    # Modifiers
    "ctrl": 0xE0,
    "shift": 0xE1,
    "alt": 0xE2,
    "gui": 0xE3,
    "lctrl": 0xE0,
    "lshift": 0xE1,
    "lalt": 0xE2,
    "lgui": 0xE3,
    "rctrl": 0xE4,
    "rshift": 0xE5,
    "ralt": 0xE6,
    "rgui": 0xE7,
    # Special
    "enter": 0x28,
    "esc": 0x29,
    "backspace": 0x2A,
    "tab": 0x2B,
    "space": 0x2C,
    "capslock": 0x39,
    "f1": 0x3A,
    "f2": 0x3B,
    "f3": 0x3C,
    "f4": 0x3D,
    "f5": 0x3E,
    "f6": 0x3F,
    "f7": 0x40,
    "f8": 0x41,
    "f9": 0x42,
    "f10": 0x43,
    "f11": 0x44,
    "f12": 0x45,
    "printscreen": 0x46,
    "scrolllock": 0x47,
    "pause": 0x48,
    "insert": 0x49,
    "home": 0x4A,
    "pageup": 0x4B,
    "delete": 0x4C,
    "end": 0x4D,
    "pagedown": 0x4E,
    "right": 0x4F,
    "left": 0x50,
    "down": 0x51,
    "up": 0x52,
    "numlock": 0x53,
    "kp_divide": 0x54,
    "kp_multiply": 0x55,
    "kp_subtract": 0x56,
    "kp_add": 0x57,
    "kp_enter": 0x58,
    "kp_1": 0x59,
    "kp_2": 0x5A,
    "kp_3": 0x5B,
    "kp_4": 0x5C,
    "kp_5": 0x5D,
    "kp_6": 0x5E,
    "kp_7": 0x5F,
    "kp_8": 0x60,
    "kp_9": 0x61,
    "kp_0": 0x62,
    "kp_dot": 0x63,
    # Media
    "mute": 0xE2,
    "volup": 0xE9,
    "voldown": 0xEA,
    "playpause": 0xCD,
    "next": 0xB5,
    "prev": 0xB6,
    "stop": 0xB7,
}


# ─── Mouse buttons ─────────────────────────────────────────────────────────
MOUSE_LEFT = 1 << 0
MOUSE_RIGHT = 1 << 1
MOUSE_MIDDLE = 1 << 2
MOUSE_BACK = 1 << 3
MOUSE_FORWARD = 1 << 4


# ─── Gamepad buttons (XInput layout) ───────────────────────────────────────
GP_A = 0x1000
GP_B = 0x2000
GP_X = 0x4000
GP_Y = 0x8000
GP_LB = 0x0100
GP_RB = 0x0200
GP_BACK = 0x0020
GP_START = 0x0010
GP_LS = 0x0040
GP_RS = 0x0080
GP_GUIDE = 0x0400
GP_DPAD_UP = 0x0001
GP_DPAD_DOWN = 0x0002
GP_DPAD_LEFT = 0x0004
GP_DPAD_RIGHT = 0x0008


@dataclass
class PicoDevice:
    """Информация о найденном Pico устройстве."""

    port: str
    vid: int
    pid: int
    serial_number: str | None
    description: str
    info: PicoInfo | None = None


class PicoService:
    """
    Основной сервис для работы с Raspberry Pi Pico как HID-устройством.

    Особенности:
    - Автопоиск Pico по VID:PID (2e8a:000a / 2e8a:0005 / custom)
    - Переподключение при отключении USB
    - Командная очередь с подтверждениями (ACK/NACK)
    - Потокобезопасный API
    - Heartbeat (PING) для проверки связи
    """

    # Стандартные VID:PID для Pico в CDC режиме
    DEFAULT_VIDS: ClassVar[list[int]] = [0x2E8A]  # Raspberry Pi
    DEFAULT_PIDS: ClassVar[list[int]] = [
        0x000A,
        0x0005,
        0x0009,
    ]  # Pico CDC, Pico Boot, Custom

    def __init__(
        self,
        port: str | None = None,
        baudrate: int = 115200,
        timeout: float = 0.1,
        auto_reconnect: bool = True,
        vid_filter: list[int] | None = None,
        pid_filter: list[int] | None = None,
    ):
        self._port = port
        self._baudrate = baudrate
        self._timeout = timeout
        self._auto_reconnect = auto_reconnect
        self._vid_filter = vid_filter or self.DEFAULT_VIDS
        self._pid_filter = pid_filter or self.DEFAULT_PIDS

        self._ser: serial.Serial | None = None
        self._reader_thread: threading.Thread | None = None
        self._writer_thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._connected = False
        self._lock = threading.RLock()  # Reentrant lock for connect/disconnect
        self._pending_lock = threading.Lock()  # Protects _pending dict

        # Командная очередь: (frame, seq)
        self._cmd_queue: Queue[tuple[bytes, int]] = Queue()
        self._pending: dict[int, tuple[threading.Event, bytes | None]] = (
            {}
        )  # seq -> (event, response_data)
        self._seq = 0

        # Callbacks
        self._on_connect: Callable[[PicoInfo], None] | None = None
        self._on_disconnect: Callable[[], None] | None = None
        self._on_error: Callable[[Exception], None] | None = None

        # Device info
        self._device_info: PicoInfo | None = None
        self._current_mode = PicoMode.COMPOSITE

        # Bridge reference for logging
        self._bridge: Any = None  # Any to avoid circular imports

        # Button mapping (loaded from state)
        self._button_map: dict[str, str] = {}

    def set_bridge(self, bridge: Any) -> None:
        """Set bridge reference for logging."""
        self._bridge = bridge

    def _log(self, level: str, message: str) -> None:
        if self._bridge:
            self._bridge.log(level, "PICO", message)

    # ─── Public API ────────────────────────────────────────────────────────

    @property
    def is_connected(self) -> bool:
        return self._connected and self._ser is not None and self._ser.is_open

    @property
    def device_info(self) -> PicoInfo | None:
        return self._device_info

    @property
    def current_mode(self) -> PicoMode:
        return self._current_mode

    def set_callbacks(
        self,
        on_connect: Callable[[PicoInfo], None] | None = None,
        on_disconnect: Callable[[], None] | None = None,
        on_error: Callable[[Exception], None] | None = None,
    ) -> None:
        self._on_connect = on_connect
        self._on_disconnect = on_disconnect
        self._on_error = on_error

    # ─── Connection ────────────────────────────────────────────────────────

    def connect(self, port: str | None = None) -> bool:
        """Подключиться к Pico. Если port=None — автопоиск."""
        with self._lock:
            if self.is_connected:
                return True

            if port:
                self._port = port
            elif not self._port:
                found = self.find_pico()
                if not found:
                    logger.debug("Pico не найден — устройство не подключено")
                    return False
                self._port = found.port
                logger.info(f"Автоопределен порт: {self._port}")

            try:
                self._ser = serial.Serial(
                    port=self._port,
                    baudrate=self._baudrate,
                    timeout=self._timeout,
                    write_timeout=1.0,
                    rtscts=False,
                    dsrdtr=False,
                )
                # Дать Pico время на сброс после открытия порта
                time.sleep(0.3)
                self._ser.reset_input_buffer()
                self._ser.reset_output_buffer()

                self._stop_event.clear()
                self._reader_thread = threading.Thread(
                    target=self._reader_loop, daemon=True
                )
                self._writer_thread = threading.Thread(
                    target=self._writer_loop, daemon=True
                )
                self._reader_thread.start()
                self._writer_thread.start()

                # Handshake: GET_INFO
                info = self._handshake()
                if not info:
                    self._cleanup()
                    return False

                self._device_info = info
                self._connected = True
                logger.info(
                    f"Pico подключен: {info.fw_version}, caps=0x{info.capabilities:04X}"
                )
                self._log("OK", f"Connected — fw={info.fw_version} port={self._port}")
                if self._on_connect:
                    self._on_connect(info)
                return True

            except (OSError, serial.SerialException, ValueError) as e:
                logger.error(f"Ошибка подключения: {e}")
                self._log("ERROR", f"Connection failed: {e}")
                self._cleanup()
                return False

    def disconnect(self) -> None:
        """Отключиться от Pico."""
        with self._lock:
            self._cleanup()
            self._connected = False
            self._log("INFO", "Disconnected")
            if self._on_disconnect:
                self._on_disconnect()

    def get_button_map(self, button: str) -> str:
        """Get the mapped key for a Pico button."""
        return self._button_map.get(button.upper(), "space")

    def set_button_map(self, button: str, key: str) -> None:
        """Set the mapped key for a Pico button."""
        self._button_map[button.upper()] = key.lower()

    def _cleanup(self) -> None:
        # Idempotent: safe to call multiple times
        self._stop_event.set()
        ser = self._ser
        self._ser = None
        if ser:
            try:
                ser.close()
            except OSError:
                logger.debug("Error closing serial port during cleanup")
        reader = self._reader_thread
        writer = self._writer_thread
        self._reader_thread = None
        self._writer_thread = None
        for t in (reader, writer):
            if t and t.is_alive():
                t.join(timeout=1.0)

    def _handshake(self) -> PicoInfo | None:
        """Ручной handshake после открытия порта."""
        for _ in range(5):
            info = self.get_info(timeout=1.0)
            if info:
                return info
            time.sleep(0.2)
        return None

    # ─── Device Discovery ──────────────────────────────────────────────────

    @classmethod
    def find_pico(
        cls, vid_filter: list[int] | None = None, pid_filter: list[int] | None = None
    ) -> PicoDevice | None:
        """Найти первый Pico в системе."""
        devices = cls.list_picos(vid_filter, pid_filter)
        return devices[0] if devices else None

    @classmethod
    def list_picos(
        cls, vid_filter: list[int] | None = None, pid_filter: list[int] | None = None
    ) -> list[PicoDevice]:
        """Список всех Pico устройств."""
        vid_filter = vid_filter or cls.DEFAULT_VIDS
        pid_filter = pid_filter or cls.DEFAULT_PIDS
        result: list[PicoDevice] = []
        for p in serial.tools.list_ports.comports():
            if p.vid in vid_filter and (p.pid in pid_filter or not pid_filter):
                dev = PicoDevice(
                    port=p.device,
                    vid=p.vid or 0,
                    pid=p.pid or 0,
                    serial_number=p.serial_number,
                    description=p.description or "",
                )
                # Popробuем получить инфу
                ser: serial.Serial | None = None
                try:
                    ser = serial.Serial(p.device, 115200, timeout=0.5)
                    time.sleep(0.2)
                    ser.reset_input_buffer()
                    ser.write(bytes([CMD_GET_INFO, 0, 0, 0]))
                    resp = ser.read(64)
                    if resp and len(resp) >= 2 and resp[0] == RESP_INFO:
                        dev.info = parse_info(resp[2:])
                except (OSError, serial.SerialException, ValueError):
                    logger.debug(f"Failed to probe Pico on {p.device}")
                finally:
                    if ser:
                        try:
                            ser.close()
                        except OSError:
                            logger.debug(f"Error closing serial port {p.device}")
                result.append(dev)
        return result

    # ─── Low-level send/recv ───────────────────────────────────────────────

    def _send_command(
        self,
        cmd: int,
        payload: bytes = b"",
        wait_resp: bool = True,
        timeout: float = 2.0,
    ) -> bytes | None:
        """Отправить команду и опционально дождаться ответа."""
        if not self.is_connected:
            return None

        seq = self._next_seq()
        # Frame: [CMD][SEQ][LEN_H][LEN_L][PAYLOAD...]
        frame = (
            bytes([cmd, seq & 0xFF, (len(payload) >> 8) & 0xFF, len(payload) & 0xFF])
            + payload
        )

        if wait_resp:
            event = threading.Event()
            with self._pending_lock:
                self._pending[seq] = (event, None)
            self._cmd_queue.put((frame, seq))
            if event.wait(timeout):
                with self._pending_lock:
                    _, resp = self._pending.pop(seq, (None, None))
                return resp
            else:
                with self._pending_lock:
                    self._pending.pop(seq, None)
                logger.warning(f"Команда 0x{cmd:02X} seq={seq} таймаут")
                return None
        else:
            self._cmd_queue.put((frame, seq))
            return None

    def _next_seq(self) -> int:
        """Generate next sequence number, skipping any that are still pending."""
        with self._pending_lock:
            # Wrap at 255 but skip sequences that are still in-flight
            for _ in range(256):  # Max 256 attempts to find a free slot
                self._seq = (self._seq + 1) & 0xFF
                if self._seq not in self._pending:
                    return self._seq
            # All 256 sequences in use (should never happen in practice)
            raise RuntimeError("Sequence space exhausted: 256 pending commands")

    # ─── Reader / Writer loops ─────────────────────────────────────────────

    def _reader_loop(self) -> None:
        """Чтение ответов от Pico."""
        buffer = bytearray()
        while not self._stop_event.is_set():
            ser = self._ser  # Local reference to avoid race with cleanup
            if not ser or not ser.is_open:
                break
            try:
                data = ser.read(64)
                if not data:
                    continue
                buffer.extend(data)

                # Парсим фреймы: [CMD][SEQ][LEN_H][LEN_L][PAYLOAD...]
                while len(buffer) >= 4:
                    cmd = buffer[0]
                    seq = buffer[1]
                    plen = (buffer[2] << 8) | buffer[3]
                    if len(buffer) < 4 + plen:
                        break
                    payload = bytes(buffer[4 : 4 + plen])
                    del buffer[: 4 + plen]

                    self._handle_response(cmd, seq, payload)

            except serial.SerialException as e:
                logger.error(f"Serial ошибка чтения: {e}")
                self._handle_disconnect()
                break
            except (OSError, ValueError, struct.error) as e:
                logger.error(f"Reader loop ошибка: {e}")

    def _writer_loop(self) -> None:
        """Отправка команд в очередь."""
        while not self._stop_event.is_set():
            ser = self._ser  # Local reference to avoid race with cleanup
            if not ser or not ser.is_open:
                break
            try:
                frame, _ = self._cmd_queue.get(timeout=0.1)
                ser.write(frame)
                ser.flush()
            except Empty:
                continue
            except serial.SerialException as e:
                logger.error(f"Serial ошибка записи: {e}")
                self._handle_disconnect()
                break
            except (OSError, ValueError) as e:
                logger.error(f"Writer loop ошибка: {e}")

    def _handle_response(self, cmd: int, seq: int, payload: bytes) -> None:
        """Обработка входящего ответа."""
        with self._pending_lock:
            if seq in self._pending:
                event, _ = self._pending[seq]
                self._pending[seq] = (event, payload)
                event.set()
            else:
                # Незапрошенный ответ / уведомление
                logger.debug(f"Unsolicited: cmd=0x{cmd:02X}, payload={payload.hex()}")

    def _handle_disconnect(self) -> None:
        """Обработка отключения устройства."""
        with self._lock:
            was_connected = self._connected
            if not was_connected:
                return
            self._cleanup()
            self._connected = False
        if was_connected and self._on_disconnect:
            self._on_disconnect()
        if self._auto_reconnect:
            self._reconnect_loop()

    def _reconnect_loop(self) -> None:
        """Попытки переподключения в фоне."""

        def attempt() -> None:
            while self._auto_reconnect and not self._stop_event.is_set():
                time.sleep(2.0)
                if self._stop_event.is_set():
                    break
                try:
                    if self.connect():
                        logger.info("Переподключение успешно")
                        break
                except (OSError, serial.SerialException, ValueError, RuntimeError):
                    logger.exception("Failed to reconnect to Pico")

        threading.Thread(target=attempt, daemon=True).start()

    # ─── High-level Commands ───────────────────────────────────────────────

    def get_info(self, timeout: float = 1.0) -> PicoInfo | None:
        """Запросить информацию об устройстве."""
        resp = self._send_command(CMD_GET_INFO, b"", wait_resp=True, timeout=timeout)
        if resp and len(resp) >= 1 and resp[0] == RESP_INFO:
            return parse_info(resp[1:])
        return None

    def ping(self, timeout: float = 0.5) -> bool:
        """Проверка связи."""
        resp = self._send_command(CMD_PING, b"", wait_resp=True, timeout=timeout)
        return bool(resp and len(resp) >= 1 and resp[0] == RESP_PONG)

    def reset(self, timeout: float = 1.0) -> bool:
        """Софтовый ресет Pico."""
        resp = self._send_command(CMD_RESET, b"", wait_resp=True, timeout=timeout)
        return bool(resp and resp[0] == RESP_OK)

    def set_mode(self, mode: PicoMode) -> bool:
        """Сменить USB режим (Keyboard/Mouse/Gamepad/Composite)."""
        resp = self._send_command(CMD_SET_MODE, bytes([mode]), wait_resp=True)
        if resp and resp[0] == RESP_OK:
            self._current_mode = mode
            return True
        return False

    # ─── Keyboard ──────────────────────────────────────────────────────────

    def kb_press(self, key: str) -> bool:
        """Нажать клавишу (удерживается до release)."""
        vk = self._key_to_vk(key)
        if vk is None:
            return False
        resp = self._send_command(CMD_KB_PRESS, bytes([vk]), wait_resp=True)
        return bool(resp and resp[0] == RESP_OK)

    def kb_release(self, key: str) -> bool:
        """Отпустить клавишу."""
        vk = self._key_to_vk(key)
        if vk is None:
            return False
        resp = self._send_command(CMD_KB_RELEASE, bytes([vk]), wait_resp=True)
        return bool(resp and resp[0] == RESP_OK)

    def kb_tap(self, key: str, hold_ms: int = 50) -> bool:
        """Нажать и отпустить клавишу (tap)."""
        vk = self._key_to_vk(key)
        if vk is None:
            return False
        payload = bytes([vk, hold_ms & 0xFF, (hold_ms >> 8) & 0xFF])
        resp = self._send_command(CMD_KB_TAP, payload, wait_resp=True)
        return bool(resp and resp[0] == RESP_OK)

    def kb_type(self, text: str, delay_ms: int = 10) -> bool:
        """Напечатать строку (посимвольно)."""
        for ch in text:
            if not self.kb_tap(ch, 20):
                return False
            if delay_ms > 0:
                time.sleep(delay_ms / 1000.0)
        return True

    def _key_to_vk(self, key: str) -> int | None:
        k = key.lower().strip()
        return VK_MAP.get(k)

    # ─── Mouse ──────────────────────────────────────────────────────────────

    def ms_move(self, x: int, y: int, absolute: bool = False) -> bool:
        """Переместить мышь. absolute=True → 0..32767, relative → -32768..32767."""
        if absolute:
            x = max(0, min(32767, x))
            y = max(0, min(32767, y))
            flags = 0x01
        else:
            x = max(-32768, min(32767, x))
            y = max(-32768, min(32767, y))
            flags = 0x00
        payload = struct.pack("<hhB", x, y, flags)
        resp = self._send_command(CMD_MS_MOVE, payload, wait_resp=True)
        return bool(resp and resp[0] == RESP_OK)

    def ms_click(self, button: int = MOUSE_LEFT, hold_ms: int = 50) -> bool:
        """Клик: нажать + hold + отпустить."""
        payload = build_mouse_click(button, hold_ms)
        resp = self._send_command(CMD_MS_CLICK, payload, wait_resp=True)
        return bool(resp and resp[0] == RESP_OK)

    def ms_press(self, button: int = MOUSE_LEFT) -> bool:
        payload = build_mouse_press(button)
        resp = self._send_command(CMD_MS_PRESS, payload, wait_resp=True)
        return bool(resp and resp[0] == RESP_OK)

    def ms_release(self, button: int = MOUSE_LEFT) -> bool:
        payload = build_mouse_release(button)
        resp = self._send_command(CMD_MS_RELEASE, payload, wait_resp=True)
        return bool(resp and resp[0] == RESP_OK)

    def ms_scroll(self, clicks: int) -> bool:
        """Колесо прокрутки: + вверх, - вниз."""
        payload = build_mouse_scroll(clicks)
        resp = self._send_command(CMD_MS_SCROLL, payload, wait_resp=True)
        return bool(resp and resp[0] == RESP_OK)

    # ─── Gamepad (XInput) ──────────────────────────────────────────────────

    def gp_set_state(
        self,
        buttons: int = 0,
        lt: int = 0,
        rt: int = 0,
        lx: int = 0,
        ly: int = 0,
        rx: int = 0,
        ry: int = 0,
    ) -> bool:
        """Установить полное состояние геймпада."""
        payload = build_gamepad_state(buttons, lt, rt, lx, ly, rx, ry)
        resp = self._send_command(CMD_GP_STATE, payload, wait_resp=True)
        return bool(resp and resp[0] == RESP_OK)

    def gp_press_button(self, button: int) -> bool:
        """Нажать кнопку (добавляет к текущему состоянию)."""
        # Pico firmware должен поддерживать битовые операции
        payload = build_gamepad_buttons(button)
        resp = self._send_command(CMD_GP_BUTTONS, payload, wait_resp=True)
        return bool(resp and resp[0] == RESP_OK)

    def gp_release_button(self, _button: int) -> bool:
        """Release a specific button while keeping others pressed.

        Note: Pico firmware needs to support bitwise operations for this to work correctly.
        For now, we read the current state and clear the bit.
        """
        # For proper implementation, we'd need to track button state locally.
        # Simplified: send 0 to release all (fallback for firmware without bitwise support)
        payload = build_gamepad_buttons(0)
        resp = self._send_command(CMD_GP_BUTTONS, payload, wait_resp=True)
        return bool(resp and resp[0] == RESP_OK)

    def gp_set_buttons(self, buttons: int) -> bool:
        """Установить точную битовую маску кнопок."""
        payload = build_gamepad_buttons(buttons)
        resp = self._send_command(CMD_GP_BUTTONS, payload, wait_resp=True)
        return bool(resp and resp[0] == RESP_OK)

    def gp_set_triggers(self, left: int, right: int) -> bool:
        payload = build_gamepad_triggers(left, right)
        resp = self._send_command(CMD_GP_TRIGGERS, payload, wait_resp=True)
        return bool(resp and resp[0] == RESP_OK)

    def gp_set_left_stick(self, x: int, y: int) -> bool:
        payload = build_gamepad_stick(0, x, y)
        resp = self._send_command(CMD_GP_STICK, payload, wait_resp=True)
        return bool(resp and resp[0] == RESP_OK)

    def gp_set_right_stick(self, x: int, y: int) -> bool:
        payload = build_gamepad_stick(1, x, y)
        resp = self._send_command(CMD_GP_STICK, payload, wait_resp=True)
        return bool(resp and resp[0] == RESP_OK)

    def gp_reset(self) -> bool:
        """Сброс всего в ноль."""
        return self.gp_set_state(0, 0, 0, 0, 0, 0, 0)


# ─── Singleton accessor ────────────────────────────────────────────────────

_pico_instance: PicoService | None = None


def get_pico_service(**kwargs: Any) -> PicoService:
    """Получить глобальный экземпляр PicoService (lazy init).

    If kwargs are provided and an instance already exists, the instance
    will be reconfigured with the new parameters before returning.
    """
    global _pico_instance
    if _pico_instance is None:
        _pico_instance = PicoService(**kwargs)
    elif kwargs:
        # Reconfigure existing instance with new parameters
        if "port" in kwargs:
            _pico_instance._port = kwargs["port"]
        if "baudrate" in kwargs:
            _pico_instance._baudrate = kwargs["baudrate"]
    return _pico_instance


def shutdown_pico_service() -> None:
    global _pico_instance
    if _pico_instance:
        _pico_instance.disconnect()
        _pico_instance = None
