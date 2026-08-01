# tests/unit/test_aim_service.py — AimService comprehensive tests for Phase 3.6
import threading
from unittest.mock import Mock, patch

import numpy as np
import pytest


class TestAimService:
    """Tests for AimService."""

    def setup_method(self):
        from app.backend.services.aim_service import AimService

        self.service = AimService()
        self.service._bridge = Mock()

    def test_detection_modes(self):
        """Test all detection modes."""
        for mode in ["auto", "multi", "circles", "color", "calibrate"]:
            result = self.service.set_detection_mode(mode)
            assert result["ok"] is True
            assert self.service.get_status()["detection_mode"] == mode

    def test_invalid_detection_mode(self):
        """Test invalid detection mode."""
        result = self.service.set_detection_mode("invalid")
        assert result["ok"] is False

    def test_target_colors(self):
        """Test all target colors."""
        for color in [
            "red",
            "blue",
            "green",
            "purple",
            "yellow",
            "cyan",
            "orange",
            "pink",
        ]:
            result = self.service.set_target_color(color)
            assert result["ok"] is True
            assert self.service.get_status()["target_color"] == color

    def test_invalid_target_color(self):
        """Test invalid target color."""
        result = self.service.set_target_color("invalid")
        assert result["ok"] is False

    def test_config(self):
        """Test full config update."""
        result = self.service.update_config(
            confidence=0.5, smooth_steps=5, reset_delay=0.005
        )
        assert result["ok"] is True

        # Check individual setters
        result = self.service.set_fov(500)
        assert result["ok"] is True
        assert self.service.get_status()["fov_radius"] == 500

        result = self.service.set_aim_speed(0.8)
        assert result["ok"] is True
        assert self.service.get_status()["aim_speed"] == 0.8

    def test_config_validation(self):
        """Test config bounds validation."""
        # FOV bounds
        self.service.set_fov(10)
        assert self.service.get_status()["fov_radius"] == 50  # Min

        self.service.set_fov(2000)
        assert self.service.get_status()["fov_radius"] == 1000  # Max

        # Speed bounds
        self.service.set_aim_speed(0.01)
        assert self.service.get_status()["aim_speed"] == 0.05  # Min

        self.service.set_aim_speed(2.0)
        assert self.service.get_status()["aim_speed"] == 1.0  # Max

    def test_filters(self):
        """Test filter config."""
        result = self.service.set_filters(
            min_area=10,
            max_area=10000,
            aspect_min=0.2,
            aspect_max=3.0,
            brightness=100,
            saturation=60,
        )
        assert result["ok"] is True

        status = self.service.get_status()
        assert status["min_area"] == 10
        assert status["max_area"] == 10000
        assert status["aspect_ratio_min"] == 0.2
        assert status["aspect_ratio_max"] == 3.0
        assert status["brightness_threshold"] == 100
        assert status["saturation_threshold"] == 60

    def test_start_stop(self):
        """Test start/stop."""
        result = self.service.start()
        assert result["ok"] is True
        assert self.service.is_running is True

        result = self.service.stop()
        assert result["ok"] is True
        assert self.service.is_running is False

    def test_get_status(self):
        """Test status returns proper structure."""
        status = self.service.get_status()
        assert isinstance(status, dict)
        assert "is_running" in status
        assert "confidence" in status
        assert "smooth_steps" in status
        assert "reset_delay" in status
        assert "last_log" in status
        assert "background_method" in status
        assert "detection_mode" in status
        assert "target_color" in status
        assert "fov_radius" in status
        assert "aim_speed" in status
        assert "min_area" in status
        assert "max_area" in status
        assert "brightness_threshold" in status
        assert "saturation_threshold" in status
        assert "prediction_factor" in status

    def test_background_method(self):
        """Test background method setting."""
        for method in ["sendinput", "postmessage", "vigem", "pico"]:
            result = self.service.set_background_method(method)
            assert result["ok"] is True
            assert self.service.get_status()["background_method"] == method

    def test_invalid_background_method(self):
        """Test invalid background method."""
        result = self.service.set_background_method("invalid")
        assert result["ok"] is False


