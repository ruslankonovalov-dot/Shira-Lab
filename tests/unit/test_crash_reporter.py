"""Unit tests for app.backend.services.crash_reporter module."""
import json
from unittest.mock import patch

import pytest

from app.backend.services import crash_reporter

pytestmark = pytest.mark.unit


class TestCrashReportBuilding:

    def test_build_report_contains_required_fields(self):
        try:
            raise ValueError("Test exception")
        except ValueError as e:
            import sys
            tb = sys.exc_info()[2]
            report = crash_reporter._build_report(
                type(e), e, tb, "1.0.0"
            )

        assert "timestamp" in report
        assert "app_version" in report
        assert report["app_version"] == "1.0.0"
        assert "python_version" in report
        assert "platform" in report
        assert "exception_type" in report
        assert report["exception_type"] == "ValueError"
        assert "exception_message" in report
        assert "Test exception" in report["exception_message"]
        assert "traceback" in report
        assert "ValueError" in report["traceback"]
        assert "Test exception" in report["traceback"]


class TestLocalCrashStorage:

    def test_save_local_creates_file(self, tmp_path, monkeypatch):
        # Patch CRASH_LOG_DIR to tmp_path
        monkeypatch.setattr(crash_reporter, "CRASH_LOG_DIR", tmp_path)

        report = {
            "timestamp": "2025-01-01T00:00:00",
            "app_version": "1.0.0",
            "python_version": "3.12.0",
            "platform": "Windows",
            "machine": "x86_64",
            "processor": "Intel",
            "exception_type": "ValueError",
            "exception_message": "Test",
            "traceback": "Traceback...",
        }

        path = crash_reporter._save_local(report)
        assert path.exists()
        loaded = json.loads(path.read_text(encoding="utf-8"))
        assert loaded["exception_type"] == "ValueError"

    def test_list_local_crashes(self, tmp_path, monkeypatch):
        monkeypatch.setattr(crash_reporter, "CRASH_LOG_DIR", tmp_path)

        # Create some fake crash files
        for i in range(3):
            (tmp_path / f"crash_2025010{i}_120000_ValueError.json").write_text(
                json.dumps({
                    "timestamp": "2025-01-01T12:00:00",
                    "exception_type": "ValueError",
                    "exception_message": "test",
                })
            )

        # Create non-crash file (should be ignored)
        (tmp_path / "other.txt").write_text("not a crash")

        crashes = crash_reporter.list_local_crashes()
        assert len(crashes) == 3
        assert all("file" in c for c in crashes)
        assert all("timestamp" in c for c in crashes)

    def test_read_local_crash(self, tmp_path, monkeypatch):
        monkeypatch.setattr(crash_reporter, "CRASH_LOG_DIR", tmp_path)

        report = {"exception_type": "KeyError", "test": "data"}
        path = tmp_path / "crash_test.json"
        path.write_text(json.dumps(report))

        loaded = crash_reporter.read_local_crash("crash_test.json")
        assert loaded == report

    def test_read_nonexistent_crash_returns_none(self, tmp_path, monkeypatch):
        monkeypatch.setattr(crash_reporter, "CRASH_LOG_DIR", tmp_path)
        result = crash_reporter.read_local_crash("nonexistent.json")
        assert result is None

    def test_delete_local_crash(self, tmp_path, monkeypatch):
        monkeypatch.setattr(crash_reporter, "CRASH_LOG_DIR", tmp_path)

        path = tmp_path / "crash_test.json"
        path.write_text("{}")

        result = crash_reporter.delete_local_crash("crash_test.json")
        assert result is True
        assert not path.exists()

    def test_delete_nonexistent_crash_returns_false(self, tmp_path, monkeypatch):
        monkeypatch.setattr(crash_reporter, "CRASH_LOG_DIR", tmp_path)
        result = crash_reporter.delete_local_crash("nonexistent.json")
        assert result is False

    def test_clear_all_crashes(self, tmp_path, monkeypatch):
        monkeypatch.setattr(crash_reporter, "CRASH_LOG_DIR", tmp_path)

        # Create 5 crash files
        for i in range(5):
            (tmp_path / f"crash_{i}.json").write_text("{}")
        # Create non-crash file (should be preserved)
        (tmp_path / "other.txt").write_text("data")

        deleted = crash_reporter.clear_all_crashes()
        assert deleted == 5
        # other.txt should still exist
        assert (tmp_path / "other.txt").exists()

    def test_clear_all_when_dir_doesnt_exist(self, tmp_path, monkeypatch):
        nonexistent = tmp_path / "nonexistent"
        monkeypatch.setattr(crash_reporter, "CRASH_LOG_DIR", nonexistent)
        result = crash_reporter.clear_all_crashes()
        assert result == 0


class TestInstallCrashHandler:

    def test_install_doesnt_raise(self, tmp_path, monkeypatch):
        """install_crash_handler should not raise even on weird environments."""
        monkeypatch.setattr(crash_reporter, "CRASH_LOG_DIR", tmp_path)
        import sys
        original_hook = sys.excepthook

        try:
            crash_reporter.install_crash_handler("1.0.0", send_reports=False)
            # sys.excepthook should be replaced
            assert sys.excepthook is not original_hook
        finally:
            sys.excepthook = original_hook

    def test_send_to_server_returns_false_on_network_error(self):
        """Server sending should fail gracefully when no network."""
        import urllib.error
        with patch("urllib.request.urlopen",
                   side_effect=urllib.error.URLError("No network")):
            result = crash_reporter._send_to_server({"test": "data"})
            assert result is False
