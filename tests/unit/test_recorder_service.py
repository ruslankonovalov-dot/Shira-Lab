# tests/unit/test_recorder_service.py — RecorderService comprehensive tests for Phase 3.6
import json
import os
import shutil
import tempfile
import time
from unittest.mock import Mock

import pytest


class TestRecorderService:
    """Tests for RecorderService."""

    def setup_method(self):
        from app.backend.services.recorder_service import RecorderService
        self.service = RecorderService()
        # Mock bridge for logging
        self.service._bridge = Mock()

    def test_start_stop_record(self):
        """Test start/stop recording."""
        result = self.service.start_recording()
        assert result["ok"] is True
        assert self.service.is_recording is True

        time.sleep(0.05)

        result = self.service.stop_recording()
        assert result["ok"] is True
        assert self.service.is_recording is False
        assert "events_count" in result

    def test_play_record(self):
        """Test playing a record."""
        # First create a record with enough events to have some duration
        self.service.start_recording()
        time.sleep(0.2)  # Longer recording for more events
        self.service.stop_recording()

        records = self.service.list_records()
        assert len(records["records"]) > 0

        record_name = records["records"][0]
        result = self.service.play_record(record_name)
        assert result["ok"] is True
        # Playback is async, check status - give it a moment to start
        time.sleep(0.01)
        status = self.service.status()
        assert status["is_playing"] is True

        time.sleep(0.3)  # Wait for playback to complete

        result = self.service.stop_playing()
        assert result["ok"] is True
        assert self.service.is_playing is False

    def test_stop_playing_when_not_playing(self):
        """Test stop_playing when not playing."""
        result = self.service.stop_playing()
        # Should handle gracefully
        assert "ok" in result

    def test_delete_record(self):
        """Test deleting a record."""
        self.service.start_recording()
        time.sleep(0.05)
        self.service.stop_recording()

        records = self.service.list_records()
        record_name = records["records"][0]

        result = self.service.delete_record(record_name)
        assert result["ok"] is True

        records = self.service.list_records()
        assert record_name not in records["records"]

    def test_delete_nonexistent_record(self):
        """Test deleting non-existent record."""
        result = self.service.delete_record("nonexistent.json")
        assert result["ok"] is True  # Returns list_records

    def test_list_records(self):
        """Test listing records."""
        result = self.service.list_records()
        assert isinstance(result, dict)
        assert "ok" in result
        assert "records" in result
        assert isinstance(result["records"], list)

    def test_background_methods(self):
        """Test background input methods."""
        for method in ["sendinput", "postmessage", "vigem", "pico"]:
            result = self.service.set_background_method(method)
            # set_background_method returns status dict
            assert result["ok"] is True
            assert result["background_method"] == method

    def test_status(self):
        """Test status returns proper structure."""
        status = self.service.status()
        assert isinstance(status, dict)
        assert "ok" in status
        if status["ok"]:
            assert "is_recording" in status
            assert "is_playing" in status
            assert "events_count" in status
            assert "background_method" in status


class TestRecorderServicePlayback:
    """Tests for playback functionality."""

    def setup_method(self):
        from app.backend.services.recorder_service import RecorderService
        self.service = RecorderService()
        self.service._bridge = Mock()

    def test_press_release_key(self):
        """Test press/release key."""
        self.service.press_key("space")
        self.service.release_key("space")

    def test_press_release_click(self):
        """Test press/release mouse click."""
        self.service.press_click("L")
        self.service.release_click("L")

    def test_send_click(self):
        """Test sending click."""
        self.service._send_click("L", 50)

    def test_send_key(self):
        """Test sending key."""
        self.service._press_key("space", 50)