class TestAimServiceCalibration:
    """Tests for aim calibration (pipette)."""

    def setup_method(self):
        from app.backend.services.aim_service import AimService

        self.service = AimService()
        self.service._bridge = Mock()

    @patch("app.backend.services.aim_service.mss.mss")
    def test_sample_color(self, mock_mss):
        """Test color sampling."""
        # Mock mss grab
        mock_sct = Mock()
        # Create a 7x7 red image
        img = np.zeros((7, 7, 4), dtype=np.uint8)
        img[:, :, 2] = 255  # Red channel
        img[:, :, 3] = 255  # Alpha
        mock_sct.grab.return_value = img
        mock_mss.return_value = mock_sct

        self.service._sct = mock_mss()

        result = self.service.sample_color_at(100, 100)
        assert result["ok"] is True
        assert "hsv" in result
        assert "std" in result
        assert "range" in result
        assert self.service.get_status()["detection_mode"] == "calibrate"
        assert len(self.service.calibrated_hsv_ranges) > 0

    @patch("app.backend.services.aim_service.mss.mss")
    def test_sample_color_out_of_bounds(self, mock_mss):
        """Test sampling out of bounds."""
        result = self.service.sample_color_at(-1, -1)
        assert result["ok"] is False
        assert "out of screen bounds" in result["error"]


class TestAimServiceDetection:
    """Tests for detection algorithms."""

    def setup_method(self):
        from app.backend.services.aim_service import AimService

        self.service = AimService()
        self.service._bridge = Mock()

    def test_circular_mean(self):
        """Test circular mean for hue."""
        # Test with hues that wrap around
        hues = np.array([175, 178, 179, 0, 2, 5], dtype=np.uint8)
        mean, std = self.service._circular_mean(hues, 180)

        # Mean should be near 0/180 boundary
        assert 0 <= mean <= 180
        assert std >= 0

    def test_filter_contours(self):
        """Test contour filtering."""
        # Create test contours
        contours = []
        # Large contour (should pass)
        contour1 = np.array(
            [[[0, 0]], [[100, 0]], [[100, 100]], [[0, 100]]], dtype=np.int32
        )
        contours.append(contour1)

        # Small contour (should fail min_area)
        contour2 = np.array([[[0, 0]], [[5, 0]], [[5, 5]], [[0, 5]]], dtype=np.int32)
        contours.append(contour2)

        frame_hsv = np.zeros((200, 200, 3), dtype=np.uint8)
        filtered = self.service._filter_contours(
            contours,
            frame_hsv,
            min_area=50,
            max_area=50000,
            aspect_ratio_min=0.3,
            aspect_ratio_max=2.0,
        )

        assert len(filtered) == 1
        assert filtered[0][2] == 10000  # Area of large contour


class TestAimServiceScanRegion:
    """Tests for scan region configuration."""

    def setup_method(self):
        from app.backend.services.aim_service import AimService

        self.service = AimService()
        self.service._bridge = Mock()

    def test_set_scan_region(self):
        """Test setting custom scan region."""
        result = self.service.set_scan_region(100, 100, 500, 500)
        assert result["ok"] is True
        assert self.service.scan_region is not None
        assert self.service.scan_region["top"] == 100
        assert self.service.scan_region["left"] == 100
        assert self.service.scan_region["width"] == 500
        assert self.service.scan_region["height"] == 500

    def test_reset_scan_region(self):
        """Test resetting scan region with zeros."""
        self.service.set_scan_region(100, 100, 500, 500)
        result = self.service.set_scan_region(0, 0, 0, 0)
        assert result["ok"] is True
        assert self.service.scan_region is None


class TestAimServiceThreadSafety:
    """Tests for thread safety."""

    def setup_method(self):
        from app.backend.services.aim_service import AimService

        self.service = AimService()
        self.service._bridge = Mock()

    def test_concurrent_config_changes(self):
        """Test concurrent config changes."""

        def change_config():
            for _ in range(100):
                self.service.update_config(0.5, 5, 0.005)
                self.service.set_fov(400)
                self.service.set_target_color("red")

        threads = [threading.Thread(target=change_config) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Should not crash
        assert self.service.get_status()["fov_radius"] == 400
        assert self.service.get_status()["target_color"] == "red"


class TestAimServiceHSVPresets:
    """Tests for HSV color presets."""

    def setup_method(self):
        from app.backend.services.aim_service import AimService

        self.service = AimService()

    def test_hsv_presets_exist(self):
        """Test all expected colors have presets."""
        expected_colors = [
            "red",
            "blue",
            "green",
            "purple",
            "yellow",
            "cyan",
            "orange",
            "pink",
        ]
        for color in expected_colors:
            assert color in self.service.HSV_PRESETS
            assert len(self.service.HSV_PRESETS[color]) > 0

    def test_get_hsv_arrays_cached(self):
        """Test HSV arrays are cached."""
        arrays1 = self.service._get_hsv_arrays("red")
        arrays2 = self.service._get_hsv_arrays("red")
        assert arrays1 is arrays2  # Same object due to caching


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
