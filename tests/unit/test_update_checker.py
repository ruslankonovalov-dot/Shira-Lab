"""Unit tests for app.backend.services.update_checker module."""

import urllib.error
from unittest.mock import MagicMock, patch

import pytest

from app.backend.services.update_checker import (_compare_versions,
                                                 check_for_updates,
                                                 check_for_updates_async)

pytestmark = pytest.mark.unit


class TestCompareVersions:
    def test_equal_versions(self):
        assert _compare_versions("1.0.0", "1.0.0") == 0

    def test_newer_version(self):
        assert _compare_versions("1.1.0", "1.0.0") == 1

    def test_older_version(self):
        assert _compare_versions("1.0.0", "1.1.0") == -1

    def test_major_version_difference(self):
        assert _compare_versions("2.0.0", "1.9.9") == 1

    def test_different_lengths(self):
        assert _compare_versions("1.0", "1.0.0") == 0  # padding with zeros

    def test_with_prerelease_suffix(self):
        # Should ignore -rc1, -beta etc and compare digits
        assert _compare_versions("1.0.0-rc1", "1.0.0") == 0

    def test_three_parts(self):
        assert _compare_versions("0.16.0", "0.15.9") == 1
        assert _compare_versions("0.16.0", "0.16.0") == 0
        assert _compare_versions("0.15.0", "0.16.0") == -1


class TestCheckForUpdates:
    def test_returns_error_on_network_failure(self):
        with patch("urllib.request.urlopen", side_effect=urllib.error.URLError("Network error")):
            result = check_for_updates("0.16.0")
            assert result["ok"] is False
            assert "error" in result

    def test_returns_update_available_when_newer(self):
        mock_response = MagicMock()
        mock_response.read.return_value = b'{"tag_name": "v0.17.0", "html_url": "https://github.com/shira/shira-lab/releases/v0.17.0", "body": "Bug fixes", "assets": []}'
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)

        with patch("urllib.request.urlopen", return_value=mock_response):
            result = check_for_updates("0.16.0")
            assert result["ok"] is True
            assert result["update_available"] is True
            assert result["latest_version"] == "0.17.0"
            assert result["current_version"] == "0.16.0"

    def test_returns_no_update_when_same(self):
        mock_response = MagicMock()
        mock_response.read.return_value = b'{"tag_name": "v0.16.0", "html_url": "https://github.com/shira/shira-lab/releases/v0.16.0", "body": "", "assets": []}'
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)

        with patch("urllib.request.urlopen", return_value=mock_response):
            result = check_for_updates("0.16.0")
            assert result["ok"] is True
            assert result["update_available"] is False

    def test_returns_no_update_when_older(self):
        mock_response = MagicMock()
        mock_response.read.return_value = (
            b'{"tag_name": "v0.15.0", "html_url": "", "body": "", "assets": []}'
        )
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)

        with patch("urllib.request.urlopen", return_value=mock_response):
            result = check_for_updates("0.16.0")
            assert result["ok"] is True
            assert result["update_available"] is False

    def test_finds_exe_download_url(self):
        mock_response = MagicMock()
        mock_response.read.return_value = b'{"tag_name": "v0.17.0", "html_url": "", "body": "", "assets": [{"name": "ShiraLab.exe", "browser_download_url": "https://github.com/shira/shira-lab/releases/download/v0.17.0/ShiraLab.exe"}]}'
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)

        with patch("urllib.request.urlopen", return_value=mock_response):
            result = check_for_updates("0.16.0")
            assert result["ok"] is True
            assert (
                result["download_url"]
                == "https://github.com/shira/shira-lab/releases/download/v0.17.0/ShiraLab.exe"
            )

    def test_handles_invalid_response(self):
        mock_response = MagicMock()
        mock_response.read.return_value = b'{"foo": "bar"}'
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)

        with patch("urllib.request.urlopen", return_value=mock_response):
            result = check_for_updates("0.16.0")
            assert result["ok"] is False


class TestAsyncUpdateChecker:
    def test_async_calls_callback(self):
        """Async checker should call callback with JSON result."""
        mock_response = MagicMock()
        mock_response.read.return_value = (
            b'{"tag_name": "v0.17.0", "html_url": "", "body": "", "assets": []}'
        )
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)

        received = []

        def callback(result_json):
            received.append(result_json)

        with patch("urllib.request.urlopen", return_value=mock_response):
            check_for_updates_async("0.16.0", callback)
            # Wait a bit for the thread to complete
            import time

            time.sleep(0.5)

        assert len(received) == 1
        assert "ok" in received[0]