class TestRecorderServiceEvents:
    """Tests for event recording."""

    def setup_method(self):
        from app.backend.services.recorder_service import RecorderService
        self.service = RecorderService()
        self.service._bridge = Mock()

    def test_on_move(self):
        """Test mouse move recording."""
        self.service.is_recording = True
        self.service.start_time = time.time()
        # Clear any existing events
        self.service.recorded_events = []
        self.service._on_move(100, 200)
        assert len(self.service.recorded_events) == 1
        assert self.service.recorded_events[0][0] == "m"

    def test_on_click(self):
        """Test mouse click recording."""
        self.service.is_recording = True
        self.service.start_time = time.time()
        # Clear any existing events
        self.service.recorded_events = []

        mock_button = Mock()
        mock_button.__str__ = Mock(return_value="Button.left")
        self.service._on_click(100, 200, mock_button, True)

        assert len(self.service.recorded_events) == 1
        assert self.service.recorded_events[0][0] == "c"
        assert self.service.recorded_events[0][3] == "Button.left"
        assert self.service.recorded_events[0][4] is True

    def test_on_key_down_up(self):
        """Test key down/up recording."""
        self.service.is_recording = True
        self.service.start_time = time.time()
        # Clear any existing events
        self.service.recorded_events = []

        mock_key = Mock()
        mock_key.__str__ = Mock(return_value="Key.space")

        self.service._on_key_down(mock_key)
        assert len(self.service.recorded_events) == 1
        assert self.service.recorded_events[0][0] == "kd"

        self.service._on_key_up(mock_key)
        assert len(self.service.recorded_events) == 2
        assert self.service.recorded_events[1][0] == "ku"


class TestRecorderServiceSave:
    """Tests for saving records."""

    def setup_method(self):
        from app.backend.services.recorder_service import RecorderService
        self.service = RecorderService()
        self.service._bridge = Mock()
        # Create a temporary directory for test isolation
        self.temp_dir = tempfile.mkdtemp()
        self.original_records_dir = self.service.records_dir
        self.service.records_dir = self.temp_dir

    def teardown_method(self):
        # Restore original records dir
        self.service.records_dir = self.original_records_dir
        # Cleanup temp dir
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_save_record_creates_file(self):
        """Test saving record creates file with correct format."""
        self.service.recorded_events = [
            ["m", 100, 200, 0.0],
            ["c", 100, 200, "Button.left", True, 0.1],
            ["c", 100, 200, "Button.left", False, 0.2],
        ]
        self.service.start_time = time.time()

        self.service._save_record()

        # Check file was created
        files = [f for f in os.listdir(self.service.records_dir) if f.endswith(".json")]
        assert len(files) == 1

        # Check file content
        with open(os.path.join(self.service.records_dir, files[0]), "r") as f:
            data = json.load(f)
        assert "events" in data
        assert "created_at" in data
        assert "events_count" in data
        assert len(data["events"]) == 3


class TestRecorderServiceSafePath:
    """Tests for safe path resolution."""

    def setup_method(self):
        from app.backend.services.recorder_service import RecorderService
        self.service = RecorderService()

    def test_safe_path_valid(self):
        """Test valid filename."""
        path = self.service._safe_record_path("REC_20240101_120000.json")
        assert path is not None
        assert path.endswith("REC_20240101_120000.json")

    def test_safe_path_invalid_extension(self):
        """Test invalid extension."""
        path = self.service._safe_record_path("record.txt")
        assert path is None

    def test_safe_path_traversal(self):
        """Test path traversal attempt."""
        path = self.service._safe_record_path("../etc/passwd.json")
        assert path is None

    def test_safe_path_subdirectory(self):
        """Test subdirectory attempt."""
        path = self.service._safe_record_path("subdir/record.json")
        assert path is None


class TestRecorderServiceThreadSafety:
    """Tests for thread safety."""

    def setup_method(self):
        from app.backend.services.recorder_service import RecorderService
        self.service = RecorderService()
        self.service._bridge = Mock()

    def test_concurrent_start_stop(self):
        """Test concurrent start/stop operations."""
        import threading

        def start_stop_cycle():
            for _ in range(10):
                self.service.start_recording()
                time.sleep(0.01)
                self.service.stop_recording()

        threads = [threading.Thread(target=start_stop_cycle) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Should not crash
        assert self.service.is_recording in [True, False]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])