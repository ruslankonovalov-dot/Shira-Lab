from __future__ import annotations

import ctypes
import logging
import os
import threading
import time
from collections.abc import Callable, Sequence
from typing import (
    Any,
    cast,
)

import cv2
import mss
import numpy as np
import numpy.typing as npt
from mss import MSS as MSSClass

from app.backend.services.singleton import singleton

logger = logging.getLogger(__name__)


# Type aliases
HSVRange = tuple[tuple[int, int, int], tuple[int, int, int]]
DetectionMode = str
BackgroundMethod = str
TargetColor = str


@singleton
class AimService:
    """Professional aim assist with visual debug and adaptive detection.

    Key design principles:
    1. Capture only FOV region (center of screen) — fast, ~5ms per frame
    2. Visual debug — save screenshots with marked targets to screenshots/debug/
    3. SendInput for mouse movement (modern, reliable)
    4. Adaptive calibration — pipette samples 7x7, computes mean + std HSV
    5. Multi-mode detection with visual feedback
    """

    HSV_PRESETS = {
        "red":    [((0, 50, 50), (15, 255, 255)), ((165, 50, 50), (180, 255, 255))],
        "blue":   [((85, 50, 50), (135, 255, 255))],
        "green":  [((35, 50, 50), (85, 255, 255))],
        "purple": [((125, 50, 50), (165, 255, 255))],
        "yellow": [((15, 50, 50), (40, 255, 255))],
        "cyan":   [((75, 50, 50), (105, 255, 255))],
        "orange": [((5, 50, 50), (30, 255, 255))],
        "pink":   [((135, 50, 50), (175, 255, 255))],
    }

    def __init__(self) -> None:
        self.is_running: bool = False
        self.confidence: float = 0.5
        self.smooth_steps: int = 5
        self.reset_delay: float = 0.005
        self.scan_region: dict[str, int] | None = None
        self.last_log: str = "READY"
        self.target_hwnd: int | None = None
        self.background_method: BackgroundMethod = "sendinput"

        self.detection_mode: DetectionMode = "auto"
        self.target_color: TargetColor = "red"
        self.multi_colors: list[TargetColor] = ["red", "blue", "green"]
        self.calibrated_hsv_ranges: list[HSVRange] = []

        # Filters
        self.min_area: int = 20
        self.max_area: int = 50000
        self.aspect_ratio_min: float = 0.3
        self.aspect_ratio_max: float = 2.0
        self.brightness_threshold: int = 80
        self.saturation_threshold: int = 50

        # FOV — default 300px radius (capture only center, fast)
        self.fov_radius: int = 300
        self.aim_speed: float = 0.3

        # Predictive aim — compensate for latency
        self.prediction_factor: float = 0.15  # 0 = off, 0.15 = light prediction
        self.last_target_pos: tuple[int, int, float] | None = None    # (tx, ty, timestamp)
        self.last_mouse_delta: tuple[int, int] = (0, 0) # for smoothing

        # Debug
        self.debug_screenshots: bool = True
        self.debug_frame_count: int = 0

        # Performance: pre-built HSV arrays
        self._hsv_cache: dict[str, list[tuple[npt.NDArray[np.uint8], npt.NDArray[np.uint8]]]] = {}  # color_name → list of (lower_arr, upper_arr)
        self._kernel_3x3: npt.NDArray[np.uint8] = np.ones((3, 3), np.uint8)

        self._bridge: object | None = None
        self._bridge_log: Callable[[str, str, str], None] | None = None
        self._screen_w: int = 0
        self._screen_h: int = 0
        self._screen_x: int = 0  # Virtual screen X offset (multi-monitor)
        self._screen_y: int = 0  # Virtual screen Y offset (multi-monitor)
        self._sct: MSSClass | None = None  # mss.mss instance

        # Thread safety
        self._lock: threading.RLock = threading.RLock()

    def _get_hsv_arrays(self, color_name: str) -> list[tuple[npt.NDArray[np.uint8], npt.NDArray[np.uint8]]]:
        """Get cached numpy arrays for HSV range (avoids re-creating every frame)."""
        if color_name not in self._hsv_cache:
            ranges = self.HSV_PRESETS.get(color_name, [])
            self._hsv_cache[color_name] = [
                (np.array(lower, dtype=np.uint8), np.array(upper, dtype=np.uint8))
                for lower, upper in ranges
            ]
        return self._hsv_cache[color_name]

    def set_bridge(self, bridge: object | None) -> None:
        self._bridge = bridge
        # Expect bridge to have a log(level, module, message) method
        if bridge and hasattr(bridge, 'log'):
            self._bridge_log = bridge.log
        else:
            self._bridge_log = None

    def _log(self, level: str, message: str) -> None:
        if self._bridge_log is not None:
            self._bridge_log(level, "AIM", message)

    def _get_screen_size(self) -> tuple[int, int, int, int]:
        if self._screen_w == 0:
            # Use VIRTUAL screen metrics for multi-monitor support
            # SM_CXVIRTUALSCREEN = 78, SM_CYVIRTUALSCREEN = 79
            # SM_XVIRTUALSCREEN = 76, SM_YVIRTUALSCREEN = 77
            user32 = ctypes.windll.user32
            self._screen_w = user32.GetSystemMetrics(78)
            self._screen_h = user32.GetSystemMetrics(79)
            self._screen_x = user32.GetSystemMetrics(76)
            self._screen_y = user32.GetSystemMetrics(77)
            # Fallback to primary if virtual is 0
            if self._screen_w == 0:
                self._screen_w = user32.GetSystemMetrics(0)
                self._screen_h = user32.GetSystemMetrics(1)
                self._screen_x = 0
                self._screen_y = 0
        return self._screen_w, self._screen_h, self._screen_x, self._screen_y

    # ─── Config ────────────────────────────────────────────────────────

    def update_config(self, confidence: float, smooth_steps: int, reset_delay: float) -> dict[str, Any]:
        with self._lock:
            self.confidence = max(0.1, min(1.0, float(confidence)))
            self.smooth_steps = max(1, int(smooth_steps))
            self.reset_delay = max(0.001, float(reset_delay))
        return self.get_status()

    def set_detection_mode(self, mode: DetectionMode) -> dict[str, Any]:
        valid: tuple[DetectionMode, ...] = ("auto", "multi", "circles", "color", "calibrate")
        if mode in valid:
            with self._lock:
                self.detection_mode = mode
            self._log("OK", f"Mode: {mode}")
            return {"ok": True, "detection_mode": mode}
        return {"ok": False, "error": f"Invalid mode: {mode}"}

    def set_target_color(self, color: TargetColor) -> dict[str, Any]:
        if color in self.HSV_PRESETS:
            with self._lock:
                self.target_color = color
            self._log("INFO", f"Color: {color}")
            return {"ok": True, "target_color": color}
        return {"ok": False, "error": f"Unknown color: {color}"}

    def set_multi_colors(self, colors: list[TargetColor]) -> dict[str, Any]:
        with self._lock:
            self.multi_colors = colors
        self._log("INFO", f"Multi colors: {colors}")
        return {"ok": True, "multi_colors": colors}

    def set_fov(self, radius: int) -> dict[str, Any]:
        with self._lock:
            self.fov_radius = max(50, min(1000, int(radius)))
        self._log("INFO", f"FOV: {self.fov_radius}px")
        return {"ok": True, "fov_radius": self.fov_radius}

    def set_aim_speed(self, speed: float) -> dict[str, Any]:
        with self._lock:
            self.aim_speed = max(0.05, min(1.0, float(speed)))
        return {"ok": True, "aim_speed": self.aim_speed}

    def set_filters(self, min_area: int, max_area: int, aspect_min: float, aspect_max: float, brightness: int, saturation: int) -> dict[str, Any]:
        with self._lock:
            self.min_area = max(1, int(min_area))
            self.max_area = max(self.min_area + 1, int(max_area))
            self.aspect_ratio_min = max(0.1, float(aspect_min))
            self.aspect_ratio_max = max(self.aspect_ratio_min, float(aspect_max))
            self.brightness_threshold = max(0, min(255, int(brightness)))
            self.saturation_threshold = max(0, min(255, int(saturation)))
        return {"ok": True}

    def set_scan_region(self, top: int, left: int, width: int, height: int) -> dict[str, Any]:
        """Set custom scan region. Pass all zeros to reset to full screen."""
        if top == 0 and left == 0 and width == 0 and height == 0:
            with self._lock:
                self.scan_region = None
        else:
            with self._lock:
                self.scan_region = {
                    "top": int(top), "left": int(left),
                    "width": max(1, int(width)), "height": max(1, int(height)),
                }
        return self.get_status()

    # ─── Calibration (pipette) ─────────────────────────────────────────

    def sample_color_at(self, x: int, y: int) -> dict[str, Any]:
        """Sample HSV color at screen position. Takes 7x7 region, computes mean + std.
        Creates adaptive tolerance range based on standard deviation.
        """
        try:
            # Validate coordinates are within screen bounds
            sw, sh, sx, sy = self._get_screen_size()
            if x < 0 or y < 0 or x >= sw or y >= sh:
                self._log("ERROR", f"Pipette coordinates out of bounds: ({x},{y}) screen={sw}x{sh}")
                return {"ok": False, "error": f"Coordinates ({x},{y}) out of screen bounds ({sw}x{sh})"}

            if self._sct is None:
                self._sct = mss.mss()

            # 7x7 region — small enough to stay on target
            half = 3
            region = {
                "top": max(0, y - half),
                "left": max(0, x - half),
                "width": half * 2 + 1,
                "height": half * 2 + 1,
            }
            sct_img = self._sct.grab(region)
            frame = np.array(sct_img)
            bgr = cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)
            hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)

            # Compute mean + std
            mean_h, std_h = self._circular_mean(hsv[:, :, 0], 180)
            mean_s = int(hsv[:, :, 1].mean())
            mean_v = int(hsv[:, :, 2].mean())
            std_s = int(hsv[:, :, 1].std())
            std_v = int(hsv[:, :, 2].std())

            # Adaptive tolerance: use std, but ensure minimum
            h_tol = max(15, int(std_h) + 10)
            s_tol = max(40, int(std_s) + 30)
            v_tol = max(40, int(std_v) + 30)

            h_low = max(0, int(mean_h) - h_tol)
            h_high = min(179, int(mean_h) + h_tol)
            s_low = max(40, int(mean_s) - s_tol)
            s_high = min(255, int(mean_s) + s_tol)
            v_low = max(40, int(mean_v) - v_tol)
            v_high = min(255, int(mean_v) + v_tol)

            # Handle hue wraparound (red wraps around 0/180)
            if h_low == 0 and h_high == 179:
                calibrated_ranges = [
                    ((0, s_low, v_low), (h_high, s_high, v_high)),
                    ((h_low, s_low, v_low), (179, s_high, v_high)),
                ]
            else:
                calibrated_ranges = [((h_low, s_low, v_low), (h_high, s_high, v_high))]

            with self._lock:
                self.calibrated_hsv_ranges = calibrated_ranges
                self.detection_mode = "calibrate"
            self._log("OK", f"Pipette ({x},{y}): H={int(mean_h)} S={mean_s} V={mean_v} std=({int(std_h)},{std_s},{std_v}) → tol H±{h_tol} S±{s_tol} V±{v_tol}")
            return {
                "ok": True,
                "hsv": [int(mean_h), mean_s, mean_v],
                "std": [int(std_h), std_s, std_v],
                "range": [[h_low, s_low, v_low], [h_high, s_high, v_high]],
            }
        except Exception as e:
            self._log("ERROR", f"Pipette failed: {e}")
            return {"ok": False, "error": str(e)}

    def _circular_mean(self, hue_array: np.ndarray[Any, Any], max_val: int) -> tuple[int, int]:
        """Compute circular mean for hue (which wraps around)."""
        radians = hue_array.astype(float) * (2 * np.pi / max_val)
        mean_rad = np.arctan2(np.sin(radians).mean(), np.cos(radians).mean())
        mean_hue = int((mean_rad * max_val / (2 * np.pi)) % max_val)
        # Std as circular distance
        diffs = np.minimum(np.abs(hue_array - mean_hue), max_val - np.abs(hue_array - mean_hue))
        std_hue = int(diffs.std())
        return mean_hue, std_hue

    # ─── Start/Stop ────────────────────────────────────────────────────────

    def start(self, target_hwnd: int | None = None) -> dict[str, Any]:
        if self.is_running:
            return self.get_status()
        if target_hwnd is not None:
            self.target_hwnd = target_hwnd
        self.is_running = True
        self.last_log = "STARTING"
        self._log("OK", f"Started — mode={self.detection_mode} fov={self.fov_radius} speed={self.aim_speed}")
        threading.Thread(target=self._worker, daemon=True).start()
        return self.get_status()

    def stop(self) -> dict[str, Any]:
        if self.is_running:
            self._log("INFO", "Stopped")
        self.is_running = False
        self.last_log = "STOPPED"
        return self.get_status()

    # ─── Mouse movement (SendInput) ────────────────────────────────────

    def _move_mouse_relative(self, dx: float, dy: float) -> None:
        """Move mouse using SendInput (modern, reliable)."""
        try:
            from app.backend.services.stealth_input import StealthInput
            StealthInput.send_mouse_move(int(dx), int(dy))
        except Exception:
            logger.debug("StealthInput send_mouse_move failed, falling back to mouse_event")
            # Fallback to mouse_event
            user32 = ctypes.windll.user32
            user32.mouse_event(0x0001, int(dx), int(dy), 0, 0)

    # ─── Detection ─────────────────────────────────────────────────────

    def _detect_auto(self, frame_hsv: np.ndarray[Any, Any], brightness_threshold: int,
                     saturation_threshold: int, min_area: int, max_area: int,
                     aspect_ratio_min: float, aspect_ratio_max: float) -> list[tuple[int, int, float]]:
        """Auto: brightness + saturation filter. Finds bright saturated objects.
        Optimized: single bitwise_and, no per-pixel loops."""
        if frame_hsv.shape[2] != 3:
            return []
        v_channel = frame_hsv[:, :, 2]
        s_channel = frame_hsv[:, :, 1]
        # Use numpy vectorized thresholding
        mask = np.where((v_channel >= brightness_threshold) &
                        (s_channel >= saturation_threshold), 255, 0).astype(np.uint8)
        _mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, self._kernel_3x3)
        _mask = cv2.morphologyEx(_mask, cv2.MORPH_CLOSE, self._kernel_3x3)
        contours, _ = cv2.findContours(_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        return self._filter_contours(cast(Sequence[cv2.Mat], contours), frame_hsv, min_area, max_area, aspect_ratio_min, aspect_ratio_max)

    def _detect_color(self, frame_hsv: np.ndarray[Any, Any], color_name: str, brightness_threshold: int,
                      saturation_threshold: int, min_area: int, max_area: int,
                      aspect_ratio_min: float, aspect_ratio_max: float) -> list[tuple[int, int, float]]:
        """Single color HSV detection — uses cached arrays.
        Falls back to adaptive V-threshold for low-contrast scenarios."""
        if frame_hsv.shape[2] != 3:
            return []
        arrays = self._get_hsv_arrays(color_name)
        if not arrays:
            return []
        mask: np.ndarray[Any, Any] = np.zeros(frame_hsv.shape[:2], dtype=np.uint8)
        for lower_arr, upper_arr in arrays:
            mask = cv2.bitwise_or(mask, cv2.inRange(frame_hsv, lower_arr, upper_arr))

        # Check if mask covers too much of the image (bg matches too)
        total_pixels = frame_hsv.shape[0] * frame_hsv.shape[1]
        mask_ratio = mask.sum() / (total_pixels * 255)

        if mask_ratio > 0.5:
            # Background matches too — use adaptive V threshold
            # Find the max V in the masked region
            v_channel = frame_hsv[:, :, 2]
            v_in_mask = cv2.bitwise_and(v_channel, v_channel, mask=mask)
            max_v = int(v_in_mask.max())

            if max_v > brightness_threshold:
                # Re-threshold with V = max_v - 5 (only brightest pixels = target)
                v_thresh = max(0, max_v - 5)
                v_mask = cv2.compare(cast(cv2.Mat, v_channel), np.array(v_thresh, dtype=v_channel.dtype), cv2.CMP_GE)
                mask = cv2.bitwise_and(mask, v_mask)

        _mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, self._kernel_3x3)
        _mask = cv2.morphologyEx(_mask, cv2.MORPH_CLOSE, self._kernel_3x3)
        contours, _ = cv2.findContours(_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        return self._filter_contours(cast(Sequence[cv2.Mat], contours), frame_hsv, min_area, max_area, aspect_ratio_min, aspect_ratio_max)

    def _detect_multi_color(self, frame_hsv: np.ndarray[Any, Any], multi_colors: Sequence[TargetColor],
                            brightness_threshold: int, saturation_threshold: int,
                            min_area: int, max_area: int,
                            aspect_ratio_min: float, aspect_ratio_max: float) -> list[tuple[int, int, float]]:
        """Multi-color detection with adaptive V-threshold fallback."""
        mask: np.ndarray[Any, Any] = np.zeros(frame_hsv.shape[:2], dtype=np.uint8)
        for color_name in multi_colors:
            arrays = self._get_hsv_arrays(color_name)
            for lower_arr, upper_arr in arrays:
                mask = cv2.bitwise_or(mask, cv2.inRange(frame_hsv, lower_arr, upper_arr))

        # Adaptive V threshold if bg matches too
        total_pixels = frame_hsv.shape[0] * frame_hsv.shape[1]
        mask_ratio = mask.sum() / (total_pixels * 255)
        if mask_ratio > 0.5:
            v_channel = frame_hsv[:, :, 2]
            v_in_mask = cv2.bitwise_and(v_channel, v_channel, mask=mask)
            max_v = int(v_in_mask.max())
            if max_v > brightness_threshold:
                v_thresh = max(0, max_v - 5)
                v_mask = cv2.compare(cast(cv2.Mat, v_channel), np.array(v_thresh, dtype=v_channel.dtype), cv2.CMP_GE)
                mask = cv2.bitwise_and(mask, v_mask)

        _mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, self._kernel_3x3)
        _mask = cv2.morphologyEx(_mask, cv2.MORPH_CLOSE, self._kernel_3x3)
        contours, _ = cv2.findContours(_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        return self._filter_contours(cast(Sequence[cv2.Mat], contours), frame_hsv, min_area, max_area, aspect_ratio_min, aspect_ratio_max)

    def _detect_calibrated(self, frame_hsv: np.ndarray[Any, Any], calibrated_hsv_ranges: list[tuple[tuple[int, int, int], tuple[int, int, int]]],
                           brightness_threshold: int, saturation_threshold: int,
                           min_area: int, max_area: int,
                           aspect_ratio_min: float, aspect_ratio_max: float) -> list[tuple[int, int, float]]:
        if not calibrated_hsv_ranges:
            return []
        mask: np.ndarray[Any, Any] = np.zeros(frame_hsv.shape[:2], dtype=np.uint8)
        for lower, upper in calibrated_hsv_ranges:
            mask = cv2.bitwise_or(mask, cv2.inRange(frame_hsv, np.array(lower), np.array(upper)))

        # Adaptive V threshold if bg matches too
        total_pixels = frame_hsv.shape[0] * frame_hsv.shape[1]
        mask_ratio = mask.sum() / (total_pixels * 255)
        if mask_ratio > 0.5:
            v_channel = frame_hsv[:, :, 2]
            v_in_mask = cv2.bitwise_and(v_channel, v_channel, mask=mask)
            max_v = int(v_in_mask.max())
            if max_v > brightness_threshold:
                v_thresh = max(0, max_v - 5)
                v_mask = cv2.compare(cast(cv2.Mat, v_channel), np.array(v_thresh, dtype=v_channel.dtype), cv2.CMP_GE)
                mask = cv2.bitwise_and(mask, v_mask)

        _mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, self._kernel_3x3)
        _mask = cv2.morphologyEx(_mask, cv2.MORPH_CLOSE, self._kernel_3x3)
        contours, _ = cv2.findContours(_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        return self._filter_contours(cast(Sequence[cv2.Mat], contours), frame_hsv, min_area, max_area, aspect_ratio_min, aspect_ratio_max)

    def _detect_circles(self, frame: np.ndarray[Any, Any], frame_hsv: np.ndarray[Any, Any],
                        min_area: int, max_area: int,
                        brightness_threshold: int, saturation_threshold: int) -> list[tuple[int, int, float]]:
        gray = cv2.cvtColor(frame, cv2.COLOR_BGRA2GRAY)
        gray = cv2.GaussianBlur(gray, (9, 9), 2)
        circles = cv2.HoughCircles(
            gray, cv2.HOUGH_GRADIENT, dp=1.2, minDist=30,
            param1=50, param2=30, minRadius=5, maxRadius=100
        )
        targets: list[tuple[int, int, float]] = []
        if circles is not None:
            circles = np.round(circles[0, :]).astype("int")
            for (x, y, r) in circles:
                y_c = max(0, min(frame_hsv.shape[0] - 1, y))
                x_c = max(0, min(frame_hsv.shape[1] - 1, x))
                pixel = frame_hsv[y_c, x_c]
                v_val = int(pixel[2])
                s_val = int(pixel[1])
                if v_val < brightness_threshold or s_val < saturation_threshold:
                    continue
                area = 3.14159 * r * r
                if area < min_area or area > max_area:
                    continue
                targets.append((x, y, area))
        return targets

    def _filter_contours(self, contours: Sequence[cv2.Mat], frame_hsv: np.ndarray[Any, Any],
                         min_area: int, max_area: int,
                         aspect_ratio_min: float, aspect_ratio_max: float) -> list[tuple[int, int, float]]:
        filtered: list[tuple[int, int, float]] = []
        for cnt in contours:
            area = cv2.contourArea(cnt)
            if area < min_area or area > max_area:
                continue
            x, y, w, h = cv2.boundingRect(cnt)
            if w == 0 or h == 0:
                continue
            aspect = max(w, h) / min(w, h)
            if aspect < aspect_ratio_min or aspect > aspect_ratio_max:
                continue
            M = cv2.moments(cnt)
            if M["m00"] == 0:
                continue
            cx = int(M["m10"] / M["m00"])
            cy = int(M["m01"] / M["m00"])
            filtered.append((cx, cy, area))
        return filtered

    def _find_nearest(self, targets: list[tuple[int, int, float]], cx: int, cy: int) -> tuple[int, int, float, float] | None:
        if not targets:
            return None
        nearest: tuple[int, int, float, float] | None = None
        min_dist = float('inf')
        for tx, ty, score in targets:
            d = ((tx - cx) ** 2 + (ty - cy) ** 2) ** 0.5
            if d < min_dist:
                min_dist = d
                nearest = (tx, ty, score, d)
        return nearest

    # ─── Debug screenshots ─────────────────────────────────────────────

    def _save_debug_screenshot(self, frame: np.ndarray[Any, Any], targets: list[tuple[int, int, float]],
                               nearest: tuple[int, int, float, float] | None,
                               region_offset: tuple[int, int], detection_mode: str) -> None:
        if not self.debug_screenshots:
            return
        try:
            debug_dir = "screenshots/debug"
            os.makedirs(debug_dir, exist_ok=True)
            # Convert BGRA to BGR for drawing
            debug_img = cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)
            # Draw all targets (green)
            for tx, ty, _ in targets:
                cv2.circle(debug_img, (tx, ty), 10, (0, 255, 0), 2)
            # Draw nearest target (red)
            if nearest:
                nx, ny = nearest[0], nearest[1]
                cv2.circle(debug_img, (nx, ny), 15, (0, 0, 255), 3)
                cv2.line(debug_img, (nx - 20, ny), (nx + 20, ny), (0, 0, 255), 2)
                cv2.line(debug_img, (nx, ny - 20), (nx, ny + 20), (0, 0, 255), 2)
            # Draw center crosshair (yellow)
            cx, cy = frame.shape[1] // 2, frame.shape[0] // 2
            cv2.line(debug_img, (cx - 15, cy), (cx + 15, cy), (0, 255, 255), 2)
            cv2.line(debug_img, (cx, cy - 15), (cx, cy + 15), (0, 255, 255), 2)
            # Add text
            cv2.putText(debug_img, f"Targets: {len(targets)} Mode: {detection_mode}",
                        (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)
            # Save (keep only last 10)
            self.debug_frame_count += 1
            path = os.path.join(debug_dir, f"aim_debug_{self.debug_frame_count:04d}.png")
            cv2.imwrite(path, debug_img)
            # Cleanup old files
            files = sorted(os.listdir(debug_dir))
            if len(files) > 10:
                for old in files[:-10]:
                    os.remove(os.path.join(debug_dir, old))
        except Exception:
            logger.debug("Failed to clean up debug frames")

    # ─── Worker ────────────────────────────────────────────────────────

    def _worker(self) -> None:
        with self._lock:
            init_mode = self.detection_mode
            init_fov = self.fov_radius
        self._log("INFO", f"Worker started — mode={init_mode} fov={init_fov}")
        self._sct = mss.mss()
        sw, sh, sx, sy = self._get_screen_size()

        # Determine capture region:
        # - If scan_region is set (custom), use it
        # - Otherwise, capture FOV box around screen center
        with self._lock:
            scan_region = dict(self.scan_region) if self.scan_region is not None else None
            fov_radius = self.fov_radius

        if scan_region is not None:
            region = dict(scan_region)
        else:
            cx_screen = sx + sw // 2
            cy_screen = sy + sh // 2
            r = fov_radius
            region = {
                "top": max(sy, cy_screen - r),
                "left": max(sx, cx_screen - r),
                "width": min(r * 2, sw),
                "height": min(r * 2, sh),
            }
        self._log("INFO", f"Capture region: {region['width']}x{region['height']} at ({region['left']},{region['top']})")

        frame_count = 0
        last_log = time.time()
        last_debug = time.time()

        try:
            while True:
                # Check running state under lock, snapshot config
                with self._lock:
                    running = self.is_running
                    if not running:
                        break
                    # Snapshot all config for this iteration
                    detection_mode = self.detection_mode
                    target_color = self.target_color
                    multi_colors = list(self.multi_colors)
                    calibrated_hsv_ranges = list(self.calibrated_hsv_ranges)
                    min_area = self.min_area
                    max_area = self.max_area
                    aspect_ratio_min = self.aspect_ratio_min
                    aspect_ratio_max = self.aspect_ratio_max
                    brightness_threshold = self.brightness_threshold
                    saturation_threshold = self.saturation_threshold
                    prediction_factor = self.prediction_factor
                    aim_speed = self.aim_speed
                    smooth_steps = self.smooth_steps
                    reset_delay = self.reset_delay
                    last_target_pos = self.last_target_pos

                # Capture
                sct_img = self._sct.grab(region)
                frame = np.array(sct_img)
                bgr = cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)
                frame_hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)

                # Center of capture region
                cx = frame.shape[1] // 2
                cy = frame.shape[0] // 2

                # Detect using snapshot config
                if detection_mode == "auto":
                    targets = self._detect_auto(frame_hsv, brightness_threshold, saturation_threshold, min_area, max_area, aspect_ratio_min, aspect_ratio_max)
                elif detection_mode == "multi":
                    targets = self._detect_multi_color(frame_hsv, multi_colors, brightness_threshold, saturation_threshold, min_area, max_area, aspect_ratio_min, aspect_ratio_max)
                elif detection_mode == "circles":
                    targets = self._detect_circles(frame, frame_hsv, min_area, max_area, brightness_threshold, saturation_threshold)
                elif detection_mode == "calibrate":
                    targets = self._detect_calibrated(frame_hsv, calibrated_hsv_ranges, brightness_threshold, saturation_threshold, min_area, max_area, aspect_ratio_min, aspect_ratio_max)
                else:
                    targets = self._detect_color(frame_hsv, target_color, brightness_threshold, saturation_threshold, min_area, max_area, aspect_ratio_min, aspect_ratio_max)

                frame_count += 1

                # Find nearest
                nearest = self._find_nearest(targets, cx, cy)

                # Move mouse
                if nearest:
                    tx, ty, score, dist = nearest
                    dx = tx - cx
                    dy = ty - cy

                    # Predictive aim: estimate where target will be next frame
                    if prediction_factor > 0 and last_target_pos:
                        last_tx, last_ty, last_time = last_target_pos
                        dt = time.time() - last_time
                        if dt > 0 and dt < 0.5:  # only predict if recent
                            vx = (tx - last_tx) / dt  # px/sec
                            vy = (ty - last_ty) / dt
                            # Predict where target will be in ~50ms (next frame)
                            pred_x = tx + vx * 0.05 * prediction_factor
                            pred_y = ty + vy * 0.05 * prediction_factor
                            dx = int(pred_x - cx)
                            dy = int(pred_y - cy)

                    with self._lock:
                        self.last_target_pos = (tx, ty, time.time())

                    move_dx = int(dx * aim_speed)
                    move_dy = int(dy * aim_speed)

                    # Skip tiny movements (avoid jitter)
                    if abs(move_dx) < 1 and abs(move_dy) < 1:
                        time.sleep(reset_delay)
                        continue

                    if smooth_steps > 1:
                        step_dx = move_dx / smooth_steps
                        step_dy = move_dy / smooth_steps
                        for i in range(smooth_steps):
                            with self._lock:
                                if not self.is_running:
                                    break
                            self._move_mouse_relative(int(step_dx), int(step_dy))
                            time.sleep(0.001)
                    else:
                        self._move_mouse_relative(move_dx, move_dy)

                # Log every 0.5s
                now = time.time()
                if now - last_log > 0.5:
                    with self._lock:
                        self.last_log = f"TRACK {len(targets)} targets, nearest dist={int(nearest[3]) if nearest else 0}"
                    if targets:
                        self._log("OK", f"{len(targets)} targets, nearest: dx={nearest[0]-cx} dy={nearest[1]-cy} dist={int(nearest[3])}") if targets and nearest is not None else None
                    else:
                        with self._lock:
                            self.last_log = "SCANNING"
                        self._log("INFO", f"No targets ({frame_count} frames)")
                    last_log = now

                # Debug screenshot every 1s
                if now - last_debug > 1.0:
                    self._save_debug_screenshot(frame, targets, nearest, (region["left"], region["top"]), detection_mode)
                    last_debug = now

                time.sleep(reset_delay)

        except Exception as e:
            with self._lock:
                self.last_log = f"ERR {e}"
            self._log("ERROR", f"Worker: {e}")
        finally:
            with self._lock:
                self.is_running = False
            self._log("INFO", "Worker ended")

    def get_status(self) -> dict[str, Any]:
        with self._lock:
            return {
                "ok": True,
                "is_running": self.is_running,
                "confidence": self.confidence,
                "smooth_steps": self.smooth_steps,
                "reset_delay": self.reset_delay,
                "scan_region": self.scan_region,
                "last_log": self.last_log,
                "background_method": self.background_method,
                "detection_mode": self.detection_mode,
                "target_color": self.target_color,
                "fov_radius": self.fov_radius,
                "aim_speed": self.aim_speed,
                "min_area": self.min_area,
                "max_area": self.max_area,
                "aspect_ratio_min": self.aspect_ratio_min,
                "aspect_ratio_max": self.aspect_ratio_max,
                "brightness_threshold": self.brightness_threshold,
                "saturation_threshold": self.saturation_threshold,
                "prediction_factor": self.prediction_factor,
            }

    def set_background_method(self, method: BackgroundMethod) -> dict[str, Any]:
        valid: tuple[BackgroundMethod, ...] = ("sendinput", "postmessage", "vigem", "pico")
        if method in valid:
            with self._lock:
                self.background_method = method
            return {"ok": True, "background_method": method}
        return {"ok": False, "error": "Invalid"}
