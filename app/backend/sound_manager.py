from __future__ import annotations

import logging
from pathlib import Path

from PySide6.QtCore import QObject, QUrl
from PySide6.QtMultimedia import QSoundEffect

logger = logging.getLogger(__name__)


class SoundManager(QObject):
    """Manages sound effects for module state changes."""

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._effects: dict[str, QSoundEffect | None] = {}
        self._enabled = True
        self._volume = 0.5
        self._load_sounds()

    def _load_sounds(self) -> None:
        """Load sound effects from resources or generate programmatically."""
        # Try to load from assets/sounds directory
        assets_dir = Path(__file__).resolve().parent.parent / "assets" / "sounds"

        sound_files: dict[str, str] = {
            "start": "start.wav",
            "stop": "stop.wav",
            "error": "error.wav",
            "panic": "panic.wav",
            "click": "click.wav",
        }

        for name, filename in sound_files.items():
            path = assets_dir / filename
            if path.exists():
                effect = QSoundEffect(self)
                effect.setSource(QUrl.fromLocalFile(str(path)))
                effect.setVolume(self._volume)
                self._effects[name] = effect
            else:
                # Create a simple synthesized tone if file doesn't exist
                self._effects[name] = None

    def play(self, name: str) -> None:
        """Play a sound effect by name."""
        if not self._enabled:
            return

        effect = self._effects.get(name)
        if effect and effect.isLoaded():
            effect.play()
        elif name == "start":
            self._beep(800, 100)
        elif name == "stop":
            self._beep(400, 100)
        elif name == "error":
            self._beep(200, 200)
        elif name == "panic":
            self._beep(1000, 300)
            # Double beep for panic
            from PySide6.QtCore import QTimer
            QTimer.singleShot(150, lambda: self._beep(800, 300))

    def _beep(self, frequency: int, duration: int) -> None:
        """Fallback: system beep using winsound on Windows."""
        import sys
        try:
            if sys.platform == "win32":
                import winsound
                winsound.Beep(frequency, duration)
            else:
                sys.stdout.write('\a')  # ASCII bell
        except (OSError, ImportError, ValueError):
            logger.debug("Failed to play system beep fallback")

    def set_enabled(self, enabled: bool) -> None:
        self._enabled = enabled

    def set_volume(self, volume: float) -> None:
        self._volume = max(0.0, min(1.0, volume))
        for effect in self._effects.values():
            if effect:
                effect.setVolume(self._volume)

    def is_enabled(self) -> bool:
        return self._enabled
