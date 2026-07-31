"""conftest.py — Корневой конфиг pytest для Shira Lab.

Содержит:
- Глобальные fixtures (qtbot, qapp — если pytest-qt установлен)
- Подавление нативных диалогов (QFileDialog, QMessageBox)
- Авто-мок Windows API для запуска на Linux/macOS CI
- Конфигурация логирования для тестов
"""
from __future__ import annotations

import os
import sys
import json
import tempfile
import platform
from pathlib import Path
from typing import Any, Iterator
from unittest.mock import MagicMock, patch

import pytest

# ============================================================
# 1. PATH SETUP
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

# Принудительный Basic style для Qt (как в main.py)
os.environ.setdefault("QT_QUICK_CONTROLS_STYLE", "Basic")
# Offscreen для CI без дисплея
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


# ============================================================
# 2. PYTEST-QT (опционально)
# ============================================================

try:
    from pytestqt.plugin import QtBot, QApplication  # noqa: F401
    HAS_PYTEST_QT = True
except ImportError:
    HAS_PYTEST_QT = False


# ============================================================
# 3. WINDOWS API MOCKS (для запуска на Linux/macOS)
# ============================================================

@pytest.fixture(autouse=True)
def _mock_win32_on_non_windows():
    """На non-Windows системах все ctypes.windll вызовы заменяются моками.

    Использует setattr(create=True) потому что на Linux/macOS ctypes
    вообще не имеет атрибута windll — patch() без create падает.
    """
    if platform.system() == "Windows":
        yield
        return

    # Создаём фейковый ctypes.windll
    fake_dlls = {
        "user32": MagicMock(name="user32"),
        "kernel32": MagicMock(name="kernel32"),
        "dwmapi": MagicMock(name="dwmapi"),
        "gdi32": MagicMock(name="gdi32"),
    }

    class _FakeWinDLL:
        def __getattr__(self, name: str):
            if name in fake_dlls:
                return fake_dlls[name]
            return MagicMock(name=f"windll.{name}")

    import ctypes
    original_windll = getattr(ctypes, "windll", None)
    ctypes.windll = _FakeWinDLL()
    try:
        yield
    finally:
        if original_windll is not None:
            ctypes.windll = original_windll
        else:
            try:
                delattr(ctypes, "windll")
            except AttributeError:
                pass


# ============================================================
# 4. TEMP PROFILE FIXTURE
# ============================================================

@pytest.fixture
def tmp_profile(tmp_path: Path) -> Path:
    """Временный profile.json для тестов persistence."""
    profile_path = tmp_path / "profile.json"
    profile_path.write_text("{}", encoding="utf-8")
    return profile_path


@pytest.fixture
def tmp_records_dir(tmp_path: Path) -> Path:
    """Временная директория для записей recorder."""
    d = tmp_path / "records"
    d.mkdir(parents=True, exist_ok=True)
    return d


# ============================================================
# 5. MOCK SERVICES
# ============================================================

@pytest.fixture
def mock_clicker() -> MagicMock:
    """Mock ClickerService для изоляции bridge тестов."""
    m = MagicMock(name="ClickerService")
    m.get_status.return_value = {
        "running": False,
        "interval_ms": 100,
        "hold_ms": 30,
        "button": "left",
        "limit": 0,
        "count": 0,
        "background_method": "sendinput",
    }
    m.start.return_value = {"ok": True, "running": True}
    m.stop.return_value = {"ok": True, "running": False}
    m.update_config.return_value = {"ok": True}
    return m


@pytest.fixture
def mock_macro() -> MagicMock:
    m = MagicMock(name="MacroService")
    m.get_status.return_value = {
        "running": False,
        "actions": [],
        "run_mode": "sequential",
        "background_method": "sendinput",
    }
    m.add_action.return_value = {"ok": True, "count": 1}
    m.start.return_value = {"ok": True, "running": True}
    m.stop.return_value = {"ok": True, "running": False}
    return m


@pytest.fixture
def mock_recorder() -> MagicMock:
    m = MagicMock(name="RecorderService")
    m.status.return_value = {
        "recording": False,
        "playing": False,
        "records": [],
    }
    m.start_recording.return_value = {"ok": True, "recording": True}
    m.stop_recording.return_value = {"ok": True, "recording": False}
    return m


@pytest.fixture
def mock_aim() -> MagicMock:
    m = MagicMock(name="AimService")
    m.get_status.return_value = {
        "running": False,
        "confidence": 0.7,
        "smooth_steps": 5,
        "reset_delay": 200,
        "detection_mode": "auto",
        "background_method": "sendinput",
    }
    m.start.return_value = {"ok": True, "running": True}
    m.stop.return_value = {"ok": True, "running": False}
    return m


# ============================================================
# 6. APPLICATION FIXTURES
# ============================================================

@pytest.fixture(scope="session")
def qapp():
    """QApplication для QML тестов (используется pytest-qt)."""
    if not HAS_PYTEST_QT:
        pytest.skip("pytest-qt не установлен: pip install pytest-qt")
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication([])
    yield app


@pytest.fixture
def qtbot(qapp):
    """QtBot fixture (если pytest-qt установлен)."""
    if not HAS_PYTEST_QT:
        pytest.skip("pytest-qt не установлен")
    from pytestqt.plugin import QtBot
    bot = QtBot(qapp)
    yield bot


# ============================================================
# 7. LOGGER FIXTURE
# ============================================================

@pytest.fixture(autouse=True)
def _configure_logging():
    """Тихий логгер для тестов (только WARNING+)."""
    import logging
    logging.basicConfig(level=logging.WARNING)
    logging.getLogger("PySide6").setLevel(logging.ERROR)
    yield


# ============================================================
# 8. HELPERS
# ============================================================

def parse_json(result: Any) -> Any:
    """Хелпер: парсить JSON-ответы @Slot(result=str) методов bridge."""
    if isinstance(result, str):
        return json.loads(result)
    return result


@pytest.fixture
def j():
    """Парсер JSON-ответов bridge для тестов."""
    return parse_json
