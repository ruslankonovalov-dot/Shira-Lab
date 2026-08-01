"""Unit tests for app.backend.services.theme_detector module."""

import sys
from unittest.mock import MagicMock, patch

import pytest

from app.backend.services.theme_detector import (
    DARK_PALETTE,
    LIGHT_PALETTE,
    detect_windows_theme,
    get_palette_for_theme,
)

pytestmark = pytest.mark.unit


# Skip winreg tests on non-Windows
winreg = pytest.importorskip("winreg") if sys.platform == "win32" else None


class TestDetectWindowsTheme:

    def test_returns_dark_on_non_windows(self):
        with patch("platform.system", return_value="Linux"):
            assert detect_windows_theme() == "dark"

    def test_returns_dark_on_macos(self):
        with patch("platform.system", return_value="Darwin"):
            assert detect_windows_theme() == "dark"

    @pytest.mark.skipif(sys.platform != "win32", reason="requires Windows winreg")
    def test_returns_light_when_registry_says_so(self):
        with patch("platform.system", return_value="Windows"):
            with patch("winreg.OpenKey") as mock_open:
                mock_open.return_value.__enter__.return_value = MagicMock()
                with patch("winreg.QueryValueEx", return_value=(1, None)):
                    with patch("winreg.CloseKey"):
                        assert detect_windows_theme() == "light"

    @pytest.mark.skipif(sys.platform != "win32", reason="requires Windows winreg")
    def test_returns_dark_when_registry_says_so(self):
        with patch("platform.system", return_value="Windows"):
            with patch("winreg.OpenKey") as mock_open:
                mock_open.return_value.__enter__.return_value = MagicMock()
                with patch("winreg.QueryValueEx", return_value=(0, None)):
                    with patch("winreg.CloseKey"):
                        assert detect_windows_theme() == "dark"

    @pytest.mark.skipif(sys.platform != "win32", reason="requires Windows winreg")
    def test_returns_dark_when_key_not_found(self):
        with patch("platform.system", return_value="Windows"):
            with patch("winreg.OpenKey", side_effect=FileNotFoundError):
                assert detect_windows_theme() == "dark"


class TestPalettes:

    def test_dark_palette_has_matrix(self):
        assert "matrix" in DARK_PALETTE
        assert "bg" in DARK_PALETTE["matrix"]
        assert "fg" in DARK_PALETTE["matrix"]

    def test_light_palette_has_matrix(self):
        assert "matrix" in LIGHT_PALETTE
        assert "bg" in LIGHT_PALETTE["matrix"]
        assert "fg" in LIGHT_PALETTE["matrix"]

    def test_dark_palette_has_multiple_themes(self):
        assert "cyberpunk" in DARK_PALETTE
        assert "amber" in DARK_PALETTE

    def test_light_palette_has_multiple_themes(self):
        assert "cyberpunk" in LIGHT_PALETTE
        assert "amber" in LIGHT_PALETTE

    def test_get_palette_for_dark_theme(self):
        p = get_palette_for_theme("dark", "matrix")
        assert p == DARK_PALETTE["matrix"]

    def test_get_palette_for_light_theme(self):
        p = get_palette_for_theme("light", "matrix")
        assert p == LIGHT_PALETTE["matrix"]

    def test_get_palette_falls_back_to_matrix(self):
        p = get_palette_for_theme("dark", "nonexistent")
        assert p == DARK_PALETTE["matrix"]
