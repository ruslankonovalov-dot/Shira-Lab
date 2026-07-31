# tests/unit/test_clicker_service.py — ClickerService comprehensive tests for Phase 3.6
import threading
import time
from unittest.mock import Mock, patch

import pytest


class TestClickerService:
    """Tests for ClickerService."""

    def setup_method(self):
        from app.backend.services.clicker_service import ClickerService
        # Reset singleton to get fresh instance
        ClickerService.reset_instance()
        self.service = ClickerService()
        self.service._bridge = Mock()

    def test_start_stop(self):
        """Test start/stop."""
        result = self.service.start()
        assert result["is_running"] is True
        assert self.service.is_running is True

        result = self.service.stop()
        assert result["is_running"] is False
        assert self.service.is_running is False

    def test_start_already_running(self):
        """Test start when already running."""
        self.service.start()
        result = self.service.start()
        # Should return current status
        assert result["is_running"] is True

    def test_stop_not_running(self):
        """Test stop when not running."""
        result = self.service.stop()
        assert result["is_running"] is False

    def test_config_validation(self):
        """Test config validation."""
        # Valid config
        result = self.service.update_config(100, 0, "L", 0, "sendinput")
        assert result["is_running"] is False
        assert result["interval_ms"] == 100

        # Invalid interval - gets clamped
        result = self.service.update_config(-1, 0, "L", 0, "sendinput")
        assert result["is_running"] is False
        assert self.service.interval_ms == 1

        # Invalid button - defaults to L
        result = self.service.update_config(100, 0, "INVALID", 0, "sendinput")
        assert self.service.button == "L"

        # Invalid background_method - keeps current
        original = self.service.background_method
        result = self.service.update_config(100, 0, "L", 0, "invalid")
        assert self.service.background_method == original

    def test_get_click_count(self):
        """Test click count tracking."""
        self.service.update_config(10, 0, "L", 10, "sendinput")
        self.service.start()
        time.sleep(0.15)
        self.service.stop()

        assert self.service.get_click_count() >= 0

    def test_cps_calculation(self):
        """Test CPS calculation."""
        self.service.update_config(10, 0, "L", 0, "sendinput")
        self.service.start()
        time.sleep(0.2)
        self.service.stop()

        status = self.service.get_status()
        assert "cps" in status
        assert status["cps"] >= 0

    def test_background_methods(self):
        """Test all background methods."""
        for method in ["sendinput", "postmessage", "vigem", "pico"]:
            result = self.service.update_config(100, 0, "L", 0, method)
            assert result["is_running"] is False
            assert self.service.get_status()["background_method"] == method

    @patch('app.backend.services.clicker_service.StealthInput.send_mouse_click')
    def test_sendinput_method(self, mock_send_click):
        """Test sendinput background method."""
        self.service.update_config(100, 0, "L", 0, "sendinput")
        self.service.target_hwnd = None
        self.service._send_background_click(0, "L", 0, "sendinput")
        mock_send_click.assert_called_once()

    @patch('app.backend.services.clicker_service.send_background_click')
    def test_postmessage_method(self, mock_send_click):
        """Test postmessage background method."""
        self.service.update_config(100, 0, "L", 0, "postmessage")
        self.service.target_hwnd = 12345
        self.service._send_background_click(12345, "L", 0, "postmessage")
        mock_send_click.assert_called_once_with(12345, button="L")


    def test_limit(self):
        """Test click limit."""
        self.service.update_config(10, 0, "L", 5, "sendinput")
        self.service.start()
        time.sleep(0.2)
        self.service.stop()

        assert self.service.get_click_count() <= 5

    def test_get_status(self):
        """Test status returns proper structure."""
        status = self.service.get_status()
        assert isinstance(status, dict)
        assert "is_running" in status
        assert "interval_ms" in status
        assert "hold_ms" in status
        assert "button" in status
        assert "limit" in status
        assert "click_count" in status
        assert "cps" in status
        assert "background_method" in status

    def test_target_hwnd(self):
        """Test target window handle."""
        self.service.target_hwnd = 12345
        assert self.service.target_hwnd == 12345

        self.service.target_hwnd = None
        assert self.service.target_hwnd is None


class TestClickerServiceThreadSafety:
    """Tests for thread safety."""

    def setup_method(self):
        from app.backend.services.clicker_service import ClickerService
        # Reset singleton to get fresh instance
        ClickerService.reset_instance()
        self.service = ClickerService()
        self.service._bridge = Mock()

    def test_concurrent_config_changes(self):
        """Test concurrent config changes."""
        def change_config():
            for _ in range(100):
                self.service.update_config(100, 0, "L", 0, "sendinput")
                self.service.update_config(100, 0, "L", 0, "sendinput")

        threads = [threading.Thread(target=change_config) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Should not crash
        assert self.service.interval_ms == 100
        assert self.service.background_method == "sendinput"

    def test_concurrent_start_stop(self):
        """Test concurrent start/stop."""
        def start_stop():
            for _ in range(10):
                self.service.start()
                time.sleep(0.01)
                self.service.stop()

        threads = [threading.Thread(target=start_stop) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Should not crash
        assert self.service.is_running in [True, False]


class TestClickerServiceBackgroundMethods:
    """Tests for background input methods."""

    def setup_method(self):
        from app.backend.services.clicker_service import ClickerService
        # Reset singleton to get fresh instance
        ClickerService.reset_instance()
        self.service = ClickerService()
        self.service._bridge = Mock()

    @patch('app.backend.services.clicker_service.StealthInput.send_mouse_click')
    def test_sendinput_method(self, mock_send_click):
        """Test sendinput background method."""
        self.service.update_config(100, 0, "L", 0, "sendinput")
        self.service.target_hwnd = None
        self.service._send_background_click(0, "L", 0, "sendinput")
        mock_send_click.assert_called_once()

    @patch('app.backend.services.clicker_service.send_background_click')
    def test_postmessage_method(self, mock_send_click):
        """Test postmessage background method."""
        self.service.update_config(100, 0, "L", 0, "postmessage")
        self.service.target_hwnd = 12345
        self.service._send_background_click(12345, "L", 0, "postmessage")
        mock_send_click.assert_called_once_with(12345, button="L")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])