"""tests/conftest.py — Дополнительные fixtures уровня tests/.

Импортируется автоматически pytest для всех тестов в tests/.
"""

from __future__ import annotations

import pytest


@pytest.fixture
def bridge(monkeypatch, tmp_path):
    """Полноценный QmlBridge с замоканными win32 и persistence.

    Используется для integration и bridge-тестов.
    """
    # Замокаем persistence чтобы не писать в реальный profile.json
    monkeypatch.setattr("app.backend.persistence.save_profile", lambda *a, **kw: None)
    monkeypatch.setattr("app.backend.persistence.load_profile", lambda *a, **kw: None)

    try:
        from app.backend.bridges import QmlBridge
    except ImportError:
        # Если bridges/ ещё не создан — fallback на старый qml_bridge
        try:
            from app.backend.qml_bridge import QmlBridge
        except ImportError:
            pytest.skip("QmlBridge недоступен (требует Windows API или рефакторинг)")

    try:
        b = QmlBridge()
        yield b
        # Cleanup
        try:
            b.hotkeys.shutdown()
        except (OSError, RuntimeError, AttributeError):
            pass
    except (ImportError, RuntimeError, AttributeError, OSError) as e:
        pytest.skip(f"Не удалось создать QmlBridge: {e}")


@pytest.fixture
def sample_hotkeys():
    """Стандартный набор горячих клавиш для тестов."""
    return {
        "clicker_toggle": {"key": "f6", "mode": "TOGGLE"},
        "aim_toggle": {"key": "f7", "mode": "TOGGLE"},
        "macro_start": {"key": "f8", "mode": "HOLD"},
        "macro_stop": {"key": "f9", "mode": "TOGGLE"},
        "recorder_start": {"key": "f10", "mode": "TOGGLE"},
        "panic_stop": {"key": "ctrl+shift+p", "mode": "TOGGLE"},
    }


@pytest.fixture
def sample_macro_actions():
    """Список макро-действий для тестов."""
    return [
        {"key": "a", "delay": 0.05, "hold": 0.03},
        {"key": "b", "delay": 0.10, "hold": 0.05},
        {"key": "c", "delay": 0.15, "hold": 0.08},
    ]
